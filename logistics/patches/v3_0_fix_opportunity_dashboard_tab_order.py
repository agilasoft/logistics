# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Patch: fix Opportunity Dashboard tab field order."""

from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	if not frappe.db.exists("DocType", "Opportunity"):
		return

	_ensure_misc_tab()
	_reorder_dashboard_fields()
	frappe.clear_cache(doctype="Opportunity")
	frappe.db.commit()


def _ensure_misc_tab():
	"""Start a new tab before native analytics fields so they leave the Dashboard tab."""
	create_custom_fields(
		{
			"Opportunity": [
				{
					"fieldname": "custom_opportunity_misc_tab",
					"fieldtype": "Tab Break",
					"label": "Additional Info",
					"insert_after": "custom_total_scope_actual_profit",
				}
			]
		},
		update=True,
	)


def _reorder_dashboard_fields():
	"""Dashboard tab must be last — after Connections — so Activities stay on Activities tab."""
	updates = {
		"custom_dashboard_tab": {
			"insert_after": "dashboard_tab",
			"label": "Dashboard",
		},
		"custom_opportunity_dashboard_html": {
			"insert_after": "custom_dashboard_tab",
			"read_only": 1,
			"hidden": 0,
			"label": "Dashboard",
			"options": '<div class="text-muted">Loading dashboard…</div>',
		},
	}
	for fieldname, props in updates.items():
		name = frappe.db.get_value("Custom Field", {"dt": "Opportunity", "fieldname": fieldname}, "name")
		if not name:
			continue
		frappe.db.set_value("Custom Field", name, props, update_modified=False)
