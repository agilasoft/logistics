"""
Enhanced periodic billing with volume-based calculations.
"""

import frappe
from frappe import _
from frappe.utils import flt
from typing import Dict, List, Optional, Any
from logistics.warehousing.api_parts.volume_billing import create_volume_based_charge_line


def periodic_billing_get_volume_charges(periodic_billing: str, clear_existing: int = 1) -> Dict[str, Any]:
    """
    Enhanced periodic billing function that supports volume-based billing.
    """
    pb = frappe.get_doc("Periodic Billing", periodic_billing)
    customer = getattr(pb, "customer", None)
    date_from = getattr(pb, "date_from", None)
    date_to = getattr(pb, "date_to", None)
    
    if not (customer and date_from and date_to):
        frappe.throw(_("Customer, Date From and Date To are required."))

    charges_field = _pb__charges_fieldname()
    if not charges_field:
        return {"ok": False, "message": _("Periodic Billing has no child table for 'Periodic Billing Charges'. Add one."), "created": 0}

    if int(clear_existing or 0):
        pb.set(charges_field, [])

    warnings: List[str] = []
    created = 0
    grand_total = 0.0

    # Process existing job charges (unchanged)
    jobs = frappe.get_all(
        "Warehouse Job",
        filters={"docstatus": 1, "customer": customer, "job_open_date": ["between", [date_from, date_to]]},
        fields=["name", "job_open_date"],
        order_by="job_open_date asc, name asc",
        ignore_permissions=True,
    ) or []
    
    if jobs:
        job_names = [j["name"] for j in jobs]
        placeholders = ", ".join(["%s"] * len(job_names))
        rows = frappe.db.sql(
            f"""SELECT c.parent AS warehouse_job, c.item_code, c.item_name, c.uom, c.quantity, c.rate, c.total, c.currency, c.billing_method, c.volume_quantity, c.volume_uom
                FROM `tabWarehouse Job Charges` c
                WHERE c.parent IN ({placeholders})
                ORDER BY FIELD(c.parent, {placeholders})""",
            tuple(job_names + job_names), as_dict=True,
        ) or []
        
        for r in rows:
            qty = flt(r.get("quantity") or 0.0)
            rate = flt(r.get("rate") or 0.0)
            total = flt(r.get("total") or (qty * rate))
            
            charge_line = {
                "item": r.get("item_code"),
                "item_name": r.get("item_name"),
                "uom": r.get("uom"),
                "quantity": qty,
                "rate": rate,
                "total": total,
                "currency": r.get("currency"),
                "warehouse_job": r.get("warehouse_job"),
                "billing_method": r.get("billing_method", "Per Day"),
            }
            
            # Add volume-specific fields if present
            if r.get("billing_method") == "Per Volume":
                charge_line.update({
                    "volume_quantity": flt(r.get("volume_quantity", 0)),
                    "volume_uom": r.get("volume_uom")
                })
            
            pb.append(charges_field, charge_line)
            created += 1
            grand_total += total

    # Enhanced storage charges with volume-based billing
    contract = _pb__find_customer_contract(customer)
    hu_list = _pb__distinct_hus_for_customer(customer, date_to)
    
    if not hu_list:
        warnings.append(_("No handling units found for this customer; storage charges skipped."))
    else:
        # Track missing rates for warning
        missing_rates = set()
        
        for hu in hu_list:
            # Get storage location for this handling unit (excluding staging locations)
            storage_location = None
            if hu:
                rows = frappe.db.sql("""
                    SELECT 
                        l.storage_location,
                        COUNT(*) as day_count,
                        SUM(ABS(l.quantity)) as total_movement
                    FROM `tabWarehouse Stock Ledger` l
                    LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
                    WHERE l.handling_unit = %s 
                      AND l.posting_date BETWEEN %s AND %s
                      AND l.storage_location IS NOT NULL
                      AND (sl.staging_area = 0 OR sl.staging_area IS NULL)
                    GROUP BY l.storage_location
                    ORDER BY day_count DESC, total_movement DESC
                    LIMIT 1
                """, (hu, date_from, date_to), as_dict=True)
                if rows:
                    storage_location = rows[0]["storage_location"]
            
            # Get handling unit type and storage type
            hu_type = frappe.db.get_value("Handling Unit", hu, "type") if hu else None
            storage_type = frappe.db.get_value("Storage Location", storage_location, "storage_type") if storage_location else None
            
            # If no non-staging storage location found, check if handling unit was only in staging areas
            if not storage_location and hu:
                staging_rows = frappe.db.sql("""
                    SELECT l.storage_location
                    FROM `tabWarehouse Stock Ledger` l
                    LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
                    WHERE l.handling_unit = %s 
                      AND l.posting_date BETWEEN %s AND %s
                      AND l.storage_location IS NOT NULL
                      AND (sl.staging_area = 1)
                    LIMIT 1
                """, (hu, date_from, date_to), as_dict=True)
                if staging_rows:
                    storage_location = staging_rows[0]["storage_location"]
            
            # Find matching contract item with enhanced billing method support
            sci = None
            if contract:
                # Try exact match first (handling_unit_type + storage_type)
                if hu_type and storage_type:
                    rows = frappe.db.sql("""
                        SELECT item_charge AS item_code, rate, currency, billing_time_unit, billing_time_multiplier, minimum_billing_time, handling_unit_type, storage_type, billing_method, volume_uom, volume_calculation_method
                        FROM `tabWarehouse Contract Item`
                        WHERE parent = %s AND parenttype = 'Warehouse Contract' AND storage_charge = 1
                        AND handling_unit_type = %s AND storage_type = %s
                        LIMIT 1
                    """, (contract, hu_type, storage_type), as_dict=True)
                    if rows:
                        sci = rows[0]
                
                # Try handling_unit_type only
                if not sci and hu_type:
                    rows = frappe.db.sql("""
                        SELECT item_charge AS item_code, rate, currency, billing_time_unit, billing_time_multiplier, minimum_billing_time, handling_unit_type, storage_type, billing_method, volume_uom, volume_calculation_method
                        FROM `tabWarehouse Contract Item`
                        WHERE parent = %s AND parenttype = 'Warehouse Contract' AND storage_charge = 1
                        AND handling_unit_type = %s AND (storage_type IS NULL OR storage_type = '')
                        LIMIT 1
                    """, (contract, hu_type), as_dict=True)
                    if rows:
                        sci = rows[0]
                
                # Try storage_type only
                if not sci and storage_type:
                    rows = frappe.db.sql("""
                        SELECT item_charge AS item_code, rate, currency, billing_time_unit, billing_time_multiplier, minimum_billing_time, handling_unit_type, storage_type, billing_method, volume_uom, volume_calculation_method
                        FROM `tabWarehouse Contract Item`
                        WHERE parent = %s AND parenttype = 'Warehouse Contract' AND storage_charge = 1
                        AND storage_type = %s AND (handling_unit_type IS NULL OR handling_unit_type = '')
                        LIMIT 1
                    """, (contract, storage_type), as_dict=True)
                    if rows:
                        sci = rows[0]
                
                # Fallback to generic storage charge
                if not sci:
                    rows = frappe.db.sql("""
                        SELECT item_charge AS item_code, rate, currency, billing_time_unit, billing_time_multiplier, minimum_billing_time, handling_unit_type, storage_type, billing_method, volume_uom, volume_calculation_method
                        FROM `tabWarehouse Contract Item`
                        WHERE parent = %s AND parenttype = 'Warehouse Contract' AND storage_charge = 1
                        AND (handling_unit_type IS NULL OR handling_unit_type = '')
                        AND (storage_type IS NULL OR storage_type = '')
                        LIMIT 1
                    """, (contract,), as_dict=True)
                    if rows:
                        sci = rows[0]
            
            if not sci:
                # Track missing rates for warning
                missing_rates.add(f"HU Type: {hu_type or 'Unknown'}, Storage Type: {storage_type or 'Unknown'}")
                continue
            
            # Create charge line based on billing method
            billing_method = sci.get("billing_method", "Per Day")
            
            if billing_method == "Per Volume":
                # Use volume-based calculation
                charge_line = create_volume_based_charge_line(
                    hu, date_from, date_to, sci, storage_location
                )
            else:
                # Use existing day-based calculation
                days = _pb__count_used_days(hu, date_from, date_to)
                if days <= 0:
                    continue
                
                charge_line = {
                    "item": sci.get("item_code"),
                    "item_name": _("Storage Charge ({0})").format(hu_type or "Generic"),
                    "uom": sci.get("billing_time_unit") or "Day",
                    "quantity": days,
                    "rate": flt(sci.get("rate") or 0.0),
                    "total": flt(days) * flt(sci.get("rate") or 0.0),
                    "currency": sci.get("currency"),
                    "handling_unit": hu,
                    "storage_location": storage_location,
                    "handling_unit_type": hu_type,
                    "storage_type": storage_type,
                    "billing_method": billing_method
                }
            
            pb.append(charges_field, charge_line)
            created += 1
            grand_total += flt(charge_line.get("total", 0))
        
        # Add warnings for missing rates
        if missing_rates:
            warning_msg = _("No storage rates defined for: {0}").format("; ".join(missing_rates))
            warnings.append(warning_msg)

    pb.save(ignore_permissions=True)
    frappe.db.commit()
    msg = _("Added {0} charge line(s). Total: {1}").format(int(created), flt(grand_total))
    if warnings:
        msg += " " + _("Notes") + ": " + " | ".join(warnings)
    return {"ok": True, "message": msg, "created": int(created), "grand_total": flt(grand_total), "warnings": warnings}


# Import required functions from the main API
from logistics.warehousing.api import _pb__charges_fieldname, _pb__find_customer_contract, _pb__distinct_hus_for_customer, _pb__count_used_days

