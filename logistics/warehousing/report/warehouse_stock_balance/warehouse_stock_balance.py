# warehouse_stock_balance.py  (fixed joins for company/branch)

import frappe
from frappe.utils import getdate

def execute(filters=None):
    f = frappe._dict(filters or {})
    if not f.get("from_date") or not f.get("to_date"):
        frappe.throw("From Date and To Date are required.")

    # Determine grouping mode
    group_by_location_hu = f.get("group_by") == "Storage Location and Handling Unit"
    
    # Build columns based on grouping mode
    columns = [
        {"label": "Item",       "fieldname": "item",       "fieldtype": "Data", "width": 300},
    ]
    
    if group_by_location_hu:
        columns.extend([
            {"label": "Storage Location", "fieldname": "storage_location", "fieldtype": "Link", "options": "Storage Location", "width": 200},
            {"label": "Handling Unit",    "fieldname": "handling_unit",    "fieldtype": "Link", "options": "Handling Unit", "width": 200},
        ])
    
    # Post-process data to handle NULL values for display
    def format_null_values(row):
        if group_by_location_hu:
            if not row.get("storage_location"):
                row["storage_location"] = ""
            if not row.get("handling_unit"):
                row["handling_unit"] = ""
        return row
    
    columns.extend([
        {"label": "Beginning",  "fieldname": "beg_qty",    "fieldtype": "Float","width": 120},
        {"label": "In",         "fieldname": "in_qty",     "fieldtype": "Float","width": 110},
        {"label": "Out",        "fieldname": "out_qty",    "fieldtype": "Float","width": 110},
        {"label": "Ending",     "fieldname": "ending_qty", "fieldtype": "Float","width": 120},
    ])

    # Proper datetime handling: from_date at 00:00:00, to_date at end of day
    params = {
        "from_date": f"{getdate(f.from_date)} 00:00:00",
        "to_date": str(getdate(f.to_date))
    }
    where_bits = ["1=1"]

    # Optional filters (kept)
    if f.get("item"):
        where_bits.append("wsl.item = %(item)s"); params["item"] = f.item
    if f.get("customer"):
        where_bits.append("wi.customer = %(customer)s"); params["customer"] = f.customer
    if f.get("storage_location"):
        where_bits.append("wsl.storage_location = %(storage_location)s"); params["storage_location"] = f.storage_location
    if f.get("handling_unit"):
        where_bits.append("wsl.handling_unit = %(handling_unit)s"); params["handling_unit"] = f.handling_unit
    if f.get("company"):
        where_bits.append("COALESCE(hu.company, sl.company) = %(company)s"); params["company"] = f.company
    if f.get("branch"):
        where_bits.append("COALESCE(hu.branch, sl.branch) = %(branch)s"); params["branch"] = f.branch

    where_sql = " AND ".join(where_bits)

    # Build SELECT and GROUP BY based on grouping mode
    if group_by_location_hu:
        select_fields = """
            b.item,
            IFNULL(b.storage_location, '') AS storage_location,
            IFNULL(b.handling_unit, '') AS handling_unit,
        """
        # Use IFNULL in GROUP BY to handle NULL values consistently
        group_by_fields = "b.item, IFNULL(b.storage_location, ''), IFNULL(b.handling_unit, '')"
        order_by_fields = "b.item, IFNULL(b.storage_location, ''), IFNULL(b.handling_unit, '')"
    else:
        select_fields = """
            b.item,
        """
        group_by_fields = "b.item"
        order_by_fields = "b.item"
    
    data = frappe.db.sql(
        """
        WITH base AS (
            SELECT
                wsl.item,
                wsl.storage_location,
                wsl.handling_unit,
                wsl.posting_date,
                -- Use same quantity logic as Warehouse Stock Ledger: prefer quantity, fallback to delta
                COALESCE(wsl.quantity, wsl.end_qty - wsl.beg_quantity, 0) AS quantity,
                wsl.creation,
                COALESCE(hu.company, sl.company) AS company,
                COALESCE(hu.branch,  sl.branch)  AS branch
            FROM `tabWarehouse Stock Ledger` wsl
            LEFT JOIN `tabStorage Location` sl ON sl.name = wsl.storage_location
            LEFT JOIN `tabHandling Unit`   hu ON hu.name = wsl.handling_unit
            LEFT JOIN `tabWarehouse Item`  wi ON wi.name = wsl.item
            WHERE {where_sql}
        )
        SELECT
            {select_fields}
            -- Beginning: sum all quantities before from_date
            COALESCE(SUM(CASE WHEN b.posting_date < %(from_date)s THEN b.quantity ELSE 0 END), 0) AS beg_qty,

            -- In within window (positive quantities) - use proper datetime range
            COALESCE(SUM(CASE
                WHEN b.posting_date >= %(from_date)s 
                 AND b.posting_date < DATE_ADD(%(to_date)s, INTERVAL 1 DAY)
                 AND b.quantity > 0 THEN b.quantity ELSE 0 END), 0) AS in_qty,

            -- Out within window (negative quantities, show as positive) - use proper datetime range
            COALESCE(SUM(CASE
                WHEN b.posting_date >= %(from_date)s 
                 AND b.posting_date < DATE_ADD(%(to_date)s, INTERVAL 1 DAY)
                 AND b.quantity < 0 THEN -b.quantity ELSE 0 END), 0) AS out_qty,

            -- Ending: sum all quantities up to end of to_date
            COALESCE(SUM(CASE
                WHEN b.posting_date < DATE_ADD(%(to_date)s, INTERVAL 1 DAY) THEN b.quantity ELSE 0 END), 0) AS ending_qty

        FROM base b
        GROUP BY {group_by_fields}
        ORDER BY {order_by_fields}
        """.format(
            where_sql=where_sql,
            select_fields=select_fields,
            group_by_fields=group_by_fields,
            order_by_fields=order_by_fields
        ),
        params,
        as_dict=True,
    )

    # Format NULL values for display
    data = [format_null_values(r) for r in data]
    
    if frappe.utils.cint(f.get("hide_zero") or 0):
        data = [r for r in data if abs(r.get("ending_qty") or 0) > 0.0000001]

    return columns, data
