# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

from types import SimpleNamespace
from unittest.mock import patch

from frappe.tests import UnitTestCase

from logistics.utils.module_integration import (
	_apply_shipment_incoterm_to_declaration_order,
	_copy_shipment_packages_to_declaration_order_line_items,
	_fill_declaration_order_countries_from_ports,
)


class _Line(SimpleNamespace):
	def set(self, fieldname, value):
		setattr(self, fieldname, value)


class _Order(SimpleNamespace):
	def append(self, fieldname, data=None):
		row = _Line()
		getattr(self, fieldname).append(row)
		return row


def _order(**kwargs):
	data = {
		"incoterm": None,
		"inv_incoterm": None,
		"country_of_origin": None,
		"country_of_destination": None,
		"port_of_loading": None,
		"port_of_discharge": None,
		"commercial_invoice_line_items": [],
	}
	data.update(kwargs)
	return _Order(**data)


class TestDeclarationOrderFromShipmentPopulation(UnitTestCase):
	def test_shipment_incoterm_wins_and_fills_invoice_incoterm(self):
		order = _order(incoterm="EXW")
		shipment = SimpleNamespace(incoterm="CIF")
		_apply_shipment_incoterm_to_declaration_order(order, shipment)
		self.assertEqual(order.incoterm, "CIF")
		self.assertEqual(order.inv_incoterm, "CIF")

	def test_quote_incoterm_kept_when_shipment_has_none(self):
		order = _order(incoterm="FOB")
		_apply_shipment_incoterm_to_declaration_order(order, SimpleNamespace(incoterm=None))
		self.assertEqual(order.incoterm, "FOB")
		self.assertEqual(order.inv_incoterm, "FOB")

	def test_existing_invoice_incoterm_is_not_replaced(self):
		order = _order(incoterm="EXW", inv_incoterm="DAP")
		_apply_shipment_incoterm_to_declaration_order(order, SimpleNamespace(incoterm="CIF"))
		self.assertEqual(order.incoterm, "CIF")
		self.assertEqual(order.inv_incoterm, "DAP")

	def test_package_maps_onto_line_item(self):
		order = _order()
		shipment = SimpleNamespace(
			packages=[
				SimpleNamespace(
					goods_description="Widgets",
					commodity="GEN",
					hs_code="1234.56",
					quantity=4,
					uom="Nos",
					no_of_packs=2,
					weight=10,
					weight_uom="Kg",
					volume=1.5,
					volume_uom="CBM",
					length=1,
					width=2,
					height=3,
					dimension_uom="Meter",
					reference_no="PKG-1",
				)
			]
		)
		_copy_shipment_packages_to_declaration_order_line_items(order, shipment)
		self.assertEqual(len(order.commercial_invoice_line_items), 1)
		row = order.commercial_invoice_line_items[0]
		self.assertEqual(row.goods_description, "Widgets")
		self.assertEqual(row.commodity_code, "GEN")
		self.assertEqual(row.tariff, "1234.56")
		self.assertEqual(row.invoice_qty, 4)
		self.assertEqual(row.customs_qty, 4)
		self.assertEqual(row.invoice_qty_uom, "Nos")
		self.assertEqual(row.gross_weight, 10)
		self.assertEqual(row.reference_no, "PKG-1")

	def test_zero_package_quantity_does_not_set_invoice_qty_zero(self):
		order = _order()
		shipment = SimpleNamespace(
			packages=[
				SimpleNamespace(
					goods_description="Empty qty",
					quantity=0,
					no_of_packs=3,
					uom="Nos",
					commodity=None,
					hs_code=None,
					weight=None,
					weight_uom=None,
					volume=None,
					volume_uom=None,
					length=None,
					width=None,
					height=None,
					dimension_uom=None,
					reference_no=None,
				)
			]
		)
		_copy_shipment_packages_to_declaration_order_line_items(order, shipment)
		row = order.commercial_invoice_line_items[0]
		self.assertEqual(row.invoice_qty, 3)
		self.assertFalse(hasattr(row, "customs_qty"))

	def test_zero_package_quantity_without_packs_omits_invoice_qty(self):
		order = _order()
		shipment = SimpleNamespace(
			packages=[
				SimpleNamespace(
					goods_description="No qty",
					quantity=0,
					no_of_packs=0,
					uom=None,
					commodity=None,
					hs_code=None,
					weight=None,
					weight_uom=None,
					volume=None,
					volume_uom=None,
					length=None,
					width=None,
					height=None,
					dimension_uom=None,
					reference_no=None,
				)
			]
		)
		_copy_shipment_packages_to_declaration_order_line_items(order, shipment)
		row = order.commercial_invoice_line_items[0]
		self.assertFalse(hasattr(row, "invoice_qty"))

	def test_countries_come_from_order_ports(self):
		order = _order(port_of_loading="USLAX", port_of_discharge="CNSHA")

		def _country(code):
			return {"USLAX": "United States", "CNSHA": "China"}.get(code)

		with patch(
			"logistics.utils.customs_country_defaults.country_from_unloco",
			side_effect=_country,
		):
			_fill_declaration_order_countries_from_ports(order)

		self.assertEqual(order.country_of_origin, "United States")
		self.assertEqual(order.country_of_destination, "China")

	def test_existing_country_is_not_overwritten(self):
		order = _order(
			port_of_loading="USLAX",
			port_of_discharge="CNSHA",
			country_of_origin="Singapore",
		)

		def _country(code):
			return {"USLAX": "United States", "CNSHA": "China"}.get(code)

		with patch(
			"logistics.utils.customs_country_defaults.country_from_unloco",
			side_effect=_country,
		):
			_fill_declaration_order_countries_from_ports(order)

		self.assertEqual(order.country_of_origin, "Singapore")
		self.assertEqual(order.country_of_destination, "China")
