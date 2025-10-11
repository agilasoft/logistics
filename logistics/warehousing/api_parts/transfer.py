from __future__ import annotations
from .common import *  # shared helpers

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
        from_loc = getattr(r, "storage_location_from", None)
        to_loc   = getattr(r, "storage_location_to", None)
        hu_from  = getattr(r, "handling_unit_from", None)
        hu_to    = getattr(r, "handling_unit_to", None)

        if not from_loc or not to_loc:
            skipped.append(f"Row {getattr(r, 'idx', '?')}: missing From/To location"); continue
        if qty <= 0:
            skipped.append(f"Row {getattr(r, 'idx', '?')}: quantity must be > 0"); continue

        _assert_location_in_job_scope(from_loc, company, branch, ctx=_("From Location"))
        _assert_location_in_job_scope(to_loc, company, branch,   ctx=_("To Location"))
        _assert_hu_in_job_scope(hu_from, company, branch, ctx=_("From HU"))
        _assert_hu_in_job_scope(hu_to,   company, branch, ctx=_("To HU"))

        common = {
            "item": getattr(r, "item", None),
            "serial_no": getattr(r, "serial_no", None) or None,
            "batch_no": getattr(r, "batch_no", None) or None,
        }
        job.append("items", {**common, "location": from_loc, "handling_unit": hu_from or None, "quantity": -qty})
        job.append("items", {**common, "location": to_loc,   "handling_unit": hu_to   or None, "quantity":  qty})
        created_pairs += 1

    job.save(ignore_permissions=True)
    frappe.db.commit()
    return {"message": _("Allocated {0} move pair(s).").format(created_pairs), "created_pairs": created_pairs, "skipped": skipped}

