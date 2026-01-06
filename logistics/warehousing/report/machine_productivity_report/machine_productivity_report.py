# apps/logistics/logistics/report/machine_productivity_report/machine_productivity_report.py
import frappe
from frappe.utils import flt, getdate

def execute(filters=None):
    f = frappe._dict(filters or {})
    cols = get_columns()
    rows = get_rows(f)

    # Totals
    tot_std = sum(flt(r.std_machine_hours) for r in rows)
    tot_act = sum(flt(r.actual_machine_hours) for r in rows)
    tot_qty = sum(flt(r.quantity) for r in rows)

    m_eff = pct(tot_std, tot_act)
    upmh  = units_per_hr(tot_qty, tot_act)

    # KPI cards
    report_summary = [
        {"value": round(tot_std, 2), "indicator": "orange", "label": "Std Machine Hrs", "datatype": "Float"},
        {"value": round(tot_act, 2), "indicator": "teal",   "label": "Actual Machine Hrs", "datatype": "Float"},
        {"value": f"{m_eff:.2f}%",   "indicator": "green" if m_eff >= 100 else "red", "label": "Machine Efficiency", "datatype": "Percent"},
        {"value": round(upmh, 3),    "indicator": "purple", "label": "Units / Machine Hr", "datatype": "Float"},
    ]

    # Table data
    data = [[
        r.job, r.job_open_date, r.company, r.branch, r.customer, r.type,
        r.machine, r.operation, r.description, r.handling_uom,
        r.quantity, r.std_machine_hours, r.actual_machine_hours,
        pct(r.std_machine_hours, r.actual_machine_hours),
        units_per_hr(r.quantity, r.actual_machine_hours)
    ] for r in rows]

    # Chart
    chart = make_chart(rows, by=f.get("chart_by") or "day")

    return cols, data, None, chart, report_summary


def get_columns():
    return [
        {"label":"Job","fieldname":"job","fieldtype":"Link","options":"Warehouse Job","width":140},
        {"label":"Job Date","fieldname":"job_open_date","fieldtype":"Date","width":100},
        {"label":"Company","fieldname":"company","fieldtype":"Link","options":"Company","width":120},
        {"label":"Branch","fieldname":"branch","fieldtype":"Link","options":"Branch","width":120},
        {"label":"Customer","fieldname":"customer","fieldtype":"Link","options":"Customer","width":140},
        {"label":"Job Type","fieldname":"type","fieldtype":"Data","width":100},

        {"label":"Machine","fieldname":"machine","fieldtype":"Link","options":"Asset","width":160},
        {"label":"Operation","fieldname":"operation","fieldtype":"Link","options":"Warehouse Operation Item","width":160},
        {"label":"Description","fieldname":"description","fieldtype":"Data","width":200},
        {"label":"Handling UOM","fieldname":"handling_uom","fieldtype":"Link","options":"UOM","width":110},
        {"label":"Quantity","fieldname":"quantity","fieldtype":"Float","width":100},

        {"label":"Std Machine Hrs","fieldname":"std_machine_hours","fieldtype":"Float","precision":"2","width":130},
        {"label":"Actual Machine Hrs","fieldname":"actual_machine_hours","fieldtype":"Float","precision":"2","width":140},
        {"label":"Machine Efficiency %","fieldname":"machine_efficiency_pct","fieldtype":"Percent","width":150},
        {"label":"Units / Machine Hr","fieldname":"units_per_machine_hour","fieldtype":"Float","precision":"3","width":140},
    ]


def get_rows(f):
    conds, params = ["wjo.parenttype='Warehouse Job'"], {}
    if f.get("from_date"):
        conds.append("wj.job_open_date >= %(from_date)s"); params["from_date"] = getdate(f.from_date)
    if f.get("to_date"):
        conds.append("wj.job_open_date <= %(to_date)s"); params["to_date"] = getdate(f.to_date)
    if f.get("company"):
        conds.append("wj.company = %(company)s"); params["company"] = f.company
    if f.get("branch"):
        conds.append("wj.branch = %(branch)s"); params["branch"] = f.branch
    if f.get("type"):
        conds.append("wj.type = %(type)s"); params["type"] = f.type
    if f.get("customer"):
        conds.append("wj.customer = %(customer)s"); params["customer"] = f.customer
    if f.get("machine"):
        conds.append("wjo.machine = %(machine)s"); params["machine"] = f.machine

    where = " AND ".join(conds)
    sql = f"""
        SELECT
            wj.name AS job, wj.job_open_date, wj.company, wj.branch, wj.customer, wj.type,
            wjo.machine, wjo.operation, wjo.description, wjo.handling_uom,
            COALESCE(wjo.quantity,0)              AS quantity,
            COALESCE(wjo.std_machine_hours,0)     AS std_machine_hours,
            COALESCE(wjo.actual_machine_hours,0)  AS actual_machine_hours
        FROM `tabWarehouse Job Operations` wjo
        INNER JOIN `tabWarehouse Job` wj ON wjo.parent = wj.name
        WHERE {where}
        ORDER BY wj.job_open_date ASC, wj.name ASC
    """
    rows = frappe.db.sql(sql, params, as_dict=True)
    for r in rows:
        r["machine_efficiency_pct"] = pct(r["std_machine_hours"], r["actual_machine_hours"])
        r["units_per_machine_hour"] = units_per_hr(r["quantity"], r["actual_machine_hours"])
    return rows


def make_chart(rows, by="day"):
    if not rows:
        return None
    by = (by or "day").lower()

    if by == "machine":
        agg = {}
        for r in rows:
            k = r.get("machine") or "—"
            a = agg.setdefault(k, {"qty":0.0,"act":0.0})
            a["qty"] += flt(r.get("quantity"))
            a["act"] += flt(r.get("actual_machine_hours"))
        labels, upmh = [], []
        for k in sorted(agg):
            labels.append(k)
            upmh.append(round(units_per_hr(agg[k]["qty"], agg[k]["act"]), 3))
        return {"data":{"labels":labels,"datasets":[{"name":"Units / Machine Hr","values":upmh}]},"type":"bar"}

    # default: by day
    days = {}
    for r in rows:
        d = str(r.get("job_open_date"))
        a = days.setdefault(d, {"std":0.0,"act":0.0,"qty":0.0})
        a["std"] += flt(r.get("std_machine_hours"))
        a["act"] += flt(r.get("actual_machine_hours"))
        a["qty"] += flt(r.get("quantity"))
    labels, meff, upmh = [], [], []
    for d in sorted(days):
        a = days[d]
        labels.append(d)
        meff.append(round(pct(a["std"], a["act"]), 2))
        upmh.append(round(units_per_hr(a["qty"], a["act"]), 3))
    return {"data":{"labels":labels,"datasets":[
        {"name":"Machine Efficiency %","values":meff},
        {"name":"Units / Machine Hr","values":upmh}
    ]},"type":"line"}


def pct(numer, denom):
    numer, denom = flt(numer), flt(denom)
    return (numer/denom*100.0) if denom else 0.0

def units_per_hr(qty, hours):
    qty, hours = flt(qty), flt(hours)
    return (qty/hours) if hours else 0.0
