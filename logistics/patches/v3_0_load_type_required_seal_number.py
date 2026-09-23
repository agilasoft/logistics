# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Preserve prior Sea Booking rule: seal required except for LCL."""
	if not frappe.db.has_column("Load Type", "required_seal_number"):
		return

	frappe.db.sql(
		"""
		UPDATE `tabLoad Type`
		SET required_seal_number = 1
		WHERE IFNULL(name, '') != 'LCL'
		"""
	)
