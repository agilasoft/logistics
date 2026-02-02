# Copyright (c) 2025 Agilasoft. All rights reserved.
"""Create Warehouse Manager and Warehouse User roles if they do not exist."""

import frappe


def execute():
	for role_name in ("Warehouse Manager", "Warehouse User"):
		if not frappe.db.exists("Role", role_name):
			frappe.get_doc(
				{
					"doctype": "Role",
					"role_name": role_name,
					"desk_access": 1,
					"disabled": 0,
				}
			).insert(ignore_permissions=True)
			frappe.db.commit()
