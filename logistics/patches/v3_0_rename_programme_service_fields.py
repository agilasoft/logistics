# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Rename special_project_services parentfield and special_project_service_line column after doctype rename."""

from __future__ import annotations

import frappe


def execute():
	frappe.reload_doc("special_projects", "doctype", "special_project_service", force=True)
	frappe.reload_doc("special_projects", "doctype", "special_project", force=True)
	frappe.reload_doc("special_projects", "doctype", "special_project_charges", force=True)

	table = "Special Project Service"
	if frappe.db.table_exists(f"tab{table}"):
		if _column_exists(table, "special_project_service_line") and not _column_exists(
			table, "special_project_service_line"
		):
			frappe.db.sql(
				f"""
				ALTER TABLE `tab{table}`
				CHANGE `special_project_service_line` `special_project_service_line` varchar(140)
				"""
			)
		frappe.db.sql(
			f"""
			UPDATE `tab{table}`
			SET parentfield = 'special_project_services'
			WHERE parenttype = 'Special Project' AND parentfield = 'special_project_services'
			"""
		)

	charges = "Special Project Charges"
	if frappe.db.table_exists(f"tab{charges}"):
		if _column_exists(charges, "special_project_service_line") and not _column_exists(
			charges, "special_project_service_line"
		):
			frappe.db.sql(
				f"""
				ALTER TABLE `tab{charges}`
				CHANGE `special_project_service_line` `special_project_service_line` varchar(140)
				"""
			)

	frappe.clear_cache(doctype=table)
	frappe.clear_cache(doctype="Special Project")
	frappe.clear_cache(doctype=charges)


def _column_exists(doctype: str, column: str) -> bool:
	return bool(
		frappe.db.sql(
			"""
			SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
			WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
			""",
			(f"tab{doctype}", column),
		)
	)
