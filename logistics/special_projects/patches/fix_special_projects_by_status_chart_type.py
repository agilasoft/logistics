# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Fix Dashboard Chart "Special Projects by Status" to use chart_type "Group By"
so it uses group_by_based_on (status) instead of empty based_on, avoiding
"Invalid field format for SELECT" error.
"""

import frappe


def execute():
    if not frappe.db.exists("Dashboard Chart", "Special Projects by Status"):
        return
    frappe.db.set_value(
        "Dashboard Chart",
        "Special Projects by Status",
        "chart_type",
        "Group By",
        update_modified=False,
    )
    frappe.db.commit()
