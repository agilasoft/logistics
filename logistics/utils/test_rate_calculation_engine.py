# Copyright (c) 2026, Agilasoft and contributors
# See license.txt

from frappe.tests.utils import FrappeTestCase

from logistics.utils.rate_calculation_engine import RateCalculationEngine


class TestRateCalculationEngine(FrappeTestCase):
	def test_fixed_amount_ignores_quantity(self):
		engine = RateCalculationEngine()
		rate_data = {
			"calculation_method": "Fixed Amount",
			"unit_rate": 100,
			"currency": "USD",
		}
		result = engine.calculate_rate(rate_data=rate_data, actual_quantity=5)
		self.assertTrue(result["success"])
		self.assertEqual(result["amount"], 100)
		self.assertEqual(result["quantity_used"], 0)
		self.assertEqual(result["calculation_details"], "Fixed Amount: 100.0 USD")

	def test_flat_rate_ignores_quantity(self):
		engine = RateCalculationEngine()
		rate_data = {
			"calculation_method": "Flat Rate",
			"unit_rate": 250,
			"currency": "USD",
		}
		result = engine.calculate_rate(rate_data=rate_data, actual_quantity=5)
		self.assertTrue(result["success"])
		self.assertEqual(result["amount"], 250)
		self.assertEqual(result["quantity_used"], 0)
		self.assertEqual(result["calculation_details"], "Flat Rate: 250.0 USD")

	def test_per_unit_multiplies_quantity(self):
		engine = RateCalculationEngine()
		rate_data = {
			"calculation_method": "Per Unit",
			"unit_rate": 10,
			"unit_type": "Weight",
			"currency": "USD",
		}
		result = engine.calculate_rate(rate_data=rate_data, actual_weight=5)
		self.assertTrue(result["success"])
		self.assertEqual(result["amount"], 50)
		self.assertIn("5 kg × 10 USD/kg = 50 USD", result["calculation_details"])

	def test_job_unit_type_always_quantity_one(self):
		engine = RateCalculationEngine()
		rate_data = {
			"calculation_method": "Per Unit",
			"unit_rate": 900,
			"unit_type": "Job",
			"currency": "PHP",
		}
		# actual_quantity would historically be weight fallback (e.g. 100 kg)
		result = engine.calculate_rate(
			rate_data=rate_data,
			actual_quantity=100,
			actual_weight=100,
		)
		self.assertTrue(result["success"])
		self.assertEqual(result["amount"], 900)
		self.assertEqual(result["quantity_used"], 1)

	def test_flat_rate_with_minimum_charge_and_no_rate_stays_zero(self):
		engine = RateCalculationEngine()
		rate_data = {
			"calculation_method": "Flat Rate",
			"unit_rate": 0,
			"minimum_charge": 5000,
			"currency": "PHP",
		}
		result = engine.calculate_rate(rate_data=rate_data)
		self.assertTrue(result["success"])
		self.assertEqual(result["amount"], 0)

	def test_flat_rate_applies_minimum_when_rate_below_floor(self):
		engine = RateCalculationEngine()
		rate_data = {
			"calculation_method": "Flat Rate",
			"unit_rate": 100,
			"minimum_charge": 5000,
			"currency": "PHP",
		}
		result = engine.calculate_rate(rate_data=rate_data)
		self.assertTrue(result["success"])
		self.assertEqual(result["amount"], 5000)

	def test_per_unit_zero_quantity_does_not_apply_minimum(self):
		engine = RateCalculationEngine()
		rate_data = {
			"calculation_method": "Per Unit",
			"unit_rate": 10,
			"unit_type": "Weight",
			"minimum_charge": 5000,
			"currency": "PHP",
		}
		result = engine.calculate_rate(rate_data=rate_data, actual_weight=0)
		self.assertTrue(result["success"])
		self.assertEqual(result["amount"], 0)