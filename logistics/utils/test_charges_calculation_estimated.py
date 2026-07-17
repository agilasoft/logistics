# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for estimated revenue/cost staying empty until pricing input exists."""

from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests import UnitTestCase
from frappe.utils import flt

from logistics.utils.charges_calculation import (
	_estimated_display_amount,
	_has_billable_rate_input,
	calculate_charge_cost,
	calculate_charge_revenue,
)


class TestChargesCalculationEstimated(UnitTestCase):
	def _flat_rate_charge(self, **overrides):
		base = dict(
			name="sqc-test",
			doctype="Sales Quote Charge",
			parenttype="Sales Quote",
			parent="OOQ-TEST",
			revenue_calculation_method="Flat Rate",
			cost_calculation_method="Flat Rate",
			unit_rate=0,
			unit_cost=0,
			minimum_charge=5000,
			cost_minimum_charge=5000,
			currency="PHP",
			cost_currency="PHP",
			unit_type="Job",
			cost_unit_type="Job",
			use_tariff_in_revenue=0,
			use_tariff_in_cost=0,
		)
		base.update(overrides)
		return SimpleNamespace(**base)

	def test_has_billable_rate_input_false_for_flat_rate_without_rate(self):
		charge = self._flat_rate_charge()
		self.assertFalse(_has_billable_rate_input(charge, is_revenue=True))
		self.assertFalse(_has_billable_rate_input(charge, is_revenue=False))

	def test_estimated_display_amount_none_without_rate(self):
		charge = self._flat_rate_charge()
		self.assertIsNone(_estimated_display_amount(charge, 5000, is_revenue=True))
		self.assertIsNone(_estimated_display_amount(charge, 5000, is_revenue=False))

	def test_flat_rate_with_minimum_and_no_rate_returns_empty_estimate(self):
		charge = self._flat_rate_charge()
		parent = SimpleNamespace(doctype="Sales Quote", weight=0, volume=0, chargeable=0, total_pieces=0)
		with patch(
			"logistics.utils.charges_calculation._fetch_rates_from_tariff_if_needed",
			return_value=None,
		):
			rev = calculate_charge_revenue(charge, parent)
			cost = calculate_charge_cost(charge, parent)
		self.assertEqual(flt(rev.get("amount")), 0)
		self.assertEqual(flt(cost.get("amount")), 0)
		self.assertIsNone(_estimated_display_amount(charge, rev.get("amount"), is_revenue=True))
		self.assertIsNone(_estimated_display_amount(charge, cost.get("amount"), is_revenue=False))

	def test_flat_rate_with_rate_applies_minimum_floor(self):
		charge = self._flat_rate_charge(unit_rate=100, unit_cost=50)
		parent = SimpleNamespace(doctype="Sales Quote", weight=0, volume=0, chargeable=0, total_pieces=0)
		with patch(
			"logistics.utils.charges_calculation._fetch_rates_from_tariff_if_needed",
			return_value=None,
		):
			rev = calculate_charge_revenue(charge, parent)
			cost = calculate_charge_cost(charge, parent)
		self.assertEqual(flt(rev.get("amount")), 5000)
		self.assertEqual(flt(cost.get("amount")), 5000)
		self.assertEqual(_estimated_display_amount(charge, rev.get("amount"), is_revenue=True), 5000)
		self.assertEqual(_estimated_display_amount(charge, cost.get("amount"), is_revenue=False), 5000)

	def test_per_unit_with_rate_shows_calculated_amount(self):
		charge = self._flat_rate_charge(
			revenue_calculation_method="Per Unit",
			cost_calculation_method="Per Unit",
			unit_rate=78000,
			unit_cost=12000,
			unit_type="Job",
			cost_unit_type="Job",
			minimum_charge=0,
			cost_minimum_charge=0,
		)
		parent = SimpleNamespace(doctype="Sales Quote", weight=0, volume=0, chargeable=0, total_pieces=0)
		with patch(
			"logistics.utils.charges_calculation._fetch_rates_from_tariff_if_needed",
			return_value=None,
		):
			rev = calculate_charge_revenue(charge, parent)
			cost = calculate_charge_cost(charge, parent)
		self.assertEqual(flt(rev.get("amount")), 78000)
		self.assertEqual(flt(cost.get("amount")), 12000)

	def test_calculate_charge_row_returns_null_estimates_without_rate(self):
		from logistics.utils.charges_calculation import calculate_charge_row

		row = {
			"name": "sqc-test",
			"doctype": "Sales Quote Charge",
			"parenttype": "Sales Quote",
			"parent": "OOQ-TEST",
			"revenue_calculation_method": "Flat Rate",
			"cost_calculation_method": "Flat Rate",
			"unit_rate": 0,
			"unit_cost": 0,
			"minimum_charge": 5000,
			"cost_minimum_charge": 5000,
			"currency": "PHP",
			"cost_currency": "PHP",
			"unit_type": "Job",
			"cost_unit_type": "Job",
		}

		class MockDoc:
			def __init__(self, data):
				self.__dict__.update(data)

			def update(self, data):
				self.__dict__.update(data)

		with patch(
			"logistics.utils.charges_calculation.frappe.new_doc",
			return_value=MockDoc(row),
		), patch(
			"logistics.utils.charges_calculation.apply_charge_type_side_cleanup",
			return_value=False,
		), patch(
			"logistics.utils.charges_calculation.calculate_charge_revenue",
			return_value={"amount": 0, "calc_notes": ""},
		), patch(
			"logistics.utils.charges_calculation.calculate_charge_cost",
			return_value={"amount": 0, "calc_notes": ""},
		), patch(
			"logistics.utils.charges_calculation._charge_row_sync_dict_for_client",
			return_value={},
		):
			result = calculate_charge_row(
				"Sales Quote Charge",
				"Sales Quote",
				"OOQ-TEST",
				row,
			)

		self.assertTrue(result.get("success"))
		self.assertIsNone(result.get("estimated_revenue"))
		self.assertIsNone(result.get("estimated_cost"))
