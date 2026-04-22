# Copyright (c) 2026, www.agilasoft.com and contributors
"""Rename Sales Quote Charge column calculation_method -> revenue_calculation_method (pre–DocType sync)."""

import frappe


def execute():
	if not frappe.db.table_exists("tabSales Quote Charge"):
		return
	cols = frappe.db.get_table_columns("Sales Quote Charge")
	if "calculation_method" not in cols:
		return
	if "revenue_calculation_method" in cols:
		return
	col_type = frappe.db.sql(
		"""
		SELECT COLUMN_TYPE FROM information_schema.COLUMNS
		WHERE TABLE_SCHEMA = DATABASE()
		AND TABLE_NAME = 'tabSales Quote Charge'
		AND COLUMN_NAME = 'calculation_method'
		""",
	)[0][0]
	frappe.db.sql(
		f"ALTER TABLE `tabSales Quote Charge` CHANGE `calculation_method` `revenue_calculation_method` {col_type}"
	)
	frappe.db.commit()
