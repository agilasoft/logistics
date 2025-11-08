from __future__ import annotations
from .common import *  # shared helpers
from .common import _get_job_scope, _fetch_job_order_items, _get_allocation_level_limit, _get_item_rules, _query_available_candidates, _filter_locations_by_level, _greedy_allocate, _order_candidates, _append_job_items, _posting_datetime, _row_is_already_posted, _validate_status_for_action, _insert_ledger_entry, _mark_row_posted, _maybe_set_staging_area_on_row, _set_sl_status_by_balance, _set_hu_status_by_balance

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate
from typing import List, Dict, Any, Optional


def _get_pick_policy(item: str, company: Optional[str] = None) -> str:
    """Get pick policy description for an item.
    
    Args:
        item: Item code
        company: Optional company for company-level policy
        
    Returns:
        Policy description string
    """
    try:
        # Get item-level pick policy (picking_method)
        item_policy = frappe.db.get_value("Warehouse Item", item, "picking_method")
        if item_policy:
            return f"Item-level: {item_policy}"
        
        # Get company-level pick policy if company is provided
        if company:
            company_policy = frappe.db.get_value("Company", company, "pick_policy")
            if company_policy:
                return f"Company-level: {company_policy}"
        
        # Default policy
        return "Default: FIFO"
    except Exception as e:
        frappe.logger().warning(f"Error getting pick policy for item {item}: {str(e)}")
        return "Default: FIFO"


