# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

# import frappe


import frappe
from frappe.utils import getdate
from datetime import datetime, time

def _dt_range(from_date, to_date):
    dfrom = datetime.combine(getdate(from_date), time.min)
    dto   = datetime.combine(getdate(to_date),   time.max).replace(microsecond=0)
    return dfrom, dto

def _fetch_rows(f):
    """
    Summarize beginning qty, receipts, issues, ending qty per Warehouse Item
    using Warehouse Stock Ledger. Note: ledger field is 'quantiy' (intentional).
    """
    dfrom, dto = _dt_range(f.from_date, f.to_date)

    where_items = ["1=1"]
    params = {"dfrom": dfrom, "dto": dto}

    if f.get("customer"):
        where_items.append("wi.customer = %(customer)s")
        params["customer"] = f.customer

    if f.get("item"):
        where_items.append("wi.name = %(item)s")
        params["item"] = f.item

    sql = f"""
        SELECT
            wi.name               AS item,
            wi.customer,
            wi.abc_class          AS current_abc,

            COALESCE(SUM(CASE
                WHEN l.posting_date < %(dfrom)s THEN l.quantiy ELSE 0 END), 0) AS beg_qty,

            COALESCE(SUM(CASE
                WHEN l.posting_date BETWEEN %(dfrom)s AND %(dto)s AND l.quantiy > 0
                THEN l.quantiy ELSE 0 END), 0) AS receipts,

            ABS(COALESCE(SUM(CASE
                WHEN l.posting_date BETWEEN %(dfrom)s AND %(dto)s AND l.quantiy < 0
                THEN l.quantiy ELSE 0 END), 0)) AS issues,

            COALESCE(SUM(CASE
                WHEN l.posting_date <= %(dto)s THEN l.quantiy ELSE 0 END), 0) AS end_qty

        FROM `tabWarehouse Item` wi
        LEFT JOIN `tabWarehouse Stock Ledger` l
               ON l.item = wi.name
        WHERE {" AND ".join(where_items)}
        GROUP BY wi.name, wi.customer, wi.abc_class
        HAVING ABS(beg_qty) > 0.000001
            OR ABS(receipts) > 0.000001
            OR ABS(issues) > 0.000001
            OR ABS(end_qty) > 0.000001
        ORDER BY wi.name
    """
    return frappe.db.sql(sql, params, as_dict=True)

def _classify(rows, f):
    """
    Compute turns & velocity and assign suggested ABC.
    Turns = issues / avg_qty (avg of beg & end). If avg=0 => turns=0.
    """
    dfrom, dto = _dt_range(f.from_date, f.to_date)
    days = max((dto.date() - dfrom.date()).days + 1, 1)

    for r in rows:
        r.avg_qty = (r.beg_qty + r.end_qty) / 2.0
        r.turns = (r.issues / r.avg_qty) if r.avg_qty else 0.0
        r.velocity_per_day = r.issues / days

    basis = (f.get("basis") or "Turns Thresholds").strip()

    if basis == "Cumulative % of Issues":
        total_issues = sum(r.issues for r in rows) or 0.0
        a_cutoff = float(f.get("a_cutoff") or 80.0)
        b_cutoff = float(f.get("b_cutoff") or 95.0)
        ranked = sorted(rows, key=lambda x: x.issues, reverse=True)
        running = 0.0
        class_map = {}
        for r in ranked:
            pct = (r.issues / total_issues * 100.0) if total_issues else 0.0
            running += pct
            if running <= a_cutoff:
                class_map[r.item] = "A"
            elif running <= b_cutoff:
                class_map[r.item] = "B"
            else:
                class_map[r.item] = "C"
        for r in rows:
            r.suggested_abc = class_map.get(r.item, "C")
    else:
        a_thr = float(f.get("a_turns_min") or 4.0)
        b_thr = float(f.get("b_turns_min") or 2.0)
        for r in rows:
            if r.turns >= a_thr:
                r.suggested_abc = "A"
            elif r.turns >= b_thr:
                r.suggested_abc = "B"
            else:
                r.suggested_abc = "C"
    return rows

def execute(filters=None):
    f = frappe._dict(filters or {})
    if not f.get("from_date") or not f.get("to_date"):
        frappe.throw("From Date and To Date are required.")

    rows = _fetch_rows(f)
    rows = _classify(rows, f)

    data, cnt = [], {"A": 0, "B": 0, "C": 0}
    for r in rows:
        cnt[r.suggested_abc] = cnt.get(r.suggested_abc, 0) + 1
        data.append({
            "item": r.item,
            "customer": r.customer,
            "beg_qty": r.beg_qty,
            "receipts": r.receipts,
            "issues": r.issues,
            "end_qty": r.end_qty,
            "avg_qty": r.avg_qty,
            "turns": r.turns,
            "velocity_per_day": r.velocity_per_day,
            "current_abc": r.current_abc,
            "suggested_abc": r.suggested_abc
        })

    columns = [
        {"label":"Item",        "fieldname":"item",        "fieldtype":"Link", "options":"Warehouse Item", "width":180},
        {"label":"Customer",    "fieldname":"customer",    "fieldtype":"Link", "options":"Customer",       "width":170},
        {"label":"Beg Qty",     "fieldname":"beg_qty",     "fieldtype":"Float","width":100},
        {"label":"Receipts",    "fieldname":"receipts",    "fieldtype":"Float","width":100},
        {"label":"Issues",      "fieldname":"issues",      "fieldtype":"Float","width":100},
        {"label":"End Qty",     "fieldname":"end_qty",     "fieldtype":"Float","width":100},
        {"label":"Avg Qty",     "fieldname":"avg_qty",     "fieldtype":"Float","width":100},
        {"label":"Turns",       "fieldname":"turns",       "fieldtype":"Float","width":90,  "precision":6},
        {"label":"Velocity / Day","fieldname":"velocity_per_day","fieldtype":"Float","width":120, "precision":6},
        {"label":"ABC (Current)","fieldname":"current_abc","fieldtype":"Data","width":110},
        {"label":"ABC (Suggested)","fieldname":"suggested_abc","fieldtype":"Data","width":130}
    ]

    chart = {
        "data": {
            "labels": ["A", "B", "C"],
            "datasets": [{
                "name":"Count", 
                "values": [cnt.get("A",0), cnt.get("B",0), cnt.get("C",0)],
                "colors": ["#28a745", "#ffc107", "#dc3545"]  # Green, Yellow, Red for A, B, C
            }]
        },
        "type": "pie"
    }

    report_summary = [
        {"label":"A", "value": int(cnt.get("A",0)), "indicator":"green"},
        {"label":"B", "value": int(cnt.get("B",0)), "indicator":"orange"},
        {"label":"C", "value": int(cnt.get("C",0)), "indicator":"red"}
    ]

    return columns, data, None, chart, report_summary

@frappe.whitelist()
def update_abc_classification(filters: dict):
    if not frappe.has_permission("Warehouse Item", "write"):
        frappe.throw("Not permitted to update ABC Class.", frappe.PermissionError)

    f = frappe._dict(filters or {})
    rows = _classify(_fetch_rows(f), f)

    # Ensure 'abc_class' exists (it does in your doctype)
    meta = frappe.get_meta("Warehouse Item")
    if not any(df.fieldname == "abc_class" for df in meta.fields):
        frappe.throw("Field 'abc_class' does not exist on Warehouse Item.")

    updated = 0
    for r in rows:
        frappe.db.set_value("Warehouse Item", r.item, "abc_class", r.suggested_abc)
        updated += 1

    return {"updated": updated}
