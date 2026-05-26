# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Backfill Sales Quote main_service Exhibits → Exhibits."""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.has_column("Sales Quote", "main_service"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabSales Quote`
		SET main_service = 'Exhibits'
		WHERE main_service = 'Exhibits'
		"""
	)
	frappe.db.commit()
