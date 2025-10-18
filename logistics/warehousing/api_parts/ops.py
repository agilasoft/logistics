from __future__ import annotations
from .common import *  # shared helpers

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate

@frappe.whitelist()
def populate_job_operations(warehouse_job: str, clear_existing: int = 1) -> Dict[str, Any]:
    if not warehouse_job:
        frappe.throw(_("warehouse_job is required"))

    job = frappe.get_doc("Warehouse Job", warehouse_job)
    job_type = (job.type or "").strip()
    if not job_type:
        frappe.throw(_("Warehouse Job Type is required to create Job Operations."))

    ops_field = _find_child_table_field("Warehouse Job", "Warehouse Job Operations")
    if not ops_field:
        frappe.throw(_("Warehouse Job has no Operations child table."))

    if int(clear_existing or 0):
        job.set(ops_field, [])

    orders = _fetch_job_order_items(job.name)
    qty_baseline = sum([flt(o.get("quantity") or 0) for o in orders])

    params: List[Any] = [job_type]
    sql = """
        SELECT name, operation_name, IFNULL(unit_std_hours, 0) AS unit_std_hours, notes
        FROM `tabWarehouse Operation Item` WHERE used_in = %s
    """
    if job_type == "VAS" and getattr(job, "vas_order_type", None):
        sql += " AND (vas_order_type = %s OR IFNULL(vas_order_type, '') = '')"
        params.append(job.vas_order_type)
    sql += " ORDER BY operation_name ASC"

    ops = frappe.db.sql(sql, tuple(params), as_dict=True) or []
    if not ops:
        return {"ok": True, "message": _("No Warehouse Operation Item found for type {0}.").format(job_type),
                "created_rows": 0, "qty_baseline": qty_baseline}

    existing_codes = set()
    for r in (getattr(job, ops_field) or []):
        code = getattr(r, "operation", None)
        if code: existing_codes.add(code)

    child_fields = _safe_meta_fieldnames("Warehouse Job Operations")
    has_desc  = "description" in child_fields
    has_notes = "notes" in child_fields
    has_uom   = False  # handling_uom column doesn't exist in database
    has_qty   = "quantity" in child_fields
    has_unith = "unit_std_hours" in child_fields
    has_totalh= "total_std_hours" in child_fields
    has_actual= "actual_hours" in child_fields

    created = 0
    for op in ops:
        code = op["name"]
        if code in existing_codes:
            continue
        unit_std = flt(op.get("unit_std_hours") or 0)
        qty = flt(qty_baseline or 0)
        payload: Dict[str, Any] = {"operation": code}
        if has_desc:   payload["description"] = op.get("operation_name")
        if has_uom and op.get("handling_uom"): payload["handling_uom"] = op.get("handling_uom")
        if has_qty:    payload["quantity"] = qty
        if has_unith:  payload["unit_std_hours"] = unit_std
        if has_totalh: payload["total_std_hours"] = unit_std * qty
        if has_actual: payload["actual_hours"] = None
        if has_notes and op.get("notes"): payload["notes"] = op.get("notes")
        job.append(ops_field, payload)
        created += 1

    job.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "message": _("Added {0} operation(s).").format(created),
            "created_rows": created, "qty_baseline": qty_baseline, "ops_field": ops_field}

