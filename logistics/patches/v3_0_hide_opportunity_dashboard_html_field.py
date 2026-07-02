# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Hide broken HTML field; dashboard renders via injected tab mount only."""

from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.exists("DocType", "Opportunity"):
		return

	name = frappe.db.get_value(
		"Custom Field", {"dt": "Opportunity", "fieldname": "custom_opportunity_dashboard_html"}, "name"
	)
	if name:
		frappe.db.set_value(
			"Custom Field",
			name,
			{"hidden": 1, "options": "", "label": "Dashboard"},
			update_modified=False,
		)
	frappe.clear_cache(doctype="Opportunity")
	frappe.db.commit()
