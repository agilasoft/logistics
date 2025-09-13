# warehouse_stock_balance.py  (fixed joins for company/branch)

import frappe

def execute(filters=None):
    f = frappe._dict(filters or {})
    if not f.get("from_date") or not f.get("to_date"):
        frappe.throw("From Date and To Date are required.")

    columns = [
        {"label": "Item",       "fieldname": "item",       "fieldtype": "Data", "width": 500},
        {"label": "Beginning",  "fieldname": "beg_qty",    "fieldtype": "Float","width": 120},
        {"label": "In",         "fieldname": "in_qty",     "fieldtype": "Float","width": 110},
        {"label": "Out",        "fieldname": "out_qty",    "fieldtype": "Float","width": 110},
        {"label": "Ending",     "fieldname": "ending_qty", "fieldtype": "Float","width": 120},
    ]

    params = {"from_date": f.from_date, "to_date": f.to_date}
    where_bits = ["1=1"]

    # Optional filters (kept)
    if f.get("item"):
        where_bits.append("wsl.item = %(item)s"); params["item"] = f.item
    if f.get("customer"):
        where_bits.append("wi.customer = %(customer)s"); params["customer"] = f.customer
    if f.get("company"):
        where_bits.append("COALESCE(hu.company, sl.company) = %(company)s"); params["company"] = f.company
    if f.get("branch"):
        where_bits.append("COALESCE(hu.branch, sl.branch) = %(branch)s"); params["branch"] = f.branch

    where_sql = " AND ".join(where_bits)

    data = frappe.db.sql(
        """
        WITH base AS (
            SELECT
                wsl.item,
                wsl.posting_date,
                wsl.quantity,
                wsl.creation,
                COALESCE(hu.company, sl.company) AS company,
                COALESCE(hu.branch,  sl.branch)  AS branch
            FROM `tabWarehouse Stock Ledger` wsl
            LEFT JOIN `tabStorage Location` sl ON sl.name = wsl.storage_location
            LEFT JOIN `tabHandling Unit`   hu ON hu.name = wsl.handling_unit
            LEFT JOIN `tabWarehouse Item`  wi ON wi.name = wsl.item
            WHERE {where_sql}
        ),
        first_on_day AS (
            SELECT item, MIN(creation) AS first_creation
            FROM base
            WHERE posting_date = %(from_date)s
            GROUP BY item
        )
        SELECT
            b.item,

            -- Beginning: balance after the first entry on from_date
            COALESCE(SUM(CASE WHEN b.posting_date < %(from_date)s THEN b.quantity ELSE 0 END), 0)
            +
            COALESCE(SUM(CASE
                WHEN b.posting_date = %(from_date)s AND b.creation = fod.first_creation
                THEN b.quantity ELSE 0 END), 0) AS beg_qty,

            -- In within window
            COALESCE(SUM(CASE
                WHEN b.posting_date BETWEEN %(from_date)s AND %(to_date)s
                 AND b.quantity > 0 THEN b.quantity ELSE 0 END), 0) AS in_qty,

            -- Out within window
            COALESCE(SUM(CASE
                WHEN b.posting_date BETWEEN %(from_date)s AND %(to_date)s
                 AND b.quantity < 0 THEN -b.quantity ELSE 0 END), 0) AS out_qty,

            -- Ending up to to_date
            COALESCE(SUM(CASE
                WHEN b.posting_date <= %(to_date)s THEN b.quantity ELSE 0 END), 0) AS ending_qty

        FROM base b
        LEFT JOIN first_on_day fod
          ON fod.item = b.item
        GROUP BY b.item
        ORDER BY b.item
        """.format(where_sql=where_sql),
        params,
        as_dict=True,
    )

    if frappe.utils.cint(f.get("hide_zero") or 0):
        data = [r for r in data if abs(r.get("ending_qty") or 0) > 0.0000001]

    return columns, data
