# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Add project field to Warehouse Job (fixes when warehouse_job.py TabError was resolved).
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	"""Add project field to Warehouse Job."""
	if not frappe.db.exists("DocType", "Warehouse Job"):
		return
	if frappe.db.exists("Custom Field", {"dt": "Warehouse Job", "fieldname": "project"}):
		return
	meta = frappe.get_meta("Warehouse Job")
	if meta.get_field("project"):
		return

	create_custom_fields(
		{
			"Warehouse Job": [
				{
					"fieldname": "project",
					"fieldtype": "Link",
					"label": "Project",
					"options": "Project",
					"insert_after": "amended_from",
					"description": "ERPNext Project for Special Projects integration",
				}
			]
		},
		update=True,
	)
	frappe.db.commit()
	print("Added project field to Warehouse Job for Special Projects")
