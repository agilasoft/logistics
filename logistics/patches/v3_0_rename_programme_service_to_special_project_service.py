# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Rename Programme Service DocType to Special Project Service (pre model sync)."""

from __future__ import annotations

import frappe


def execute():
	if frappe.db.exists("DocType", "Programme Service") and not frappe.db.exists(
		"DocType", "Special Project Service"
	):
		frappe.rename_doc(
			"DocType", "Programme Service", "Special Project Service", force=True, merge=False
		)
		frappe.db.commit()
