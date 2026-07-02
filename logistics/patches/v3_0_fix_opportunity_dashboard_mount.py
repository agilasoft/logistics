# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Patch: remove hidden dashboard section; mount HTML field on tab directly."""

from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.exists("DocType", "Opportunity"):
		return

	_remove_dashboard_section()
	_fix_dashboard_html_field()
	frappe.clear_cache(doctype="Opportunity")
	frappe.db.commit()


def _remove_dashboard_section():
	name = frappe.db.get_value(
		"Custom Field", {"dt": "Opportunity", "fieldname": "custom_opportunity_dashboard_section"}, "name"
	)
	if name:
		frappe.delete_doc("Custom Field", name, force=1, ignore_permissions=True)


def _fix_dashboard_html_field():
	name = frappe.db.get_value(
		"Custom Field", {"dt": "Opportunity", "fieldname": "custom_opportunity_dashboard_html"}, "name"
	)
	if not name:
		return
	frappe.db.set_value(
		"Custom Field",
		name,
		{
			"insert_after": "custom_dashboard_tab",
			"hidden": 0,
			"read_only": 1,
			"label": "Dashboard",
			"options": "",
		},
		update_modified=False,
	)
