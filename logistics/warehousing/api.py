# Copyright (c) 2025, www.agilasoft.com
# For license information, please see license.txt

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
from datetime import date, timedelta

import frappe
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate


# =============================================================================
# Meta helpers
# =============================================================================

def _safe_meta_fieldnames(doctype: str) -> set:
    meta = frappe.get_meta(doctype)
    out = set()
    for df in meta.get("fields", []) or []:
        fn = getattr(df, "fieldname", None) or (df.get("fieldname") if isinstance(df, dict) else None)
        if fn:
            out.add(fn)
    return out


def _find_child_table_field(parent_doctype: str, child_doctype: str) -> Optional[str]:
    meta = frappe.get_meta(parent_doctype)
    for df in meta.get("fields", []) or []:
        if (getattr(df, "fieldtype", None) or df.get("fieldtype")) == "Table":
            if (getattr(df, "options", None) or df.get("options")) == child_doctype:
                return getattr(df, "fieldname", None) or df.get("fieldname")
    return None


# =============================================================================
# Scope helpers (Company / Branch)
# =============================================================================

def _get_job_scope(job: Any) -> Tuple[Optional[str], Optional[str]]:
    jf = _safe_meta_fieldnames("Warehouse Job")
    company = getattr(job, "company", None) if "company" in jf else None
    branch  = getattr(job, "branch", None)  if "branch"  in jf else None
    return company or None, branch or None


