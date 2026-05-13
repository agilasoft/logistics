# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Remove Special Project Request and its child table after app files are deleted."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Special Project Request") and not frappe.db.exists(
		"DocType", "Special Project Activity Request"
	):
		return

	frappe.flags.in_patch = True
	try:
		for name in frappe.get_all(
			"Report", filters={"ref_doctype": "Special Project Request"}, pluck="name"
		):
			frappe.delete_doc("Report", name, force=True, ignore_missing=True, ignore_permissions=True)

		for name in frappe.get_all(
			"Number Card", filters={"document_type": "Special Project Request"}, pluck="name"
		):
			frappe.delete_doc("Number Card", name, force=True, ignore_missing=True, ignore_permissions=True)

		# Child table first
		if frappe.db.exists("DocType", "Special Project Activity Request"):
			frappe.delete_doc(
				"DocType",
				"Special Project Activity Request",
				force=True,
				ignore_permissions=True,
			)

		if frappe.db.exists("DocType", "Special Project Request"):
			frappe.delete_doc("DocType", "Special Project Request", force=True, ignore_permissions=True)

		frappe.db.commit()
	finally:
		frappe.flags.in_patch = False