def _filter_candidates_by_hu_priority(
    candidates: List[Dict[str, Any]],
    order_row: Dict[str, Any],
    company: Optional[str] = None,
    branch: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Filter and prioritize candidates based on handling unit requirements from order.
    
    Priority hierarchy:
    1. Specific handling unit from order (if specified)
    2. Handling unit type from order (if specified)
    3. Pick policy
    
    Args:
        candidates: List of candidate dictionaries
        order_row: Order row dictionary
        company: Company filter
        branch: Branch filter
        
    Returns:
        Filtered and prioritized list of candidates
    """
    if not candidates:
        return []
    
    order_handling_unit = order_row.get("handling_unit")
    order_handling_unit_type = order_row.get("handling_unit_type")
    
    # Priority 1: Specific handling unit from order
    if order_handling_unit:
        hu_filtered = [c for c in candidates if c.get("handling_unit") == order_handling_unit]
        if hu_filtered:
            return hu_filtered
    
    # Priority 2: Handling unit type from order
    if order_handling_unit_type:
        # Get HU type for each candidate
        type_filtered = []
        for c in candidates:
            hu_name = c.get("handling_unit")
            if hu_name:
                try:
                    hu_type = frappe.db.get_value("Handling Unit", hu_name, "type")
                    if hu_type == order_handling_unit_type:
                        type_filtered.append(c)
                except Exception:
                    pass
        
        if type_filtered:
            return type_filtered
    
    # Priority 3: Pick policy (already handled by _order_candidates)
    return candidates

@frappe.whitelist()
def allocate_pick(warehouse_job: str) -> Dict[str, Any]:
    """Build pick-lines from Orders, applying Company/Branch scope and item rules."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "Pick":
        frappe.throw(_("Allocate Picks can only run for Warehouse Job Type = Pick."))

    # Clear existing items before allocation
    job.set("items", [])
    job.save(ignore_permissions=True)
    frappe.db.commit()
    print(f"Cleared existing items from job {warehouse_job}")
    frappe.logger().info(f"Cleared existing items from job {warehouse_job}")

    company, branch = _get_job_scope(job)
    jo_items = _fetch_job_order_items(job.name)
    if not jo_items:
        return {"ok": True, "message": _("No items found on Warehouse Job Order Items."), "created_rows": 0, "created_qty": 0}

    # Allocation Level Limit (relative to staging)
    staging_area = getattr(job, "staging_area", None)
    level_limit_label = _get_allocation_level_limit()

    total_created_rows = 0
    total_created_qty  = 0.0
    details: List[Dict[str, Any]] = []
    warnings: List[str] = []

    for row in jo_items:
        item   = row.get("item")
        req_qty = flt(row.get("quantity"))
        if not item or req_qty <= 0:
            continue

        fixed_serial = row.get("serial_no") or None
        fixed_batch  = row.get("batch_no")  or None
        rules = _get_item_rules(item)

        if fixed_serial or fixed_batch:
            candidates = _query_available_candidates(item=item, batch_no=fixed_batch, serial_no=fixed_serial,
                                                     company=company, branch=branch)
        else:
            candidates = _query_available_candidates(item=item, company=company, branch=branch)

        # Filter by allocation level (same path as staging up to configured level)
        candidates = _filter_locations_by_level(candidates, staging_area, level_limit_label)
        
        # Apply handling unit priority hierarchy
        candidates = _filter_candidates_by_hu_priority(candidates, row, company, branch)

        if fixed_serial or fixed_batch:
            allocations = _greedy_allocate(candidates, req_qty, rules, force_exact=True)
        else:
            ordered    = _order_candidates(candidates, rules, req_qty)
            allocations= _greedy_allocate(ordered, req_qty, rules, force_exact=False)

        if not allocations:
            scope_note = []
            if company: scope_note.append(_("Company = {0}").format(company))
            if branch:  scope_note.append(_("Branch = {0}").format(branch))
            if level_limit_label and staging_area:
                scope_note.append(_("Within {0} of staging {1}").format(level_limit_label, staging_area))
            scope_text = f" [{', '.join(scope_note)}]" if scope_note else ""
            warnings.append(_("No allocatable stock for Item {0} (Row {1}) within scope{2}.")
                            .format(item, row.get("idx"), scope_text))

        created_rows, created_qty = _append_job_items(
            job=job, source_parent=job.name, source_child=row["name"],
            item=item, uom=row.get("uom"), allocations=allocations,
            order_data=row,
        )
        total_created_rows += created_rows
        total_created_qty  += created_qty

        details.append({
            "job_order_item": row["name"],
            "item": item,
            "requested_qty": req_qty,
            "created_rows": created_rows,
            "created_qty": created_qty,
            "short_qty": max(0.0, req_qty - abs(created_qty)),
        })

    job.save(ignore_permissions=True)
    frappe.db.commit()

    msg = _("Allocated {0} units across {1} pick rows.").format(flt(total_created_qty), int(total_created_rows))

    return {
        "ok": True, "message": msg,
        "created_rows": total_created_rows, "created_qty": total_created_qty,
        "lines": details, "warnings": warnings,
    }

@frappe.whitelist()
def initiate_vas_pick(warehouse_job: str, clear_existing: int = 1):
    """VAS → Build pick rows for BOM components using same policies as standard picks."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "VAS":
        frappe.throw(_("Initiate VAS Pick can only run for Warehouse Job Type = VAS."))
    if (job.reference_order_type or "").strip() != "VAS Order" or not job.reference_order:
        frappe.throw(_("This VAS job must reference a VAS Order."))

    company, branch = _get_job_scope(job)
    if int(clear_existing or 0):
        job.set("items", [])

    vo = frappe.db.get_value("VAS Order", job.reference_order, ["customer", "type"], as_dict=True) or {}
    customer = vo.get("customer")
    vas_type = (vo.get("type") or "").strip()

    jo_items = _fetch_job_order_items(job.name)
    if not jo_items:
        return {"ok": True, "message": _("No parent items on Warehouse Job Order Items."), "created_rows": 0, "created_qty": 0}

    created_rows = 0
    created_qty  = 0.0
    details: List[Dict[str, Any]] = []
    skipped: List[str] = []
    warnings: List[str] = []

    def _find_vas_bom(parent_item: str) -> Optional[str]:
        base = {"item": parent_item}
        if vas_type: base["vas_order_type"] = vas_type
        if customer:
            r = frappe.get_all("Warehouse Item VAS BOM", filters={**base, "customer": customer},
                               fields=["name"], limit=1, ignore_permissions=True)
            if r: return r[0]["name"]
        r = frappe.get_all("Warehouse Item VAS BOM", filters=base, fields=["name"], limit=1, ignore_permissions=True)
        return r[0]["name"] if r else None

    for parent in jo_items:
        p_item = parent.get("item")
        p_qty  = flt(parent.get("quantity") or 0)
        if not p_item or p_qty <= 0:
            skipped.append(_("Job Order Row {0}: missing item or non-positive quantity").format(parent.get("name"))); continue

        bom = _find_vas_bom(p_item)
        if not bom:
            skipped.append(_("No VAS BOM for {0} (type={1}, customer={2})").format(p_item, vas_type or "N/A", customer or "N/A"))
            continue

        inputs = frappe.get_all(
            "Customer VAS Item Input",
            filters={"parent": bom, "parenttype": "Warehouse Item VAS BOM"},
            fields=["name", "item", "quantity", "uom"],
            order_by="idx asc", ignore_permissions=True,
        )
        if not inputs:
            skipped.append(_("VAS BOM {0} has no inputs").format(bom)); continue

        for comp in inputs:
            c_item = comp.get("item")
            per    = flt(comp.get("quantity") or 0)
            uom    = comp.get("uom")
            req    = per * p_qty
            if not c_item or req <= 0:
                skipped.append(_("BOM {0} component missing item/quantity (row {1})").format(bom, comp.get("name"))); continue

            rules = _get_item_rules(c_item)
            cand  = _query_available_candidates(item=c_item, company=company, branch=branch)
            ordered = _order_candidates(cand, rules, req)
            allocs  = _greedy_allocate(ordered, req, rules, force_exact=False)

            if not allocs:
                scope_note = []
                if company: scope_note.append(_("Company = {0}").format(company))
                if branch:  scope_note.append(_("Branch = {0}").format(branch))
                scope_text = f" [{', '.join(scope_note)}]" if scope_note else ""
                warnings.append(_("No allocatable stock for VAS component {0} (Row {1}) within scope{2}.")
                                .format(c_item, comp.get("idx"), scope_text))

            # NEGATIVE for VAS pick
            allocs_neg = []
            for a in allocs:
                q = flt(a.get("qty") or 0)
                if q > 0:
                    b = dict(a); b["qty"] = -q
                    allocs_neg.append(b)

            c_rows, c_qty = _append_job_items(
                job=job, source_parent=job.name, source_child=f"{parent.get('name')}::{bom}",
                item=c_item, uom=uom, allocations=allocs_neg,
                order_data=parent,
            )
            created_rows += c_rows
            created_qty  += c_qty  # negative sum

            details.append({
                "parent_job_order_item": parent.get("name"),
                "parent_item": p_item,
                "component_item": c_item,
                "requested_qty": req,
                "allocated_qty": c_qty,  # negative
                "created_rows": c_rows,
                "short_qty": max(0.0, req + c_qty),
            })

    job.save(ignore_permissions=True)
    frappe.db.commit()

    msg = _("Initiated VAS Pick. Allocated {0} units in {1} row(s).").format(flt(created_qty), int(created_rows))
    if warnings:
        msg += " " + _("Notes") + ": " + " | ".join(warnings)

    return {
        "ok": True, "message": msg,
        "created_rows": int(created_rows), "created_qty": flt(created_rows and created_qty or 0),
        "lines": details, "skipped": skipped, "warnings": warnings,
    }

@frappe.whitelist()
def post_pick(warehouse_job: str) -> Dict[str, Any]:
    """Pick step: Out from Location (−ABS) + In to Staging (+ABS); marks pick_posted."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    staging_area = getattr(job, "staging_area", None)
    if not staging_area:
        frappe.throw(_("Staging Area is required on the Warehouse Job."))

    posting_dt = _posting_datetime(job)
    created_out = created_in = 0
    skipped: List[str] = []

    affected_locs: Set[str] = set()
    affected_hus: Set[str]  = set()

    for it in (job.items or []):
        if _row_is_already_posted(it, "pick"):
            skipped.append(_("Item Row {0}: pick already posted.").format(getattr(it, "idx", "?"))); continue

        item = getattr(it, "item", None)
        loc  = getattr(it, "location", None)
        qty  = abs(flt(getattr(it, "quantity", 0)))
        if not item or not loc or qty == 0:
            continue
        hu   = getattr(it, "handling_unit", None)
        bn   = getattr(it, "batch_no", None)
        sn   = getattr(it, "serial_no", None)

        _validate_status_for_action(action="Pick", location=loc,          handling_unit=hu)
        _validate_status_for_action(action="Pick", location=staging_area, handling_unit=hu)

        _insert_ledger_entry(job, item=item, qty=-qty, location=loc,
                             handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt)
        created_out += 1

        _insert_ledger_entry(job, item=item, qty=qty,  location=staging_area,
                             handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt)
        created_in += 1

        _mark_row_posted(it, "pick", posting_dt)
        _maybe_set_staging_area_on_row(it, staging_area)

        affected_locs.add(loc)
        affected_locs.add(staging_area)
        if hu: affected_hus.add(hu)

    job.save(ignore_permissions=True)

    for l in affected_locs:
        _set_sl_status_by_balance(l)
    for h in affected_hus:
        _set_hu_status_by_balance(h, after_release=False)

    frappe.db.commit()

    msg = _("Pick posted: {0} OUT from location, {1} IN to staging.").format(created_out, created_in)
    if skipped: msg += " " + _("Skipped") + f": {len(skipped)}"
    return {"ok": True, "message": msg, "out_from_location": created_out, "in_to_staging": created_in, "skipped": skipped}

