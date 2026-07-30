# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from logistics.utils.operational_exchange_rates import (
	resolve_sales_quote_charge_exchange_rates,
	validate_sales_quote_charge_exchange_rates_for_submit,
)


class TestSalesQuoteChargeExchangeRates(IntegrationTestCase):
	def test_missing_source_currency_sets_exchange_rate_to_zero(self):
		charge = frappe._dict(
			currency="JPY",
			bill_to_exchange_rate_source="IATA",
			bill_to_exchange_rate=9.02,
			cost_currency="EUR",
			pay_to_exchange_rate_source="IATA",
			pay_to_exchange_rate=9.02,
		)
		doc = frappe._dict(
			doctype="Sales Quote",
			date="2026-06-30",
			company=None,
			charges=[charge],
		)

		with patch(
			"logistics.utils.operational_exchange_rates.get_exchange_rate_for_source_currency_date",
			return_value=None,
		):
			resolve_sales_quote_charge_exchange_rates(doc)

		self.assertEqual(charge.bill_to_exchange_rate, 0)
		self.assertEqual(charge.pay_to_exchange_rate, 0)

	def test_found_source_currency_sets_exchange_rate(self):
		charge = frappe._dict(
			currency="CNY",
			bill_to_exchange_rate_source="IATA",
			bill_to_exchange_rate=1,
			cost_currency="CNY",
			pay_to_exchange_rate_source="IATA",
			pay_to_exchange_rate=1,
		)
		doc = frappe._dict(
			doctype="Sales Quote",
			date="2026-06-30",
			company=None,
			charges=[charge],
		)

		with patch(
			"logistics.utils.operational_exchange_rates.get_exchange_rate_for_source_currency_date",
			return_value=9.02,
		):
			resolve_sales_quote_charge_exchange_rates(doc)

		self.assertEqual(charge.bill_to_exchange_rate, 9.02)
		self.assertEqual(charge.pay_to_exchange_rate, 9.02)

	def test_submit_validation_throws_when_resolved_rate_is_zero(self):
		charge = frappe._dict(
			item_code="FREIGHT",
			bill_to="CUST-001",
			currency="JPY",
			bill_to_exchange_rate_source="IATA",
			bill_to_exchange_rate=9.02,
			pay_to=None,
			cost_currency=None,
			pay_to_exchange_rate_source=None,
			pay_to_exchange_rate=None,
		)
		doc = frappe._dict(
			doctype="Sales Quote",
			date="2026-06-30",
			company=None,
			charges=[charge],
		)

		with patch(
			"logistics.utils.operational_exchange_rates.get_exchange_rate_for_source_currency_date",
			return_value=None,
		):
			with self.assertRaises(frappe.ValidationError) as ctx:
				validate_sales_quote_charge_exchange_rates_for_submit(doc)

		self.assertIn("Exchange Rate", str(ctx.exception))
		self.assertEqual(charge.bill_to_exchange_rate, 0)

	def test_submit_validation_passes_when_rate_resolves(self):
		charge = frappe._dict(
			item_code="FREIGHT",
			bill_to="CUST-001",
			currency="CNY",
			bill_to_exchange_rate_source="IATA",
			bill_to_exchange_rate=0,
			pay_to=None,
			cost_currency=None,
			pay_to_exchange_rate_source=None,
			pay_to_exchange_rate=None,
		)
		doc = frappe._dict(
			doctype="Sales Quote",
			date="2026-06-30",
			company=None,
			charges=[charge],
		)

		with patch(
			"logistics.utils.operational_exchange_rates.get_exchange_rate_for_source_currency_date",
			return_value=9.02,
		):
			validate_sales_quote_charge_exchange_rates_for_submit(doc)

		self.assertEqual(charge.bill_to_exchange_rate, 9.02)

	def test_submit_validation_allows_blank_rate_without_party(self):
		"""Blank rates are skipped by booking sync when there is no bill_to/pay_to."""
		charge = frappe._dict(
			item_code="FREIGHT",
			bill_to=None,
			currency="JPY",
			bill_to_exchange_rate_source=None,
			bill_to_exchange_rate=None,
			pay_to=None,
			cost_currency=None,
			pay_to_exchange_rate_source=None,
			pay_to_exchange_rate=None,
		)
		doc = frappe._dict(
			doctype="Sales Quote",
			date="2026-06-30",
			company=None,
			charges=[charge],
		)
		validate_sales_quote_charge_exchange_rates_for_submit(doc)
