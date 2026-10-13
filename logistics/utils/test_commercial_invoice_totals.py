# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from logistics.utils.commercial_invoice_totals import calculate_commercial_invoice_totals


def _doc(**kwargs):
	data = {
		"doctype": "Declaration Order",
		"inv_currency": "USD",
		"inv_total_amount": 0,
		"commercial_invoice_line_items": [],
		"commercial_invoice_charges": [],
	}
	data.update(kwargs)
	return data


class UnitTestCommercialInvoiceTotals(UnitTestCase):
	def test_line_items_only_set_fob_and_cif_to_line_total(self):
		totals = calculate_commercial_invoice_totals(
			_doc(
				commercial_invoice_line_items=[
					{"invoice_qty": 2, "price": 100},
					{"invoice_qty": 1, "price": 50},
				]
			)
		)
		self.assertEqual(totals["expected_invoice_line_total"], 250)
		self.assertEqual(totals["fob"], 250)
		self.assertEqual(totals["cif"], 250)

	def test_freight_and_insurance_increase_cif_not_fob(self):
		totals = calculate_commercial_invoice_totals(
			_doc(
				commercial_invoice_line_items=[{"invoice_qty": 1, "price": 1000}],
				commercial_invoice_charges=[
					{"charge_code": "OFT", "amount": 200, "currency": "USD"},
					{"charge_code": "ONS", "amount": 50, "currency": "USD"},
				],
			)
		)
		self.assertEqual(totals["fob"], 1000)
		self.assertEqual(totals["cif"], 1250)

	def test_add_to_fob_charge_increases_fob_and_cif(self):
		totals = calculate_commercial_invoice_totals(
			_doc(
				commercial_invoice_line_items=[{"invoice_qty": 1, "price": 1000}],
				commercial_invoice_charges=[
					{"charge_code": "LCH", "amount": 75, "currency": "USD", "add_to_fob": 1},
					{"charge_code": "OFT", "amount": 200, "currency": "USD"},
				],
			)
		)
		self.assertEqual(totals["fob"], 1075)
		self.assertEqual(totals["cif"], 1275)

	def test_deduction_charge_reduces_fob_and_cif(self):
		totals = calculate_commercial_invoice_totals(
			_doc(
				commercial_invoice_line_items=[{"invoice_qty": 1, "price": 1000}],
				commercial_invoice_charges=[{"charge_code": "DIS", "amount": 100, "currency": "USD"}],
			)
		)
		self.assertEqual(totals["fob"], 900)
		self.assertEqual(totals["cif"], 900)

	def test_included_in_inv_amt_charge_skipped_from_cif(self):
		totals = calculate_commercial_invoice_totals(
			_doc(
				inv_total_amount=1500,
				commercial_invoice_line_items=[{"invoice_qty": 1, "price": 1000}],
				commercial_invoice_charges=[
					{
						"charge_code": "OFT",
						"amount": 500,
						"currency": "USD",
						"included_in_inv_amt": 1,
					}
				],
			)
		)
		self.assertEqual(totals["cif"], 1000)

	def test_balance_uses_line_total_as_invoice_total_when_lines_exist(self):
		totals = calculate_commercial_invoice_totals(
			_doc(
				inv_total_amount=1300,
				commercial_invoice_line_items=[{"invoice_qty": 1, "price": 1000}],
				commercial_invoice_charges=[{"charge_code": "OFT", "amount": 200, "currency": "USD"}],
			)
		)
		self.assertEqual(totals["inv_total_amount"], 1000)
		self.assertEqual(totals["balance"], "-200.00")

	def test_charges_excl_from_itot_omits_charges_from_balance(self):
		totals = calculate_commercial_invoice_totals(
			_doc(
				inv_total_amount=1000,
				charges_excl_from_itot=1,
				commercial_invoice_line_items=[{"invoice_qty": 1, "price": 1000}],
				commercial_invoice_charges=[{"charge_code": "OFT", "amount": 200, "currency": "USD"}],
			)
		)
		self.assertEqual(totals["inv_total_amount"], 1000)
		self.assertEqual(totals["balance"], "0.00")
		self.assertEqual(totals["cif"], 1200)

	def test_invoice_total_equals_line_sum(self):
		totals = calculate_commercial_invoice_totals(
			_doc(
				inv_total_amount=999,
				commercial_invoice_line_items=[
					{"invoice_qty": 2, "price": 100},
					{"invoice_qty": 1, "price": 50},
				],
			)
		)
		self.assertEqual(totals["inv_total_amount"], 250)
		self.assertEqual(totals["expected_invoice_line_total"], 250)

	def test_zero_invoice_qty_is_not_counted_as_one(self):
		totals = calculate_commercial_invoice_totals(
			_doc(
				commercial_invoice_line_items=[
					{"invoice_qty": 0, "customs_qty": 4, "price": 10},
					{"invoice_qty": 0, "price": 25},
				]
			)
		)
		self.assertEqual(totals["expected_invoice_line_total"], 40)
		self.assertEqual(totals["inv_total_amount"], 40)

	def test_typed_invoice_total_kept_when_there_are_no_lines(self):
		totals = calculate_commercial_invoice_totals(_doc(inv_total_amount=1300))
		self.assertNotIn("inv_total_amount", totals)
		self.assertEqual(totals["fob"], 1300)

	def test_blank_invoice_qty_is_allowed_and_zero_is_rejected(self):
		from logistics.utils.commercial_invoice_totals import throw_if_invoice_qty_is_zero

		throw_if_invoice_qty_is_zero(_doc(commercial_invoice_line_items=[{"goods_description": "A"}]))
		throw_if_invoice_qty_is_zero(
			_doc(commercial_invoice_line_items=[{"invoice_qty": None, "goods_description": "A"}])
		)
		with self.assertRaises(frappe.ValidationError):
			throw_if_invoice_qty_is_zero(
				_doc(commercial_invoice_line_items=[{"invoice_qty": 0, "goods_description": "A"}])
			)

	def test_invoice_details_total_line_measurements(self):
		totals = calculate_commercial_invoice_totals(
			_doc(
				inv_volume=99,
				inv_volume_uom="M3",
				inv_gross_weight=1,
				commercial_invoice_line_items=[
					{
						"invoice_qty": 1,
						"price": 5,
						"volume": 1.5,
						"volume_uom": "CBM",
						"gross_weight": 10,
						"gross_weight_uom": "Kg",
						"net_weight": 8,
						"net_weight_uom": "Kg",
						"no_of_packs": 2,
					},
					{
						"invoice_qty": 1,
						"price": 5,
						"volume": 2.5,
						"volume_uom": "CBM",
						"gross_weight": 4,
						"gross_weight_uom": "Kg",
						"net_weight": 3,
						"net_weight_uom": "Kg",
						"no_of_packs": 3,
					},
				],
			)
		)
		self.assertEqual(totals["inv_volume"], 4)
		self.assertEqual(totals["inv_volume_uom"], "CBM")
		self.assertEqual(totals["inv_gross_weight"], 14)
		self.assertEqual(totals["inv_gross_weight_uom"], "Kg")
		self.assertEqual(totals["inv_net_weight"], 11)
		self.assertEqual(totals["inv_net_weight_uom"], "Kg")
		self.assertEqual(totals["packages"], 5)
		self.assertNotIn("packages_uom", totals)

	def test_blank_line_uom_sums_quantity_without_replacing_header_uom(self):
		totals = calculate_commercial_invoice_totals(
			_doc(
				inv_volume_uom="CBM",
				commercial_invoice_line_items=[{"volume": 2}, {"volume": 3, "gross_weight": 0}],
			)
		)
		self.assertEqual(totals["inv_volume"], 5)
		self.assertNotIn("inv_volume_uom", totals)
		self.assertNotIn("inv_gross_weight", totals)

	def test_lines_without_measurements_leave_invoice_details_untouched(self):
		totals = calculate_commercial_invoice_totals(
			_doc(
				inv_volume=9,
				commercial_invoice_line_items=[{"invoice_qty": 1, "price": 10}],
			)
		)
		self.assertNotIn("inv_volume", totals)
		self.assertNotIn("packages", totals)
		self.assertEqual(totals["inv_total_amount"], 10)

	@patch("logistics.utils.measurements.convert_volume")
	def test_mixed_volume_uoms_convert_into_header_uom(self, mock_convert):
		mock_convert.side_effect = lambda value, from_uom=None, to_uom=None, company=None: (
			value * 2 if from_uom == "CFT" else value
		)
		totals = calculate_commercial_invoice_totals(
			_doc(
				inv_volume_uom="CBM",
				commercial_invoice_line_items=[
					{"volume": 2, "volume_uom": "CFT"},
					{"volume": 1, "volume_uom": "CBM"},
				],
			)
		)
		self.assertEqual(totals["inv_volume"], 5)
		self.assertEqual(totals["inv_volume_uom"], "CBM")
		mock_convert.assert_called_once()

	@patch("frappe.db.exists", return_value="Carton")
	def test_packages_uom_follows_shared_package_type_when_it_is_a_uom(self, _exists):
		totals = calculate_commercial_invoice_totals(
			_doc(
				commercial_invoice_line_items=[
					{"no_of_packs": 2, "package_type": "Carton"},
					{"no_of_packs": 1, "package_type": "Carton"},
				]
			)
		)
		self.assertEqual(totals["packages"], 3)
		self.assertEqual(totals["packages_uom"], "Carton")

	@patch("frappe.db.exists", return_value=None)
	def test_packages_uom_skipped_when_package_type_is_not_a_uom(self, _exists):
		totals = calculate_commercial_invoice_totals(
			_doc(
				commercial_invoice_line_items=[
					{"no_of_packs": 2, "package_type": "Outer carton"},
					{"no_of_packs": 1, "package_type": "Outer carton"},
				]
			)
		)
		self.assertEqual(totals["packages"], 3)
		self.assertNotIn("packages_uom", totals)
