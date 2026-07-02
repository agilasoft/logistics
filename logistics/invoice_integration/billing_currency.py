# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Shared billing currency / exchange-rate helpers for logistics invoice dialogs."""

from __future__ import annotations

from typing import Any, Dict, Optional

import frappe
from frappe import _
from frappe.utils import flt


def company_currency(company: Optional[str]) -> str:
	return frappe.get_cached_value("Company", company, "default_currency") or frappe.defaults.get_global_default(
		"currency"
	)


def customer_default_billing_currency(customer: Optional[str], company: str) -> str:
	ccy = company_currency(company)
	if customer:
		cust_cur = frappe.db.get_value("Customer", customer, "default_currency")
		if cust_cur:
			return cust_cur
	return ccy


def supplier_default_billing_currency(supplier: Optional[str], company: str) -> str:
	ccy = company_currency(company)
	if supplier:
		sup_cur = frappe.db.get_value("Supplier", supplier, "default_currency")
		if sup_cur:
			return sup_cur
	return ccy


def resolve_selling_charge_currency(ch, job_type: str, company: str) -> str:
	cur = getattr(ch, "selling_currency", None) or getattr(ch, "currency", None)
	return (cur or "").strip() or company_currency(company)


def resolve_cost_charge_currency(ch, company: str, consolidation_doctype: Optional[str] = None) -> str:
	if consolidation_doctype == "Sea Consolidation":
		cur = (
			getattr(ch, "cost_currency", None)
			or getattr(ch, "buying_currency", None)
			or getattr(ch, "currency", None)
		)
	elif consolidation_doctype == "Air Consolidation":
		cur = getattr(ch, "currency", None)
	else:
		cur = (
			getattr(ch, "cost_currency", None)
			or getattr(ch, "buying_currency", None)
			or getattr(ch, "currency", None)
		)
	return (cur or "").strip() or company_currency(company)


def _operational_row_rate(ch, row_field: str, source_field: str, date_field: str) -> float:
	return flt(getattr(ch, row_field, None))


def _has_operational_exchange(ch, source_field: str, date_field: str) -> bool:
	return bool(getattr(ch, source_field, None)) or bool(getattr(ch, date_field, None))


def charge_to_company_rate(
	ch,
	charge_currency: str,
	company_currency_code: str,
	posting_date: str,
	*,
	purpose: str = "for_selling",
	row_rate_field: str = "bill_to_exchange_rate",
	source_field: str = "bill_to_exchange_rate_source",
	date_field: str = "bill_to_exchange_rate_date",
) -> float:
	"""Company base currency units per 1 unit of charge_currency."""
	if charge_currency == company_currency_code:
		return 1.0
	row_rate = _operational_row_rate(ch, row_rate_field, source_field, date_field)
	has_operational = _has_operational_exchange(ch, source_field, date_field)
	if row_rate > 0 and (has_operational or row_rate != 1.0):
		return row_rate
	from erpnext.setup.utils import get_exchange_rate

	rate = flt(get_exchange_rate(charge_currency, company_currency_code, posting_date, purpose))
	if not rate:
		frappe.throw(
			_("Exchange rate not found for {0} to {1} on {2}.").format(
				charge_currency, company_currency_code, posting_date
			)
		)
	return rate


def charge_to_company_rate_selling(ch, charge_currency: str, company_currency_code: str, posting_date: str) -> float:
	return charge_to_company_rate(
		ch,
		charge_currency,
		company_currency_code,
		posting_date,
		purpose="for_selling",
		row_rate_field="bill_to_exchange_rate",
		source_field="bill_to_exchange_rate_source",
		date_field="bill_to_exchange_rate_date",
	)


def charge_to_company_rate_buying(ch, charge_currency: str, company_currency_code: str, posting_date: str) -> float:
	return charge_to_company_rate(
		ch,
		charge_currency,
		company_currency_code,
		posting_date,
		purpose="for_buying",
		row_rate_field="pay_to_exchange_rate",
		source_field="pay_to_exchange_rate_source",
		date_field="pay_to_exchange_rate_date",
	)


def convert_amount_to_billing_currency(
	amount: float,
	charge_currency: str,
	billing_currency: str,
	company_currency_code: str,
	billing_exchange_rate: float,
	charge_to_company_rate_value: float,
) -> float:
	"""Convert charge amount from charge_currency into billing_currency."""
	amount = flt(amount)
	if charge_currency == billing_currency:
		return amount
	if billing_currency == company_currency_code:
		return flt(amount * charge_to_company_rate_value)
	if charge_currency == company_currency_code:
		if not billing_exchange_rate:
			frappe.throw(_("Exchange rate is required when billing in {0}.").format(billing_currency))
		return flt(amount / billing_exchange_rate)
	if not charge_to_company_rate_value or not billing_exchange_rate:
		frappe.throw(
			_("Cannot convert {0} to {1}: missing exchange rate.").format(charge_currency, billing_currency)
		)
	return flt(amount * charge_to_company_rate_value / billing_exchange_rate)


def invoice_billing_context(
	company: str,
	billing_currency: Optional[str],
	exchange_rate: Optional[float],
	posting_date: str,
	*,
	purpose: str = "for_selling",
) -> Dict[str, Any]:
	company_currency_code = company_currency(company)
	billing = (billing_currency or "").strip() or company_currency_code
	rate = flt(exchange_rate) or 1.0
	if billing == company_currency_code:
		rate = 1.0
	elif not rate:
		from erpnext.setup.utils import get_exchange_rate

		rate = flt(get_exchange_rate(billing, company_currency_code, posting_date, purpose))
		if not rate:
			frappe.throw(
				_("Exchange rate not found for {0} to {1} on {2}.").format(
					billing, company_currency_code, posting_date
				)
			)
	return {
		"company_currency": company_currency_code,
		"billing_currency": billing,
		"billing_exchange_rate": rate,
	}
