# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import unittest

from frappe.utils import flt

from logistics.job_management.api import (
	STOCK_RECEIVED_BUT_NOT_BILLED_ACCOUNT_TYPE,
	_cost_account_sql_predicate,
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
