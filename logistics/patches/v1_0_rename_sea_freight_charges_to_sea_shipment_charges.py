# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Rename Sea Freight Charges to Sea Shipment Charges (doctype, tables, and references)."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Sea Freight Charges"):
		return

	# 1. Rename parent DocType (renames table tabSea Freight Charges -> tabSea Shipment Charges)
	frappe.rename_doc("DocType", "Sea Freight Charges", "Sea Shipment Charges", force=True, merge=False)
	frappe.db.commit()

	# 2. Update parenttype in child tables, then rename child doctypes
	for old_child, new_child in (
		("Sea Freight Charges Weight Break", "Sea Shipment Charges Weight Break"),
		("Sea Freight Charges Qty Break", "Sea Shipment Charges Qty Break"),
	):
		if not frappe.db.exists("DocType", old_child):
			continue
		# Update parenttype so child rows point to renamed parent
		old_tab = "tab" + old_child
		frappe.db.sql(
			"UPDATE `{0}` SET parenttype = %s WHERE parenttype = %s".format(old_tab),
			("Sea Shipment Charges", "Sea Freight Charges"),
		)
		frappe.rename_doc("DocType", old_child, new_child, force=True, merge=False)
		frappe.db.commit()

	# 3. Update reference_doctype in Sales Quote Weight Break and Qty Break
	for doctype in ("Sales Quote Weight Break", "Sales Quote Qty Break"):
		if frappe.db.exists("DocType", doctype):
			tab = "tab" + doctype
			frappe.db.sql(
				"UPDATE `{0}` SET reference_doctype = %s WHERE reference_doctype = %s".format(tab),
				("Sea Shipment Charges", "Sea Freight Charges"),
			)
	frappe.db.commit()
