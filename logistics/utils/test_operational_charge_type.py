# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from frappe.tests import UnitTestCase

from logistics.utils.charges_calculation import (
	normalize_operational_charge_rows_on_parent,
	normalize_operational_charge_type,
)


class TestOperationalChargeType(UnitTestCase):
	def test_other_maps_to_default(self):
		self.assertEqual(normalize_operational_charge_type("Other", default="Revenue"), "Revenue")
		self.assertEqual(normalize_operational_charge_type("Other"), "Margin")

	def test_allowed_values_unchanged(self):
		for ct in ("Margin", "Disbursement", "Revenue", "Cost"):
			self.assertEqual(normalize_operational_charge_type(ct), ct)

	def test_normalize_rows_on_parent(self):
		import frappe

		parent = frappe._dict(
			charges=[
				frappe._dict(charge_type="Other"),
				frappe._dict(charge_type="Margin"),
			]
		)
		changed = normalize_operational_charge_rows_on_parent(parent)
		self.assertEqual(changed, 1)
		self.assertEqual(parent.charges[0].charge_type, "Margin")
		self.assertEqual(parent.charges[1].charge_type, "Margin")
