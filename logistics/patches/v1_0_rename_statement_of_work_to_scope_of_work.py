# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Rename Statement of Work DocType to Scope of Work."""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.exists("DocType", "Statement of Work"):
		return
	if frappe.db.exists("DocType", "Scope of Work"):
		return
	frappe.flags.in_patch = True
	try:
		frappe.rename_doc(
			"DocType",
			"Statement of Work",
			"Scope of Work",
			force=True,
			merge=False,
		)
	finally:
		frappe.flags.in_patch = False
