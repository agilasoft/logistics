# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

# import frappe

# logistics/warehousing/report/batch_expiry_risk/batch_expiry_risk.py
import frappe
from frappe.utils import getdate, add_days, cint

def execute(filters=None):
    f = frappe._dict(filters or {})
    as_of = getdate(f.as_of or frappe.utils.today())
    horizon = cint(f.days or 30)

    where = ["1=1"]
    params = {"as_of": as_of}
    if f.customer:
        where.append("wb.customer = %(customer)s")
        params["customer"] = f.customer
    if f.item:
        where.append("wb.item_code = %(item)s")
        params["item"] = f.item

    rows = frappe.db.sql(
        f"""
        SELECT
            wb.customer,
            wb.item_code,
            wb.name            AS batch,
            wb.expiry_date,
            DATEDIFF(wb.expiry_date, %(as_of)s) AS days_to_expiry,
            COALESCE(SUM(l.quantity), 0)         AS qty,
            wb.batch_uom                         AS uom,
            COUNT(DISTINCT l.storage_location)   AS locations
        FROM `tabWarehouse Batch` wb
        LEFT JOIN `tabWarehouse Stock Ledger` l
            ON l.batch_no = wb.name
        WHERE {" AND ".join(where)}
        GROUP BY wb.name
        HAVING ABS(qty) > 0.000001
        ORDER BY wb.expiry_date
        """,
        params,
        as_dict=True,
    )

    expired_cnt = due_cnt = ok_cnt = 0
    data = []
    for r in rows:
        status = "Expired" if r.expiry_date and r.days_to_expiry < 0 else (
                 "Due Soon" if r.expiry_date and r.days_to_expiry <= horizon else "OK")
        if status == "Expired":
            expired_cnt += 1
        elif status == "Due Soon":
            due_cnt += 1
        else:
            ok_cnt += 1

        data.append({
            "customer": r.customer,
            "item_code": r.item_code,
            "batch": r.batch,
            "expiry_date": r.expiry_date,
            "days_to_expiry": r.days_to_expiry,
            "qty": r.qty,
            "uom": r.uom,
            "locations": r.locations,
            "status": status,
        })

    columns = [
        {"label": "Customer",      "fieldname": "customer",       "fieldtype": "Link", "options": "Customer", "width": 180},
        {"label": "Item",          "fieldname": "item_code",      "fieldtype": "Link", "options": "Warehouse Item", "width": 180},
        {"label": "Batch",         "fieldname": "batch",          "fieldtype": "Data", "width": 180},
        {"label": "Expiry Date",   "fieldname": "expiry_date",    "fieldtype": "Date", "width": 110},
        {"label": "Days to Expiry","fieldname": "days_to_expiry", "fieldtype": "Int",  "width": 120},
        {"label": "Qty",           "fieldname": "qty",            "fieldtype": "Float","width": 100},
        {"label": "UOM",           "fieldname": "uom",            "fieldtype": "Link", "options": "UOM", "width": 90},
        {"label": "Locations",     "fieldname": "locations",      "fieldtype": "Int",  "width": 100},
        {"label": "Status",        "fieldname": "status",         "fieldtype": "Data", "width": 100},
    ]

    chart = {
        "type": "donut",
        "data": {
            "labels": ["Expired", "Due Soon", "OK"],          # plain strings
            "datasets": [{"name": "Batches", "values": [expired_cnt, due_cnt, ok_cnt]}]  # plain numbers
        }
    }

    summary = [
        {"label": "Expired", "value": expired_cnt, "indicator": "red",    "datatype": "Int"},
        {"label": "Due Soon","value": due_cnt,     "indicator": "orange", "datatype": "Int"},
        {"label": "OK",      "value": ok_cnt,      "indicator": "green",  "datatype": "Int"},
    ]

    # IMPORTANT: do not return any 'message' or HTML; prepared report will escape it.
    return columns, data, None, chart, summary
