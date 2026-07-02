# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Drop persisted columns for virtual scope actuals; ensure DocType field flags are synced."""

from __future__ import unicode_literals

import frappe


def execute():
	_drop_scope_actual_columns()
	frappe.clear_cache(doctype="Opportunity Service Scope")
	frappe.db.commit()


def _drop_scope_actual_columns():
	if not frappe.db.table_exists("Opportunity Service Scope"):
		return
	columns = set(frappe.db.get_table_columns("Opportunity Service Scope") or [])
	for column in ("actual_revenue", "actual_profit"):
		if column not in columns:
			continue
		frappe.db.sql_ddl(
			f"ALTER TABLE `tabOpportunity Service Scope` DROP COLUMN `{column}`"
		)
