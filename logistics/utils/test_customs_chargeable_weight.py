# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.utils.charges_calculation import (
	_get_parent_actual_data,
	_sum_customs_line_chargeable_weight,
	get_quantity_from_parent_by_unit_type,
	sum_customs_line_chargeable_weight,
)


class TestCustomsChargeableWeight(FrappeTestCase):
	def _parent_with_lines(self, doctype, lines):
		"""Plain object: frappe._dict exposes .items as dict.items() and breaks charge parent reads."""
		parent = type("CustomsParent", (), {})()
		parent.doctype = doctype
		parent.company = "Test Company"
		parent.commercial_invoice_line_items = [frappe._dict(row) for row in lines]
		return parent

	def test_sum_empty_lines_returns_zero(self):
		parent = self._parent_with_lines("Declaration", [])
		self.assertEqual(_sum_customs_line_chargeable_weight(parent), 0)

	def test_sum_chargeable_weights_without_uom(self):
		parent = self._parent_with_lines(
			"Declaration",
			[
				{"chargeable_weight": 100},
				{"chargeable_weight": 50},
			],
		)
		self.assertEqual(_sum_customs_line_chargeable_weight(parent), 150)

	def test_sum_falls_back_to_gross_weight_per_line(self):
		parent = self._parent_with_lines(
			"Declaration Order",
			[
				{"chargeable_weight": 0, "gross_weight": 80},
				{"chargeable_weight": 20},
			],
		)
		self.assertEqual(_sum_customs_line_chargeable_weight(parent), 100)

	@patch("logistics.utils.measurements.convert_weight")
	@patch("logistics.utils.measurements.get_default_uoms")
	def test_sum_converts_line_uoms(self, mock_defaults, mock_convert):
		mock_defaults.return_value = {"chargeable_weight": "Kg", "weight": "Kg"}
		mock_convert.side_effect = lambda value, from_uom=None, to_uom=None, company=None: (
			value * 2 if from_uom == "Lb" else value
		)
		parent = self._parent_with_lines(
			"Declaration",
			[
				{"chargeable_weight": 10, "chargeable_weight_uom": "Kg"},
				{"chargeable_weight": 5, "chargeable_weight_uom": "Lb"},
			],
		)
		self.assertEqual(_sum_customs_line_chargeable_weight(parent), 20)
		self.assertEqual(mock_convert.call_count, 2)

	def test_get_parent_actual_data_declaration_uses_line_sum(self):
		parent = self._parent_with_lines(
			"Declaration",
			[
				{"chargeable_weight": 30},
				{"gross_weight": 20},
			],
		)
		data = _get_parent_actual_data(None, parent)
		self.assertEqual(data["actual_chargeable_weight"], 50)
		self.assertEqual(data["actual_weight"], 50)

	def test_get_quantity_from_parent_chargeable_weight(self):
		parent = self._parent_with_lines(
			"Declaration Order",
			[{"chargeable_weight": 42}],
		)
		qty = get_quantity_from_parent_by_unit_type(parent, "Chargeable Weight")
		self.assertEqual(qty, 42)

	def test_whitelisted_sum_api(self):
		result = sum_customs_line_chargeable_weight(
			commercial_invoice_line_items=[
				{"chargeable_weight": 7},
				{"gross_weight": 3},
			],
			company=None,
		)
		self.assertEqual(float(result), 10)
