# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Tests for charge_type Revenue/Cost side cleanup."""

from __future__ import annotations

import unittest

import frappe

from logistics.utils.charges_calculation import (
	apply_charge_type_side_cleanup,
	compute_charge_row_estimates,
)


class TestChargeTypeSideClear(unittest.TestCase):
	def test_revenue_clears_cost_inputs_and_estimated_cost(self):
		doc = frappe.new_doc("Sales Quote Charge")
		doc.charge_type = "Revenue"
		doc.unit_cost = 100
		doc.cost_quantity = 2
		doc.cost_calculation_method = "Per Unit"
		doc.estimated_cost = 200
		doc.cost_calc_notes = "old notes"

		self.assertTrue(apply_charge_type_side_cleanup(doc))
		self.assertEqual(frappe.utils.flt(doc.unit_cost), 0)
		self.assertEqual(frappe.utils.flt(doc.cost_quantity), 0)
		self.assertFalse(doc.cost_calculation_method)
		self.assertEqual(frappe.utils.flt(doc.estimated_cost), 0)
		self.assertEqual(doc.cost_calc_notes, "")

	def test_cost_clears_revenue_inputs_and_estimated_revenue(self):
		doc = frappe.new_doc("Sales Quote Charge")
		doc.charge_type = "Cost"
		doc.unit_rate = 50
		doc.quantity = 3
		doc.revenue_calculation_method = "Per Unit"
		doc.estimated_revenue = 150
		doc.revenue_calc_notes = "old notes"

		self.assertTrue(apply_charge_type_side_cleanup(doc))
		self.assertEqual(frappe.utils.flt(doc.unit_rate), 0)
		self.assertEqual(frappe.utils.flt(doc.quantity), 0)
		self.assertFalse(doc.revenue_calculation_method)
		self.assertEqual(frappe.utils.flt(doc.estimated_revenue), 0)
		self.assertEqual(doc.revenue_calc_notes, "")

	def test_margin_does_not_clear(self):
		doc = frappe.new_doc("Sales Quote Charge")
		doc.charge_type = "Margin"
		doc.unit_cost = 100
		doc.unit_rate = 50

		self.assertFalse(apply_charge_type_side_cleanup(doc))
		self.assertEqual(frappe.utils.flt(doc.unit_cost), 100)
		self.assertEqual(frappe.utils.flt(doc.unit_rate), 50)

	def test_disbursement_does_not_clear_on_type_cleanup(self):
		doc = frappe.new_doc("Sales Quote Charge")
		doc.charge_type = "Disbursement"
		doc.unit_cost = 80
		doc.unit_rate = 99

		self.assertFalse(apply_charge_type_side_cleanup(doc))
		self.assertEqual(frappe.utils.flt(doc.unit_cost), 80)
		self.assertEqual(frappe.utils.flt(doc.unit_rate), 99)

	def test_compute_charge_row_estimates_zeros_cost_for_revenue_type(self):
		doc = frappe.new_doc("Sales Quote Charge")
		doc.charge_type = "Revenue"
		doc.unit_cost = 100
		doc.cost_quantity = 2
		doc.cost_calculation_method = "Per Unit"
		doc.estimated_cost = 200
		doc.revenue_calculation_method = "Flat Rate"
		doc.unit_rate = 10
		doc.quantity = 1

		compute_charge_row_estimates(doc)

		self.assertEqual(frappe.utils.flt(doc.unit_cost), 0)
		self.assertEqual(frappe.utils.flt(doc.estimated_cost), 0)
		self.assertGreaterEqual(frappe.utils.flt(doc.estimated_revenue), 0)

	def test_cost_break_rows_deleted_for_revenue_type(self):
		if not frappe.db.exists("DocType", "Sales Quote Qty Break"):
			self.skipTest("Sales Quote Qty Break not installed")

		ref_name = frappe.db.get_value("Sales Quote Charge", {}, "name")
		if not ref_name:
			self.skipTest("No Sales Quote Charge row in database")

		qb = frappe.new_doc("Sales Quote Qty Break")
		qb.reference_doctype = "Sales Quote Charge"
		qb.reference_no = ref_name
		qb.type = "Cost"
		qb.qty_break = 1
		qb.unit_rate = 5
		qb.insert(ignore_permissions=True)

		try:
			doc = frappe.get_doc("Sales Quote Charge", ref_name)
			doc.charge_type = "Revenue"
			apply_charge_type_side_cleanup(doc)

			remaining = frappe.db.count(
				"Sales Quote Qty Break",
				{
					"reference_doctype": "Sales Quote Charge",
					"reference_no": ref_name,
					"type": "Cost",
				},
			)
			self.assertEqual(remaining, 0)
		finally:
			frappe.db.delete(
				"Sales Quote Qty Break",
				{
					"reference_doctype": "Sales Quote Charge",
					"reference_no": ref_name,
					"type": "Cost",
					"qty_break": 1,
				},
			)


if __name__ == "__main__":
	unittest.main()
