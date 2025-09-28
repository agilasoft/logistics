from __future__ import annotations
from .common import *  # shared helpers

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate

@frappe.whitelist()
def warehouse_job_fetch_count_sheet(warehouse_job: str, clear_existing: int = 1):
    """Build Count Sheet for items present in Orders; respects Job scope."""
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "Stocktake":
        frappe.throw(_("Fetch Count Sheet is only available for Warehouse Job Type = Stocktake."))

    order_items = frappe.get_all(
        "Warehouse Job Order Items",
        filters={"parent": job.name, "parenttype": "Warehouse Job"},
        fields=["distinct item AS item"],
        ignore_permissions=True,
    )
    item_list = [r["item"] for r in order_items if (r.get("item") or "").strip()]
    item_set  = set(item_list)
    if not item_set:
        return {"ok": True, "message": _("No items found in Orders. Add items in the Orders table first."), "created_rows": 0}

    company, branch = _get_job_scope(job)

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

    slf = _safe_meta_fieldnames("Storage Location")
    huf = _safe_meta_fieldnames("Handling Unit")
    llf = _safe_meta_fieldnames("Warehouse Stock Ledger")

    conds = ["l.item IN ({})".format(", ".join(["%s"] * len(item_set)))]
    params: List[Any] = list(item_set)

    if company and (("company" in slf) or ("company" in huf) or ("company" in llf)) :
        conds.append("COALESCE(hu.company, sl.company, l.company) = %s"); params.append(company)
    if branch and  (("branch"  in slf) or ("branch"  in huf) or ("branch"  in llf)):
        conds.append("COALESCE(hu.branch,  sl.branch,  l.branch)  = %s"); params.append(branch)

    aggregates = frappe.db.sql(f"""
        SELECT l.item, l.storage_location, l.handling_unit, l.batch_no, l.serial_no,
               SUM(l.quantity) AS system_qty
        FROM `tabWarehouse Stock Ledger` l
        LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
        LEFT JOIN `tabHandling Unit`    hu ON hu.name = l.handling_unit
        WHERE {' AND '.join(conds)}
        GROUP BY l.item, l.storage_location, l.handling_unit, l.batch_no, l.serial_no
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

    for a in aggregates:
        if a.get("item") not in item_set: continue
        _append_count_row(a.get("item"), a.get("storage_location"), a.get("handling_unit"),
                          a.get("batch_no"), a.get("serial_no"), flt(a.get("system_qty") or 0))

    for it in item_set:
        for loc in locations:
            _append_count_row(it, loc["name"], None, None, None, 0)
        for hu in hus:
            _append_count_row(it, None, hu["name"], None, None, 0)

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

    job.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "message": _("Created {0} adjustment item(s). Net delta: {1}").format(int(created), flt(net_delta)),
            "created_rows": int(created), "net_delta": flt(net_delta)}

