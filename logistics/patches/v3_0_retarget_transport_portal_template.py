# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Point stored transport portal pages at the customer template under logistics/www."""

from __future__ import annotations

OLD_TEMPLATE = "logistics/transport/www/transport_portal.html"
NEW_TEMPLATE = "logistics/www/transport_portal.html"
DOCTYPES = ("Transport Portal Page", "Transport Portal Web Page")


def execute():
	import frappe

	for doctype in DOCTYPES:
		if not frappe.db.table_exists(doctype):
			continue
		if not frappe.db.has_column(doctype, "template_path"):
			continue
		frappe.db.sql(
			f"""
			UPDATE `tab{doctype}`
			SET template_path = %s
			WHERE template_path = %s
			""",
			(NEW_TEMPLATE, OLD_TEMPLATE),
		)
