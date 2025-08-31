# Copyright (c) 2025, www.agilasoft.com and contributors
# Copyright (c) 2025
# MIT License. Part of logistics.warehousing

import frappe
from frappe.utils import getdate

def execute(filters=None):
    filters = frappe._dict(filters or {})
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    return [
        {"label": "Posting Date",    "fieldname": "posting_date",    "fieldtype": "Datetime", "width": 165},
        {"label": "Warehouse Job",   "fieldname": "warehouse_job",   "fieldtype": "Link",     "options": "Warehouse Job", "width": 140},
        {"label": "Customer",        "fieldname": "customer",        "fieldtype": "Link",     "options": "Customer",      "width": 160},
        {"label": "Item",            "fieldname": "item",            "fieldtype": "Link",     "options": "Warehouse Item","width": 160},
        {"label": "Item Name",       "fieldname": "item_name",       "fieldtype": "Data",     "width": 200},
        {"label": "Storage Location","fieldname": "storage_location","fieldtype": "Link",     "options": "Storage Location", "width": 160},
        {"label": "Handling Unit",   "fieldname": "handling_unit",   "fieldtype": "Link",     "options": "Handling Unit", "width": 140},
        {"label": "Serial No",       "fieldname": "serial_no",       "fieldtype": "Link",     "options": "Warehouse Serial", "width": 140},
        {"label": "Batch No",        "fieldname": "batch_no",        "fieldtype": "Link",     "options": "Warehouse Batch", "width": 140},
        {"label": "Qty (±)",         "fieldname": "qty",             "fieldtype": "Float",    "width": 110, "precision": "3"},
        {"label": "In Qty",          "fieldname": "in_qty",          "fieldtype": "Float",    "width": 110, "precision": "3"},
        {"label": "Out Qty",         "fieldname": "out_qty",         "fieldtype": "Float",    "width": 110, "precision": "3"},
        {"label": "Beg Qty",         "fieldname": "beg_quantity",    "fieldtype": "Float",    "width": 110, "precision": "3"},
        {"label": "End Qty",         "fieldname": "end_qty",         "fieldtype": "Float",    "width": 110, "precision": "3"},
    ]

def get_data(filters):
    conditions = []
    params = {}

    # DATE RANGE (inclusive start; inclusive end by using < next day)
    if filters.get("date_from"):
        conditions.append("l.posting_date >= %(date_from)s")
        params["date_from"] = f"{getdate(filters.date_from)} 00:00:00"

    if filters.get("date_to"):
        conditions.append("l.posting_date < DATE_ADD(%(date_to)s, INTERVAL 1 DAY)")
        params["date_to"] = str(getdate(filters.date_to))

    # OTHER FILTERS
    if filters.get("customer"):
        conditions.append("wi.customer = %(customer)s")
        params["customer"] = filters.customer

    if filters.get("item"):
        conditions.append("l.item = %(item)s")
        params["item"] = filters.item

    if filters.get("storage_location"):
        conditions.append("l.storage_location = %(storage_location)s")
        params["storage_location"] = filters.storage_location

    if filters.get("handling_unit"):
        conditions.append("l.handling_unit = %(handling_unit)s")
        params["handling_unit"] = filters.handling_unit

    if filters.get("serial_no"):
        conditions.append("l.serial_no = %(serial_no)s")
        params["serial_no"] = filters.serial_no

    if filters.get("batch_no"):
        conditions.append("l.batch_no = %(batch_no)s")
        params["batch_no"] = filters.batch_no

    if filters.get("warehouse_job"):
        conditions.append("l.warehouse_job = %(warehouse_job)s")
        params["warehouse_job"] = filters.warehouse_job

    where = " AND ".join(conditions)
    if where:
        where = "WHERE " + where

    # Note: 'quantiy' is the field name in your DocType (typo retained intentionally)
    sql = f"""
        SELECT
            l.posting_date,
            l.warehouse_job,
            wi.customer,
            l.item,
            wi.item_name,
            l.storage_location,
            l.handling_unit,
            l.serial_no,
            l.batch_no,
            l.quantiy               AS qty,
            IF(l.quantiy >= 0,  l.quantiy, 0)  AS in_qty,
            IF(l.quantiy  < 0, -l.quantiy, 0)  AS out_qty,
            l.beg_quantity,
            l.end_qty
        FROM `tabWarehouse Stock Ledger` l
        LEFT JOIN `tabWarehouse Item` wi ON wi.name = l.item
        {where}
        ORDER BY l.posting_date, l.name
    """

    return frappe.db.sql(sql, params, as_dict=True)


