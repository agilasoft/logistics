# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt, getdate

def execute(filters=None):
    filters = frappe._dict(filters or {})

    columns = get_columns()
    rows = get_rows(filters)

    # Totals for KPI cards
    tot_qty = sum(flt(r.get("quantity")) for r in rows)
    tot_std = sum(flt(r.get("total_std_hours")) for r in rows)
    tot_act = sum(flt(r.get("actual_hours")) for r in rows)

    eff = (tot_std / tot_act * 100.0) if tot_act else 0.0
    uph = (tot_qty / tot_act) if tot_act else 0.0  # units per actual-hour

    # Optional client-side message (can be blank)
    message = None

    # Chart (by day or by operation)
    chart = make_chart(rows, by=filters.get("chart_by") or "day")

    # KPI cards
    report_summary = [
        {"value": round(tot_qty, 3), "indicator": "blue", "label": "Total Quantity", "datatype": "Float"},
        {"value": round(tot_std, 3), "indicator": "orange", "label": "Total Std Hours", "datatype": "Float"},
        {"value": round(tot_act, 3), "indicator": "teal", "label": "Total Actual Hours", "datatype": "Float"},
        {"value": f"{eff:.2f}%", "indicator": "green" if eff >= 100 else "red", "label": "Efficiency", "datatype": "Percent"},
        {"value": round(uph, 3), "indicator": "purple", "label": "Units / Hr (Actual)", "datatype": "Float"},
    ]

    # Convert rows (dict) to data list matching columns order
    data = [
        [
            r["job"], r["job_open_date"], r["company"], r["branch"], r["customer"], r["type"],
            r["operation"], r["description"], r["handling_uom"], r["quantity"],
            r["unit_std_hours"], r["total_std_hours"], r["actual_hours"],
            r["efficiency_pct"], r["units_per_hour"], r["variance_hours"]
        ]
        for r in rows
    ]

    return columns, data, message, chart, report_summary


def get_columns():
    return [
        {"label": "Job", "fieldname": "job", "fieldtype": "Link", "options": "Warehouse Job", "width": 140},
        {"label": "Job Date", "fieldname": "job_open_date", "fieldtype": "Date", "width": 100},
        {"label": "Company", "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 120},
        {"label": "Branch", "fieldname": "branch", "fieldtype": "Link", "options": "Branch", "width": 120},
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140},
        {"label": "Job Type", "fieldname": "type", "fieldtype": "Data", "width": 100},
        {"label": "Operation", "fieldname": "operation", "fieldtype": "Link", "options": "Warehouse Operation Item", "width": 160},
        {"label": "Description", "fieldname": "description", "fieldtype": "Data", "width": 200},
        {"label": "Handling UOM", "fieldname": "handling_uom", "fieldtype": "Link", "options": "UOM", "width": 110},
        {"label": "Quantity", "fieldname": "quantity", "fieldtype": "Float", "width": 100},
        {"label": "Unit Std Hrs", "fieldname": "unit_std_hours", "fieldtype": "Float", "precision": "2", "width": 110},
        {"label": "Total Std Hrs", "fieldname": "total_std_hours", "fieldtype": "Float", "precision": "2", "width": 120},
        {"label": "Actual Hrs", "fieldname": "actual_hours", "fieldtype": "Float", "precision": "2", "width": 100},
        {"label": "Efficiency %", "fieldname": "efficiency_pct", "fieldtype": "Percent", "width": 110},
        {"label": "Units / Hr", "fieldname": "units_per_hour", "fieldtype": "Float", "precision": "3", "width": 110},
        {"label": "Variance Hrs (Act - Std)", "fieldname": "variance_hours", "fieldtype": "Float", "precision": "2", "width": 160},
    ]


