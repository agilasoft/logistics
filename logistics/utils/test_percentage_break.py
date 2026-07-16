# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Unit tests for Percentage Break tier resolution and amount formula."""

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import flt

from logistics.utils.charges_calculation import (
	_resolve_percentage_break_rate,
	calculate_charge_revenue,
)


class TestPercentageBreakCalculation(UnitTestCase):
	def test_resolve_highest_qualifying_break(self):
		charge = SimpleNamespace(name="PB-TEST-1", doctype="Sales Quote Charge")
		breaks = [
			{"value_break": 1000, "percentage_rate": 3, "currency": "USD"},
			{"value_break": 2000, "percentage_rate": 5, "currency": "USD"},
			{"value_break": 3000, "percentage_rate": 10, "currency": "USD"},
		]
		with patch("logistics.utils.charges_calculation.frappe.get_all", return_value=breaks):
			applicable = _resolve_percentage_break_rate(charge, 3000, "Selling")
		self.assertEqual(flt(applicable["percentage_rate"]), 10)
		self.assertEqual(flt(applicable["value_break"]), 3000)

	def test_resolve_mid_tier(self):
		charge = SimpleNamespace(name="PB-TEST-2", doctype="Sales Quote Charge")
		breaks = [
			{"value_break": 1000, "percentage_rate": 3, "currency": "USD"},
			{"value_break": 2000, "percentage_rate": 5, "currency": "USD"},
			{"value_break": 3000, "percentage_rate": 10, "currency": "USD"},
		]
		with patch("logistics.utils.charges_calculation.frappe.get_all", return_value=breaks):
			applicable = _resolve_percentage_break_rate(charge, 2500, "Selling")
		self.assertEqual(flt(applicable["percentage_rate"]), 5)

	def test_amount_goods_value_times_percent_plus_minimum(self):
		"""Value=200, 5%, minimum=100 → total 110."""
		charge = SimpleNamespace(
			name="PB-TEST-3",
			doctype="Sales Quote Charge",
			parenttype="Sales Quote",
			revenue_calculation_method="Percentage Break",
			unit_type="Value",
			quantity=2000,
			minimum_charge=100,
			maximum_charge=0,
			currency="USD",
			base_amount=0,
			uom=None,
			use_tariff_in_revenue=0,
			tariff=None,
		)
		parent = SimpleNamespace(doctype="Sales Quote", goods_value=200, declared_value=0)
		breaks = [
			{"value_break": 1000, "percentage_rate": 3, "currency": "USD"},
			{"value_break": 2000, "percentage_rate": 5, "currency": "USD"},
			{"value_break": 3000, "percentage_rate": 10, "currency": "USD"},
		]
		with patch("logistics.utils.charges_calculation.frappe.get_all", return_value=breaks):
			with patch(
				"logistics.utils.charges_calculation._fetch_rates_from_tariff_if_needed",
				return_value=None,
			):
				result = calculate_charge_revenue(charge, parent)
		self.assertTrue(result.get("success"), result.get("calc_notes"))
		self.assertEqual(flt(result.get("amount")), 110)
		self.assertIn("5.0%", result.get("calc_notes") or "")
		self.assertIn("minimum 100", result.get("calc_notes") or "")

	def test_amount_falls_back_to_quantity_not_base_amount(self):
		"""No parent goods value: use Quantity × % (+ min); ignore Base Amount."""
		charge = SimpleNamespace(
			name="PB-TEST-4",
			doctype="Sales Quote Charge",
			parenttype="Sales Quote",
			revenue_calculation_method="Percentage Break",
			unit_type="Value",
			quantity=2000,
			minimum_charge=100,
			maximum_charge=0,
			currency="USD",
			base_amount=99999,
			uom=None,
			use_tariff_in_revenue=0,
			tariff=None,
		)
		parent = SimpleNamespace(doctype="Sales Quote", goods_value=0, declared_value=0)
		breaks = [
			{"value_break": 1000, "percentage_rate": 3, "currency": "USD"},
			{"value_break": 2000, "percentage_rate": 5, "currency": "USD"},
			{"value_break": 3000, "percentage_rate": 10, "currency": "USD"},
		]
		with patch("logistics.utils.charges_calculation.frappe.get_all", return_value=breaks):
			with patch(
				"logistics.utils.charges_calculation._fetch_rates_from_tariff_if_needed",
				return_value=None,
			):
				result = calculate_charge_revenue(charge, parent)
		# 2000 × 5% + 100 = 200
		self.assertTrue(result.get("success"), result.get("calc_notes"))
		self.assertEqual(flt(result.get("amount")), 200)
		self.assertIn("5.0%", result.get("calc_notes") or "")
		self.assertIn("goods 2000", result.get("calc_notes") or "")
