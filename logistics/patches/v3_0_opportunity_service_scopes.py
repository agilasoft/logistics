# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Add Services tab and scope child table custom fields on Opportunity."""

from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	if not frappe.db.exists("DocType", "Opportunity"):
		return

	create_custom_fields(_opportunity_custom_fields(), update=True)
	frappe.clear_cache(doctype="Opportunity")
	frappe.db.commit()


def _opportunity_custom_fields():
	return {
		"Opportunity": [
			{
				"fieldname": "custom_services_tab",
				"fieldtype": "Tab Break",
				"label": "Services",
				"insert_after": "base_opportunity_amount",
			},
			{
				"fieldname": "custom_opportunity_scopes_section",
				"fieldtype": "Section Break",
				"label": "Scopes",
				"insert_after": "custom_services_tab",
			},
			{
				"fieldname": "custom_opportunity_scopes",
				"fieldtype": "Table",
				"label": "Scopes",
				"options": "Opportunity Service Scope",
				"insert_after": "custom_opportunity_scopes_section",
			},
			{
				"fieldname": "custom_opportunity_scope_totals_section",
				"fieldtype": "Section Break",
				"label": "Scope Totals",
				"insert_after": "custom_opportunity_scopes",
			},
			{
				"fieldname": "custom_total_scope_opportunity_value",
				"fieldtype": "Currency",
				"label": "Total Opportunity Value",
				"options": "currency",
				"read_only": 1,
				"insert_after": "custom_opportunity_scope_totals_section",
			},
			{
				"fieldname": "custom_total_scope_actual_revenue",
				"fieldtype": "Currency",
				"label": "Total Actual Revenue",
				"options": "currency",
				"read_only": 1,
				"insert_after": "custom_total_scope_opportunity_value",
			},
			{
				"fieldname": "custom_total_scope_actual_profit",
				"fieldtype": "Currency",
				"label": "Total Actual Profit",
				"options": "currency",
				"read_only": 1,
				"insert_after": "custom_total_scope_actual_revenue",
			},
		]
	}