def get_rows(filters):
    conditions = ["wjo.parenttype='Warehouse Job'"]
    params = {}

    # Date range (Job Open Date)
    if filters.get("from_date"):
        conditions.append("wj.job_open_date >= %(from_date)s")
        params["from_date"] = getdate(filters.get("from_date"))
    if filters.get("to_date"):
        conditions.append("wj.job_open_date <= %(to_date)s")
        params["to_date"] = getdate(filters.get("to_date"))

    if filters.get("company"):
        conditions.append("wj.company = %(company)s")
        params["company"] = filters.get("company")

    if filters.get("branch"):
        conditions.append("wj.branch = %(branch)s")
        params["branch"] = filters.get("branch")

    # Job Type can be a list or single value
    if filters.get("type"):
        types = filters.get("type")
        if isinstance(types, (list, tuple)):
            conditions.append("wj.type in %(types)s")
        else:
            conditions.append("wj.type = %(types)s")
            types = [types]
        params["types"] = tuple(types)

    if filters.get("customer"):
        conditions.append("wj.customer = %(customer)s")
        params["customer"] = filters.get("customer")

    if filters.get("operation"):
        conditions.append("wjo.operation = %(operation)s")
        params["operation"] = filters.get("operation")

    if filters.get("handling_uom"):
        conditions.append("wjo.handling_uom = %(handling_uom)s")
        params["handling_uom"] = filters.get("handling_uom")

    if flt(filters.get("min_efficiency")) > 0:
        # Apply later on computed rows
        min_eff = flt(filters.get("min_efficiency"))
    else:
        min_eff = None

    if filters.get("only_variances"):
        only_var = True
    else:
        only_var = False

    where = " AND ".join(conditions) if conditions else "1=1"

    # Join child table (Warehouse Job Operations) to parent (Warehouse Job)
    # Child table name is `tabWarehouse Job Operations`
    query = f"""
        SELECT
            wj.name AS job,
            wj.job_open_date,
            wj.company,
            wj.branch,
            wj.customer,
            wj.type,
            wjo.operation,
            wjo.description,
            wjo.handling_uom,
            COALESCE(wjo.quantity, 0) AS quantity,
            COALESCE(wjo.unit_std_hours, 0) AS unit_std_hours,
            COALESCE(wjo.total_std_hours, 0) AS total_std_hours,
            COALESCE(wjo.actual_hours, 0) AS actual_hours
        FROM `tabWarehouse Job Operations` wjo
        INNER JOIN `tabWarehouse Job` wj
            ON wjo.parent = wj.name
        WHERE {where}
        ORDER BY wj.job_open_date ASC, wj.name ASC
    """

    raw = frappe.db.sql(query, params, as_dict=True)

    rows = []
    for r in raw:
        total_std = flt(r.total_std_hours)
        actual = flt(r.actual_hours)
        qty = flt(r.quantity)

        efficiency_pct = (total_std / actual * 100.0) if actual else 0.0
        units_per_hour = (qty / actual) if actual else 0.0
        variance_hours = actual - total_std

        if min_eff is not None and efficiency_pct < min_eff:
            continue
        if only_var and abs(variance_hours) <= 1e-9:
            continue

        r.update(
            efficiency_pct=efficiency_pct,
            units_per_hour=units_per_hour,
            variance_hours=variance_hours,
        )
        rows.append(r)

    return rows


def make_chart(rows, by="day"):
    """
    Build a simple bar/line chart:
    - by='day'   -> x: job_open_date; y: Efficiency %
    - by='op'    -> x: operation;    y: Efficiency % (avg)
    """
    if not rows:
        return None

    if by.lower() in ("operation", "op"):
        # Average efficiency by operation
        buckets = {}
        for r in rows:
            key = r.get("operation") or "—"
            b = buckets.setdefault(key, {"eff_sum": 0.0, "eff_cnt": 0})
            b["eff_sum"] += flt(r.get("efficiency_pct"))
            b["eff_cnt"] += 1
        labels = []
        eff_values = []
        for op, agg in sorted(buckets.items(), key=lambda kv: kv[0] or ""):
            labels.append(op)
            avg_eff = (agg["eff_sum"] / agg["eff_cnt"]) if agg["eff_cnt"] else 0.0
            eff_values.append(round(avg_eff, 2))

        return {
            "data": {
                "labels": labels,
                "datasets": [{"name": "Efficiency % (avg)", "values": eff_values}],
            },
            "type": "bar",
        }

    # Default: by day
    buckets = {}
    for r in rows:
        key = str(r.get("job_open_date"))
        agg = buckets.setdefault(key, {"std": 0.0, "act": 0.0, "qty": 0.0})
        agg["std"] += flt(r.get("total_std_hours"))
        agg["act"] += flt(r.get("actual_hours"))
        agg["qty"] += flt(r.get("quantity"))

    labels = []
    eff_values = []
    uph_values = []
    for d in sorted(buckets.keys()):
        labels.append(d)
        std = buckets[d]["std"]
        act = buckets[d]["act"]
        qty = buckets[d]["qty"]
        eff = (std / act * 100.0) if act else 0.0
        uph = (qty / act) if act else 0.0
        eff_values.append(round(eff, 2))
        uph_values.append(round(uph, 3))

    # 2 datasets: Efficiency % and Units/Hr
    return {
        "data": {
            "labels": labels,
            "datasets": [
                {"name": "Efficiency %", "values": eff_values},
                {"name": "Units/Hr", "values": uph_values},
            ],
        },
        "type": "line",
    }
