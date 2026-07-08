# Copyright (c) 2026, Agilasoft and contributors

import frappe


def execute():
	if not frappe.db.has_column("Cash Advance Request", "job_number"):
		return
	frappe.db.sql_ddl("ALTER TABLE `tabCash Advance Request` DROP COLUMN `job_number`")
