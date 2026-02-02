from __future__ import annotations
from typing import Any, Dict, List, Optional

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate

# Import specific functions from common
from .common import _get_job_scope, _safe_meta_fieldnames, _get_item_uom

@frappe.whitelist()
def warehouse_job_fetch_count_sheet(warehouse_job: str, clear_existing: int = 1):
    """Build Count Sheet for items present in Orders; respects Job scope."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "Stocktake":
        frappe.throw(_("Fetch Count Sheet is only available for Warehouse Job Type = Stocktake."))

    # Get items from Orders table
    order_items = frappe.get_all(
        "Warehouse Job Order Items",
        filters={"parent": job.name, "parenttype": "Warehouse Job"},
        fields=["distinct item AS item"],
        ignore_permissions=True,
    )
    item_list = [r["item"] for r in order_items if (r.get("item") or "").strip()]
    item_set  = set(item_list)
    
    company, branch = _get_job_scope(job)
    
    # If no items in Orders, get items from stock ledger based on job scope and filters
    if not item_set:
        # Get customer from job
        customer = getattr(job, "customer", None)
        
        # Get field names for filtering
        slf = _safe_meta_fieldnames("Storage Location")
        huf = _safe_meta_fieldnames("Handling Unit")
        llf = _safe_meta_fieldnames("Warehouse Stock Ledger")
        
        # Build additional filters for stock ledger query
        additional_filters = []
        additional_params = []
        
        # Add customer filter if present
        if customer:
            # Check if customer field exists in Warehouse Item
            wi_fields = _safe_meta_fieldnames("Warehouse Item")
            if "customer" in wi_fields:
                additional_filters.append("wi.customer = %s")
                additional_params.append(customer)
        
        # Get items from stock ledger that match the job scope
        stock_items_query = f"""
            SELECT DISTINCT l.item
            FROM `tabWarehouse Stock Ledger` l
            LEFT JOIN `tabStorage Location` sl ON l.storage_location = sl.name
            LEFT JOIN `tabHandling Unit` hu ON l.handling_unit = hu.name
            LEFT JOIN `tabWarehouse Item` wi ON l.item = wi.name
            WHERE l.quantity > 0
        """
        
        # Add company/branch filters
        if company and (("company" in slf) or ("company" in huf) or ("company" in llf)):
            stock_items_query += " AND COALESCE(hu.company, sl.company, l.company) = %s"
            additional_params.append(company)
        if branch and (("branch" in slf) or ("branch" in huf) or ("branch" in llf)):
            # Ensure all non-null branch values match the job branch
            branch_conditions = []
            if "branch" in huf:
                branch_conditions.append("(hu.branch IS NULL OR hu.branch = %s)")
                additional_params.append(branch)
            if "branch" in slf:
                branch_conditions.append("(sl.branch IS NULL OR sl.branch = %s)")
                additional_params.append(branch)
            if "branch" in llf:
                branch_conditions.append("(l.branch IS NULL OR l.branch = %s)")
                additional_params.append(branch)
            if branch_conditions:
                stock_items_query += " AND " + " AND ".join(branch_conditions)
        
        # Add additional filters
        if additional_filters:
            stock_items_query += " AND " + " AND ".join(additional_filters)
        
        stock_items = frappe.db.sql(stock_items_query, tuple(additional_params), as_dict=True) or []
        item_list = [r["item"] for r in stock_items if (r.get("item") or "").strip()]
        item_set = set(item_list)
        
        if not item_set:
            return {"ok": True, "message": _("No items found in Orders or Stock Ledger. Add items in the Orders table first or check your filters."), "created_rows": 0}

    if int(clear_existing or 0):
        job.set("counts", [])

    # optional sync from Stocktake Order header
    if (job.reference_order_type or "").strip() == "Stocktake Order" and getattr(job, "reference_order", None):
        so_meta = _safe_meta_fieldnames("Stocktake Order")
        desired = ["count_type", "blind_count", "qa_required", "count_date"]
        fields_to_fetch = [f for f in desired if f in so_meta]
        if fields_to_fetch:
            so = frappe.db.get_value("Stocktake Order", job.reference_order, fields_to_fetch, as_dict=True) or {}
            for k in fields_to_fetch:
                v = so.get(k)
                if v not in (None, "") and not getattr(job, k, None):
                    setattr(job, k, v)

    # Get field names for filtering
    slf = _safe_meta_fieldnames("Storage Location")
    huf = _safe_meta_fieldnames("Handling Unit")
    llf = _safe_meta_fieldnames("Warehouse Stock Ledger")

    conds = ["l.item IN ({})".format(", ".join(["%s"] * len(item_set)))]
    params: List[Any] = list(item_set)

    if company and (("company" in slf) or ("company" in huf) or ("company" in llf)) :
        conds.append("COALESCE(hu.company, sl.company, l.company) = %s"); params.append(company)
    if branch and  (("branch"  in slf) or ("branch"  in huf) or ("branch"  in llf)):
        # Ensure all non-null branch values match the job branch to prevent fetching branches not similar to job doc
        # Storage locations with different branches must be excluded
        branch_conditions = []
        if "branch" in huf:
            branch_conditions.append("(hu.branch IS NULL OR hu.branch = %s)")
            params.append(branch)
        if "branch" in slf:
            # Strictly enforce: if storage location has a branch, it must match job branch
            branch_conditions.append("(sl.branch IS NULL OR sl.branch = %s)")
            params.append(branch)
        if "branch" in llf:
            branch_conditions.append("(l.branch IS NULL OR l.branch = %s)")
            params.append(branch)
        if branch_conditions:
            conds.append("(" + " AND ".join(branch_conditions) + ")")

    # Include storage location branch in query for post-processing validation
    select_fields = "l.item, l.storage_location, l.handling_unit, l.batch_no, l.serial_no, SUM(l.quantity) AS system_qty"
    group_by_fields = "l.item, l.storage_location, l.handling_unit, l.batch_no, l.serial_no"
    if branch and "branch" in slf:
        select_fields += ", sl.branch AS storage_location_branch"
        group_by_fields += ", sl.branch"
    
    aggregates = frappe.db.sql(f"""
        SELECT {select_fields}
        FROM `tabWarehouse Stock Ledger` l
        LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
        LEFT JOIN `tabHandling Unit`    hu ON hu.name = l.handling_unit
        WHERE {' AND '.join(conds)}
        GROUP BY {group_by_fields}
        HAVING SUM(l.quantity) > 0
    """, tuple(params), as_dict=True) or []

    # zero-stock placeholders
    loc_params, loc_conds = [], []
    if company and ("company" in slf): loc_conds.append("sl.company = %s"); loc_params.append(company)
    if branch  and ("branch"  in slf): loc_conds.append("sl.branch  = %s"); loc_params.append(branch)
    loc_where = ("WHERE " + " AND ".join(loc_conds)) if loc_conds else ""
    locations = frappe.db.sql(f"SELECT sl.name AS name FROM `tabStorage Location` sl {loc_where}",
                              tuple(loc_params), as_dict=True) or []

    hu_params, hu_conds = [], []
    if company and ("company" in huf): hu_conds.append("hu.company = %s"); hu_params.append(company)
    if branch  and ("branch"  in huf): hu_conds.append("hu.branch  = %s");  hu_params.append(branch)
    hu_where = ("WHERE " + " AND ".join(hu_conds)) if hu_conds else ""
    hus = frappe.db.sql(f"SELECT hu.name AS name FROM `tabHandling Unit` hu {hu_where}",
                        tuple(hu_params), as_dict=True) or []

    existing_keys = set()
    for r in (job.counts or []):
        k = (r.item or "", r.location or "", r.handling_unit or "", r.batch_no or "", r.serial_no or "")
        existing_keys.add(k)

    created_rows = 0
    blind = int(getattr(job, "blind_count", 0) or 0)

    def _append_count_row(item: str, location: Optional[str], handling_unit: Optional[str],
                          batch_no: Optional[str], serial_no: Optional[str], sys_qty: Optional[float]):
        nonlocal created_rows
        key = (item or "", location or "", handling_unit or "", batch_no or "", serial_no or "")
        if key in existing_keys:
            return
        payload = {
            "item": item,
            "location": location,
            "handling_unit": handling_unit,
            "batch_no": batch_no,
            "serial_no": serial_no,
            "system_count": (None if blind else flt(sys_qty or 0)),
            "actual_quantity": None,
            "blind_count": blind,
        }
        job.append("counts", payload)
        existing_keys.add(key)
        created_rows += 1

    # Only create count rows for items that actually exist in stock ledger
    # Additional validation: ensure storage locations match job branch
    for a in aggregates:
        if a.get("item") not in item_set: continue
        
        # Validate storage location branch matches job branch if branch is specified
        storage_location = a.get("storage_location")
        if branch and storage_location and "branch" in slf:
            # Check storage location branch from query result
            sl_branch = a.get("storage_location_branch")
            if sl_branch and sl_branch != branch:
                # Skip storage locations with different branches
                continue
        
        _append_count_row(a.get("item"), storage_location, a.get("handling_unit"),
                          a.get("batch_no"), a.get("serial_no"), flt(a.get("system_qty") or 0))

    job.save(ignore_permissions=True)
    frappe.db.commit()

    msg_bits = [_("Created {0} count line(s).").format(created_rows)]
    if blind: msg_bits.append(_("Blind: system counts hidden"))
    if company: msg_bits.append(_("Company: {0}").format(company))
    if branch:  msg_bits.append(_("Branch: {0}").format(branch))

    return {"ok": True, "message": " | ".join(msg_bits), "created_rows": created_rows,
            "header": {"count_date": getattr(job, "count_date", None),
                       "count_type": getattr(job, "count_type", None),
                       "blind_count": blind,
                       "qa_required": int(getattr(job, "qa_required", 0) or 0)}}

@frappe.whitelist()
def populate_stocktake_adjustments(warehouse_job: str, clear_existing: int = 1) -> Dict[str, Any]:
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "Stocktake":
        frappe.throw(_("This action is only available for Warehouse Job Type = Stocktake."))

    if int(clear_existing or 0):
        job.set("items", [])

    item_fields = _safe_meta_fieldnames("Warehouse Job Item")
    has_uom = "uom" in item_fields
    has_location = "location" in item_fields
    has_handling = "handling_unit" in item_fields
    has_source_row = "source_row" in item_fields
    has_source_par = "source_parent" in item_fields

    created = 0
    net_delta = 0.0

    for r in (job.counts or []):
        if (getattr(r, "actual_quantity", None) in (None, "")) or (getattr(r, "system_count", None) in (None, "")):
            continue
        actual = flt(getattr(r, "actual_quantity", 0))
        system = flt(getattr(r, "system_count", 0))
        delta = actual - system
        if delta == 0:
            continue

        payload: Dict[str, Any] = {
            "item": getattr(r, "item", None),
            "quantity": delta,
            "serial_no": getattr(r, "serial_no", None) or None,
            "batch_no": getattr(r, "batch_no", None) or None,
        }
        if has_location: payload["location"] = getattr(r, "location", None) or None
        if has_handling: payload["handling_unit"] = getattr(r, "handling_unit", None) or None
        if has_uom:      payload["uom"] = _get_item_uom(payload["item"])
        if has_source_row: payload["source_row"] = f"COUNT:{getattr(r, 'name', '')}"
        if has_source_par: payload["source_parent"] = job.name

        job.append("items", payload)
        created  += 1
        net_delta+= delta

    # Set the populate adjustment triggered flag
    job.populate_adjustment_triggered = 1
    
    job.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "message": _("Created {0} adjustment item(s). Net delta: {1}").format(int(created), flt(net_delta)),
            "created_rows": int(created), "net_delta": flt(net_delta)}