def _get_location_scope(location: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not location:
        return None, None
    lf = _safe_meta_fieldnames("Storage Location")
    fields = []
    if "company" in lf: fields.append("company")
    if "branch"  in lf: fields.append("branch")
    if not fields:
        return None, None
    row = frappe.db.get_value("Storage Location", location, fields, as_dict=True) or {}
    return row.get("company"), row.get("branch")


def _get_handling_unit_scope(hu_name: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not hu_name:
        return None, None
    hf = _safe_meta_fieldnames("Handling Unit")
    fields = []
    if "company" in hf: fields.append("company")
    if "branch"  in hf: fields.append("branch")
    if not fields:
        return None, None
    row = frappe.db.get_value("Handling Unit", hu_name, fields, as_dict=True) or {}
    return row.get("company"), row.get("branch")


def _same_scope(job_company: Optional[str], job_branch: Optional[str],
                entity_company: Optional[str], entity_branch: Optional[str]) -> bool:
    if job_company and (entity_company not in (None, job_company)):
        return False
    if job_branch and (entity_branch not in (None, job_branch)):
        return False
    return True


def _assert_location_in_job_scope(location: Optional[str], job_company: Optional[str],
                                  job_branch: Optional[str], ctx: str = "Location"):
    if not location:
        return
    lc, lb = _get_location_scope(location)
    if not _same_scope(job_company, job_branch, lc, lb):
        frappe.throw(_("{0} {1} is out of scope for Company/Branch on this Job.").format(ctx, location))


def _assert_hu_in_job_scope(hu: Optional[str], job_company: Optional[str],
                            job_branch: Optional[str], ctx: str = "Handling Unit"):
    if not hu:
        return
    hc, hb = _get_handling_unit_scope(hu)
    if not _same_scope(job_company, job_branch, hc, hb):
        frappe.throw(_("{0} {1} is out of scope for Company/Branch on this Job.").format(ctx, hu))


# =============================================================================
# Small utils
# =============================================================================

def _get_item_uom(item: Optional[str]) -> Optional[str]:
    if not item:
        return None
    return frappe.db.get_value("Warehouse Item", item, "uom")


def _fetch_job_order_items(job_name: str) -> List[Dict[str, Any]]:
    return frappe.get_all(
        "Warehouse Job Order Items",
        filters={"parent": job_name, "parenttype": "Warehouse Job"},
        fields=["name", "item", "quantity", "uom", "serial_no", "batch_no", "handling_unit"],
        order_by="idx asc",
        ignore_permissions=True,
    ) or []


# =============================================================================
# Availability query (scoped by Company/Branch)
# =============================================================================

def _query_available_candidates(
    item: str,
    *,
    company: Optional[str],
    branch: Optional[str],
    batch_no: Optional[str] = None,
    serial_no: Optional[str] = None,
) -> List[Dict[str, Any]]:
    slf = _safe_meta_fieldnames("Storage Location")
    huf = _safe_meta_fieldnames("Handling Unit")
    llf = _safe_meta_fieldnames("Warehouse Stock Ledger")

    conds = []
    params: List[Any] = [item, batch_no, batch_no, serial_no, serial_no]

    if company and (("company" in slf) or ("company" in huf) or ("company" in llf)):
        conds.append("COALESCE(hu.company, sl.company, l.company) = %s")
        params.append(company)
    if branch and (("branch" in slf) or ("branch" in huf) or ("branch" in llf)):
        conds.append("COALESCE(hu.branch, sl.branch, l.branch) = %s")
        params.append(branch)

    scope_sql = (" AND " + " AND ".join(conds)) if conds else ""

    sql = f"""
        SELECT
            l.storage_location,
            l.handling_unit,
            l.batch_no,
            l.serial_no,
            SUM(l.quantity) AS available_qty,
            MIN(l.posting_date) AS first_seen,
            MAX(l.posting_date) AS last_seen,
            b.expiry_date AS expiry_date,
            IFNULL(sl.bin_priority, 999999) AS bin_priority
        FROM `tabWarehouse Stock Ledger` l
        LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
        LEFT JOIN `tabHandling Unit` hu    ON hu.name = l.handling_unit
        LEFT JOIN `tabWarehouse Batch` b   ON b.name = l.batch_no
        WHERE l.item = %s
          AND (%s IS NULL OR l.batch_no = %s)
          AND (%s IS NULL OR l.serial_no = %s)
          {scope_sql}
        GROUP BY l.storage_location, l.handling_unit, l.batch_no, l.serial_no
        HAVING SUM(l.quantity) > 0
    """
    return frappe.db.sql(sql, tuple(params), as_dict=True) or []


def _order_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    def key(c):
        # FIFO by first_seen, then bin priority, then largest qty first
        return (
            c.get("first_seen") or now_datetime(),
            int(c.get("bin_priority") or 999999),
            -flt(c.get("available_qty") or 0),
        )
    return sorted(candidates, key=key)


def _greedy_allocate(candidates: List[Dict[str, Any]], required_qty: float) -> List[Dict[str, Any]]:
    remaining = flt(required_qty)
    out: List[Dict[str, Any]] = []
    for c in candidates:
        if remaining <= 0:
            break
        avail = max(0.0, flt(c.get("available_qty") or 0.0))
        if avail <= 0:
            continue
        take = min(avail, remaining)
        out.append({
            "location": c.get("storage_location"),
            "handling_unit": c.get("handling_unit"),
            "batch_no": c.get("batch_no"),
            "serial_no": c.get("serial_no"),
            "qty": take,
        })
        remaining -= take
    return out


def _append_job_items(job: Any, *, item: str, uom: Optional[str], allocations: List[Dict[str, Any]],
                      source_row: Optional[str]) -> Tuple[int, float]:
    created_rows = 0
    created_qty = 0.0

    jf = _safe_meta_fieldnames("Warehouse Job Item")
    for a in allocations:
        qty = flt(a.get("qty") or 0)
        if qty == 0:
            continue
        payload = {
            "location": a.get("location"),
            "handling_unit": a.get("handling_unit"),
            "item": item,
            "quantity": qty,
            "serial_no": a.get("serial_no"),
            "batch_no": a.get("batch_no"),
        }
        if "uom" in jf and uom:
            payload["uom"] = uom
        if "source_row" in jf and source_row:
            payload["source_row"] = source_row
        if "source_parent" in jf:
            payload["source_parent"] = job.name

        job.append("items", payload)
        created_rows += 1
        created_qty += qty

    return created_rows, created_qty


# =============================================================================
# Putaway candidate locations (exclude staging)
# =============================================================================

def _putaway_candidate_locations(
    *,
    item: str,
    company: Optional[str],
    branch: Optional[str],
    exclude_locations: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    exclude_locations = exclude_locations or []

    # Consolidation: locations already holding the item, exclude staging bins and explicit excludes
    cons = frappe.db.sql(
        """
        SELECT
            l.storage_location AS location,
            IFNULL(sl.bin_priority, 999999) AS bin_priority
        FROM `tabWarehouse Stock Ledger` l
        LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
        WHERE l.item = %s
          AND (%s IS NULL OR sl.company = %s)
          AND (%s IS NULL OR sl.branch  = %s)
          AND IFNULL(sl.staging_area, 0) = 0
          {not_in}
        GROUP BY l.storage_location, sl.bin_priority
        HAVING SUM(l.quantity) > 0
        ORDER BY bin_priority ASC
        """.format(
            not_in=("AND l.storage_location NOT IN ({})".format(
                ", ".join(["%s"] * len(exclude_locations))) if exclude_locations else "")
        ),
        tuple([item, company, company, branch, branch] + exclude_locations),
        as_dict=True,
    ) or []
    cons_set = {r["location"] for r in cons}

    # Other in-scope locations, excluding staging and excludes
    others = frappe.db.sql(
        """
        SELECT
            sl.name AS location,
            IFNULL(sl.bin_priority, 999999) AS bin_priority
        FROM `tabStorage Location` sl
        WHERE (%s IS NULL OR sl.company = %s)
          AND (%s IS NULL OR sl.branch  = %s)
          AND IFNULL(sl.staging_area, 0) = 0
          {not_in}
        ORDER BY bin_priority ASC
        """.format(
            not_in=("AND sl.name NOT IN ({})".format(", ".join(["%s"] * len(exclude_locations)))
                    if exclude_locations else "")
        ),
        tuple([company, company, branch, branch] + exclude_locations),
        as_dict=True,
    ) or []
    # Keep only the ones not already in cons list
    others = [r for r in others if r["location"] not in cons_set]

    return cons + others


# =============================================================================
# ALLOCATIONS
# =============================================================================

@frappe.whitelist()
def allocate_pick(warehouse_job: str) -> Dict[str, Any]:
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "Pick":
        frappe.throw(_("Allocate Picks can only run for Warehouse Job Type = Pick."))

    company, branch = _get_job_scope(job)
    jo_items = _fetch_job_order_items(job.name)
    if not jo_items:
        return {"ok": True, "message": _("No items found on Warehouse Job Order Items."), "created_rows": 0, "created_qty": 0}

    total_rows = 0
    total_qty = 0.0
    details: List[Dict[str, Any]] = []
    warns: List[str] = []

    for r in jo_items:
        item = r.get("item")
        req_qty = flt(r.get("quantity") or 0)
        if not item or req_qty <= 0:
            continue

        candidates = _query_available_candidates(
            item=item,
            company=company,
            branch=branch,
            batch_no=r.get("batch_no") or None,
            serial_no=r.get("serial_no") or None,
        )
        ordered = _order_candidates(candidates)
        allocs = _greedy_allocate(ordered, req_qty)

        if not allocs:
            scope = []
            if company: scope.append(_("Company={0}").format(company))
            if branch:  scope.append(_("Branch={0}").format(branch))
            warns.append(_("No allocatable stock for Item {0} (Row {1}) within scope{2}.").format(
                item, r.get("name"), (" [" + ", ".join(scope) + "]") if scope else ""
            ))

        cr, cq = _append_job_items(job, item=item, uom=r.get("uom"), allocations=allocs, source_row=r.get("name"))
        total_rows += cr
        total_qty  += cq

        details.append({
            "order_row": r.get("name"),
            "item": item,
            "requested_qty": req_qty,
            "created_rows": cr,
            "created_qty": cq,
            "short_qty": max(0.0, req_qty - cq),
        })

    job.save(ignore_permissions=True)
    frappe.db.commit()

    msg = _("Allocated {0} units across {1} pick rows.").format(flt(total_qty), int(total_rows))
    if warns:
        msg += " " + _("Notes") + ": " + " | ".join(warns)

    return {"ok": True, "message": msg, "created_rows": total_rows, "created_qty": total_qty, "lines": details, "warnings": warns}


@frappe.whitelist()
def allocate_putaway(warehouse_job: str) -> Dict[str, Any]:
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "Putaway":
        frappe.throw(_("Allocate Putaway can only run for Warehouse Job Type = Putaway."))

    company, branch = _get_job_scope(job)
    orders = _fetch_job_order_items(job.name)
    if not orders:
        return {"ok": True, "message": _("No items found on Warehouse Job Order Items."), "created_rows": 0, "created_qty": 0}

    jf = _safe_meta_fieldnames("Warehouse Job Item")
    dest_field = "location" if "location" in jf else ("to_location" if "to_location" in jf else None)

    created_rows = 0
    created_qty  = 0.0
    details: List[Dict[str, Any]] = []
    warns: List[str] = []

    # exclude: any location marked staging_area == 1 plus the Job's own staging_area
    exclude = []
    job_staging = getattr(job, "staging_area", None)
    if job_staging:
        exclude.append(job_staging)

    cached: Dict[str, List[Dict[str, Any]]] = {}

    for r in orders:
        qty = flt(r.get("quantity") or 0)
        if qty <= 0:
            continue
        item = r.get("item")

        # choose best destination (excluding staging)
        if item not in cached:
            cached[item] = _putaway_candidate_locations(item=item, company=company, branch=branch, exclude_locations=exclude)
        dest = cached[item][0]["location"] if cached[item] else None

        # validate HU in scope if provided
        hu = (r.get("handling_unit") or "").strip() or None
        _assert_hu_in_job_scope(hu, company, branch, ctx=_("Handling Unit"))
        if dest:
            _assert_location_in_job_scope(dest, company, branch, ctx=_("Destination Location"))

        payload = {
            "item": item,
            "quantity": qty,
            "serial_no": r.get("serial_no") or None,
            "batch_no": r.get("batch_no") or None,
            "handling_unit": hu,
        }
        if dest_field and dest:
            payload[dest_field] = dest
        if "uom" in jf and r.get("uom"):
            payload["uom"] = r.get("uom")
        if "source_row" in jf:
            payload["source_row"] = r.get("name")
        if "source_parent" in jf:
            payload["source_parent"] = job.name

        job.append("items", payload)
        created_rows += 1
        created_qty  += qty

        if not dest:
            warns.append(_("Order Row {0}: no destination location available in scope.").format(r.get("name")))
        if not hu:
            warns.append(_("Order Row {0}: no handling unit provided.").format(r.get("name")))

        details.append({"order_row": r.get("name"), "item": item, "qty": qty, "dest_location": dest, "dest_handling_unit": hu})

    job.save(ignore_permissions=True)
    frappe.db.commit()

    msg = _("Prepared {0} units across {1} putaway rows (staging excluded).").format(flt(created_qty), int(created_rows))
    if warns:
        msg += " " + _("Notes") + ": " + " | ".join(warns)

    return {"ok": True, "message": msg, "created_rows": created_rows, "created_qty": created_qty, "lines": details, "warnings": warns}


@frappe.whitelist()
def allocate_move(warehouse_job: str, clear_existing: int = 1) -> Dict[str, Any]:
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
        f_loc = getattr(r, "storage_location_from", None)
        t_loc = getattr(r, "storage_location_to", None)
        hu_f  = getattr(r, "handling_unit_from", None)
        hu_t  = getattr(r, "handling_unit_to", None)

        if not f_loc or not t_loc or qty <= 0:
            skipped.append(_("Row {0}: missing From/To or qty <= 0").format(getattr(r, "idx", "?")))
            continue

        _assert_location_in_job_scope(f_loc, company, branch, ctx=_("From Location"))
        _assert_location_in_job_scope(t_loc, company, branch, ctx=_("To Location"))
        _assert_hu_in_job_scope(hu_f, company, branch, ctx=_("From HU"))
        _assert_hu_in_job_scope(hu_t, company, branch, ctx=_("To HU"))

        common = {
            "item": getattr(r, "item", None),
            "serial_no": getattr(r, "serial_no", None) or None,
            "batch_no": getattr(r, "batch_no", None) or None,
        }
        job.append("items", {**common, "location": f_loc, "handling_unit": hu_f or None, "quantity": -qty})
        job.append("items", {**common, "location": t_loc, "handling_unit": hu_t or None, "quantity":  qty})
        created_pairs += 1

    job.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "message": _("Allocated {0} move pair(s).").format(created_pairs), "created_pairs": created_pairs, "skipped": skipped}


# =============================================================================
# COUNT SHEET + ADJUSTMENTS
# =============================================================================

@frappe.whitelist()
def warehouse_job_fetch_count_sheet(warehouse_job: str, clear_existing: int = 1):
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "Stocktake":
        frappe.throw(_("Fetch Count Sheet is only available for Warehouse Job Type = Stocktake."))

    orders = frappe.get_all(
        "Warehouse Job Order Items",
        filters={"parent": job.name, "parenttype": "Warehouse Job"},
        fields=["distinct item AS item"],
        ignore_permissions=True,
    )
    item_list = [r["item"] for r in orders if (r.get("item") or "").strip()]
    if not item_list:
        return {"ok": True, "message": _("No items found in Orders. Add items in the Orders table first."), "created_rows": 0}

    company, branch = _get_job_scope(job)

    if int(clear_existing or 0):
        job.set("counts", [])

    conds = ["l.item IN ({})".format(", ".join(["%s"] * len(item_list)))]
    params: List[Any] = list(item_list)

    slf = _safe_meta_fieldnames("Storage Location")
    huf = _safe_meta_fieldnames("Handling Unit")
    llf = _safe_meta_fieldnames("Warehouse Stock Ledger")

    if company and (("company" in slf) or ("company" in huf) or ("company" in llf)):
        conds.append("COALESCE(hu.company, sl.company, l.company) = %s"); params.append(company)
    if branch and (("branch" in slf) or ("branch" in huf) or ("branch" in llf)):
        conds.append("COALESCE(hu.branch, sl.branch, l.branch) = %s"); params.append(branch)

    sql = f"""
        SELECT l.item, l.storage_location, l.handling_unit, l.batch_no, l.serial_no,
               SUM(l.quantity) AS system_qty
        FROM `tabWarehouse Stock Ledger` l
        LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
        LEFT JOIN `tabHandling Unit` hu    ON hu.name = l.handling_unit
        WHERE {' AND '.join(conds)}
        GROUP BY l.item, l.storage_location, l.handling_unit, l.batch_no, l.serial_no
        HAVING SUM(l.quantity) > 0
    """
    aggregates = frappe.db.sql(sql, tuple(params), as_dict=True) or []

    created = 0
    blind = int(getattr(job, "blind_count", 0) or 0)

    seen = set()
    for a in aggregates:
        key = (a["item"] or "", a.get("storage_location") or "", a.get("handling_unit") or "",
               a.get("batch_no") or "", a.get("serial_no") or "")
        if key in seen:
            continue
        job.append("counts", {
            "item": a["item"],
            "location": a.get("storage_location"),
            "handling_unit": a.get("handling_unit"),
            "batch_no": a.get("batch_no"),
            "serial_no": a.get("serial_no"),
            "system_count": (None if blind else flt(a.get("system_qty") or 0)),
            "actual_quantity": None,
            "blind_count": blind,
        })
        created += 1
        seen.add(key)

    job.save(ignore_permissions=True)
    frappe.db.commit()
    msg = _("Created {0} count line(s).").format(created)
    if blind: msg += " " + _("Blind: system counts hidden")
    return {"ok": True, "message": msg, "created_rows": created}


@frappe.whitelist()
def populate_stocktake_adjustments(warehouse_job: str, clear_existing: int = 1):
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    if (job.type or "").strip() != "Stocktake":
        frappe.throw(_("This action is only available for Warehouse Job Type = Stocktake."))

    if int(clear_existing or 0):
        job.set("items", [])

    jf = _safe_meta_fieldnames("Warehouse Job Item")
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

        payload = {
            "item": getattr(r, "item", None),
            "quantity": delta,
            "serial_no": getattr(r, "serial_no", None) or None,
            "batch_no": getattr(r, "batch_no", None) or None,
        }
        if "location" in jf:
            payload["location"] = getattr(r, "location", None) or None
        if "handling_unit" in jf:
            payload["handling_unit"] = getattr(r, "handling_unit", None) or None
        if "uom" in jf:
            payload["uom"] = _get_item_uom(payload["item"])
        if "source_row" in jf:
            payload["source_row"] = f"COUNT:{getattr(r, 'name', '')}"
        if "source_parent" in jf:
            payload["source_parent"] = job.name

        job.append("items", payload)
        created += 1
        net_delta += delta

    job.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "message": _("Created {0} adjustment item(s). Net delta: {1}").format(int(created), flt(net_delta))}


# =============================================================================
# JOB OPERATIONS
# =============================================================================

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
        SELECT name, operation_name, IFNULL(unit_std_hours, 0) AS unit_std_hours, handling_uom, notes
        FROM `tabWarehouse Operation Item` WHERE used_in = %s
    """
    if job_type == "VAS" and getattr(job, "vas_order_type", None):
        sql += " AND (vas_order_type = %s OR IFNULL(vas_order_type, '') = '')"
        params.append(job.vas_order_type)
    sql += " ORDER BY operation_name ASC"

    ops = frappe.db.sql(sql, tuple(params), as_dict=True) or []
    if not ops:
        return {"ok": True, "message": _("No Warehouse Operation Item found for type {0}.").format(job_type), "created_rows": 0}

    child_fields = _safe_meta_fieldnames("Warehouse Job Operations")
    existing_codes = {getattr(r, "operation", None) for r in getattr(job, ops_field) or []}

    created = 0
    for op in ops:
        code = op["name"]
        if code in existing_codes:
            continue
        unit_std = flt(op.get("unit_std_hours") or 0)
        qty = flt(qty_baseline or 0)

        payload: Dict[str, Any] = {"operation": code}
        if "description" in child_fields:
            payload["description"] = op.get("operation_name")
        if "handling_uom" in child_fields and op.get("handling_uom"):
            payload["handling_uom"] = op.get("handling_uom")
        if "quantity" in child_fields:
            payload["quantity"] = qty
        if "unit_std_hours" in child_fields:
            payload["unit_std_hours"] = unit_std
        if "total_std_hours" in child_fields:
            payload["total_std_hours"] = unit_std * qty
        if "actual_hours" in child_fields:
            payload["actual_hours"] = None
        if "notes" in child_fields and op.get("notes"):
            payload["notes"] = op.get("notes")

        job.append(ops_field, payload)
        created += 1

    job.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "message": _("Added {0} operation(s).").format(created), "created_rows": created, "qty_baseline": qty_baseline}


# =============================================================================
# SALES INVOICE FROM JOB CHARGES
# =============================================================================

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
    charges = list(getattr(job, charges_field, []) or [])
    if not charges:
        frappe.throw(_("No rows found in {0}.").format(_("Warehouse Job Charges")))

    jf = _safe_meta_fieldnames("Warehouse Job")
    customer = customer or (getattr(job, "customer", None) if "customer" in jf else None)
    company  = company  or (getattr(job, "company",  None) if "company"  in jf else None)

    if not customer: frappe.throw(_("Customer is required (set on Warehouse Job or pass it here)."))
    if not company:  frappe.throw(_("Company is required."))

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

    item_fields = _safe_meta_fieldnames("Sales Invoice Item")
    row_fields  = _safe_meta_fieldnames("Warehouse Job Charges")
    created = 0

    for ch in charges:
        item_code = getattr(ch, "item_code", None)
        if not item_code:
            continue
        qty   = flt(getattr(ch, "quantity", 0.0)) if "quantity" in row_fields else 0.0
        rate  = flt(getattr(ch, "rate", 0.0))     if "rate" in row_fields     else 0.0
        total = flt(getattr(ch, "total", 0.0))    if "total" in row_fields    else 0.0
        if qty and not rate and total:
            rate = total / qty
        if (not qty) and total and not rate:
            qty, rate = 1.0, total
        if not qty and not rate and not total:
            continue

        row = {"item_code": item_code, "qty": qty or 0.0, "rate": rate or (total if (not qty and total) else 0.0)}
        if "uom" in item_fields and "uom" in row_fields:
            uom = getattr(ch, "uom", None)
            if uom: row["uom"] = uom
        if "item_name" in item_fields and "item_name" in row_fields:
            nm = getattr(ch, "item_name", None)
            if nm: row["item_name"] = nm
        if "cost_center" in item_fields and cost_center:
            row["cost_center"] = cost_center

        si.append("items", row)
        created += 1

    if not created:
        frappe.throw(_("No valid charge rows to invoice."))

    si.insert()
    return {"ok": True, "message": _("Sales Invoice {0} created.").format(si.name), "sales_invoice": si.name, "created_rows": created}


# =============================================================================
# PERIODIC BILLING (minimal)
# =============================================================================

def _pb__charges_fieldname() -> Optional[str]:
    return _find_child_table_field("Periodic Billing", "Periodic Billing Charges")


@frappe.whitelist()
def periodic_billing_get_charges(periodic_billing: str, clear_existing: int = 1) -> Dict[str, Any]:
    pb = frappe.get_doc("Periodic Billing", periodic_billing)
    customer = getattr(pb, "customer", None)
    date_from = getattr(pb, "date_from", None)
    date_to   = getattr(pb, "date_to", None)
    if not (customer and date_from and date_to):
        frappe.throw(_("Customer, Date From and Date To are required."))

    charges_field = _pb__charges_fieldname()
    if not charges_field:
        return {"ok": False, "message": _("Periodic Billing has no child table for 'Periodic Billing Charges'."), "created": 0}

    if int(clear_existing or 0):
        pb.set(charges_field, [])

    created = 0
    grand_total = 0.0

    jobs = frappe.get_all(
        "Warehouse Job",
        filters={"docstatus": 1, "customer": customer, "job_open_date": ["between", [date_from, date_to]]},
        fields=["name", "job_open_date"],
        order_by="job_open_date asc, name asc",
        ignore_permissions=True,
    ) or []

    if jobs:
        job_names = [j["name"] for j in jobs]
        placeholders = ", ".join(["%s"] * len(job_names))
        rows = frappe.db.sql(
            f"""SELECT c.parent AS warehouse_job, c.item_code, c.item_name, c.uom, c.quantity, c.rate, c.total, c.currency
                FROM `tabWarehouse Job Charges` c
                WHERE c.parent IN ({placeholders})
                ORDER BY FIELD(c.parent, {placeholders})""",
            tuple(job_names + job_names),
            as_dict=True,
        ) or []
        for r in rows:
            qty   = flt(r.get("quantity") or 0)
            rate  = flt(r.get("rate") or 0)
            total = flt(r.get("total") or (qty * rate))
            pb.append(charges_field, {
                "item": r.get("item_code"),
                "item_name": r.get("item_name"),
                "uom": r.get("uom"),
                "quantity": qty,
                "rate": rate,
                "total": total,
                "currency": r.get("currency"),
                "warehouse_job": r.get("warehouse_job"),
            })
            created += 1
            grand_total += total

    pb.save(ignore_permissions=True)
    frappe.db.commit()
    return {"ok": True, "message": _("Added {0} charge line(s). Total: {1}").format(int(created), flt(grand_total)), "created": int(created), "grand_total": flt(grand_total)}


@frappe.whitelist()
def create_sales_invoice_from_periodic_billing(
    periodic_billing: str,
    posting_date: Optional[str] = None,
    company: Optional[str] = None,
    cost_center: Optional[str] = None,
) -> Dict[str, Any]:
    if not periodic_billing:
        frappe.throw(_("periodic_billing is required"))

    pb = frappe.get_doc("Periodic Billing", periodic_billing)
    customer  = getattr(pb, "customer", None)
    date_from = getattr(pb, "date_from", None)
    date_to   = getattr(pb, "date_to", None)
    if not customer:
        frappe.throw(_("Customer is required on Periodic Billing."))
    if not (date_from and date_to):
        frappe.throw(_("Date From and Date To are required on Periodic Billing."))

    charges_field = _find_child_table_field("Periodic Billing", "Periodic Billing Charges")
    if not charges_field:
        frappe.throw(_("Periodic Billing has no child table for 'Periodic Billing Charges'."))

    charges = list(getattr(pb, charges_field, []) or [])
    if not charges:
        frappe.throw(_("No rows found in Periodic Billing Charges."))

    company = company or frappe.defaults.get_default("company")
    if not company:
        frappe.throw(_("Company is required (pass it in, or set a Default Company)."))

    si = frappe.new_doc("Sales Invoice")
    si.customer = customer
    si.company = company
    if posting_date: si.posting_date = posting_date

    sif = _safe_meta_fieldnames("Sales Invoice")
    if "periodic_billing" in sif:
        setattr(si, "periodic_billing", pb.name)

    base_remarks = (getattr(si, "remarks", "") or "").strip()
    notes = [
        _("Auto-created from Periodic Billing {0}").format(pb.name),
        _("Period: {0} to {1}").format(date_from, date_to),
    ]
    si.remarks = (base_remarks + ("\n" if base_remarks else "") + "\n".join(notes)).strip()

    item_fields = _safe_meta_fieldnames("Sales Invoice Item")
    row_fields  = _safe_meta_fieldnames("Periodic Billing Charges")

    created_rows = 0
    for ch in charges:
        item_code = getattr(ch, "item", None) or getattr(ch, "item_code", None)
        if not item_code:
            continue

        qty   = flt(getattr(ch, "quantity", 0.0)) if "quantity" in row_fields else 0.0
        rate  = flt(getattr(ch, "rate", 0.0))     if "rate" in row_fields else 0.0
        total = flt(getattr(ch, "total", 0.0))    if "total" in row_fields else 0.0
        if qty and not rate and total:
            rate = total / qty
        if (not qty) and total and not rate:
            qty, rate = 1.0, total
        if not qty and not rate and not total:
            continue

        row = {"item_code": item_code, "qty": qty or 0.0, "rate": rate or (total if (not qty and total) else 0.0)}
        if "uom" in item_fields and "uom" in row_fields:
            uom = getattr(ch, "uom", None)
            if uom: row["uom"] = uom
        if "item_name" in item_fields and "item_name" in row_fields:
            nm = getattr(ch, "item_name", None)
            if nm: row["item_name"] = nm
        if "cost_center" in item_fields and cost_center:
            row["cost_center"] = cost_center

        si.append("items", row)
        created_rows += 1

    if created_rows == 0:
        frappe.throw(_("No valid Periodic Billing Charges to create Sales Invoice items."))

    si.insert()
    return {"ok": True, "message": _("Sales Invoice {0} created.").format(si.name), "sales_invoice": si.name, "created_rows": created_rows}


# =============================================================================
# LEDGER POSTING — NEW FLOW WITH PER-ROW DEDUPE
# =============================================================================

def _posting_datetime(job: Any):
    dt = getattr(job, "job_open_date", None)
    return get_datetime(dt) if dt else now_datetime()


def _ledger_has_field(fieldname: str) -> bool:
    return fieldname in _safe_meta_fieldnames("Warehouse Stock Ledger")


def _insert_ledger_entry(
    job: Any,
    *,
    item: str,
    qty: float,
    location: Optional[str],
    handling_unit: Optional[str],
    batch_no: Optional[str],
    serial_no: Optional[str],
    posting_dt,
):
    company, branch = _get_job_scope(job)
    if not company or not branch:
        frappe.throw(_("Company and Branch must be set on the Warehouse Job."))

    _assert_location_in_job_scope(location, company, branch)
    _assert_hu_in_job_scope(handling_unit, company, branch)

    led = frappe.new_doc("Warehouse Stock Ledger")
    led.posting_date     = posting_dt
    if _ledger_has_field("warehouse_job"):
        led.warehouse_job = job.name
    led.item             = item
    led.storage_location = location
    if _ledger_has_field("handling_unit"): led.handling_unit = handling_unit or None
    if _ledger_has_field("serial_no"):     led.serial_no     = serial_no or None
    if _ledger_has_field("batch_no"):      led.batch_no      = batch_no or None
    led.quantity         = qty
    if _ledger_has_field("company"): led.company = company
    if _ledger_has_field("branch"):  led.branch  = branch
    led.insert(ignore_permissions=True)


# -------- Per-row dedupe helpers (flags + timestamps if fields exist) --------

def _row_flag_fields() -> Dict[str, Tuple[str, str]]:
    """Map action -> (flag_field, timestamp_field) IF they exist on child row."""
    jf = _safe_meta_fieldnames("Warehouse Job Item")
    out: Dict[str, Tuple[str, str]] = {}
    pairs = {
        "pick":       ("pick_posted",       "pick_posted_at"),
        "staging":    ("staging_posted",    "staging_posted_at"),
        "putaway":    ("putaway_posted",    "putaway_posted_at"),
        "release":    ("release_posted",    "release_posted_at"),
        "receiving":  ("receiving_posted",  "receiving_posted_at"),
    }
    for action, (f, t) in pairs.items():
        if f in jf:
            out[action] = (f, t if t in jf else "")
    return out


def _row_is_already_posted(row: Any, action: str) -> bool:
    flags = _row_flag_fields()
    if action not in flags:
        return False
    f, _ = flags[action]
    return bool(getattr(row, f, 0))


def _mark_row_posted(row: Any, action: str, when) -> None:
    flags = _row_flag_fields()
    if action not in flags:
        return
    f, t = flags[action]
    setattr(row, f, 1)
    if t:
        setattr(row, t, when)


def _maybe_set_staging_area_on_row(row: Any, staging_area: Optional[str]) -> None:
    if not staging_area:
        return
    jf = _safe_meta_fieldnames("Warehouse Job Item")
    if "staging_area" in jf and not getattr(row, "staging_area", None):
        setattr(row, "staging_area", staging_area)


# ------------------------- Posting functions -------------------------

@frappe.whitelist()
def post_receiving(warehouse_job: str) -> Dict[str, Any]:
    """
    Putaway flow step 1:
      * In: Staging (ABS(qty)) for each item row.
      * Sets row.staging_area (if field exists).
      * Marks per-row 'staging_posted' (or 'receiving_posted' if present).
    """
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    staging_area = getattr(job, "staging_area", None)
    if not staging_area:
        frappe.throw(_("Staging Area is required on the Warehouse Job."))

    posting_dt = _posting_datetime(job)
    created = 0
    skipped: List[str] = []

    # choose action key for the staging step
    action_key = "staging" if "staging_posted" in _safe_meta_fieldnames("Warehouse Job Item") else "receiving"

    for it in (job.items or []):
        if _row_is_already_posted(it, action_key):
            skipped.append(_("Item Row {0}: staging already posted.").format(getattr(it, "idx", "?")))
            continue
        item = getattr(it, "item", None)
        qty  = abs(flt(getattr(it, "quantity", 0)))
        if not item or qty == 0:
            continue
        hu   = getattr(it, "handling_unit", None)
        bn   = getattr(it, "batch_no", None)
        sn   = getattr(it, "serial_no", None)

        _insert_ledger_entry(job, item=item, qty=qty, location=staging_area,
                             handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt)
        _mark_row_posted(it, action_key, posting_dt)
        _maybe_set_staging_area_on_row(it, staging_area)
        created += 1

    job.save(ignore_permissions=True)
    frappe.db.commit()

    msg = _("Receiving posted into staging: {0} entry(ies).").format(created)
    if skipped:
        msg += " " + _("Skipped") + f": {len(skipped)}"
    return {"ok": True, "message": msg, "created": created, "skipped": skipped}


@frappe.whitelist()
def post_putaway(warehouse_job: str) -> Dict[str, Any]:
    """
    Putaway flow step 2:
      * Out: Staging (−ABS(qty))
      * In:  Destination (item.location or item.to_location)
      * Marks per-row 'putaway_posted'
    """
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    staging_area = getattr(job, "staging_area", None)
    if not staging_area:
        frappe.throw(_("Staging Area is required on the Warehouse Job."))

    posting_dt = _posting_datetime(job)
    jf = _safe_meta_fieldnames("Warehouse Job Item")

    created_out = created_in = 0
    skipped: List[str] = []

    for it in (job.items or []):
        if _row_is_already_posted(it, "putaway"):
            skipped.append(_("Item Row {0}: putaway already posted.").format(getattr(it, "idx", "?")))
            continue

        item = getattr(it, "item", None)
        qty  = abs(flt(getattr(it, "quantity", 0)))
        if not item or qty == 0:
            continue
        hu   = getattr(it, "handling_unit", None)
        bn   = getattr(it, "batch_no", None)
        sn   = getattr(it, "serial_no", None)
        dest = getattr(it, "to_location", None) if "to_location" in jf else getattr(it, "location", None)

        if not dest:
            skipped.append(_("Item Row {0}: missing destination location.").format(getattr(it, "idx", "?")))
            continue

        # OUT staging
        _insert_ledger_entry(job, item=item, qty=-qty, location=staging_area,
                             handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt)
        created_out += 1
        # IN destination
        _insert_ledger_entry(job, item=item, qty=qty, location=dest,
                             handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt)
        created_in += 1

        _mark_row_posted(it, "putaway", posting_dt)

    job.save(ignore_permissions=True)
    frappe.db.commit()

    msg = _("Putaway posted: {0} OUT from staging, {1} IN to destinations.").format(created_out, created_in)
    if skipped:
        msg += " " + _("Skipped") + f": {len(skipped)}"
    return {"ok": True, "message": msg, "out_from_staging": created_out, "in_to_destination": created_in, "skipped": skipped}


@frappe.whitelist()
def post_pick(warehouse_job: str) -> Dict[str, Any]:
    """
    Pick flow step 1 and VAS step 1:
      * Out: Location (−ABS(qty)) — from item.location
      * In:  Staging  (+ABS(qty))
      * Marks per-row 'pick_posted'
      * Also fills row.staging_area (if field exists)
    """
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    staging_area = getattr(job, "staging_area", None)
    if not staging_area:
        frappe.throw(_("Staging Area is required on the Warehouse Job."))

    posting_dt = _posting_datetime(job)
    created_out = created_in = 0
    skipped: List[str] = []

    for it in (job.items or []):
        if _row_is_already_posted(it, "pick"):
            skipped.append(_("Item Row {0}: pick already posted.").format(getattr(it, "idx", "?")))
            continue

        item = getattr(it, "item", None)
        loc  = getattr(it, "location", None)
        qty  = abs(flt(getattr(it, "quantity", 0)))
        if not item or not loc or qty == 0:
            continue
        hu   = getattr(it, "handling_unit", None)
        bn   = getattr(it, "batch_no", None)
        sn   = getattr(it, "serial_no", None)

        # OUT location
        _insert_ledger_entry(job, item=item, qty=-qty, location=loc,
                             handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt)
        created_out += 1
        # IN staging
        _insert_ledger_entry(job, item=item, qty=qty, location=staging_area,
                             handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt)
        created_in += 1

        _mark_row_posted(it, "pick", posting_dt)
        _maybe_set_staging_area_on_row(it, staging_area)

    job.save(ignore_permissions=True)
    frappe.db.commit()

    msg = _("Pick posted: {0} OUT from location, {1} IN to staging.").format(created_out, created_in)
    if skipped:
        msg += " " + _("Skipped") + f": {len(skipped)}"
    return {"ok": True, "message": msg, "out_from_location": created_out, "in_to_staging": created_in, "skipped": skipped}


@frappe.whitelist()
def post_release(warehouse_job: str) -> Dict[str, Any]:
    """
    Pick flow step 2:
      * Out: Staging (−ABS(qty))
      * Marks per-row 'staging_posted' (if present) or 'release_posted'
    """
    job = frappe.get_doc("Warehouse Job", warehouse_job)
    staging_area = getattr(job, "staging_area", None)
    if not staging_area:
        frappe.throw(_("Staging Area is required on the Warehouse Job."))

    posting_dt = _posting_datetime(job)
    created = 0
    skipped: List[str] = []

    # choose a logical flag for completion of staging release
    action_key = "staging" if "staging_posted" in _safe_meta_fieldnames("Warehouse Job Item") else "release"

    for it in (job.items or []):
        if _row_is_already_posted(it, action_key):
            skipped.append(_("Item Row {0}: staging already released.").format(getattr(it, "idx", "?")))
            continue

        item = getattr(it, "item", None)
        qty  = abs(flt(getattr(it, "quantity", 0)))
        if not item or qty == 0:
            continue
        hu   = getattr(it, "handling_unit", None)
        bn   = getattr(it, "batch_no", None)
        sn   = getattr(it, "serial_no", None)

        _insert_ledger_entry(job, item=item, qty=-qty, location=staging_area,
                             handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt)
        _mark_row_posted(it, action_key, posting_dt)
        created += 1

    job.save(ignore_permissions=True)
    frappe.db.commit()

    msg = _("Release posted: {0} OUT from staging.").format(created)
    if skipped:
        msg += " " + _("Skipped") + f": {len(skipped)}"
    return {"ok": True, "message": msg, "created": created, "skipped": skipped}