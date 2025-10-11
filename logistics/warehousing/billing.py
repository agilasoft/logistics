"""
Warehouse Billing System

This module provides comprehensive billing functionality for warehouse operations,
including periodic billing, storage charges, and job charges.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta


@frappe.whitelist()
def periodic_billing_get_charges(periodic_billing: str, clear_existing: int = 1) -> Dict[str, Any]:
    """
    Generate billing charges for periodic billing.
    
    This function processes both warehouse job charges and storage charges
    based on the contract setup and handling units.
    """
    try:
        # Get periodic billing document
        pb = frappe.get_doc("Periodic Billing", periodic_billing)
        customer = getattr(pb, "customer", None)
        date_from = str(getattr(pb, "date_from", None)) if getattr(pb, "date_from", None) else None
        date_to = str(getattr(pb, "date_to", None)) if getattr(pb, "date_to", None) else None
        warehouse_contract = getattr(pb, "warehouse_contract", None)
        company = getattr(pb, "company", None)
        branch = getattr(pb, "branch", None)
        
        # Validate required fields
        if not (customer and date_from and date_to):
            frappe.throw(_("Customer, Date From and Date To are required."))

        # Clear existing charges if requested
        if int(clear_existing or 0):
            pb.set("charges", [])

        warnings = []
        created = 0
        grand_total = 0.0
        
        # Step 1: Process Warehouse Job Charges
        # First, try to get existing charges from warehouse_job_charges table
        job_charges_created, job_total, job_warnings = get_existing_warehouse_job_charges(
            customer, date_from, date_to, company, branch
        )
        
        # If no existing charges found and we have a contract, generate contract-based charges
        if not job_charges_created and warehouse_contract:
            from logistics.warehousing.charges import get_warehouse_job_charges_with_contract
            contract_charges, contract_total, contract_warnings = get_warehouse_job_charges_with_contract(
                customer, date_from, date_to, warehouse_contract, company, branch
            )
            job_charges_created.extend(contract_charges)
            job_total += contract_total
            job_warnings.extend(contract_warnings)
        
        # If still no charges, generate basic job charges
        if not job_charges_created:
            basic_charges, basic_total, basic_warnings = get_warehouse_job_charges(
                customer, date_from, date_to, company, branch
            )
            job_charges_created.extend(basic_charges)
            job_total += basic_total
            job_warnings.extend(basic_warnings)
        
        for charge in job_charges_created:
            pb.append("charges", charge)
            created += 1
            grand_total += flt(charge.get("total", 0))
        
        warnings.extend(job_warnings)
        
        # Step 2: Process Storage Charges (if contract specified)
        if warehouse_contract:
            storage_charges_created, storage_total, storage_warnings = get_storage_charges_from_contract(
                customer, date_from, date_to, warehouse_contract, company, branch
            )
            
            for charge in storage_charges_created:
                pb.append("charges", charge)
                created += 1
                grand_total += flt(charge.get("total", 0))
            
            warnings.extend(storage_warnings)
        else:
            warnings.append(_("No warehouse contract specified. Only job charges will be processed."))
        
        # Step 3: Save and return results
        if created > 0:
            pb.save(ignore_permissions=True)
            frappe.db.commit()
        
        msg = _("Added {0} charge line(s). Total: {1}").format(int(created), flt(grand_total))
        if warnings:
            msg += " " + _("Notes") + ": " + " | ".join(warnings)
        
        return {"ok": True, "message": msg, "created": int(created), "grand_total": flt(grand_total), "warnings": warnings}
        
    except Exception as e:
        frappe.log_error(f"Periodic billing error: {str(e)}")
        return {"ok": False, "message": str(e), "created": 0, "grand_total": 0.0, "warnings": []}


def get_existing_warehouse_job_charges(customer: str, date_from: str, date_to: str, company: Optional[str] = None, branch: Optional[str] = None) -> Tuple[List[Dict], float, List[str]]:
    """Get existing warehouse job charges from the warehouse_job_charges table."""
    charges = []
    total = 0.0
    warnings = []
    
    try:
        # Get warehouse jobs for the customer in the date range
        job_filters = {
            "docstatus": 1, 
            "customer": customer, 
            "job_open_date": ["between", [date_from, date_to]]
        }
        
        if company:
            job_filters["company"] = company
        if branch:
            job_filters["branch"] = branch

        jobs = frappe.get_all(
            "Warehouse Job",
            filters=job_filters,
            fields=["name", "job_open_date"],
            order_by="job_open_date asc, name asc",
            ignore_permissions=True,
        ) or []
        
        # Get existing charges for each job
        for job in jobs:
            job_charges = frappe.get_all(
                "Warehouse Job Charges",
                filters={"parent": job.name, "parenttype": "Warehouse Job"},
                fields=["item_code", "item_name", "uom", "quantity", "rate", "total", "currency", "calculation_notes"],
                ignore_permissions=True,
            ) or []
            
            for charge in job_charges:
                charges.append({
                    "item": charge.get("item_code"),
                    "item_name": charge.get("item_name"),
                    "uom": charge.get("uom"),
                    "quantity": flt(charge.get("quantity", 0)),
                    "rate": flt(charge.get("rate", 0)),
                    "total": flt(charge.get("total", 0)),
                    "currency": charge.get("currency", "PHP"),
                    "warehouse_job": job.name,
                    "calculation_notes": charge.get("calculation_notes", "Existing warehouse job charge")
                })
                total += flt(charge.get("total", 0))
        
    except Exception as e:
        warnings.append(f"Error fetching existing warehouse job charges: {str(e)}")
    
    return charges, total, warnings


def get_warehouse_job_charges(customer: str, date_from: str, date_to: str, company: Optional[str] = None, branch: Optional[str] = None) -> Tuple[List[Dict], float, List[str]]:
    """Get warehouse job charges for the billing period."""
    charges = []
    total = 0.0
    warnings = []
    
    try:
        # Get warehouse jobs for the customer in the date range
        filters = {
            "docstatus": 1, 
            "customer": customer, 
            "job_open_date": ["between", [date_from, date_to]]
        }
        
        if company:
            filters["company"] = company
        if branch:
            filters["branch"] = branch

        jobs = frappe.get_all(
            "Warehouse Job",
            filters=filters,
            fields=["name", "job_open_date"],
            order_by="job_open_date asc, name asc",
            ignore_permissions=True,
        ) or []
        
        # Generate charges for each job based on job activity
        for job in jobs:
            # Get job details
            job_doc = frappe.get_doc("Warehouse Job", job.name)
            
            # Calculate billing quantity based on job activity
            # For now, use a simple per-day calculation
            job_open_date = job.get("job_open_date")
            if job_open_date:
                start_date = datetime.strptime(str(job_open_date), "%Y-%m-%d")
                end_date = datetime.strptime(str(date_to), "%Y-%m-%d")
                days = (end_date - start_date).days + 1
            else:
                days = 1
            
            # Create a basic charge for the job
            # This should be enhanced to use contract rates if available
            charge = {
                "item": "WAREHOUSE-JOB-SERVICE",  # Default item
                "item_name": "Warehouse Job Service",
                "uom": "Day",
                "quantity": float(days),
                "rate": 100.0,  # Default rate - should come from contract
                "total": float(days) * 100.0,
                "currency": "PHP",
                "warehouse_job": job.name,
                "calculation_notes": f"""Warehouse Job Charge:
  • Job: {job.name}
  • Period: {job_open_date} to {date_to}
  • Days: {days}
  • Rate: 100.0 per day
  • Total: {days} × 100.0 = {float(days) * 100.0}"""
            }
            
            charges.append(charge)
            total += charge["total"]
        
    except Exception as e:
        warnings.append(f"Error processing warehouse job charges: {str(e)}")
    
    return charges, total, warnings


def get_storage_charges_from_contract(customer: str, date_from: str, date_to: str, warehouse_contract: str, company: Optional[str] = None, branch: Optional[str] = None) -> Tuple[List[Dict], float, List[str]]:
    """Get storage charges based on contract setup."""
    charges = []
    total = 0.0
    warnings = []
    
    try:
        # Get handling units for the customer
        hu_list = get_customer_handling_units(customer, date_to, company, branch)
        
        if not hu_list:
            warnings.append(_("No handling units found for this customer; storage charges skipped."))
            return charges, total, warnings
        
        # Get contract items
        contract_items = frappe.db.sql("""
            SELECT 
                item_charge AS item_code, rate, currency, uom, 
                handling_unit_type, storage_type, unit_type, storage_charge
            FROM `tabWarehouse Contract Item`
            WHERE parent = %s AND parenttype = 'Warehouse Contract' AND storage_charge = 1
            ORDER BY handling_unit_type, storage_type
        """, (warehouse_contract,), as_dict=True)
        
        frappe.logger().info(f"DEBUG: Found {len(contract_items)} contract items: {contract_items}")
        
        if not contract_items:
            warnings.append(_("No storage charge items found in contract."))
            return charges, total, warnings
        
        # Process each handling unit
        for hu in hu_list:
            hu_details = get_handling_unit_billing_details(hu, date_from, date_to)
            if not hu_details:
                continue
                
            # Find matching contract item
            contract_item = find_matching_contract_item(contract_items, hu_details)
            if not contract_item:
                continue
                
            # Calculate charges
            hu_charges = calculate_handling_unit_storage_charges(hu, hu_details, contract_item, date_from, date_to)
            charges.extend(hu_charges)
            total += sum(flt(charge.get("total", 0)) for charge in hu_charges)
        
    except Exception as e:
        warnings.append(f"Error getting storage charges from contract: {str(e)}")
    
    return charges, total, warnings


def get_customer_handling_units(customer: str, date_to: str, company: Optional[str] = None, branch: Optional[str] = None) -> List[str]:
    """Get distinct handling units for a customer."""
    try:
        # Get handling units from Warehouse Stock Ledger via Warehouse Item
        hu_data = frappe.db.sql("""
            SELECT DISTINCT l.handling_unit
            FROM `tabWarehouse Stock Ledger` l
            LEFT JOIN `tabWarehouse Item` wi ON wi.name = l.item
            WHERE wi.customer = %s 
              AND DATE(l.posting_date) <= %s 
              AND l.handling_unit IS NOT NULL
            ORDER BY l.handling_unit
        """, (customer, date_to), as_dict=True)
        
        return [row["handling_unit"] for row in hu_data if row["handling_unit"]]
        
    except Exception as e:
        frappe.log_error(f"Error getting handling units for customer {customer}: {str(e)}")
        return []


def get_handling_unit_billing_details(hu: str, date_from: str, date_to: str) -> Dict[str, Any]:
    """Get comprehensive billing details for a handling unit."""
    try:
        # Get handling unit type
        hu_type = frappe.db.get_value("Handling Unit", hu, "type") if hu else None
        
        # Get storage location (excluding staging)
        storage_location = None
        storage_type = None
        
        if hu:
            rows = frappe.db.sql("""
                SELECT 
                    l.storage_location,
                    COUNT(*) as day_count,
                    SUM(ABS(l.quantity)) as total_movement
                FROM `tabWarehouse Stock Ledger` l
                LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
                WHERE l.handling_unit = %s 
                  AND DATE(l.posting_date) BETWEEN %s AND %s
                  AND l.storage_location IS NOT NULL
                  AND (sl.staging_area = 0 OR sl.staging_area IS NULL)
                GROUP BY l.storage_location
                ORDER BY day_count DESC, total_movement DESC
                LIMIT 1
            """, (hu, date_from, date_to), as_dict=True)
            
            if rows:
                storage_location = rows[0]["storage_location"]
                storage_type = frappe.db.get_value("Storage Location", storage_location, "storage_type")
        
        # Check if only in staging areas
        if not storage_location and hu:
            staging_check = frappe.db.sql("""
                SELECT COUNT(*) as staging_days
                FROM `tabWarehouse Stock Ledger` l
                LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
                WHERE l.handling_unit = %s 
                  AND DATE(l.posting_date) BETWEEN %s AND %s
                  AND l.storage_location IS NOT NULL
                  AND sl.staging_area = 1
            """, (hu, date_from, date_to), as_dict=True)
            
            if staging_check and staging_check[0]["staging_days"] > 0:
                return None  # Skip staging-only handling units
        
        return {
            "handling_unit": hu,
            "handling_unit_type": hu_type,
            "storage_location": storage_location,
            "storage_type": storage_type,
            "date_from": date_from,
            "date_to": date_to,
            "total_volume": 0.0,
            "total_weight": 0.0
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting handling unit details for {hu}: {str(e)}")
        return None


def find_matching_contract_item(contract_items: List[Dict], hu_details: Dict) -> Dict[str, Any]:
    """Find the best matching contract item for a handling unit."""
    hu_type = hu_details.get("handling_unit_type")
    storage_type = hu_details.get("storage_type")
    
    # Try exact match first (both handling_unit_type and storage_type)
    if hu_type and storage_type:
        for item in contract_items:
            if (item.get("handling_unit_type") == hu_type and 
                item.get("storage_type") == storage_type and 
                item.get("storage_charge")):
                return item
    
    # Try handling_unit_type only
    if hu_type:
        for item in contract_items:
            if (item.get("handling_unit_type") == hu_type and 
                not item.get("storage_type") and 
                item.get("storage_charge")):
                return item
    
    # Try storage_type only
    if storage_type:
        for item in contract_items:
            if (not item.get("handling_unit_type") and 
                item.get("storage_type") == storage_type and 
                item.get("storage_charge")):
                return item
    
    # Fallback to generic storage charge
    for item in contract_items:
        if (not item.get("handling_unit_type") and 
            not item.get("storage_type") and 
            item.get("storage_charge")):
            return item
    
    return None


def calculate_handling_unit_storage_charges(hu: str, hu_details: Dict, contract_item: Dict, date_from: str, date_to: str) -> List[Dict]:
    """Calculate storage charges for a handling unit."""
    charges = []
    
    try:
        # Calculate billing quantity based on unit type
        unit_type = contract_item.get("unit_type", "Day")
        billing_quantity = calculate_billing_quantity_for_method(unit_type, hu_details, date_from, date_to)
        
        if billing_quantity <= 0:
            return charges
        
        rate = flt(contract_item.get("rate", 0))
        total = billing_quantity * rate
        
        # Create charge line
        item_code = contract_item.get("item_code")
        frappe.logger().info(f"DEBUG: Creating charge with item_code: {item_code}")
        
        charge = {
            "item": item_code,
            "item_name": _("Storage Charge ({0})").format(hu_details.get("handling_unit_type") or "Generic"),
            "uom": contract_item.get("uom", "Day"),
            "quantity": billing_quantity,
            "rate": rate,
            "total": total,
            "currency": contract_item.get("currency", "PHP"),
            "handling_unit": hu,
            "storage_location": hu_details.get("storage_location"),
            "handling_unit_type": hu_details.get("handling_unit_type"),
            "storage_type": hu_details.get("storage_type"),
            "calculation_notes": generate_storage_calculation_notes(hu, hu_details, contract_item, billing_quantity, rate, date_from, date_to)
        }
        
        charges.append(charge)
        
    except Exception as e:
        frappe.log_error(f"Error calculating storage charges for {hu}: {str(e)}")
    
    return charges


def calculate_billing_quantity_for_method(unit_type: str, hu_details: Dict, date_from: str, date_to: str) -> float:
    """Calculate billing quantity based on unit type."""
    if unit_type == "Handling Unit":
        return calculate_per_handling_unit_quantity(hu_details, date_from, date_to)
    elif unit_type == "Volume":
        return calculate_per_volume_quantity(hu_details, date_from, date_to)
    elif unit_type == "Weight":
        return calculate_per_weight_quantity(hu_details, date_from, date_to)
    elif unit_type == "Package":
        return calculate_per_container_quantity(hu_details, date_from, date_to)
    elif unit_type == "Piece":
        return calculate_per_piece_quantity(hu_details, date_from, date_to)
    elif unit_type == "Operation Time":
        return calculate_per_hour_quantity(hu_details, date_from, date_to)
    else:  # Default to Per Day
        return calculate_per_day_quantity(hu_details, date_from, date_to)


def calculate_per_day_quantity(hu_details: Dict, date_from: str, date_to: str) -> float:
    """Calculate days for Per Day billing."""
    start_date = datetime.strptime(str(date_from), "%Y-%m-%d")
    end_date = datetime.strptime(str(date_to), "%Y-%m-%d")
    days = (end_date - start_date).days + 1
    return float(days)


def calculate_per_handling_unit_quantity(hu_details: Dict, date_from: str, date_to: str) -> float:
    """Calculate quantity for Per Handling Unit billing."""
    start_date = datetime.strptime(str(date_from), "%Y-%m-%d")
    end_date = datetime.strptime(str(date_to), "%Y-%m-%d")
    days = (end_date - start_date).days + 1
    return float(days)


def calculate_per_volume_quantity(hu_details: Dict, date_from: str, date_to: str) -> float:
    """Calculate volume for Per Volume billing."""
    return flt(hu_details.get("total_volume", 0))


def calculate_per_weight_quantity(hu_details: Dict, date_from: str, date_to: str) -> float:
    """Calculate weight for Per Weight billing."""
    return flt(hu_details.get("total_weight", 0))


def calculate_per_container_quantity(hu_details: Dict, date_from: str, date_to: str) -> float:
    """Calculate containers for Per Container billing."""
    return 1.0  # Default to 1 container per handling unit


def calculate_per_piece_quantity(hu_details: Dict, date_from: str, date_to: str) -> float:
    """Calculate pieces for Per Piece billing."""
    return 1.0  # Default to 1 piece per handling unit


def calculate_per_hour_quantity(hu_details: Dict, date_from: str, date_to: str) -> float:
    """Calculate hours for Per Hour billing."""
    start_date = datetime.strptime(str(date_from), "%Y-%m-%d")
    end_date = datetime.strptime(str(date_to), "%Y-%m-%d")
    days = (end_date - start_date).days + 1
    return float(days * 24)  # Convert days to hours


def generate_job_calculation_notes(charge: Dict, job: Dict) -> str:
    """Generate calculation notes for warehouse job charges."""
    return f"""Warehouse Job Charge Calculation:
  • Warehouse Job: {job.get('name', 'N/A')}
  • Item: {charge.get('item_code', 'N/A')} - {charge.get('item_name', 'N/A')}
  • UOM: {charge.get('uom', 'N/A')}
  • Rate per {charge.get('uom', 'N/A')}: {charge.get('rate', 0)}
  • Quantity: {charge.get('quantity', 0)}
  • Calculation: {charge.get('quantity', 0)} × {charge.get('rate', 0)} = {charge.get('total', 0)}
  • Currency: {charge.get('currency', 'PHP')}
  • Contract Setup Applied:
    - Rate sourced from Warehouse Job Charges table
    - Applied based on job execution and contract terms
    - Charge type: Service/Operation charge"""


def generate_storage_calculation_notes(hu: str, hu_details: Dict, contract_item: Dict, billing_quantity: float, rate: float, date_from: str, date_to: str) -> str:
    """Generate calculation notes for storage charges."""
    return f"""Storage Charge Calculation:
  • Handling Unit: {hu}
  • Period: {date_from} to {date_to}
  • Billing Method: {contract_item.get('unit_type', 'Day')}
  • UOM: {contract_item.get('uom', 'N/A')}
  • Rate per {contract_item.get('uom', 'N/A')}: {rate}
  • Billing Quantity: {billing_quantity}
  • Calculation: {billing_quantity} × {rate} = {billing_quantity * rate}
  • Storage Location: {hu_details.get('storage_location', 'N/A')}
  • Handling Unit Type: {hu_details.get('handling_unit_type', 'N/A')}
  • Storage Type: {hu_details.get('storage_type', 'N/A')}
  • Contract Setup Applied:
    - {'Exact match' if contract_item.get('handling_unit_type') and contract_item.get('storage_type') else 'Generic match'}: {contract_item.get('handling_unit_type', 'Any')} + {contract_item.get('storage_type', 'Any')}"""


# Additional utility functions for billing

@frappe.whitelist()
def get_contract_setup_summary(warehouse_contract: str) -> Dict[str, Any]:
    """Get a summary of the warehouse contract setup for billing."""
    try:
        contract = frappe.get_doc("Warehouse Contract", warehouse_contract)
        
        # Get contract items
        items = frappe.get_all(
            "Warehouse Contract Item",
            filters={"parent": warehouse_contract, "parenttype": "Warehouse Contract"},
            fields=["item_charge", "rate", "currency", "handling_unit_type", "storage_type", "unit_type", "storage_charge", "inbound_charge", "outbound_charge", "transfer_charge", "vas_charge", "stocktake_charge"],
            order_by="handling_unit_type, storage_type"
        )
        
        # Count different charge types
        storage_count = len([item for item in items if item.get("storage_charge")])
        inbound_count = len([item for item in items if item.get("inbound_charge")])
        outbound_count = len([item for item in items if item.get("outbound_charge")])
        transfer_count = len([item for item in items if item.get("transfer_charge")])
        vas_count = len([item for item in items if item.get("vas_charge")])
        stocktake_count = len([item for item in items if item.get("stocktake_charge")])
        
        return {
            "contract_name": contract.name,
            "customer": contract.customer,
            "valid_from": contract.valid_from,
            "valid_until": contract.valid_until,
            "total_items": len(items),
            "storage_charges": storage_count,
            "inbound_charges": inbound_count,
            "outbound_charges": outbound_count,
            "transfer_charges": transfer_count,
            "vas_charges": vas_count,
            "stocktake_charges": stocktake_count,
            "items": items
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting contract setup summary: {str(e)}")
        return {"error": str(e)}


@frappe.whitelist()
def test_billing_system(periodic_billing: str) -> Dict[str, Any]:
    """Test the billing system for a specific periodic billing document."""
    try:
        pb = frappe.get_doc("Periodic Billing", periodic_billing)
        
        # Get basic info
        info = {
            "periodic_billing": pb.name,
            "customer": pb.customer,
            "date_from": pb.date_from,
            "date_to": pb.date_to,
            "warehouse_contract": pb.warehouse_contract,
            "company": pb.company,
            "branch": pb.branch
        }
        
        # Test handling units
        if pb.customer and pb.date_to:
            hu_list = get_customer_handling_units(pb.customer, pb.date_to, pb.company, pb.branch)
            info["handling_units_found"] = len(hu_list)
            info["handling_units"] = hu_list[:10]  # First 10 for testing
        
        # Test contract items
        if pb.warehouse_contract:
            contract_items = frappe.db.sql("""
                SELECT item_charge, rate, currency, handling_unit_type, storage_type, unit_type, storage_charge
                FROM `tabWarehouse Contract Item`
                WHERE parent = %s AND parenttype = 'Warehouse Contract' AND storage_charge = 1
            """, (pb.warehouse_contract,), as_dict=True)
            info["contract_storage_items"] = len(contract_items)
            info["contract_items"] = contract_items
        
        return {"ok": True, "info": info}
        
    except Exception as e:
        frappe.log_error(f"Error testing billing system: {str(e)}")
        return {"ok": False, "error": str(e)}
