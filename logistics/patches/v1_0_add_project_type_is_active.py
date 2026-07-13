# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Add Is Active checkbox to ERPNext Project Type."""

from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	if not frappe.db.exists("DocType", "Project Type"):
		return

	create_custom_fields(
		{
			"Project Type": [
				{
					"fieldname": "is_active",
					"fieldtype": "Check",
					"label": "Is Active",
					"default": "1",
					"insert_after": "description",
					"in_list_view": 1,
					"in_standard_filter": 1,
				},
			]
		},
		update=True,
	)

	frappe.db.sql(
		"UPDATE `tabProject Type` SET is_active = 1 WHERE IFNULL(is_active, 0) = 0"
	)
	frappe.clear_cache(doctype="Project Type")
