# Copyright (c) 2026, logistics.agilasoft.com and contributors
# For license information, please see license.txt
"""Apply Sea Freight Settings defaults to documents (branch, cost center, profit center)."""

import frappe


def _sea_freight_settings_match_company(settings, company):
	"""If Default Company is set on Sea Freight Settings, only apply defaults for that company."""
	if not company:
		return False
	default_company = getattr(settings, "default_company", None)
	if not default_company:
		return True
	return default_company == company


def _set_link_if_empty(doc, fieldname, doctype, value):
	if getattr(doc, fieldname, None) or not value:
		return
	if frappe.db.exists(doctype, value):
		setattr(doc, fieldname, value)


def apply_accounting_defaults_from_sea_freight_settings(doc):
	"""Fill branch, cost center, and profit center from Sea Freight Settings when still empty.

	Does not overwrite user or quote-sourced values. When Default Company is set on settings,
	defaults apply only to documents for that company.
	"""
	if getattr(doc, "_sea_freight_settings_accounting_applied", None):
		return
	try:
		settings = frappe.get_single("Sea Freight Settings")
	except Exception:
		return
	if not settings or not _sea_freight_settings_match_company(settings, getattr(doc, "company", None)):
		return

	_set_link_if_empty(doc, "branch", "Branch", getattr(settings, "default_branch", None))
	_set_link_if_empty(doc, "cost_center", "Cost Center", getattr(settings, "default_cost_center", None))
	_set_link_if_empty(doc, "profit_center", "Profit Center", getattr(settings, "default_profit_center", None))
	doc._sea_freight_settings_accounting_applied = True
