# Copyright (c) 2026, logistics.agilasoft.com and contributors
# For license information, please see license.txt
"""Apply Sea Freight Settings defaults to documents (branch, cost center, profit center)."""

import frappe

from logistics.sea_freight.doctype.sea_freight_settings.sea_freight_settings import SeaFreightSettings


def apply_accounting_defaults_from_sea_freight_settings(doc):
	"""Fill branch, cost center, and profit center from Sea Freight Settings when still empty.

	Does not overwrite user or quote-sourced values. Uses settings for the document company.
	"""
	if getattr(doc, "_sea_freight_settings_accounting_applied", None):
		return
	company = getattr(doc, "company", None)
	if not company:
		return
	try:
		settings = SeaFreightSettings.get_settings(company)
	except Exception:
		return
	if not settings:
		return

	def _set_link_if_empty(doc, fieldname, doctype, value):
		if getattr(doc, fieldname, None) or not value:
			return
		if frappe.db.exists(doctype, value):
			setattr(doc, fieldname, value)

	_set_link_if_empty(doc, "branch", "Branch", getattr(settings, "default_branch", None))
	_set_link_if_empty(doc, "cost_center", "Cost Center", getattr(settings, "default_cost_center", None))
	_set_link_if_empty(doc, "profit_center", "Profit Center", getattr(settings, "default_profit_center", None))
	doc._sea_freight_settings_accounting_applied = True
