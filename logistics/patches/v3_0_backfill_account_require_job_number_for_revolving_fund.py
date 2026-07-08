# Copyright (c) 2026, Agilasoft and contributors

import frappe


def execute():
	# Custom Account fields sync in post_schema_updates, after post_model_sync patches.
	if not frappe.db.has_column("Account", "require_job_number"):
		return

	frappe.db.sql(
		"""
		UPDATE `tabAccount`
		SET require_job_number = 1
		WHERE fund_type = 'Revolving Fund'
		  AND IFNULL(require_job_number, 0) = 0
		"""
	)
