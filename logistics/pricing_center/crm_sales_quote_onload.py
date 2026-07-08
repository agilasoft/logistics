# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Desk onload flags for CRM Sales Quote actions."""

from __future__ import unicode_literals

import frappe

from logistics.pricing_center.doctype.pricing_center_settings.pricing_center_settings import (
	get_crm_sales_quote_settings,
)


def _company_for_doc(doc):
	return doc.get("company") or frappe.defaults.get_user_default("Company")


def _set_crm_sales_quote_onload(doc):
	settings = get_crm_sales_quote_settings(_company_for_doc(doc))
	doc.set_onload("logistics_allow_sales_quote_from_lead", settings.allow_sales_quote_from_lead)
	doc.set_onload("logistics_allow_sales_quote_from_prospect", settings.allow_sales_quote_from_prospect)


def lead_onload(doc, method=None):
	_set_crm_sales_quote_onload(doc)


def prospect_onload(doc, method=None):
	_set_crm_sales_quote_onload(doc)
	doc.set_onload(
		"logistics_is_customer",
		bool(frappe.db.exists("Customer", {"prospect_name": doc.name})),
	)
