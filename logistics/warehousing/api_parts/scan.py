from __future__ import annotations
from .common import *  # shared helpers

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate

def _barcode_fields(doctype: str) -> List[str]:
    """Return plausible barcode-like fields present on a DocType."""
    f = _safe_meta_fieldnames(doctype)
    order = ["barcode", "qr_code", "code"]
    return [x for x in order if x in f]

def _resolve_by_barcode(doctype: str, scanned: str) -> Optional[str]:
    """Try to resolve a scanned string to a doc name by (1) exact name, (2) barcode-like fields."""
    if not scanned:
        return None
    # 1) direct name match
    if frappe.db.exists(doctype, scanned):
        return scanned
    # 2) barcode-like fields
    for bf in _barcode_fields(doctype):
        name = frappe.db.get_value(doctype, {bf: scanned}, "name")
        if name:
            return name
    return None

def _resolve_scanned_location(scanned: Optional[str]) -> Optional[str]:
    return _resolve_by_barcode("Storage Location", (scanned or "").strip()) if scanned else None

def _resolve_scanned_hu(scanned: Optional[str]) -> Optional[str]:
    return _resolve_by_barcode("Handling Unit", (scanned or "").strip()) if scanned else None

@frappe.whitelist()
def post_items_by_scan(
    warehouse_job: str,
    action: str,
    location_code: Optional[str] = None,
    handling_unit_code: Optional[str] = None,
    qty: Optional[float] = None,
    item: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Scan-driven posting for Warehouse Job.
    - action: 'receiving' | 'pick' | 'putaway' | 'release'
    - location_code: scanned Storage Location barcode/name (source for Pick, destination for Putaway)
    - handling_unit_code: scanned HU barcode/name (filters candidate rows)
    - qty: optional partial quantity to post; if omitted, posts all matching rows
    - item: optional item filter when scanning HU that contains multiple items

    Returns summary of ledger entries and rows affected.
    """
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    action_key = _action_key(action)

    # Resolve scanned codes
    loc = _resolve_scanned_location(location_code) if location_code else None
    hu  = _resolve_scanned_hu(handling_unit_code) if handling_unit_code else None

    # Company/Branch scope safety
    company, branch = _get_job_scope(job)
    _assert_location_in_job_scope(loc, company, branch, ctx=_("Scanned Location"))
    _assert_hu_in_job_scope(hu, company, branch, ctx=_("Scanned Handling Unit"))

    # Collect candidates
    candidates = _iter_candidate_rows(job, action_key, loc, hu, item)
    if not candidates:
        return {"ok": True, "message": _("No matching rows for scan."), "out_entries": 0, "in_entries": 0, "posted_rows": 0, "posted_qty": 0.0}

    # Determine how much to post
    total_match_qty = sum([abs(flt(getattr(r, "quantity", 0))) for r in candidates])
    to_post = abs(flt(qty or total_match_qty))
    if to_post <= 0:
        return {"ok": True, "message": _("Nothing to post (qty=0)."), "out_entries": 0, "in_entries": 0, "posted_rows": 0, "posted_qty": 0.0}

    posting_dt = _posting_datetime(job)

    out_ct = in_ct = posted_rows = 0
    remaining = to_post

    affected_locs: Set[str] = set()
    affected_hus: Set[str]  = set()
    staging_area = getattr(job, "staging_area", None)

    for r in candidates:
        if remaining <= 0:
            break
        row_qty = abs(flt(getattr(r, "quantity", 0)))
        if row_qty <= 0:
            continue

        portion = min(row_qty, remaining)
        # Split if needed
        target_row = _split_job_item_for_partial(job, r, portion)
        o, i = _post_one(job, action_key, target_row, portion, posting_dt)
        out_ct += o; in_ct += i
        posted_rows += 1
        remaining -= portion

        # track affected locations/HUs for status updates
        hu = getattr(target_row, "handling_unit", None)
        if hu: affected_hus.add(hu)
        if action_key == "pick":
            if getattr(target_row, "location", None): affected_locs.add(getattr(target_row, "location"))
            if staging_area: affected_locs.add(staging_area)
        elif action_key == "putaway":
            dest = _row_destination_location(target_row)
            if staging_area: affected_locs.add(staging_area)
            if dest: affected_locs.add(dest)
        elif action_key in ("staging", "receiving", "release"):
            if staging_area: affected_locs.add(staging_area)

    job.save(ignore_permissions=True)

    # Recompute statuses
    for l in affected_locs:
        _set_sl_status_by_balance(l)
    # receiving/release differ for HU inactive flag
    after_release = (action_key == "release")
    for h in affected_hus:
        _set_hu_status_by_balance(h, after_release=after_release)

    frappe.db.commit()

    done = to_post - remaining
    msg_map = {
        "pick":    _("Pick posted by scan: {0} rows, {1} qty."),
        "putaway": _("Putaway posted by scan: {0} rows, {1} qty."),
        "staging": _("Staging updated by scan: {0} rows, {1} qty."),
        "receiving": _("Receiving posted by scan: {0} rows, {1} qty."),
        "release": _("Release posted by scan: {0} rows, {1} qty."),
    }
    msg = msg_map.get(action_key, _("Posted by scan: {0} rows, {1} qty.")).format(int(posted_rows), flt(done))

    return {
        "ok": True,
        "message": msg,
        "action": action_key,
        "posted_rows": int(posted_rows),
        "posted_qty": flt(done),
        "out_entries": int(out_ct),
        "in_entries": int(in_ct),
        "scanned": {"location": loc, "handling_unit": hu, "item": item},
    }

@frappe.whitelist()
def post_job_by_scan(
    warehouse_job: str,
    action: str,
    location_code: str = None,
    handling_unit_code: str = None,
    qty: float = None,
    item: str = None,
) -> dict:
    """
    Thin wrapper to your existing scan-driven poster for the desk page.
    """
    return post_items_by_scan(
        warehouse_job=warehouse_job,
        action=action,
        location_code=location_code,
        handling_unit_code=handling_unit_code,
        qty=qty,
        item=item,
    )

