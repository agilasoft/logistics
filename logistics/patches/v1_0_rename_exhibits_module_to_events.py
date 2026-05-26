# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Rename standard app module Exhibits → Events in database."""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.exists("Module Def", "Exhibits"):
		return
	if frappe.db.exists("Module Def", "Events"):
		frappe.db.sql("DELETE FROM `tabModule Def` WHERE name = 'Exhibits'")
	else:
		frappe.db.set_value("Module Def", "Exhibits", "name", "Events", update_modified=False)
		frappe.db.set_value("Module Def", "Exhibits", "module_name", "Events", update_modified=False)

	frappe.db.sql(
		"""
		UPDATE `tabDocType`
		SET module = 'Events'
		WHERE module = 'Exhibits'
		"""
	)
	frappe.db.sql(
		"""
		UPDATE `tabReport`
		SET module = 'Events'
		WHERE module = 'Exhibits'
		"""
	)
	frappe.db.sql(
		"""
		UPDATE `tabWorkspace`
		SET module = 'Events'
		WHERE module = 'Exhibits'
		"""
	)
	frappe.db.commit()
	frappe.clear_cache()
