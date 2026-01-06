from __future__ import annotations
from .common import *  # shared helpers

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate

@frappe.whitelist()
def post_release(warehouse_job: str) -> Dict[str, Any]:
    """Release step: Out from Staging (−ABS); marks staging/release posted."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    staging_area = getattr(job, "staging_area", None)
    if not staging_area:
        frappe.throw(_("Staging Area is required on the Warehouse Job."))

    posting_dt = _posting_datetime(job)
    created = 0
    skipped: List[str] = []

    affected_hus: Set[str] = set()

    action_key = "staging" if "staging_posted" in _safe_meta_fieldnames("Warehouse Job Item") else "release"

    for it in (job.items or []):
        if _row_is_already_posted(it, action_key):
            skipped.append(_("Item Row {0}: staging already released.").format(getattr(it, "idx", "?"))); continue

        item = getattr(it, "item", None)
        qty  = abs(flt(getattr(it, "quantity", 0)))
        if not item or qty == 0:
            continue
        hu   = getattr(it, "handling_unit", None)
        bn   = getattr(it, "batch_no", None)
        sn   = getattr(it, "serial_no", None)

        _validate_status_for_action(action="Release", location=staging_area, handling_unit=hu)

        _insert_ledger_entry(job, item=item, qty=-qty, location=staging_area,
                             handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt)
        _mark_row_posted(it, action_key, posting_dt)
        created += 1

        if hu: affected_hus.add(hu)

    job.save(ignore_permissions=True)

    _set_sl_status_by_balance(staging_area)
    for h in affected_hus:
        _set_hu_status_by_balance(h, after_release=True)

    frappe.db.commit()

    msg = _("Release posted: {0} OUT from staging.").format(created)
    if skipped: msg += " " + _("Skipped") + f": {len(skipped)}"
    return {"ok": True, "message": msg, "created": created, "skipped": skipped}

