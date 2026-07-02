# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Drop Sales Quote / Job Number from Opportunity scopes; relabel annual vs YTD totals."""

from __future__ import unicode_literals

import frappe


def execute():
	_drop_scope_link_columns()
	_update_opportunity_scope_total_labels()
	frappe.clear_cache(doctype="Opportunity Service Scope")
	frappe.clear_cache(doctype="Opportunity")
	frappe.db.commit()


def _drop_scope_link_columns():
	if not frappe.db.table_exists("Opportunity Service Scope"):
		return
	columns = set(frappe.db.get_table_columns("Opportunity Service Scope") or [])
	for column in ("sales_quote", "job_number", "actual_revenue", "actual_profit"):
		if column not in columns:
			continue
		frappe.db.sql_ddl(f"ALTER TABLE `tabOpportunity Service Scope` DROP COLUMN `{column}`")


def _update_opportunity_scope_total_labels():
	labels = {
		"custom_total_scope_opportunity_value": "Total Annual Opportunity Value",
		"custom_total_scope_actual_revenue": "Total Actual Revenue (YTD)",
		"custom_total_scope_actual_profit": "Total Actual Profit (YTD)",
	}
	for fieldname, label in labels.items():
		name = frappe.db.get_value(
			"Custom Field",
			{"dt": "Opportunity", "fieldname": fieldname},
			"name",
		)
		if name:
			frappe.db.set_value("Custom Field", name, "label", label, update_modified=False)
