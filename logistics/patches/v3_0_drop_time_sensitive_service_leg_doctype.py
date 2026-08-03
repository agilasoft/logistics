# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

"""Remove the obsolete Time Sensitive Case Service Leg child DocType."""

import frappe


def execute():
	if frappe.db.exists("DocType", "Time Sensitive Case Service Leg"):
		frappe.delete_doc(
			"DocType",
			"Time Sensitive Case Service Leg",
			force=True,
			ignore_permissions=True,
		)

