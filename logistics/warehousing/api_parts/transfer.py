from __future__ import annotations
from .common import *  # shared helpers
from .common import _get_job_scope, _assert_location_in_job_scope, _assert_hu_in_job_scope, _safe_meta_fieldnames

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate

@frappe.whitelist()
def allocate_move(warehouse_job: str, clear_existing: int = 1):
    """Populate Items with paired move rows based on Orders; validates scope."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "Move":
        frappe.throw(_("Warehouse Job must be of type 'Move' to allocate moves from Orders."))

    company, branch = _get_job_scope(job)
    if int(clear_existing or 0):
        job.set("items", [])

    created_pairs = 0
    skipped: List[str] = []

    for r in (job.orders or []):
        qty = abs(flt(getattr(r, "quantity", 0)))
        if qty <= 0:
            skipped.append(f"Row {getattr(r, 'idx', '?')}: quantity must be > 0"); continue

        from_loc = getattr(r, "storage_location_from", None)
        to_loc   = getattr(r, "storage_location_to", None)
        hu_from  = getattr(r, "handling_unit_from", None)
        hu_to    = getattr(r, "handling_unit_to", None)

        # Check for missing required fields and add to skipped list
        missing_fields = []
        if not from_loc:
            missing_fields.append("storage_location_from")
        if not to_loc:
            missing_fields.append("storage_location_to")
        if not hu_from:
            missing_fields.append("handling_unit_from")
        if not hu_to:
            missing_fields.append("handling_unit_to")
        
        if missing_fields:
            skipped.append(f"Row {getattr(r, 'idx', '?')}: missing required fields: {', '.join(missing_fields)}"); continue

        # Validate locations and handling units are in scope
        _assert_location_in_job_scope(from_loc, company, branch, ctx=_("From Location"))
        _assert_location_in_job_scope(to_loc, company, branch,   ctx=_("To Location"))
        _assert_hu_in_job_scope(hu_from, company, branch, ctx=_("From HU"))
        _assert_hu_in_job_scope(hu_to,   company, branch, ctx=_("To HU"))

        common = {
            "item": getattr(r, "item", None),
            "serial_no": getattr(r, "serial_no", None) or None,
            "batch_no": getattr(r, "batch_no", None) or None,
        }
        
        # Add physical dimensions from order if available
        job_item_fields = _safe_meta_fieldnames("Warehouse Job Item")
        if "length" in job_item_fields and getattr(r, "length", None):
            common["length"] = flt(getattr(r, "length"))
        if "width" in job_item_fields and getattr(r, "width", None):
            common["width"] = flt(getattr(r, "width"))
        if "height" in job_item_fields and getattr(r, "height", None):
            common["height"] = flt(getattr(r, "height"))
        if "volume" in job_item_fields and getattr(r, "volume", None):
            common["volume"] = flt(getattr(r, "volume"))
        if "weight" in job_item_fields and getattr(r, "weight", None):
            common["weight"] = flt(getattr(r, "weight"))
        if "volume_uom" in job_item_fields and getattr(r, "volume_uom", None):
            common["volume_uom"] = getattr(r, "volume_uom")
        if "weight_uom" in job_item_fields and getattr(r, "weight_uom", None):
            common["weight_uom"] = getattr(r, "weight_uom")
        if "dimension_uom" in job_item_fields and getattr(r, "dimension_uom", None):
            common["dimension_uom"] = getattr(r, "dimension_uom")
        
        job.append("items", {**common, "location": from_loc, "handling_unit": hu_from or None, "quantity": -qty})
        job.append("items", {**common, "location": to_loc,   "handling_unit": hu_to   or None, "quantity":  qty})
        created_pairs += 1

    job.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "message": _("Allocated {0} move pair(s).").format(created_pairs), "created_pairs": created_pairs, "skipped": skipped}

