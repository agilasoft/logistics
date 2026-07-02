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
