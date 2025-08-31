# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

# import frappe


def execute(filters=None):
	columns, data = [], []
	return columns, data
    
import frappe

def execute(filters=None):
    filters = frappe._dict(filters or {})
    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw("From Date and To Date are required.")

    cols = [
        {"label":"Item","fieldname":"item","fieldtype":"Link","options":"Warehouse Item","width":180},
        {"label":"Storage Location","fieldname":"storage_location","fieldtype":"Link","options":"Storage Location","width":160},
        {"label":"Handling Unit","fieldname":"handling_unit","fieldtype":"Link","options":"Handling Unit","width":160},
        {"label":"Batch No","fieldname":"batch_no","fieldtype":"Link","options":"Warehouse Batch","width":120},
        {"label":"Serial No","fieldname":"serial_no","fieldtype":"Link","options":"Warehouse Serial","width":120},
        {"label":"Beginning","fieldname":"beg_qty","fieldtype":"Float","width":110},
        {"label":"In","fieldname":"in_qty","fieldtype":"Float","width":110},
        {"label":"Out","fieldname":"out_qty","fieldtype":"Float","width":110},
        {"label":"Ending","fieldname":"ending_qty","fieldtype":"Float","width":110},
    ]

    params = {"from_date": filters.from_date, "to_date": filters.to_date}
    conds = []

    if filters.get("item"):
        conds.append("wsl.item = %(item)s")
        params["item"] = filters.item
    if filters.get("storage_location"):
        conds.append("wsl.storage_location = %(storage_location)s")
        params["storage_location"] = filters.storage_location
    if filters.get("handling_unit"):
        conds.append("wsl.handling_unit = %(handling_unit)s")
        params["handling_unit"] = filters.handling_unit
    if filters.get("customer"):
        # Enforce that the Warehouse Item belongs to the selected Customer
        conds.append("wi.customer = %(customer)s")
        params["customer"] = filters.customer

    extra_where = (" AND " + " AND ".join(conds)) if conds else ""

    data = frappe.db.sql(
        f"""
        SELECT
            wsl.item,
            wsl.storage_location,
            wsl.handling_unit,
            wsl.batch_no,
            wsl.serial_no,
            COALESCE(SUM(CASE
                WHEN wsl.posting_date < %(from_date)s THEN wsl.quantiy
                ELSE 0 END), 0) AS beg_qty,
            COALESCE(SUM(CASE
                WHEN wsl.posting_date >= %(from_date)s AND wsl.posting_date <= %(to_date)s AND wsl.quantiy > 0
                THEN wsl.quantiy ELSE 0 END), 0) AS in_qty,
            COALESCE(SUM(CASE
                WHEN wsl.posting_date >= %(from_date)s AND wsl.posting_date <= %(to_date)s AND wsl.quantiy < 0
                THEN -wsl.quantiy ELSE 0 END), 0) AS out_qty,
            COALESCE(SUM(CASE
                WHEN wsl.posting_date <= %(to_date)s THEN wsl.quantiy
                ELSE 0 END), 0) AS ending_qty
        FROM `tabWarehouse Stock Ledger` wsl
        LEFT JOIN `tabWarehouse Item` wi ON wi.name = wsl.item
        WHERE 1 = 1 {extra_where}
        GROUP BY
            wsl.item, wsl.storage_location, wsl.handling_unit, wsl.batch_no, wsl.serial_no
        ORDER BY wsl.item, wsl.storage_location, wsl.handling_unit
        """,
        params,
        as_dict=True,
    )

    return cols, data

