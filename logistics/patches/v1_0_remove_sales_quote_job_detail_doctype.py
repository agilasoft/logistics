# Copyright (c) 2026, Agilasoft and contributors
"""Remove legacy Sales Quote Job Detail DocType after moving to Internal Job Detail on operational documents."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Sales Quote Job Detail"):
		return
	frappe.delete_doc("DocType", "Sales Quote Job Detail", force=True)
	frappe.db.commit()
