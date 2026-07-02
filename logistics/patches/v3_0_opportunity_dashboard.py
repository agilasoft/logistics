# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Opportunity Dashboard tab and CRM Settings default metric."""

from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	if frappe.db.exists("DocType", "Opportunity"):
		create_custom_fields(_opportunity_dashboard_fields(), update=True)
	if frappe.db.exists("DocType", "CRM Settings"):
		create_custom_fields(_crm_settings_fields(), update=True)
	frappe.clear_cache(doctype="Opportunity")
	frappe.clear_cache(doctype="CRM Settings")
	frappe.db.commit()


def _crm_settings_fields():
	return {
		"CRM Settings": [
			{
				"fieldname": "custom_opportunity_dashboard_default_metric",
				"fieldtype": "Select",
				"label": "Opportunity Dashboard Default Metric",
				"options": "Revenue\nProfit",
				"default": "Revenue",
				"description": "Default comparison on the Opportunity Dashboard tab (Revenue or Profit vs annual opportunity value).",
				"insert_after": "close_opportunity_after_days",
			},
		]
	}


def _opportunity_dashboard_fields():
	return {
		"Opportunity": [
			{
				"fieldname": "custom_opportunity_misc_tab",
				"fieldtype": "Tab Break",
				"label": "Additional Info",
				"insert_after": "custom_total_scope_actual_profit",
			},
			{
				"fieldname": "custom_dashboard_tab",
				"fieldtype": "Tab Break",
				"label": "Dashboard",
				"insert_after": "dashboard_tab",
			},
			{
				"fieldname": "custom_opportunity_dashboard_html",
				"fieldtype": "HTML",
				"label": "Dashboard",
				"read_only": 1,
				"options": "",
				"insert_after": "custom_dashboard_tab",
			},
		]
	}
