# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
"""Customer credit totals from ERPNext Customer Credit Limit rows.

Exposure is the positive general-ledger balance for the same customer and
company as a credit-limit row. The credit limit is the sum of those rows.
"""

from __future__ import unicode_literals


def _amount(value):
	try:
		return float(value or 0)
	except (TypeError, ValueError):
		return 0.0


def summarize_customer_credit(limit_rows, balance_rows):
	"""Combine Customer Credit Limit rows with customer/company balances.

	``limit_rows`` use ``parent`` (Customer) and ``company``.
	``balance_rows`` use ``party`` (Customer) and ``company``.
	Only a positive balance that matches a credit-limit row is exposure.
	"""
	keys = set()
	limit_total = 0.0
	for row in limit_rows or []:
		parent = row.get("parent")
		company = row.get("company")
		if not parent:
			continue
		limit_total += _amount(row.get("credit_limit"))
		if company:
			keys.add((parent, company))

	exposure = 0.0
	seen = set()
	for row in balance_rows or []:
		key = (row.get("party"), row.get("company"))
		if key not in keys or key in seen:
			continue
		seen.add(key)
		outstanding = _amount(row.get("outstanding"))
		if outstanding > 0:
			exposure += outstanding

	return {"exposure": exposure, "limit": limit_total}


def customer_credit_totals():
	"""Read Customer Credit Limit and GL balances. Returns exposure and limit."""
	try:
		import frappe
	except ImportError:
		return {"exposure": 0.0, "limit": 0.0}

	limit_rows = []
	balance_rows = []
	try:
		if frappe.db.table_exists("Customer Credit Limit"):
			limit_rows = frappe.db.sql(
				"""
				SELECT parent, company, credit_limit
				FROM `tabCustomer Credit Limit`
				WHERE parenttype = 'Customer'
				""",
				as_dict=True,
			)
	except Exception:
		limit_rows = []

	try:
		if frappe.db.table_exists("GL Entry"):
			balance_rows = frappe.db.sql(
				"""
				SELECT party, company, SUM(debit) - SUM(credit) AS outstanding
				FROM `tabGL Entry`
				WHERE party_type = 'Customer'
				  AND IFNULL(is_cancelled, 0) = 0
				GROUP BY party, company
				""",
				as_dict=True,
			)
	except Exception:
		balance_rows = []

	return summarize_customer_credit(limit_rows, balance_rows)
