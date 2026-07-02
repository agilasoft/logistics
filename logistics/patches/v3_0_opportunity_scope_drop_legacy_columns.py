# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Re-drop legacy Opportunity Service Scope columns after DocType sync."""

from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.table_exists("Opportunity Service Scope"):
		return
	columns = set(frappe.db.get_table_columns("Opportunity Service Scope") or [])
	for column in ("sales_quote", "job_number", "actual_revenue", "actual_profit"):
		if column not in columns:
			continue
		frappe.db.sql_ddl(f"ALTER TABLE `tabOpportunity Service Scope` DROP COLUMN `{column}`")
	frappe.clear_cache(doctype="Opportunity Service Scope")
	frappe.db.commit()
