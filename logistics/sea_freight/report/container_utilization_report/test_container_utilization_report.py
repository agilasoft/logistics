# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import TestCase
from unittest.mock import patch


class _Dict(dict):
	def __getattr__(self, key):
		try:
			return self[key]
		except KeyError as exc:
			raise AttributeError(key) from exc

	def __setattr__(self, key, value):
		self[key] = value


def _flt(value, precision=None):
	if value in (None, ""):
		number = 0.0
	else:
		number = float(value)
	if precision is None:
		return number
	return round(number, precision)


def _ensure_frappe():
	if "frappe" in sys.modules:
		return
	try:
		import frappe  # noqa: F401
	except ImportError:
		frappe = ModuleType("frappe")
		frappe.__path__ = []
		frappe._ = lambda text: text
		frappe._dict = lambda value=None, **kwargs: _Dict({**(value or {}), **kwargs})
		frappe.db = SimpleNamespace(
			sql=lambda *args, **kwargs: [],
			has_column=lambda *args, **kwargs: False,
		)
		utils = ModuleType("frappe.utils")
		utils.flt = _flt
		utils.getdate = lambda value=None: value
		utils.formatdate = lambda value=None: value
		frappe.utils = utils
		sys.modules["frappe"] = frappe
		sys.modules["frappe.utils"] = utils


_ensure_frappe()

from logistics.sea_freight.report.container_utilization_report.container_utilization_report import (  # noqa: E402
	execute,
)


class TestContainerUtilizationReport(TestCase):
	def test_query_uses_gross_weight_and_skips_missing_type_columns(self):
		import frappe

		row = frappe._dict(
			{
				"container_type": "20GP",
				"container_size": "20ft",
				"total_containers": 2,
				"total_weight": 10000,
				"total_volume": 20,
				"max_weight": 25000,
				"max_volume": 33,
			}
		)
		filters = {
			"from_date": "2026-09-15",
			"to_date": "2026-10-15",
			"company": "ALL SYSTEMS LOGISTICS INC.",
			"container_type": "20GP",
		}
		with (
			patch(
				"logistics.sea_freight.report.container_utilization_report.container_utilization_report.frappe.db.has_column",
				return_value=False,
			),
			patch(
				"logistics.sea_freight.report.container_utilization_report.container_utilization_report.frappe.db.sql",
				return_value=[row],
			) as sql,
		):
			columns, data, message, chart, summary = execute(filters)

		query, values = sql.call_args[0][:2]
		self.assertNotIn("ct.max_weight", query)
		self.assertNotIn("ct.max_volume", query)
		self.assertIn("ct.max_gross_weight", query)
		self.assertIn("sfc.max_volume", query)
		self.assertIn("sship.booking_date >= %(from_date)s", query)
		self.assertIn("sship.booking_date <= %(to_date)s", query)
		self.assertIn("sship.company = %(company)s", query)
		self.assertIn("sfc.type = %(container_type)s", query)
		self.assertEqual(values, filters)
		self.assertIsNone(message)
		self.assertEqual([col["fieldname"] for col in columns][:4], [
			"container_type",
			"container_size",
			"total_containers",
			"total_weight",
		])
		self.assertEqual(len(data), 1)
		self.assertAlmostEqual(data[0].weight_utilization, (10000 / (25000 * 2)) * 100)
		self.assertAlmostEqual(data[0].volume_utilization, (20 / (33 * 2)) * 100)
		self.assertAlmostEqual(
			data[0].avg_utilization,
			(data[0].weight_utilization + data[0].volume_utilization) / 2,
		)
		self.assertEqual(chart["data"]["labels"], ["20GP (20ft)"])
		self.assertEqual(summary[0]["value"], 2)

	def test_query_reads_container_type_volume_when_column_exists(self):
		with (
			patch(
				"logistics.sea_freight.report.container_utilization_report.container_utilization_report.frappe.db.has_column",
				return_value=True,
			) as has_column,
			patch(
				"logistics.sea_freight.report.container_utilization_report.container_utilization_report.frappe.db.sql",
				return_value=[],
			) as sql,
		):
			execute({})

		has_column.assert_called_once_with("Container Type", "max_volume")
		query = sql.call_args[0][0]
		self.assertIn("ct.max_volume", query)
		self.assertNotIn("ct.max_weight", query)
		self.assertIn("ct.max_gross_weight", query)

	def test_zero_capacity_does_not_divide(self):
		import frappe

		row = frappe._dict(
			{
				"container_type": "40HC",
				"container_size": "40ft",
				"total_containers": 1,
				"total_weight": 500,
				"total_volume": 2,
				"max_weight": 0,
				"max_volume": 0,
			}
		)
		with (
			patch(
				"logistics.sea_freight.report.container_utilization_report.container_utilization_report.frappe.db.has_column",
				return_value=False,
			),
			patch(
				"logistics.sea_freight.report.container_utilization_report.container_utilization_report.frappe.db.sql",
				return_value=[row],
			),
		):
			_columns, data, _message, chart, summary = execute(None)

		self.assertEqual(data[0].weight_utilization, 0)
		self.assertEqual(data[0].volume_utilization, 0)
		self.assertEqual(data[0].avg_utilization, 0)
		self.assertEqual(chart["data"]["datasets"][0]["values"], [0])
		self.assertTrue(summary)

	def test_query_columns_exist_on_doctypes(self):
		repo = Path(__file__).resolve().parents[4]
		aliases = {
			"ct": _doctype_fields(repo / "logistics/logistics/doctype/container_type/container_type.json"),
			"sfc": _doctype_fields(
				repo / "logistics/sea_freight/doctype/sea_freight_containers/sea_freight_containers.json"
			),
			"sship": _doctype_fields(repo / "logistics/sea_freight/doctype/sea_shipment/sea_shipment.json"),
		}
		with (
			patch(
				"logistics.sea_freight.report.container_utilization_report.container_utilization_report.frappe.db.has_column",
				return_value=False,
			),
			patch(
				"logistics.sea_freight.report.container_utilization_report.container_utilization_report.frappe.db.sql",
				return_value=[],
			) as sql,
		):
			execute({"from_date": "2026-09-15", "to_date": "2026-10-15", "company": "ALL SYSTEMS LOGISTICS INC."})

		query = sql.call_args[0][0]
		referenced = re.findall(r"\b(ct|sfc|sship)\.([a-z_]+)\b", query)
		self.assertTrue(referenced)
		missing = sorted(
			"{0}.{1}".format(alias, field)
			for alias, field in referenced
			if field not in aliases[alias]
		)
		self.assertEqual(missing, [])
		self.assertIn(("ct", "max_gross_weight"), referenced)
		self.assertNotIn(("ct", "max_weight"), referenced)
		self.assertNotIn(("ct", "max_volume"), referenced)


def _doctype_fields(path):
	payload = json.loads(path.read_text(encoding="utf-8"))
	return {field["fieldname"] for field in payload["fields"]} | {"name", "parent", "docstatus"}
