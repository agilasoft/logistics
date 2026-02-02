# Copyright (c) 2025, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Fix Report docs (Script Report) that have null/empty json field.

report_view.js does JSON.parse(this.report_doc.json); if json is undefined/null
from the API, the client gets JSON.parse(undefined) which throws:
  SyntaxError: "undefined" is not valid JSON

Set a valid default json string so the report view can parse it.
"""

import frappe


def execute():
    default_json = '{"filters": [], "order_by": "creation desc", "add_totals_row": 0, "page_length": 20}'
    report_name = "Fuel Consumption Analysis"

    if not frappe.db.exists("Report", report_name):
        return

    current = frappe.db.get_value("Report", report_name, "json")
    if current is None or current == "" or current == "null":
        frappe.db.set_value("Report", report_name, "json", default_json)
        frappe.db.commit()
        print(f"Set json field for Report: {report_name}")
