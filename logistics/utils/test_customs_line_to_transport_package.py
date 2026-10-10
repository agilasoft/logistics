# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from types import SimpleNamespace
import unittest

from logistics.utils.customs_line_to_transport_package import (
	customs_line_has_cargo,
	customs_lines_for_transport,
	transport_package_from_customs_line,
)


def _line(**kwargs):
	return SimpleNamespace(**kwargs)


class TestCustomsLineToTransportPackage(unittest.TestCase):
	def test_line_item_maps_onto_transport_package(self):
		row = transport_package_from_customs_line(
			_line(
				goods_description="Widgets\nSecond line",
				commodity_code="GEN",
				tariff="1234.56",
				invoice_qty=4,
				invoice_qty_uom="Nos",
				no_of_packs=2,
				gross_weight=10,
				gross_weight_uom="Kg",
				volume=1.5,
				volume_uom="CBM",
				length=1,
				width=2,
				height=3,
				dimension_uom="Meter",
				reference_no="PKG-1",
			)
		)
		self.assertEqual(row["description"], "Widgets")
		self.assertEqual(row["goods_description"], "Widgets\nSecond line")
		self.assertEqual(row["commodity"], "GEN")
		self.assertEqual(row["hs_code"], "1234.56")
		self.assertEqual(row["quantity"], 4)
		self.assertEqual(row["uom"], "Nos")
		self.assertEqual(row["no_of_packs"], 2)
		self.assertEqual(row["weight"], 10)
		self.assertEqual(row["weight_uom"], "Kg")
		self.assertEqual(row["volume"], 1.5)
		self.assertEqual(row["length"], 1)
		self.assertEqual(row["width"], 2)
		self.assertEqual(row["height"], 3)
		self.assertEqual(row["reference_no"], "PKG-1")

	def test_missing_required_measures_are_zero(self):
		row = transport_package_from_customs_line(_line(goods_description="Spare parts"))
		self.assertEqual(row["description"], "Spare parts")
		self.assertEqual(row["weight"], 0)
		self.assertEqual(row["length"], 0)
		self.assertEqual(row["height"], 0)
		self.assertNotIn("width", row)
		self.assertNotIn("quantity", row)

	def test_quantity_falls_back_to_customs_qty(self):
		row = transport_package_from_customs_line(
			_line(goods_description="Bolts", invoice_qty=0, customs_qty=6, customs_qty_uom="Nos")
		)
		self.assertEqual(row["quantity"], 6)
		self.assertEqual(row["uom"], "Nos")

	def test_blank_line_is_skipped(self):
		self.assertFalse(customs_line_has_cargo(_line(goods_description="  ", invoice_qty=0, no_of_packs=0)))
		self.assertIsNone(transport_package_from_customs_line(_line()))

	def test_product_code_becomes_description_when_goods_text_is_blank(self):
		row = transport_package_from_customs_line(_line(product_code="SKU-9", gross_weight=1))
		self.assertEqual(row["description"], "SKU-9")
		self.assertEqual(row["weight"], 1)

	def test_declaration_lines_win_over_declaration_order(self):
		declaration = SimpleNamespace(
			commercial_invoice_line_items=[_line(goods_description="On the declaration")]
		)
		order = SimpleNamespace(
			commercial_invoice_line_items=[_line(goods_description="On the order")]
		)
		lines = customs_lines_for_transport(declaration, order)
		self.assertEqual(len(lines), 1)
		self.assertEqual(lines[0].goods_description, "On the declaration")

	def test_empty_declaration_uses_declaration_order_lines(self):
		declaration = SimpleNamespace(commercial_invoice_line_items=[_line(goods_description="")])
		order = SimpleNamespace(
			commercial_invoice_line_items=[
				_line(goods_description="From the order", no_of_packs=3),
				_line(),
			]
		)
		lines = customs_lines_for_transport(declaration, order)
		packages = [transport_package_from_customs_line(line, idx) for idx, line in enumerate(lines, start=1)]
		packages = [row for row in packages if row]
		self.assertEqual(len(packages), 1)
		self.assertEqual(packages[0]["description"], "From the order")
		self.assertEqual(packages[0]["no_of_packs"], 3)


if __name__ == "__main__":
	unittest.main()
