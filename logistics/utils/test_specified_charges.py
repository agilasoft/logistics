# Copyright (c) 2026, Agilasoft and contributors

from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests import UnitTestCase
from frappe.utils import flt

from logistics.utils.charges_calculation import (
	_has_billable_rate_input,
	_parent_charge_table_rows,
	_sum_specified_charges_total,
	calculate_charge_revenue,
)


class TestSpecifiedCharges(UnitTestCase):
	def _charge_row(self, **overrides):
		base = dict(
			name="sqc-base",
			doctype="Sales Quote Charge",
			parenttype="Sales Quote",
			parent="SQ-TEST",
			item_code="ITEM-A",
			revenue_calculation_method="Flat Rate",
			unit_rate=1000,
			currency="USD",
			use_tariff_in_revenue=0,
		)
		base.update(overrides)
		return SimpleNamespace(**base)

	def test_has_billable_rate_input_requires_rate_and_items(self):
		charge = self._charge_row(
			name="sqc-sc",
			revenue_calculation_method="Specified Charges",
			unit_rate=0.1,
			selling_specified_item_codes='["ITEM-A"]',
		)
		self.assertTrue(_has_billable_rate_input(charge, is_revenue=True))
		charge_no_items = self._charge_row(
			name="sqc-sc2",
			revenue_calculation_method="Specified Charges",
			unit_rate=0.1,
			selling_specified_item_codes="[]",
		)
		with patch(
			"logistics.utils.charges_calculation._charge_reference_is_persistable",
			return_value=False,
		):
			self.assertFalse(_has_billable_rate_input(charge_no_items, is_revenue=True))

	def test_parent_charge_table_rows_uses_consolidation_charges_field(self):
		child = SimpleNamespace(doctype="Sea Consolidation Charges", name="scc-1")
		row = SimpleNamespace(name="scc-row", item_code="ITEM-A")
		parent = SimpleNamespace(
			doctype="Sea Consolidation",
			consolidation_charges=[row],
		)
		with patch("logistics.utils.charges_calculation.frappe.get_meta") as mock_meta:
			mock_meta.return_value.get_table_fields.return_value = []
			rows = _parent_charge_table_rows(parent, child)
		self.assertEqual(len(rows), 1)
		self.assertEqual(getattr(rows[0], "item_code"), "ITEM-A")

	def test_sum_specified_charges_total(self):
		parent = SimpleNamespace(
			doctype="Sales Quote",
			charges=[
				self._charge_row(name="sqc-a", item_code="ITEM-A", unit_rate=1000),
				self._charge_row(name="sqc-b", item_code="ITEM-B", unit_rate=500),
			],
		)
		target = self._charge_row(
			name="sqc-fee",
			item_code="FEE",
			revenue_calculation_method="Specified Charges",
			unit_rate=0.1,
		)
		target.selling_specified_item_codes = '["ITEM-A","ITEM-B"]'
		with patch(
			"logistics.utils.charges_calculation._fetch_rates_from_tariff_if_needed",
			return_value=None,
		):
			total, err = _sum_specified_charges_total(
				target, parent, is_revenue=True, record_type="Selling", visiting=set()
			)
		self.assertIsNone(err)
		self.assertEqual(flt(total), 1500)

	def test_calculate_charge_revenue_specified_charges(self):
		parent = SimpleNamespace(
			doctype="Sales Quote",
			weight=0,
			volume=0,
			chargeable=0,
			total_pieces=0,
			charges=[
				self._charge_row(name="sqc-a", item_code="ITEM-A", unit_rate=1000),
				self._charge_row(name="sqc-b", item_code="ITEM-B", unit_rate=500),
			],
		)
		target = self._charge_row(
			name="sqc-fee",
			item_code="FEE",
			revenue_calculation_method="Specified Charges",
			unit_rate=0.1,
		)
		target.selling_specified_item_codes = '["ITEM-A","ITEM-B"]'
		with patch(
			"logistics.utils.charges_calculation._fetch_rates_from_tariff_if_needed",
			return_value=None,
		):
			res = calculate_charge_revenue(target, parent)
		self.assertTrue(res.get("success"))
		self.assertEqual(flt(res.get("amount")), 150)

	def test_circular_dependency_detected(self):
		parent = SimpleNamespace(
			doctype="Sales Quote",
			weight=0,
			volume=0,
			chargeable=0,
			total_pieces=0,
			charges=[
				self._charge_row(
					name="sqc-a",
					item_code="ITEM-A",
					revenue_calculation_method="Specified Charges",
					unit_rate=0.1,
				),
				self._charge_row(
					name="sqc-b",
					item_code="ITEM-B",
					revenue_calculation_method="Specified Charges",
					unit_rate=0.1,
				),
			],
		)
		target = parent.charges[0]

		def fake_items(charge_doc, record_type):
			name = getattr(charge_doc, "name", None)
			if name == "sqc-a":
				return ["ITEM-B"]
			if name == "sqc-b":
				return ["ITEM-A"]
			return []

		with patch(
			"logistics.utils.charges_calculation._resolve_specified_charge_items",
			side_effect=fake_items,
		), patch(
			"logistics.utils.charges_calculation._fetch_rates_from_tariff_if_needed",
			return_value=None,
		):
			total, err = _sum_specified_charges_total(
				target,
				parent,
				is_revenue=True,
				record_type="Selling",
				visiting={"sqc-a"},
			)
		self.assertEqual(flt(total), 0)
		self.assertIn("Circular", err or "")
