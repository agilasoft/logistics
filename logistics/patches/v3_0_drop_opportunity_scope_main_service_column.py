# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Drop legacy ``main_service`` column after ``service_type`` rename."""

from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.table_exists("tabOpportunity Service Scope"):
		return
	columns = set(frappe.db.get_table_columns("Opportunity Service Scope") or [])
	if "main_service" not in columns:
		return
	if "service_type" in columns:
		frappe.db.sql(
			"""
			UPDATE `tabOpportunity Service Scope`
			SET service_type = main_service
			WHERE (service_type IS NULL OR service_type = '')
			  AND main_service IS NOT NULL AND main_service != ''
			"""
		)
	frappe.db.sql_ddl("ALTER TABLE `tabOpportunity Service Scope` DROP COLUMN `main_service`")
	frappe.clear_cache(doctype="Opportunity Service Scope")
	frappe.db.commit()
