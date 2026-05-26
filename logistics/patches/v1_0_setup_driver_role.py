# Copyright (c) 2025 Agilasoft. All rights reserved.
"""Create Driver role for native mobile app users if it does not exist."""

import frappe


def execute():
	if frappe.db.exists("Role", "Driver"):
		return

	frappe.get_doc(
		{
			"doctype": "Role",
			"role_name": "Driver",
			"desk_access": 1,
			"disabled": 0,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
