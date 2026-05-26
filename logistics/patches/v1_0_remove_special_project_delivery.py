# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Remove Special Project Delivery child table (Deliveries tab removed from Special Project)."""

from __future__ import unicode_literals

import frappe


def execute():
	table = "tabSpecial Project Delivery"
	if frappe.db.table_exists(table):
		frappe.db.sql("DELETE FROM `{}` WHERE parenttype = %s".format(table), ("Special Project",))

	report = "Special Project Delivery Status Report"
	if frappe.db.exists("Report", report):
		frappe.delete_doc("Report", report, force=True, ignore_permissions=True)

	doctype = "Special Project Delivery"
	if frappe.db.exists("DocType", doctype):
		frappe.delete_doc("DocType", doctype, force=True, ignore_permissions=True)

	frappe.db.commit()
