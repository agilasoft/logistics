# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# For license information, please see license.txt

import frappe


def after_install():
	if not frappe.db.exists("Workflow Center Settings"):
		doc = frappe.get_doc({"doctype": "Workflow Center Settings", "enabled": 1})
		doc.insert(ignore_permissions=True)
