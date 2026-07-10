# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, see license.txt

"""Resolve GL accounts from Item / Item Group defaults with company fallback."""

from __future__ import unicode_literals

from typing import Optional, Tuple

import frappe
from frappe import _


def _item_default_accounts(item_code: str, company: str, parenttype: str, parent: str) -> dict:
	row = frappe.db.sql(
		"""
		SELECT income_account, expense_account, purchase_expense_account
		FROM `tabItem Default`
		WHERE parent=%(parent)s AND parenttype=%(parenttype)s AND company=%(company)s
		LIMIT 1
		""",
		{"parent": parent, "parenttype": parenttype, "company": company},
		as_dict=True,
	)
	return row[0] if row else {}


def get_expense_account_for_item(item_code: str, company: str) -> Optional[str]:
	"""Resolve expense account: Item Default -> Item Group Default -> Company default."""
	if not item_code:
		return None

	row = _item_default_accounts(item_code, company, "Item", item_code)
	acc = row.get("expense_account") or row.get("purchase_expense_account")
	if acc:
		return acc

	item_group = frappe.db.get_value("Item", item_code, "item_group")
	if item_group:
		row = _item_default_accounts(item_code, company, "Item Group", item_group)
		acc = row.get("expense_account") or row.get("purchase_expense_account")
		if acc:
			return acc

	co_defaults = frappe.db.get_value(
		"Company",
		company,
		["default_expense_account", "purchase_expense_account"],
		as_dict=True,
	) or {}
	return co_defaults.get("default_expense_account") or co_defaults.get("purchase_expense_account") or None


def get_income_account_for_item(item_code: str, company: str) -> Optional[str]:
	"""Resolve income account: Item Default -> Item Group Default -> Company default."""
	if not item_code:
		return None

	row = _item_default_accounts(item_code, company, "Item", item_code)
	acc = row.get("income_account")
	if acc:
		return acc

	item_group = frappe.db.get_value("Item", item_code, "item_group")
	if item_group:
		row = _item_default_accounts(item_code, company, "Item Group", item_group)
		acc = row.get("income_account")
		if acc:
			return acc

	return frappe.db.get_value("Company", company, "default_income_account") or None


def get_item_accounts_for_internal_billing(item_code: str, company: str) -> Tuple[str, str]:
	"""Return (expense_account, income_account) for internal billing; throw if either is missing."""
	expense_account = get_expense_account_for_item(item_code, company)
	income_account = get_income_account_for_item(item_code, company)
	missing = []
	if not expense_account:
		missing.append(_("expense"))
	if not income_account:
		missing.append(_("income"))
	if missing:
		frappe.throw(
			_("Item {0} (company {1}): set {2} account in Item Defaults for internal billing.").format(
				item_code,
				company,
				" and ".join(missing),
			)
		)
	return expense_account, income_account
