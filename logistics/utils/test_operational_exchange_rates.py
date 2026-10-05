# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from logistics.utils.operational_exchange_rates import (
	apply_operational_exchange_rates_to_charge_rows,
	resolve_sales_quote_charge_exchange_rates,
	resolve_single_operational_exchange_rate_row,
	validate_sales_quote_charge_exchange_rates_for_submit,
)


class TestSalesQuoteChargeExchangeRates(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self._override_patch = patch(
			"logistics.utils.operational_exchange_rates.source_allows_rate_override",
			return_value=False,
		)
		self._override_patch.start()

	def tearDown(self):
		self._override_patch.stop()
		super().tearDown()

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


class TestExchangeRateSourceOverride(IntegrationTestCase):
	def _sales_quote(self, charge):
		return frappe._dict(
			doctype="Sales Quote",
			date="2026-06-30",
			company=None,
			charges=[charge],
		)

	def test_unticked_source_overwrites_charge_rate(self):
		charge = frappe._dict(
			currency="CNY",
			bill_to_exchange_rate_source="IATA",
			bill_to_exchange_rate=1.25,
			cost_currency="EUR",
			pay_to_exchange_rate_source="IATA",
			pay_to_exchange_rate=3.5,
		)
		with patch(
			"logistics.utils.operational_exchange_rates.source_allows_rate_override",
			return_value=False,
		), patch(
			"logistics.utils.operational_exchange_rates.get_exchange_rate_for_source_currency_date",
			return_value=9.02,
		):
			resolve_sales_quote_charge_exchange_rates(self._sales_quote(charge))

		self.assertEqual(charge.bill_to_exchange_rate, 9.02)
		self.assertEqual(charge.pay_to_exchange_rate, 9.02)

	def test_ticked_source_keeps_charge_rate(self):
		charge = frappe._dict(
			currency="CNY",
			bill_to_exchange_rate_source="MANUAL",
			bill_to_exchange_rate=1.25,
			cost_currency="EUR",
			pay_to_exchange_rate_source="MANUAL",
			pay_to_exchange_rate=3.5,
		)
		with patch(
			"logistics.utils.operational_exchange_rates.source_allows_rate_override",
			return_value=True,
		), patch(
			"logistics.utils.operational_exchange_rates.get_exchange_rate_for_source_currency_date",
			return_value=9.02,
		):
			resolve_sales_quote_charge_exchange_rates(self._sales_quote(charge))

		self.assertEqual(charge.bill_to_exchange_rate, 1.25)
		self.assertEqual(charge.pay_to_exchange_rate, 3.5)

	def test_unticked_operational_rate_is_replaced(self):
		row = frappe._dict(
			exchange_rate_source="IATA",
			currency="USD",
			exchange_rate_date="2026-06-30",
			rate=1.11,
		)
		with patch(
			"logistics.utils.operational_exchange_rates.source_allows_rate_override",
			return_value=False,
		), patch(
			"logistics.utils.operational_exchange_rates.get_exchange_rate_for_source_currency_date",
			return_value=9.02,
		):
			resolve_single_operational_exchange_rate_row(row)

		self.assertEqual(row.rate, 9.02)

	def test_ticked_operational_rate_is_kept(self):
		row = frappe._dict(
			exchange_rate_source="MANUAL",
			currency="USD",
			exchange_rate_date="2026-06-30",
			rate=1.11,
		)
		with patch(
			"logistics.utils.operational_exchange_rates.source_allows_rate_override",
			return_value=True,
		), patch(
			"logistics.utils.operational_exchange_rates.get_exchange_rate_for_source_currency_date",
			return_value=9.02,
		):
			resolve_single_operational_exchange_rate_row(row)

		self.assertEqual(row.rate, 1.11)

	def test_ticked_operational_rate_still_rejects_zero(self):
		row = frappe._dict(
			exchange_rate_source="MANUAL",
			currency="USD",
			exchange_rate_date="2026-06-30",
			rate=0,
		)
		with patch(
			"logistics.utils.operational_exchange_rates.source_allows_rate_override",
			return_value=True,
		):
			with self.assertRaises(frappe.ValidationError):
				resolve_single_operational_exchange_rate_row(row)

	def test_apply_keeps_charge_rate_when_source_is_ticked(self):
		ox = frappe._dict(
			entity_type="Customer",
			entity="CUST-001",
			currency="USD",
			exchange_rate_source="MANUAL",
			exchange_rate_date="2026-06-30",
			rate=9.02,
		)
		charge = frappe._dict(
			doctype="Air Booking Charges",
			bill_to="CUST-001",
			currency="USD",
			bill_to_exchange_rate_source="MANUAL",
			bill_to_exchange_rate=1.25,
		)
		parent = frappe._dict(
			meta=SimpleNamespace(get_field=lambda name: True),
			operational_exchange_rates=[ox],
			charges=[charge],
		)
		with patch(
			"logistics.utils.operational_exchange_rates.source_allows_rate_override",
			return_value=True,
		):
			apply_operational_exchange_rates_to_charge_rows(parent)

		self.assertEqual(charge.bill_to_exchange_rate, 1.25)
		self.assertEqual(ox.rate, 1.25)

	def test_apply_copies_operational_rate_when_source_is_unticked(self):
		ox = frappe._dict(
			entity_type="Customer",
			entity="CUST-001",
			currency="USD",
			exchange_rate_source="IATA",
			exchange_rate_date="2026-06-30",
			rate=9.02,
		)
		charge = frappe._dict(
			doctype="Air Booking Charges",
			bill_to="CUST-001",
			currency="USD",
			bill_to_exchange_rate_source="IATA",
			bill_to_exchange_rate=1.25,
		)
		parent = frappe._dict(
			meta=SimpleNamespace(get_field=lambda name: True),
			operational_exchange_rates=[ox],
			charges=[charge],
		)
		with patch(
			"logistics.utils.operational_exchange_rates.source_allows_rate_override",
			return_value=False,
		), patch(
			"logistics.utils.operational_exchange_rates.frappe.get_meta",
			return_value=SimpleNamespace(has_field=lambda name: False),
		):
			apply_operational_exchange_rates_to_charge_rows(parent)

		self.assertEqual(charge.bill_to_exchange_rate, 9.02)
		self.assertEqual(ox.rate, 9.02)
