from __future__ import annotations
from .common import *  # shared helpers

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate

def _ensure_serial(serial_code: Optional[str], item: Optional[str] = None, customer: Optional[str] = None) -> str:
    if not serial_code:
        return ""
    if frappe.db.exists("Warehouse Serial", serial_code):
        return serial_code
    doc = frappe.new_doc("Warehouse Serial")
    doc.serial_no = serial_code  # autoname=field:serial_no
    if hasattr(doc, "item_code") and item:
        doc.item_code = item
    if hasattr(doc, "customer") and customer:
        doc.customer = customer
    doc.insert()
    return doc.name

def _ensure_batch(
    batch_code: Optional[str],
    item: Optional[str] = None,
    customer: Optional[str] = None,
    expiry: Optional[str] = None,
    uom: Optional[str] = None,
) -> str:
    if not batch_code:
        return ""
    if frappe.db.exists("Warehouse Batch", batch_code):
        if uom:
            current_uom = frappe.db.get_value("Warehouse Batch", batch_code, "batch_uom")
            if not current_uom:
                frappe.db.set_value("Warehouse Batch", batch_code, "batch_uom", uom)
        return batch_code
    doc = frappe.new_doc("Warehouse Batch")
    doc.batch_no = batch_code  # autoname=field:batch_no
    if hasattr(doc, "item_code") and item:
        doc.item_code = item
    if hasattr(doc, "customer") and customer:
        doc.customer = customer
    if hasattr(doc, "expiry_date") and expiry:
        doc.expiry_date = expiry
    if hasattr(doc, "batch_uom") and uom:
        doc.batch_uom = uom
    doc.insert()
    return doc.name

@frappe.whitelist()
def create_serial_and_batch_for_inbound(inbound_order: str):
    if not inbound_order:
        frappe.throw(_("Inbound Order is required"))
    customer = None
    try:
        parent = frappe.get_doc("Inbound Order", inbound_order)
        customer = getattr(parent, "customer", None)
    except Exception:
        pass

    rows = frappe.get_all(
        "Inbound Order Item",
        filters={"parent": inbound_order, "parenttype": "Inbound Order"},
        fields=[
            "name", "item", "uom",
            "serial_tracking", "serial_no", "serial_no_text",
            "batch_tracking", "batch_no", "batch_no_text", "batch_expiry",
        ],
        order_by="idx asc",
    )

    created_serial = linked_serial = 0
    created_batch  = linked_batch  = 0
    updated_batch_uom = 0
    skipped = 0
    errors: List[str] = []

    for r in rows:
        try:
            to_set: Dict[str, Any] = {}
            row_uom = r.uom or _get_item_uom(r.item)

            if int(r.serial_tracking or 0):
                existing = (r.serial_no or "").strip()
                code = _first_token(r.serial_no_text or "")
                if not existing:
                    if code:
                        if frappe.db.exists("Warehouse Serial", code):
                            to_set["serial_no"] = code; linked_serial += 1
                        else:
                            to_set["serial_no"] = _ensure_serial(code, r.item, customer); created_serial += 1
                    else:
                        skipped += 1

            if int(r.batch_tracking or 0):
                existing_b = (r.batch_no or "").strip()
                code_b = _first_token(r.batch_no_text or "")
                if not existing_b:
                    if code_b:
                        if frappe.db.exists("Warehouse Batch", code_b):
                            if row_uom:
                                current_uom = frappe.db.get_value("Warehouse Batch", code_b, "batch_uom")
                                if not current_uom:
                                    frappe.db.set_value("Warehouse Batch", code_b, "batch_uom", row_uom)
                                    updated_batch_uom += 1
                            to_set["batch_no"] = code_b; linked_batch += 1
                        else:
                            to_set["batch_no"] = _ensure_batch(code_b, r.item, customer, r.batch_expiry, row_uom)
                            created_batch += 1
                    else:
                        skipped += 1

            if to_set:
                frappe.db.set_value("Inbound Order Item", r.name, to_set)
        except Exception as e:
            errors.append(f"Row {r.name}: {e}")

    return {
        "created": {"serial": created_serial, "batch": created_batch},
        "linked":  {"serial": linked_serial,  "batch": linked_batch},
        "updated": {"batch_uom": updated_batch_uom},
        "skipped": skipped,
        "errors": errors,
    }

@frappe.whitelist()
def post_receiving(warehouse_job: str) -> Dict[str, Any]:
    """Putaway step 1: In to Staging (+ABS(qty)) per item row; marks staging/receiving posted."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    staging_area = getattr(job, "staging_area", None)
    if not staging_area:
        frappe.throw(_("Staging Area is required on the Warehouse Job."))

    posting_dt = _posting_datetime(job)
    created = 0
    skipped: List[str] = []

    action_key = "staging" if "staging_posted" in _safe_meta_fieldnames("Warehouse Job Item") else "receiving"

    for it in (job.items or []):
        if _row_is_already_posted(it, action_key):
            skipped.append(_("Item Row {0}: staging already posted.").format(getattr(it, "idx", "?"))); continue
        item = getattr(it, "item", None)
        qty  = abs(flt(getattr(it, "quantity", 0)))
        if not item or qty == 0:
            continue
        hu   = getattr(it, "handling_unit", None)
        bn   = getattr(it, "batch_no", None)
        sn   = getattr(it, "serial_no", None)

        _validate_status_for_action(action="Receiving", location=staging_area, handling_unit=hu)

        _insert_ledger_entry(job, item=item, qty=qty, location=staging_area,
                             handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt)
        _mark_row_posted(it, action_key, posting_dt)
        _maybe_set_staging_area_on_row(it, staging_area)
        created += 1

    job.save(ignore_permissions=True)

    # status recompute
    _set_sl_status_by_balance(staging_area)
    seen_hus = {getattr(r, "handling_unit", None) for r in (job.items or []) if getattr(r, "handling_unit", None)}
    for h in seen_hus:
        _set_hu_status_by_balance(h, after_release=False)

    frappe.db.commit()

    msg = _("Receiving posted into staging: {0} entry(ies).").format(created)
    if skipped: msg += " " + _("Skipped") + f": {len(skipped)}"
    return {"ok": True, "message": msg, "created": created, "skipped": skipped}

