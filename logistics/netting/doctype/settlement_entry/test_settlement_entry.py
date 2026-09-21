# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

from frappe.tests import UnitTestCase
from frappe.utils import flt

from logistics.netting.doctype.settlement_entry.settlement_entry import (
	apply_row_conversion,
	fx_plug,
	net_settlement_amounts,
	original_book_amount,
	party_clearing_amounts,
	row_exchange_gain_loss,
	settlement_amount,
	settlement_in_base,
)


class _Row:
	def __init__(self, **kwargs):
		self.party_type = kwargs.get("party_type")
		self.allocated_amount = kwargs.get("allocated_amount")
		self.exchange_rate = kwargs.get("exchange_rate")
		self.invoice_conversion_rate = kwargs.get("invoice_conversion_rate")
		self.allocated_amount_in_settlement_currency = kwargs.get("allocated_amount_in_settlement_currency")
		self.exchange_gain_loss = kwargs.get("exchange_gain_loss")


def _totals(rows, conversion_rate):
	total_receivable = 0
	total_payable = 0
	total_fx = 0
	for row in rows:
		apply_row_conversion(row, conversion_rate)
		amount = flt(row.allocated_amount_in_settlement_currency)
		if row.party_type == "Customer":
			total_receivable += amount
		elif row.party_type == "Supplier":
			total_payable += amount
		total_fx += flt(row.exchange_gain_loss)
	return {
		"total_receivable": flt(total_receivable, 2),
		"total_payable": flt(total_payable, 2),
		"net_amount": flt(total_receivable - total_payable, 2),
		"base_total_receivable": settlement_in_base(total_receivable, conversion_rate),
		"base_total_payable": settlement_in_base(total_payable, conversion_rate),
		"base_net_amount": settlement_in_base(total_receivable - total_payable, conversion_rate),
		"total_exchange_gain_loss": flt(total_fx, 2),
	}


class TestSettlementEntryCurrency(UnitTestCase):
	def test_same_currency_nets_with_rate_one(self):
		rows = [
			_Row(
				party_type="Customer",
				allocated_amount=1000,
				exchange_rate=1,
				invoice_conversion_rate=1,
			),
			_Row(
				party_type="Supplier",
				allocated_amount=400,
				exchange_rate=1,
				invoice_conversion_rate=1,
			),
		]
		totals = _totals(rows, conversion_rate=1)
		self.assertEqual(totals["total_receivable"], 1000)
		self.assertEqual(totals["total_payable"], 400)
		self.assertEqual(totals["net_amount"], 600)
		self.assertEqual(totals["base_net_amount"], 600)
		self.assertEqual(totals["total_exchange_gain_loss"], 0)

	def test_mixed_eur_receivable_usd_payable_settled_in_usd_company_hkd(self):
		# SI EUR 1000 @ 8.5 book HKD, EUR→USD 1.10 → USD 1100
		# PI USD 800 @ 7.8 book HKD, USD→USD 1 → USD 800
		# Settlement USD→HKD 7.80; net USD 300 → HKD 2340
		si = _Row(
			party_type="Customer",
			allocated_amount=1000,
			exchange_rate=1.10,
			invoice_conversion_rate=8.5,
		)
		pi = _Row(
			party_type="Supplier",
			allocated_amount=800,
			exchange_rate=1.0,
			invoice_conversion_rate=7.8,
		)
		totals = _totals([si, pi], conversion_rate=7.80)

		self.assertEqual(si.allocated_amount_in_settlement_currency, 1100)
		self.assertEqual(pi.allocated_amount_in_settlement_currency, 800)
		self.assertEqual(totals["total_receivable"], 1100)
		self.assertEqual(totals["total_payable"], 800)
		self.assertEqual(totals["net_amount"], 300)
		self.assertEqual(totals["base_net_amount"], 2340)
		self.assertEqual(si.exchange_gain_loss, 80)
		self.assertEqual(pi.exchange_gain_loss, 0)
		self.assertEqual(totals["total_exchange_gain_loss"], 80)

	def test_cheaper_payable_is_a_gain(self):
		# PI EUR 100 originally booked at 8.5 (HKD 850), settled at EUR→USD 1.0 * USD→HKD 7.8 = 780
		row = _Row(
			party_type="Supplier",
			allocated_amount=100,
			exchange_rate=1.0,
			invoice_conversion_rate=8.5,
		)
		apply_row_conversion(row, conversion_rate=7.8)
		self.assertEqual(row.exchange_gain_loss, 70)

	def test_party_clears_at_original_book_and_net_at_settlement_rate(self):
		# Account in invoice currency: AR EUR, AP USD (settlement), company HKD
		ar_acc, ar_rate, ar_company = party_clearing_amounts(1000, "EUR", 8.5, "EUR", "HKD")
		self.assertEqual(ar_acc, 1000)
		self.assertEqual(ar_rate, 8.5)
		self.assertEqual(ar_company, 8500)

		ap_acc, ap_rate, ap_company = party_clearing_amounts(800, "USD", 7.8, "USD", "HKD")
		self.assertEqual(ap_acc, 800)
		self.assertEqual(ap_rate, 7.8)
		self.assertEqual(ap_company, 6240)

		# Party accounts in company currency
		ar_ccy_acc, ar_ccy_rate, ar_ccy_company = party_clearing_amounts(1000, "EUR", 8.5, "HKD", "HKD")
		self.assertEqual(ar_ccy_acc, 8500)
		self.assertEqual(ar_ccy_rate, 1.0)
		self.assertEqual(ar_ccy_company, 8500)

		net_acc, net_rate, net_company = net_settlement_amounts(300, "USD", 7.8, "USD", "HKD")
		self.assertEqual(net_acc, 300)
		self.assertEqual(net_rate, 7.8)
		self.assertEqual(net_company, 2340)

		net_hkd_acc, net_hkd_rate, net_hkd_company = net_settlement_amounts(300, "USD", 7.8, "HKD", "HKD")
		self.assertEqual(net_hkd_acc, 2340)
		self.assertEqual(net_hkd_rate, 1.0)
		self.assertEqual(net_hkd_company, 2340)

		# JE: CR AR 8500, DR AP 6240, DR net 2340 → plug CR 80
		fx_debit, fx_credit = fx_plug(6240 + 2340, 8500)
		self.assertEqual(fx_debit, 0)
		self.assertEqual(fx_credit, 80)
		self.assertEqual(6240 + 2340 + fx_debit, 8500 + fx_credit)

	def test_fx_plug_balances_loss_as_debit(self):
		fx_debit, fx_credit = fx_plug(8500, 6240 + 2730)
		self.assertEqual(fx_debit, 470)
		self.assertEqual(fx_credit, 0)
		self.assertEqual(8500 + fx_debit, 6240 + 2730 + fx_credit)

	def test_settlement_amount_helpers(self):
		self.assertEqual(settlement_amount(1000, 1.1), 1100)
		self.assertEqual(original_book_amount(1000, 8.5), 8500)
		self.assertEqual(settlement_in_base(1100, 7.8), 8580)
		self.assertEqual(row_exchange_gain_loss(1000, 8.5, 1100, 7.8, "Customer"), 80)
		self.assertEqual(row_exchange_gain_loss(800, 7.8, 800, 7.8, "Supplier"), 0)
