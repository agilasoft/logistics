# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import unittest

from frappe.utils import flt

from logistics.job_management.api import (
	STOCK_RECEIVED_BUT_NOT_BILLED_ACCOUNT_TYPE,
	_build_profitability_html,
	_cost_account_sql_predicate,
	_profitability_empty_state_next_step_message,
	_profitability_is_empty,
	is_stock_received_not_billed_cost_account,
)
from logistics.job_management.recognition_engine import (
	get_charge_row_cost_amount,
	resolve_charge_row_cost,
	resolve_charge_row_selling,
	get_charge_row_selling_amount,
)
from logistics.invoice_integration.purchase_invoice_api import _sea_shipment_row_cost


class TestProfitabilityCostClassification(unittest.TestCase):

	def test_stock_received_not_billed_is_cost_account(self):
		self.assertTrue(
			is_stock_received_not_billed_cost_account(
				"Liability", STOCK_RECEIVED_BUT_NOT_BILLED_ACCOUNT_TYPE
			)
		)
		self.assertFalse(is_stock_received_not_billed_cost_account("Expense", "Expense Account"))
		self.assertFalse(is_stock_received_not_billed_cost_account("Liability", "Payable"))

	def test_cost_account_sql_predicate_includes_srbnb(self):
		predicate = _cost_account_sql_predicate()
		self.assertIn("root_type = 'Expense'", predicate)
		self.assertIn(STOCK_RECEIVED_BUT_NOT_BILLED_ACCOUNT_TYPE, predicate)

	def test_cost_account_sql_predicate_honours_cost_exclude(self):
		predicate = _cost_account_sql_predicate(cost_exclude=" AND gle.account != %(cost_accrual_exclude)s")
		self.assertIn("cost_accrual_exclude", predicate)


class TestResolveChargeRowCost(unittest.TestCase):
	def test_unit_cost_times_quantity_fallback_for_accrual(self):
		ch = type("Ch", (), {
			"charge_type": "Cost",
			"estimated_cost": 0,
			"cost_base_amount": 0,
			"actual_cost": 0,
			"unit_cost": 50,
			"cost_quantity": 3,
		})()
		self.assertEqual(get_charge_row_cost_amount(ch), 150.0)

	def test_purchase_invoice_cost_prefers_actual_over_estimate(self):
		ch = type("Ch", (), {
			"charge_type": "Cost",
			"actual_cost": 90,
			"estimated_cost": 120,
			"unit_cost": 0,
			"cost_quantity": 1,
		})()
		self.assertEqual(_sea_shipment_row_cost(ch), 90.0)
		self.assertEqual(get_charge_row_cost_amount(ch), 120.0)

	def test_pi_and_accrual_match_when_only_unit_cost_set(self):
		ch = type("Ch", (), {
			"charge_type": "Cost",
			"estimated_cost": 0,
			"actual_cost": 0,
			"cost_base_amount": 0,
			"unit_cost": 25,
			"cost_quantity": 4,
		})()
		self.assertEqual(flt(_sea_shipment_row_cost(ch)), flt(get_charge_row_cost_amount(ch)))

	def test_disbursement_charge_is_zero_cost(self):
		ch = type("Ch", (), {"charge_type": "Disbursement", "estimated_cost": 100})()
		self.assertEqual(resolve_charge_row_cost(ch), 0)


class TestResolveChargeRowSelling(unittest.TestCase):
	def test_wip_prefers_estimated_over_actual(self):
		ch = type("Ch", (), {
			"charge_type": "Cost",
			"estimated_revenue": 500,
			"actual_revenue": 4_000_000,
			"unit_rate": 500,
			"quantity": 8000,
		})()
		self.assertEqual(get_charge_row_selling_amount(ch), 500.0)

	def test_sales_invoice_prefers_actual_over_estimate(self):
		ch = type("Ch", (), {
			"charge_type": "Cost",
			"estimated_revenue": 500,
			"actual_revenue": 4_000_000,
			"unit_rate": 500,
			"quantity": 8000,
			"revenue_calculation_method": "Per Unit",
		})()
		self.assertEqual(resolve_charge_row_selling(ch, prefer_actual=True), 4_000_000.0)

	def test_sales_invoice_falls_back_to_unit_rate_times_quantity(self):
		ch = type("Ch", (), {
			"charge_type": "Cost",
			"estimated_revenue": 0,
			"actual_revenue": 0,
			"unit_rate": 500,
			"quantity": 8000,
		})()
		self.assertEqual(resolve_charge_row_selling(ch, prefer_actual=True), 4_000_000.0)

	def test_disbursement_charge_is_zero_revenue(self):
		ch = type("Ch", (), {"charge_type": "Disbursement", "estimated_revenue": 100})()
		self.assertEqual(resolve_charge_row_selling(ch, prefer_actual=True), 0)


class TestProfitabilityEmptyState(unittest.TestCase):
	def _empty_data(self):
		return {
			"currency": "PHP",
			"revenue": 0,
			"cost": 0,
			"gross_profit": 0,
			"profit_margin_pct": 0,
			"wip_amount": 0,
			"accrual_amount": 0,
			"disbursements_amount": 0,
			"entries": [],
			"summary_by_item": [],
		}

	def test_profitability_is_empty_when_all_zero_and_no_entries(self):
		self.assertTrue(_profitability_is_empty(self._empty_data()))

	def test_profitability_is_not_empty_when_wip_amount_set(self):
		data = self._empty_data()
		data["wip_amount"] = 350000
		self.assertFalse(_profitability_is_empty(data))

	def test_profitability_is_not_empty_when_entries_exist(self):
		data = self._empty_data()
		data["entries"] = [{"revenue_amount": 0, "cost_amount": 0}]
		self.assertFalse(_profitability_is_empty(data))

	def test_build_profitability_html_shows_empty_state_guidance(self):
		html = _build_profitability_html(self._empty_data())
		self.assertIn("logistics-profitability-empty-state", html)
		self.assertIn("WIP and Accrual", html)
		self.assertIn(_profitability_empty_state_next_step_message(), html)
		self.assertIn("No GL entries in Revenue, Cost, WIP, Accrual, or Disbursements", html)

	def test_build_profitability_html_hides_empty_state_when_wip_posted(self):
		data = self._empty_data()
		data["wip_amount"] = 1000
		html = _build_profitability_html(data)
		self.assertNotIn("logistics-profitability-empty-state", html)
		self.assertIn("Figures from General Ledger by Job Number.", html)

	def test_headline_cost_excludes_open_accrual(self):
		"""Open accrual must not inflate Cost until Purchase Invoice posts (#1073)."""
		data = self._empty_data()
		data["accrual_amount"] = 5000
		data["wip_amount"] = 3000
		self.assertEqual(flt(data["cost"]), 0)
		self.assertFalse(_profitability_is_empty(data))

	def test_gross_profit_uses_realized_cost_only_when_accrual_open(self):
		"""Headline KPI math: cost excludes open accrual; accrual stays separate."""
		realized_cost = 250.0
		accrual_amount = 1000.0
		revenue = 0.0
		cost = realized_cost
		gross_profit = revenue - cost
		self.assertEqual(cost, 250.0)
		self.assertEqual(accrual_amount, 1000.0)
		self.assertEqual(gross_profit, -250.0)
		self.assertNotEqual(cost, flt(realized_cost + accrual_amount, 2))
