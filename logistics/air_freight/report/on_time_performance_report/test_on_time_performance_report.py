# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

import sys
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

from logistics.air_freight.report.dangerous_goods_compliance_report.test_dangerous_goods_compliance_report import (  # noqa: E402
	_unknown_columns,
)
from logistics.air_freight.report.on_time_performance_report.on_time_performance_report import (  # noqa: E402
	execute,
)


class TestOnTimePerformanceReport(TestCase):
	def test_execute_selects_job_status(self):
		filters = {
			"from_date": "2026-09-15",
			"to_date": "2026-10-15",
			"company": "ALL SYSTEMS LOGISTICS INC.",
		}
		with patch(
			"logistics.air_freight.report.on_time_performance_report.on_time_performance_report.frappe.db.sql",
			return_value=[],
		) as sql:
			columns, rows, message, chart, summary = execute(dict(filters))

		query, values = sql.call_args[0][:2]
		self.assertIn("aship.job_status as status", query)
		self.assertNotIn("aship.status", query)
		self.assertEqual(_unknown_columns(query), [])
		self.assertEqual(values, filters)
		self.assertEqual(rows, [])
		self.assertIsNone(message)
		self.assertIsNone(chart)
		self.assertEqual(summary, [])
		status_column = next(column for column in columns if column["fieldname"] == "status")
		self.assertEqual(status_column["label"], "Job Status")
