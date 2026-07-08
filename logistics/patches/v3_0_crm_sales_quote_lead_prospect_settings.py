# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""CRM Sales Quote: Lead/Prospect settings, prospect traceability field, Prospect client script."""

from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from logistics.pricing_center.utils.client_script_sync import sync_pricing_center_client_scripts


def execute():
	if frappe.db.exists("DocType", "Sales Quote"):
		create_custom_fields(_sales_quote_prospect_field(), update=True)
	sync_pricing_center_client_scripts()
	frappe.clear_cache(doctype="Sales Quote")
	frappe.clear_cache(doctype="Prospect")
	frappe.db.commit()


def _sales_quote_prospect_field():
	return {
		"Sales Quote": [
			{
				"fieldname": "prospect",
				"fieldtype": "Link",
				"label": "Prospect",
				"options": "Prospect",
				"insert_after": "lead",
				"read_only": 1,
			},
		]
	}
