# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors

from __future__ import unicode_literals

import frappe


def after_migrate():
	# Runs after orphan cleanup, which drops a standard DocType whose controller
	# did not import. Cash Advance Liquidation is a parent; if that row is gone
	# the desk route /desk/cash-advance-liquidation is a missing Page.
	ensure_cash_advance_liquidation_doctype()
	if frappe.flags.in_install:
		return
	_ensure_cash_advance_settings()
	_backfill_account_require_job_number_for_revolving_fund()


def ensure_cash_advance_liquidation_doctype():
	"""Reimport the parent DocType when it is missing or still the old child table.

	The pre-sync rename only moves the child when Cash Advance Request Item does
	not exist yet. Sites that already had that child kept the name Cash Advance
	Liquidation on an istable DocType, or lost the parent row entirely. Either
	way the list route cannot resolve.
	"""
	if frappe.db.exists("DocType", "Cash Advance Liquidation"):
		istable = frappe.db.get_value("DocType", "Cash Advance Liquidation", "istable")
		table_ok = frappe.db.table_exists("tabCash Advance Liquidation")
		if not istable and table_ok:
			return
		if istable and not frappe.db.exists("DocType", "Cash Advance Request Item"):
			frappe.rename_doc(
				"DocType",
				"Cash Advance Liquidation",
				"Cash Advance Request Item",
				force=True,
			)

	if not frappe.db.exists("DocType", "Cash Advance Liquidation Item"):
		frappe.reload_doc("cash_advance", "doctype", "cash_advance_liquidation_item", force=True)
	frappe.reload_doc("cash_advance", "doctype", "cash_advance_liquidation", force=True)
	frappe.clear_cache(doctype="Cash Advance Liquidation")


def _ensure_cash_advance_settings():
	if not frappe.db.exists("DocType", "Cash Advance Settings"):
		return

	legacy = _load_legacy_cash_advance_settings_data()
	companies = frappe.get_all("Company", pluck="name")
	if not companies:
		return

	skip_keys = {
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"idx",
		"company",
	}

	for company in companies:
		if frappe.db.exists("Cash Advance Settings", {"company": company}):
			continue
		doc = frappe.new_doc("Cash Advance Settings")
		doc.company = company
		if legacy:
			for key, value in legacy.items():
				if key in skip_keys or value is None:
					continue
				if doc.meta.has_field(key):
					doc.set(key, value)
		doc.flags.ignore_validate = True
		doc.insert(ignore_permissions=True)


def _load_legacy_cash_advance_settings_data():
	if frappe.db.exists("Cash Advance Settings", "Cash Advance Settings"):
		return frappe.db.get_value("Cash Advance Settings", "Cash Advance Settings", "*", as_dict=True)

	latest_name = frappe.db.get_value("Cash Advance Settings", {}, "name", order_by="modified desc")
	if latest_name:
		return frappe.db.get_value("Cash Advance Settings", latest_name, "*", as_dict=True)

	return None


def _backfill_account_require_job_number_for_revolving_fund():
	if not frappe.db.has_column("Account", "require_job_number"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabAccount`
		SET require_job_number = 1
		WHERE fund_type = 'Revolving Fund'
		  AND IFNULL(require_job_number, 0) = 0
		"""
	)
