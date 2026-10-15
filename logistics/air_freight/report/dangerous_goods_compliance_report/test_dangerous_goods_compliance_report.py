# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch


def _ensure_frappe():
	if "frappe" in sys.modules and "frappe.utils" in sys.modules:
		utils = sys.modules["frappe.utils"]
		for name in ("flt", "getdate", "formatdate", "get_datetime", "format_datetime"):
			if not hasattr(utils, name):
				setattr(utils, name, lambda value, precision=None: value)
		return
	try:
		import frappe  # noqa: F401
		from frappe.utils import flt  # noqa: F401
	except ImportError:
		frappe = SimpleNamespace()
		frappe._ = lambda text: text
		frappe.db = SimpleNamespace(sql=lambda *args, **kwargs: [])
		utils = SimpleNamespace(
			flt=lambda value, precision=None: float(value or 0),
			getdate=lambda value: value,
			formatdate=lambda value: value,
			get_datetime=lambda value: value,
			format_datetime=lambda value: value,
		)
		frappe.utils = utils
		sys.modules["frappe"] = frappe
		sys.modules["frappe.utils"] = utils


_ensure_frappe()

from logistics.air_freight.report.dangerous_goods_compliance_report.dangerous_goods_compliance_report import (  # noqa: E402
	execute,
	get_chart_data,
)

_REPORT_DIR = Path(__file__).resolve().parent
_AIR_FREIGHT = _REPORT_DIR.parents[1]
_STANDARD_COLUMNS = {
	"name",
	"owner",
	"creation",
	"modified",
	"modified_by",
	"docstatus",
	"idx",
	"parent",
	"parentfield",
	"parenttype",
}
_REQUEST_FILTERS = {
	"from_date": "2026-09-15",
	"to_date": "2026-10-15",
	"company": "ALL SYSTEMS LOGISTICS INC.",
}


def _fieldnames(doctype_folder):
	path = _AIR_FREIGHT / "doctype" / doctype_folder / f"{doctype_folder}.json"
	payload = json.loads(path.read_text(encoding="utf-8"))
	names = {field["fieldname"] for field in payload["fields"] if field.get("fieldname")}
	names.update(_STANDARD_COLUMNS)
	return names


def _unknown_columns(query):
	fields = {
		"aship": _fieldnames("air_shipment"),
		"asp": _fieldnames("air_shipment_packages"),
	}
	missing = []
	for alias, column in re.findall(r"\b(aship|asp)\.([a-z_]+)\b", query):
		if column not in fields[alias]:
			missing.append(f"{alias}.{column}")
	return missing


class TestDangerousGoodsComplianceReport(TestCase):
	def test_execute_selects_job_status_for_the_reported_filters(self):
		with patch(
			"logistics.air_freight.report.dangerous_goods_compliance_report.dangerous_goods_compliance_report.frappe.db.sql",
			return_value=[],
		) as sql:
			columns, rows, message, chart, summary = execute(dict(_REQUEST_FILTERS))

		query, values = sql.call_args[0][:2]
		self.assertIn("aship.job_status as status", query)
		self.assertNotIn("aship.status", query)
		self.assertEqual(_unknown_columns(query), [])
		self.assertIn("aship.docstatus = 1", query)
		self.assertIn("aship.booking_date >= %(from_date)s", query)
		self.assertIn("aship.booking_date <= %(to_date)s", query)
		self.assertIn("aship.company = %(company)s", query)
		self.assertEqual(values, _REQUEST_FILTERS)
		self.assertEqual(sql.call_args.kwargs.get("as_dict"), 1)
		self.assertIsNone(message)
		self.assertIsNone(chart)
		self.assertEqual(rows, [])
		self.assertEqual(summary, [])
		status_column = next(column for column in columns if column["fieldname"] == "status")
		self.assertEqual(status_column["label"], "Job Status")

	def test_compliance_filter_and_chart_use_doctype_options(self):
		doctype = json.loads(
			(_AIR_FREIGHT / "doctype" / "air_shipment" / "air_shipment.json").read_text(encoding="utf-8")
		)
		options = next(
			field["options"]
			for field in doctype["fields"]
			if field.get("fieldname") == "dg_compliance_status"
		).split("\n")
		script = (_REPORT_DIR / "dangerous_goods_compliance_report.js").read_text(encoding="utf-8")
		filter_options = script.split('"options": "\\n', 1)[1].split('"', 1)[0].split("\\n")
		self.assertEqual(filter_options, options)

		rows = [{"dg_compliance_status": option, "contains_dg": 1, "dg_packages_count": 1, "compliance_issues": 0} for option in options]
		rows.append({"dg_compliance_status": None, "contains_dg": 0, "dg_packages_count": 0, "compliance_issues": 2})
		chart = get_chart_data(rows)
		self.assertEqual(chart["data"]["labels"], options + ["Unknown"])
		self.assertEqual(chart["data"]["datasets"][0]["values"], [1, 1, 1, 1, 1])
		self.assertEqual(len(chart["colors"]), len(chart["data"]["labels"]))

	def test_optional_filters_stay_parameterized(self):
		filters = {
			"contains_dg": 1,
			"compliance_status": "Under Review",
			"has_compliance_issues": 1,
		}
		with patch(
			"logistics.air_freight.report.dangerous_goods_compliance_report.dangerous_goods_compliance_report.frappe.db.sql",
			return_value=[],
		) as sql:
			execute(filters)

		query, values = sql.call_args[0][:2]
		self.assertIn("aship.contains_dangerous_goods = 1", query)
		self.assertIn("aship.dg_compliance_status = %(compliance_status)s", query)
		self.assertIn("asp.emergency_contact_name IS NULL", query)
		self.assertEqual(values["compliance_status"], "Under Review")
		self.assertEqual(_unknown_columns(query), [])
