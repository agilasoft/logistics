# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Backfill is_active on Milestone Template records created before the field was added."""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.exists("DocType", "Milestone Template"):
		return
	if not frappe.db.has_column("Milestone Template", "is_active"):
		return

	frappe.db.sql(
		"""
		UPDATE `tabMilestone Template`
		SET is_active = 1
		WHERE IFNULL(is_active, 0) = 0
		"""
	)
	frappe.db.commit()
