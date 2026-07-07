# Copyright (c) 2026, Agilasoft and contributors

import frappe


def execute():
	frappe.db.sql(
		"""
		UPDATE `tabAccount`
		SET require_job_number = 1
		WHERE fund_type = 'Revolving Fund'
		  AND IFNULL(require_job_number, 0) = 0
		"""
	)
