# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe


def execute():
	"""Seed Sea Freight Settings.default_release_type when Prepaid exists and the field is empty."""
	if not frappe.db.has_column("Sea Freight Settings", "default_release_type"):
		return
	if not frappe.db.exists("Release Type", "Prepaid"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabSea Freight Settings`
		SET default_release_type = 'Prepaid'
		WHERE IFNULL(default_release_type, '') = ''
		"""
	)
