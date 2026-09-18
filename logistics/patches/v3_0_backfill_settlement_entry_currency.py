# Copyright (c) 2026, Agilasoft and contributors

import frappe
from frappe.utils import flt

from logistics.netting.doctype.settlement_entry.settlement_entry import (
	AMOUNT_PRECISION,
	apply_row_conversion,
	fetch_exchange_rate,
	get_reference_currency_fields,
	settlement_in_base,
)


def execute():
	if not frappe.db.has_column("Settlement Entry", "settlement_currency"):
		return
	if not frappe.db.has_column("Settlement Entry Transaction", "currency"):
		return

	company_currency_map = {
		row.name: row.default_currency
		for row in frappe.get_all("Company", fields=["name", "default_currency"])
	}

	entries = frappe.get_all(
		"Settlement Entry",
		fields=["name", "company", "posting_date", "settlement_currency", "conversion_rate"],
	)

	for entry in entries:
		company_currency = company_currency_map.get(entry.company)
		if not company_currency:
			continue

		settlement_currency = entry.settlement_currency or company_currency
		conversion_rate = flt(entry.conversion_rate)
		if settlement_currency == company_currency:
			conversion_rate = 1.0
		elif not conversion_rate:
			conversion_rate = fetch_exchange_rate(
				settlement_currency, company_currency, entry.posting_date, throw=False
			) or 1.0

		frappe.db.set_value(
			"Settlement Entry",
			entry.name,
			{
				"company_currency": company_currency,
				"settlement_currency": settlement_currency,
				"conversion_rate": conversion_rate,
			},
			update_modified=False,
		)

		_backfill_rows(entry.name, settlement_currency, conversion_rate, entry.posting_date)


def _backfill_rows(parent, settlement_currency, conversion_rate, posting_date):
	rows = frappe.get_all(
		"Settlement Entry Transaction",
		filters={"parent": parent},
		fields=[
			"name",
			"reference_doctype",
			"reference_name",
			"party_type",
			"allocated_amount",
			"currency",
			"invoice_conversion_rate",
			"exchange_rate",
		],
	)

	total_receivable = 0
	total_payable = 0
	total_fx = 0

	for row in rows:
		row = frappe._dict(row)
		currency, invoice_rate = get_reference_currency_fields(
			row.reference_doctype, row.reference_name, settlement_currency
		)
		if not row.currency:
			row.currency = currency
		if not flt(row.invoice_conversion_rate):
			row.invoice_conversion_rate = invoice_rate or 1.0

		if not flt(row.exchange_rate):
			from_currency = row.currency or settlement_currency
			if from_currency == settlement_currency:
				row.exchange_rate = 1.0
			elif settlement_currency == row.currency:
				row.exchange_rate = 1.0
			else:
				args = "for_selling" if row.party_type == "Customer" else "for_buying"
				row.exchange_rate = fetch_exchange_rate(
					from_currency, settlement_currency, posting_date, args, throw=False
				)
				if not flt(row.exchange_rate):
					# When settlement currency is company currency, invoice conversion_rate is the book rate.
					row.exchange_rate = flt(row.invoice_conversion_rate) or 1.0

		apply_row_conversion(row, conversion_rate)

		frappe.db.set_value(
			"Settlement Entry Transaction",
			row.name,
			{
				"currency": row.currency,
				"invoice_conversion_rate": row.invoice_conversion_rate,
				"exchange_rate": row.exchange_rate,
				"allocated_amount_in_settlement_currency": row.allocated_amount_in_settlement_currency,
				"exchange_gain_loss": row.exchange_gain_loss,
			},
			update_modified=False,
		)

		amount = flt(row.allocated_amount_in_settlement_currency)
		if row.party_type == "Customer":
			total_receivable += amount
		elif row.party_type == "Supplier":
			total_payable += amount
		total_fx += flt(row.exchange_gain_loss)

	net_amount = flt(total_receivable - total_payable, AMOUNT_PRECISION)
	frappe.db.set_value(
		"Settlement Entry",
		parent,
		{
			"total_receivable": flt(total_receivable, AMOUNT_PRECISION),
			"total_payable": flt(total_payable, AMOUNT_PRECISION),
			"net_amount": net_amount,
			"base_total_receivable": settlement_in_base(total_receivable, conversion_rate),
			"base_total_payable": settlement_in_base(total_payable, conversion_rate),
			"base_net_amount": settlement_in_base(net_amount, conversion_rate),
			"total_exchange_gain_loss": flt(total_fx, AMOUNT_PRECISION),
		},
		update_modified=False,
	)
