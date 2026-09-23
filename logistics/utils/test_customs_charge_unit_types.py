# Copyright (c) 2026, AgilaSoft and Contributors
# See license.txt

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import flt

from logistics.utils.charges_calculation import (
	_apply_charge_parent_overrides,
	_get_parent_actual_data,
	_get_quantity_for_calculation_method,
	calculate_charge_revenue,
	get_quantity_from_parent_by_unit_type,
)
from logistics.utils.commercial_invoice_totals import (
	seed_number_of_line_items_from_item_count_charges,
	sync_number_of_line_items,
)
from logistics.utils.rate_calculation_engine import RateCalculationEngine


def _customs_parent(doctype="Declaration", **kwargs):
	"""Plain object: frappe._dict exposes .items as dict.items() and breaks charge parent reads."""
	parent = type("CustomsParent", (), {})()
	parent.doctype = doctype
	parent.company = "Test Company"
	parent.packages = kwargs.pop("packages", 99)
	parent.commercial_invoice_line_items = [
		frappe._dict(row) for row in kwargs.pop("commercial_invoice_line_items", [])
	]
	parent.number_of_line_items = kwargs.pop("number_of_line_items", 0)
	parent.number_of_line_items_manual = kwargs.pop("number_of_line_items_manual", 0)
	parent.cif = kwargs.pop("cif", 0)
	parent.fob = kwargs.pop("fob", 0)
	parent.inv_total_amount = kwargs.pop("inv_total_amount", 0)
	parent.total_weight = kwargs.pop("total_weight", 500)
	for key, val in kwargs.items():
		setattr(parent, key, val)
	return parent


def _charge(**kwargs):
	defaults = dict(
		name="CHG-TEST",
		doctype="Declaration Charges",
		parenttype="Declaration",
		parent="DECL-TEST",
		revenue_calculation_method="Per Unit",
		unit_type="Job",
		unit_rate=2500,
		quantity=1,
		minimum_charge=0,
		maximum_charge=0,
		currency="USD",
		base_amount=0,
		uom=None,
		use_tariff_in_revenue=0,
		tariff=None,
		revenue_tariff=None,
		item_code=None,
	)
	defaults.update(kwargs)
	return SimpleNamespace(**defaults)


