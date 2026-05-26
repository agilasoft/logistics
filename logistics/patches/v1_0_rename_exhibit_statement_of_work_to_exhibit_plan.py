# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Rename Exhibit Statement of Work DocType to Event Plan."""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.exists("DocType", "Exhibit Statement of Work"):
		return
	if frappe.db.exists("DocType", "Event Plan"):
		return
	frappe.flags.in_patch = True
	try:
		frappe.rename_doc(
			"DocType",
			"Exhibit Statement of Work",
			"Event Plan",
			force=True,
			merge=False,
		)
	finally:
		frappe.flags.in_patch = False