@frappe.whitelist()
def create_sales_invoice_from_job(
    warehouse_job: str,
    customer: Optional[str] = None,
    company: Optional[str] = None,
    posting_date: Optional[str] = None,
    cost_center: Optional[str] = None,
) -> Dict[str, Any]:
    if not warehouse_job:
        frappe.throw(_("warehouse_job is required"))

    job = frappe.get_doc("Warehouse Job", warehouse_job)

    charges_field = _find_child_table_field("Warehouse Job", "Warehouse Job Charges") or "charges"
    charges: List[Any] = list(getattr(job, charges_field, []) or [])
    if not charges:
        frappe.throw(_("No rows found in {0}.").format(_("Warehouse Job Charges")))

    jf = _safe_meta_fieldnames("Warehouse Job")
    customer = customer or (getattr(job, "customer", None) if "customer" in jf else None)
    company  = company  or (getattr(job, "company",  None) if "company"  in jf else None)
    if not customer: frappe.throw(_("Customer is required (set Customer on Warehouse Job or pass it here)."))
    if not company:  frappe.throw(_("Company is required."))

    cf = _safe_meta_fieldnames("Warehouse Job Charges")
    row_has_currency = "currency" in cf
    row_has_rate     = "rate" in cf
    row_has_total    = "total" in cf
    row_has_uom      = "uom" in cf
    row_has_itemname = "item_name" in cf
    row_has_qty      = "quantity" in cf

    currencies = set()
    valid_rows: List[Dict[str, Any]] = []
    for ch in charges:
        item_code = getattr(ch, "item_code", None)
        if not item_code:
            continue
        qty   = flt(getattr(ch, "quantity", 0.0)) if row_has_qty   else 0.0
        rate  = flt(getattr(ch, "rate", 0.0))     if row_has_rate  else 0.0
        total = flt(getattr(ch, "total", 0.0))    if row_has_total else 0.0
        uom = (getattr(ch, "uom", None) or None) if row_has_uom else None
        item_name = (getattr(ch, "item_name", None) or None) if row_has_itemname else None
        curr = (getattr(ch, "currency", None) or "").strip() if row_has_currency else ""

        if row_has_currency and curr:
            currencies.add(curr)

        if qty and not rate and total:
            rate = total / qty
        if (not qty or qty == 0) and total and not rate:
            qty, rate = 1.0, total
        if not qty and not rate and not total:
            continue

        valid_rows.append({
            "item_code": item_code,
            "item_name": item_name,
            "qty": flt(qty) if qty else (1.0 if (total or rate) else 0.0),
            "rate": flt(rate) if rate else (flt(total) if (not qty and total) else 0.0),
            "uom": uom,
            "currency": curr or None,
        })

    if not valid_rows:
        frappe.throw(_("No valid charge rows to invoice."))

    chosen_currency = None
    if row_has_currency:
        currencies = {c for c in currencies if c}
        if len(currencies) > 1:
            frappe.throw(_("All charge rows must have the same currency. Found: {0}").format(", ".join(sorted(currencies))))
        chosen_currency = (list(currencies)[0] if currencies else None)

    si = frappe.new_doc("Sales Invoice")
    si.customer = customer
    si.company  = company
    if posting_date: si.posting_date = posting_date

    sif = _safe_meta_fieldnames("Sales Invoice")
    if "warehouse_job" in sif:
        setattr(si, "warehouse_job", job.name)
    else:
        base_remarks = (getattr(si, "remarks", "") or "").strip()
        note = _("Auto-created from Warehouse Job {0}").format(job.name)
        si.remarks = f"{base_remarks}\n{note}" if base_remarks else note

    if chosen_currency and "currency" in sif:
        si.currency = chosen_currency

    sif_item_fields = _safe_meta_fieldnames("Sales Invoice Item")
    for r in valid_rows:
        row_payload = {"item_code": r["item_code"], "qty": r["qty"] or 0.0, "rate": r["rate"] or 0.0}
        if "uom" in sif_item_fields and r.get("uom"): row_payload["uom"] = r["uom"]
        if "item_name" in sif_item_fields and r.get("item_name"): row_payload["item_name"] = r["item_name"]
        if cost_center and "cost_center" in sif_item_fields: row_payload["cost_center"] = cost_center
        si.append("items", row_payload)

    si.insert()
    return {"ok": True, "message": _("Sales Invoice {0} created.").format(si.name), "sales_invoice": si.name}

@frappe.whitelist()
def update_job_operations_times(warehouse_job: str, updates_json: str) -> dict:
    """
    updates_json: JSON list like
      [{ "name": "<child_name>", "start_datetime": "<iso>", "end_datetime": "<iso>" }, ...]
    - Works whether your doctype fields are start_datetime/end_datetime OR start_date/end_date.
    - Computes duration in hours into 'actual_hours' when both ends present (if field exists).
    """
    if not warehouse_job:
        frappe.throw(_("warehouse_job is required"))
    job = frappe.get_doc("Warehouse Job", warehouse_job)

    ops_fn = _find_child_table_field("Warehouse Job", "Warehouse Job Operations")
    if not ops_fn:
        frappe.throw(_("Warehouse Job has no Operations child table."))

    childf = _wjo_fields()
    has = lambda f: (f in childf)
    start_f, end_f = _ops_time_fields()

    try:
        updates = frappe.parse_json(updates_json or "[]")
        if not isinstance(updates, list):
            raise ValueError("updates_json must be a JSON array")
    except Exception as e:
        frappe.throw(_("Invalid updates_json: {0}").format(e))

    by_name = {getattr(r, "name", None): r for r in getattr(job, ops_fn, []) or []}
    changed = 0
    results = []

    for u in updates:
        cname = (u.get("name") or "").strip()
        if not cname or cname not in by_name:
            continue
        row = by_name[cname]

        s_raw = u.get("start_datetime")
        e_raw = u.get("end_datetime")
        s_dt = get_datetime(s_raw) if s_raw else None
        e_dt = get_datetime(e_raw) if e_raw else None

        # assign to actual fieldnames present
        if s_dt and start_f and has(start_f):
            setattr(row, start_f, s_dt)
        if e_dt and end_f and has(end_f):
            setattr(row, end_f, e_dt)

        dur_hours = None
        if s_dt and e_dt and has("actual_hours"):
            sec = max(0.0, (e_dt - s_dt).total_seconds())
            dur_hours = round(sec / 3600.0, 4)
            setattr(row, "actual_hours", dur_hours)

        results.append({
            "name": cname,
            "start_datetime": (s_dt or (getattr(row, start_f, None) if (start_f and has(start_f)) else None)),
            "end_datetime":   (e_dt or (getattr(row, end_f,   None) if (end_f   and has(end_f))   else None)),
            "actual_hours": (dur_hours if dur_hours is not None else (float(getattr(row, "actual_hours", 0) or 0) if has("actual_hours") else None)),
        })
        changed += 1

    if changed:
        job.save(ignore_permissions=True)
        frappe.db.commit()

    return {"ok": True, "updated": changed, "rows": results}