class TestCustomsChargeUnitTypes(UnitTestCase):
	def test_header_item_count_not_packages(self):
		parent = _customs_parent(
			number_of_line_items=15,
			packages=99,
			commercial_invoice_line_items=[{"price": 1}] * 2,
		)
		data = _get_parent_actual_data(None, parent)
		self.assertEqual(data["actual_item_count"], 15)
		self.assertEqual(get_quantity_from_parent_by_unit_type(parent, "Item Count"), 15)

	def test_one_row_manual_header_100(self):
		parent = _customs_parent(
			number_of_line_items=100,
			number_of_line_items_manual=1,
			packages=40,
			commercial_invoice_line_items=[{"price": 10}],
		)
		self.assertEqual(get_quantity_from_parent_by_unit_type(parent, "Item Count"), 100)

	def test_empty_header_uses_row_count(self):
		parent = _customs_parent(
			number_of_line_items=0,
			commercial_invoice_line_items=[{"price": 1}, {"price": 2}],
		)
		self.assertEqual(get_quantity_from_parent_by_unit_type(parent, "Item Count"), 2)

	def test_value_uses_cif_not_goods_value_field(self):
		parent = _customs_parent(cif=120000, fob=100000, inv_total_amount=90000)
		data = _get_parent_actual_data(None, parent)
		self.assertEqual(data["actual_goods_value"], 120000)
		self.assertEqual(
			_get_quantity_for_calculation_method(data, "Per Unit", "Value"),
			120000,
		)

	def test_job_qty_stays_one_with_weight_and_lines(self):
		parent = _customs_parent(
			total_weight=500,
			number_of_line_items=15,
			commercial_invoice_line_items=[{"price": 1}] * 15,
		)
		self.assertEqual(get_quantity_from_parent_by_unit_type(parent, "Job"), 1)

	def test_desk_overrides_win_over_saved_parent(self):
		parent = _customs_parent(cif=1000, number_of_line_items=2)
		_apply_charge_parent_overrides(
			parent,
			{"cif": 50000, "number_of_line_items": 7},
		)
		data = _get_parent_actual_data(None, parent)
		self.assertEqual(data["actual_goods_value"], 50000)
		self.assertEqual(data["actual_item_count"], 7)

	def test_sync_empty_header_auto_fills_row_count(self):
		parent = _customs_parent(
			number_of_line_items=0,
			commercial_invoice_line_items=[{}, {}],
		)
		sync_number_of_line_items(parent)
		self.assertEqual(parent.number_of_line_items, 2)
		self.assertFalse(parent.number_of_line_items_manual)

	def test_sync_does_not_reset_manual_100_when_adding_a_row(self):
		parent = _customs_parent(
			number_of_line_items=100,
			number_of_line_items_manual=1,
			commercial_invoice_line_items=[{}],
		)
		sync_number_of_line_items(parent)
		self.assertEqual(parent.number_of_line_items, 100)
		self.assertTrue(parent.number_of_line_items_manual)

	def test_sync_raises_header_when_rows_exceed_manual_estimate(self):
		parent = _customs_parent(
			number_of_line_items=12,
			number_of_line_items_manual=1,
			commercial_invoice_line_items=[{}] * 15,
		)
		sync_number_of_line_items(parent)
		self.assertEqual(parent.number_of_line_items, 15)
		self.assertFalse(parent.number_of_line_items_manual)

	def test_seed_from_item_count_charge_sets_manual(self):
		parent = _customs_parent(number_of_line_items=0)
		parent.charges = [
			SimpleNamespace(unit_type="Item Count", quantity=100, cost_unit_type=None, cost_quantity=0)
		]
		seed_number_of_line_items_from_item_count_charges(parent)
		self.assertEqual(parent.number_of_line_items, 100)
		self.assertTrue(parent.number_of_line_items_manual)

	def test_item_count_charge_uses_header(self):
		parent = _customs_parent(number_of_line_items=15, commercial_invoice_line_items=[{}] * 2)
		charge = _charge(
			revenue_calculation_method="Per Unit",
			unit_type="Item Count",
			unit_rate=50,
			quantity=12,
		)
		with patch(
			"logistics.utils.charges_calculation._fetch_rates_from_tariff_if_needed",
			return_value=None,
		):
			result = calculate_charge_revenue(charge, parent)
		self.assertTrue(result.get("success"), result.get("calc_notes"))
		self.assertEqual(flt(result.get("amount")), 750)
		self.assertEqual(flt(charge.quantity), 15)

	def test_item_count_keeps_quote_qty_when_header_and_lines_empty(self):
		parent = _customs_parent(number_of_line_items=0, commercial_invoice_line_items=[])
		charge = _charge(
			revenue_calculation_method="Per Unit",
			unit_type="Item Count",
			unit_rate=50,
			quantity=12,
		)
		with patch(
			"logistics.utils.charges_calculation._fetch_rates_from_tariff_if_needed",
			return_value=None,
		):
			result = calculate_charge_revenue(charge, parent)
		self.assertTrue(result.get("success"), result.get("calc_notes"))
		self.assertEqual(flt(result.get("amount")), 600)
		self.assertEqual(flt(charge.quantity), 12)

	def test_percentage_value_uses_cif_over_quote_base(self):
		parent = _customs_parent(cif=120000)
		charge = _charge(
			revenue_calculation_method="Percentage",
			unit_type="Value",
			unit_rate=0.5,
			base_amount=100000,
			quantity=1,
		)
		with patch(
			"logistics.utils.charges_calculation._fetch_rates_from_tariff_if_needed",
			return_value=None,
		):
			result = calculate_charge_revenue(charge, parent)
		self.assertTrue(result.get("success"), result.get("calc_notes"))
		self.assertEqual(flt(result.get("amount")), 600)
		self.assertEqual(flt(charge.base_amount), 120000)

	def test_job_charge_amount_ignores_lines_and_cif(self):
		parent = _customs_parent(
			cif=120000,
			number_of_line_items=15,
			total_weight=500,
			commercial_invoice_line_items=[{}] * 15,
		)
		charge = _charge(
			revenue_calculation_method="Per Unit",
			unit_type="Job",
			unit_rate=2500,
			quantity=1,
		)
		with patch(
			"logistics.utils.charges_calculation._fetch_rates_from_tariff_if_needed",
			return_value=None,
		):
			result = calculate_charge_revenue(charge, parent)
		self.assertTrue(result.get("success"), result.get("calc_notes"))
		self.assertEqual(flt(result.get("amount")), 2500)
		self.assertEqual(flt(charge.quantity), 1)

	def test_engine_value_unit_type_uses_goods_value(self):
		engine = RateCalculationEngine()
		result = engine.calculate_rate(
			rate_data={"calculation_method": "Per Unit", "rate": 0.01, "unit_type": "Value", "currency": "USD"},
			actual_quantity=8,
			actual_goods_value=1000,
		)
		self.assertTrue(result.get("success"))
		self.assertEqual(flt(result.get("amount")), 10)
