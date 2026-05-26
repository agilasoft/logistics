# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Default lifecycle stage on existing Special Projects."""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.table_exists("tabSpecial Project"):
		return
	if not frappe.db.has_column("Special Project", "lifecycle_stage"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabSpecial Project`
		SET lifecycle_stage = 'Pre-Show'
		WHERE IFNULL(lifecycle_stage, '') = ''
		"""
	)
	frappe.db.commit()
