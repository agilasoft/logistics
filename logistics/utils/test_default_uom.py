# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Dimension, volume, and weight UOM defaults come from one Logistics Settings map."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from logistics.utils.default_uom import (
	EXCLUDED_MEASUREMENT_UOM_DOCTYPES,
	apply_measurement_uom_defaults,
	measurement_uom_kind,
)


class _Field:
	def __init__(self, fieldname, fetch_from=None, fieldtype=None, options=None):
		self.fieldname = fieldname
		self.fetch_from = fetch_from
		self.fieldtype = fieldtype
		self.options = options


class _Meta:
	def __init__(self, fields):
		self.fields = fields

	def get_field(self, name):
		for field in self.fields:
			if field.fieldname == name:
				return field
		return None


class _Doc:
	def __init__(self, doctype, fields, **values):
		self.doctype = doctype
		self.meta = _Meta(fields)
		self.company = values.get("company")
		self._values = dict(values)
		self.children = []

	def get(self, key, default=None):
		return self._values.get(key, default)

	def set(self, key, value):
		self._values[key] = value

	def get_all_children(self):
		return list(self.children)


DEFAULTS = {
	"dimension": "Millimeter",
	"volume": "Cubic Meter",
	"weight": "Gram",
	"chargeable_weight": "Gram",
	"aggregation_volume": "Base Cubic Meter",
}


class TestMeasurementUomKind(unittest.TestCase):
	def test_field_names_share_one_map(self):
		self.assertEqual(measurement_uom_kind("dimension_uom"), "dimension")
		self.assertEqual(measurement_uom_kind("internal_dimension_uom"), "dimension")
		self.assertEqual(measurement_uom_kind("volume_uom"), "volume")
		self.assertEqual(measurement_uom_kind("capacity_volume_uom"), "volume")
		self.assertEqual(measurement_uom_kind("reserved_weight_uom"), "weight")
		self.assertEqual(measurement_uom_kind("gross_weight_uom"), "weight")
		self.assertEqual(measurement_uom_kind("chargeable_weight_uom"), "chargeable_weight")
		self.assertEqual(measurement_uom_kind("total_volume_uom"), "aggregation_volume")
		self.assertEqual(measurement_uom_kind("inv_volume_uom"), "aggregation_volume")
		self.assertEqual(measurement_uom_kind("peak_uom"), "volume")
		self.assertIsNone(measurement_uom_kind("default_weight_uom"))
		self.assertIsNone(measurement_uom_kind("base_volume_uom"))
		self.assertIsNone(measurement_uom_kind("uom"))

	def test_doctype_json_has_no_hardcoded_measurement_defaults(self):
		root = Path(__file__).resolve().parents[1]
		offenders = []
		for path in root.rglob("*.json"):
			if "node_modules" in path.parts:
				continue
			try:
				data = json.loads(path.read_text())
			except Exception:
				continue
			if not isinstance(data, dict):
				continue
			for field in data.get("fields") or []:
				if not isinstance(field, dict):
					continue
				kind = measurement_uom_kind(field.get("fieldname"))
				if kind and field.get("default"):
					offenders.append(f"{path.name}:{field.get('fieldname')}={field.get('default')}")
		self.assertEqual(offenders, [])


class TestApplyMeasurementUomDefaults(unittest.TestCase):
	def _doc(self, **values):
		fields = [
			_Field("dimension_uom"),
			_Field("volume_uom"),
			_Field("weight_uom"),
			_Field("total_volume_uom"),
			_Field("chargeable_weight_uom"),
		]
		return _Doc("Sea Freight Packages", fields, **values)

	@patch("logistics.utils.default_uom.measurement_uom_defaults", return_value=DEFAULTS)
	def test_empty_fields_take_logistics_settings(self, _defaults):
		doc = self._doc()
		apply_measurement_uom_defaults(doc)
		self.assertEqual(doc.get("dimension_uom"), "Millimeter")
		self.assertEqual(doc.get("volume_uom"), "Cubic Meter")
		self.assertEqual(doc.get("weight_uom"), "Gram")
		self.assertEqual(doc.get("total_volume_uom"), "Base Cubic Meter")
		self.assertEqual(doc.get("chargeable_weight_uom"), "Gram")

	@patch("logistics.utils.default_uom.measurement_uom_defaults", return_value=DEFAULTS)
	def test_existing_value_is_kept(self, _defaults):
		doc = self._doc(weight_uom="Pound", dimension_uom="Inch")
		apply_measurement_uom_defaults(doc)
		self.assertEqual(doc.get("weight_uom"), "Pound")
		self.assertEqual(doc.get("dimension_uom"), "Inch")
		self.assertEqual(doc.get("volume_uom"), "Cubic Meter")

	@patch("logistics.utils.default_uom.measurement_uom_defaults", return_value=DEFAULTS)
	def test_conversion_doctype_is_not_defaulted(self, _defaults):
		doctype = next(iter(EXCLUDED_MEASUREMENT_UOM_DOCTYPES))
		doc = _Doc(doctype, [_Field("dimension_uom"), _Field("volume_uom")])
		apply_measurement_uom_defaults(doc)
		self.assertIsNone(doc.get("dimension_uom"))
		self.assertIsNone(doc.get("volume_uom"))

	@patch("logistics.utils.default_uom.frappe.db.get_value", return_value="From Item")
	@patch("logistics.utils.default_uom.measurement_uom_defaults", return_value=DEFAULTS)
	def test_fetch_from_wins_over_settings(self, _defaults, _get_value):
		doc = _Doc(
			"Air Booking Packages",
			[_Field("weight_uom", fetch_from="warehouse_item.weight_uom"), _Field("warehouse_item", fieldtype="Link", options="Warehouse Item")],
			warehouse_item="ITEM-1",
		)
		apply_measurement_uom_defaults(doc)
		self.assertEqual(doc.get("weight_uom"), "From Item")

	@patch("logistics.utils.default_uom.measurement_uom_defaults", return_value=DEFAULTS)
	def test_child_rows_are_filled_with_the_parent(self, _defaults):
		parent = self._doc()
		child = self._doc()
		parent.children.append(child)
		apply_measurement_uom_defaults(parent, company="Acme")
		self.assertEqual(child.get("dimension_uom"), "Millimeter")
		self.assertEqual(parent.get("weight_uom"), "Gram")


if __name__ == "__main__":
	unittest.main()
