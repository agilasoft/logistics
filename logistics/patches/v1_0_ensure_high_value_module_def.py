# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Ensure Module Def exists for High Value (idempotent)."""

from __future__ import annotations

import frappe


def execute():
	if frappe.db.exists("Module Def", "High Value"):
		return
	doc = frappe.new_doc("Module Def")
	doc.app_name = "logistics"
	doc.module_name = "High Value"
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
