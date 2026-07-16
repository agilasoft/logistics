# Copyright (c) 2026, AgilaSoft and Contributors

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt

from logistics.utils.charges_calculation import (
	_apply_unit_break_to_rate_data,
	_charge_side_uses_unit_breaks,
	_get_quantity_for_calculation_method,
	_resolve_unit_break_rate,
	_spread_row_qty_into_actual_data,
	calculate_charge_revenue,
)


class TestChargeUnitBreaks(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_value_unit_type_uses_goods_value(self):
		actual_data = {"actual_goods_value": 50000, "actual_quantity": 0}
		qty = _get_quantity_for_calculation_method(actual_data, "Per Unit", "Value")
		self.assertEqual(qty, 50000)

	def test_job_unit_type_always_one_not_weight_fallback(self):
		"""Job must not use actual_quantity (weight/volume fallback) or qty inflates."""
		actual_data = {
			"actual_quantity": 100.0,
			"actual_weight": 100.0,
			"actual_volume": 8.0,
			"actual_pieces": 1.0,
		}
		qty = _get_quantity_for_calculation_method(actual_data, "Per Unit", "Job")
		self.assertEqual(qty, 1.0)
		self.assertEqual(
			_get_quantity_for_calculation_method(actual_data, "Per Unit", "Shipment"),
			1.0,
		)

	def test_charge_side_uses_unit_breaks_flag(self):
		row = frappe._dict(use_unit_breaks=1, cost_use_unit_breaks=0)
		self.assertTrue(_charge_side_uses_unit_breaks(row, True))
		self.assertFalse(_charge_side_uses_unit_breaks(row, False))

	def test_resolve_unit_break_rate_picks_highest_matching_tier(self):
		if not frappe.db.exists("DocType", "Charge Unit Break"):
			self.skipTest("Charge Unit Break DocType not installed")

		ref_doctype = "Sales Quote Charge"
		ref_no = "TEST-UNIT-BREAK-001"
		for row in frappe.get_all(
			"Charge Unit Break",
			filters={"reference_doctype": ref_doctype, "reference_no": ref_no},
			pluck="name",
		):
			frappe.delete_doc("Charge Unit Break", row, force=1)

		for threshold, rate in ((100, 10), (500, 8), (1000, 5)):
			doc = frappe.new_doc("Charge Unit Break")
			doc.reference_doctype = ref_doctype
			doc.reference_no = ref_no
			doc.type = "Selling"
			doc.unit_type = "Weight"
			doc.unit_break = threshold
			doc.unit_rate = rate
			doc.currency = "USD"
			doc.insert(ignore_permissions=True)

		charge_doc = frappe._dict(doctype=ref_doctype, name=ref_no)
		applicable = _resolve_unit_break_rate(charge_doc, 750, "Selling", unit_type="Weight")
		self.assertIsNotNone(applicable)
		self.assertEqual(flt(applicable.get("unit_rate")), 8)

	def test_apply_unit_break_overrides_rate_data(self):
		if not frappe.db.exists("DocType", "Charge Unit Break"):
			self.skipTest("Charge Unit Break DocType not installed")

		ref_doctype = "Sales Quote Charge"
		ref_no = "TEST-UNIT-BREAK-002"
		for row in frappe.get_all(
			"Charge Unit Break",
			filters={"reference_doctype": ref_doctype, "reference_no": ref_no},
			pluck="name",
		):
			frappe.delete_doc("Charge Unit Break", row, force=1)

		doc = frappe.new_doc("Charge Unit Break")
		doc.reference_doctype = ref_doctype
		doc.reference_no = ref_no
		doc.type = "Selling"
		doc.unit_type = "TEU"
		doc.unit_break = 2
		doc.unit_rate = 150
		doc.currency = "USD"
		doc.insert(ignore_permissions=True)

		charge_doc = frappe._dict(
			doctype=ref_doctype,
			name=ref_no,
			use_unit_breaks=1,
			unit_type="TEU",
			currency="USD",
			uom="Nos",
		)
		rate_data = {"calculation_method": "Per Unit", "rate": 100, "unit_rate": 100, "currency": "USD"}
		actual_data = {"actual_teu": 4, "actual_quantity": 4}
		prefix = _apply_unit_break_to_rate_data(
			charge_doc, rate_data, actual_data, "TEU", "Selling", True
		)
		self.assertTrue(prefix)
		self.assertEqual(flt(rate_data.get("rate")), 150)

	def test_apply_unit_break_notes_rate_adjustment(self):
		if not frappe.db.exists("DocType", "Charge Unit Break"):
			self.skipTest("Charge Unit Break DocType not installed")

		ref_doctype = "Sales Quote Charge"
		ref_no = "TEST-UNIT-BREAK-NOTES"
		for row in frappe.get_all(
			"Charge Unit Break",
			filters={"reference_doctype": ref_doctype, "reference_no": ref_no},
			pluck="name",
		):
			frappe.delete_doc("Charge Unit Break", row, force=1)

		doc = frappe.new_doc("Charge Unit Break")
		doc.reference_doctype = ref_doctype
		doc.reference_no = ref_no
		doc.type = "Selling"
		doc.unit_type = "Weight"
		doc.unit_break = 500
		doc.unit_rate = 8
		doc.currency = "USD"
		doc.insert(ignore_permissions=True)

		charge_doc = frappe._dict(
			doctype=ref_doctype,
			name=ref_no,
			use_unit_breaks=1,
			unit_type="Weight",
			revenue_calculation_method="Per Unit",
			unit_rate=10,
			currency="USD",
			uom="Kg",
			quantity=750,
		)
		rate_data = {"calculation_method": "Per Unit", "rate": 10, "unit_rate": 10, "currency": "USD"}
		actual_data = {"actual_weight": 750, "actual_quantity": 750}
		prefix = _apply_unit_break_to_rate_data(
			charge_doc, rate_data, actual_data, "Weight", "Selling", True
		)
		self.assertIn("Unit Break", prefix)
		self.assertIn("adjusted from 10 to 8", prefix)
		self.assertEqual(flt(charge_doc.unit_rate), 8)

	def test_spread_row_qty_into_actual_data_for_teu(self):
		actual_data = {"actual_teu": 0, "actual_quantity": 0}
		_spread_row_qty_into_actual_data(actual_data, "TEU", 4)
		self.assertEqual(actual_data["actual_teu"], 4)

	def test_calculate_charge_revenue_includes_unit_break_in_calc_notes(self):
		if not frappe.db.exists("DocType", "Charge Unit Break"):
			self.skipTest("Charge Unit Break DocType not installed")

		ref_doctype = "Sales Quote Charge"
		ref_no = "TEST-UNIT-BREAK-CALC"
		for row in frappe.get_all(
			"Charge Unit Break",
			filters={"reference_doctype": ref_doctype, "reference_no": ref_no},
			pluck="name",
		):
			frappe.delete_doc("Charge Unit Break", row, force=1)

		for threshold, rate in ((100, 10), (500, 8)):
			doc = frappe.new_doc("Charge Unit Break")
			doc.reference_doctype = ref_doctype
			doc.reference_no = ref_no
			doc.type = "Selling"
			doc.unit_type = "Weight"
			doc.unit_break = threshold
			doc.unit_rate = rate
			doc.currency = "USD"
			doc.insert(ignore_permissions=True)

		charge_doc = frappe._dict(
			doctype=ref_doctype,
			name=ref_no,
			use_unit_breaks=1,
			unit_type="Weight",
			revenue_calculation_method="Per Unit",
			unit_rate=10,
			currency="USD",
			uom="Kg",
			quantity=750,
			parenttype="Sales Quote",
			parent="SQ-TEST",
		)
		result = calculate_charge_revenue(charge_doc, parent_doc=frappe._dict(doctype="Sales Quote"))
		self.assertTrue(result.get("success"))
		notes = result.get("calc_notes") or ""
		self.assertIn("Unit Break", notes)
		self.assertIn("750", notes)
		self.assertIn("8", notes)
