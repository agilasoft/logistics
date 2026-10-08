# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch


def _ensure_frappe():
	if "frappe" in sys.modules:
		return
	try:
		import frappe  # noqa: F401
	except ImportError:
		frappe = SimpleNamespace()
		frappe._ = lambda text: text
		frappe.db = SimpleNamespace(sql=lambda *args, **kwargs: [])
		sys.modules["frappe"] = frappe


_ensure_frappe()

from logistics.mice.report.mice_billing_status_report.mice_billing_status_report import (  # noqa: E402
	classify_project_billing_status,
	execute,
)


class TestMiceBillingStatusReport(TestCase):
	def test_classify_project_billing_status(self):
		self.assertEqual(classify_project_billing_status(0, 0, 0, 0, 0), "Not Billed")
		self.assertEqual(classify_project_billing_status(2, 0, 0, 0, 2), "Cancelled")
		self.assertEqual(classify_project_billing_status(3, 3, 0, 0, 0), "Pending")
		self.assertEqual(classify_project_billing_status(2, 1, 0, 0, 1), "Pending")
		self.assertEqual(classify_project_billing_status(4, 0, 4, 0, 0), "Billed")
		self.assertEqual(classify_project_billing_status(3, 0, 2, 1, 0), "Billed")
		self.assertEqual(classify_project_billing_status(2, 0, 0, 2, 0), "Paid")
		self.assertEqual(classify_project_billing_status(3, 0, 0, 2, 1), "Paid")
		self.assertEqual(classify_project_billing_status(4, 1, 2, 1, 0), "Partially Billed")
		self.assertEqual(classify_project_billing_status(3, 1, 1, 0, 1), "Partially Billed")

	def test_execute_derives_status_without_selecting_missing_column(self):
		raw_rows = [
			{
				"exhibit": "MICE-0001",
				"organizer": "ORG-1",
				"customer": "CUST-1",
				"lifecycle_stage": "Pre-Show",
				"line_count": 2,
				"pending_count": 1,
				"invoiced_count": 1,
				"paid_count": 0,
				"cancelled_count": 0,
			},
			{
				"exhibit": "MICE-0002",
				"organizer": "ORG-2",
				"customer": "CUST-2",
				"lifecycle_stage": "Show",
				"line_count": 0,
				"pending_count": 0,
				"invoiced_count": 0,
				"paid_count": 0,
				"cancelled_count": 0,
			},
		]
		with patch(
			"logistics.mice.report.mice_billing_status_report.mice_billing_status_report.frappe.db.sql",
			return_value=raw_rows,
		) as sql:
			columns, rows = execute(
				{"organizer": "ORG-1", "customer": "CUST-1", "billing_status": "Partially Billed"}
			)
		query, values = sql.call_args[0][:2]
		self.assertNotIn("ep.billing_status", query)
		self.assertIn("`tabMICE Project Billing`", query)
		self.assertIn("ep.organizer = %(organizer)s", query)
		self.assertIn("org.customer = %(customer)s", query)
		self.assertEqual(values, {"organizer": "ORG-1", "customer": "CUST-1"})
		self.assertEqual([col["fieldname"] for col in columns], [
			"exhibit",
			"organizer",
			"customer",
			"billing_status",
			"lifecycle_stage",
			"billing_lines",
			"invoiced_lines",
		])
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["exhibit"], "MICE-0001")
		self.assertEqual(rows[0]["billing_status"], "Partially Billed")
		self.assertEqual(rows[0]["billing_lines"], 2)
		self.assertEqual(rows[0]["invoiced_lines"], 1)

	def test_execute_keeps_unbilled_projects_when_filter_is_empty(self):
		with patch(
			"logistics.mice.report.mice_billing_status_report.mice_billing_status_report.frappe.db.sql",
			return_value=[
				{
					"exhibit": "MICE-0003",
					"organizer": None,
					"customer": None,
					"lifecycle_stage": "Pre-Show",
					"line_count": 0,
					"pending_count": 0,
					"invoiced_count": 0,
					"paid_count": 0,
					"cancelled_count": 0,
				}
			],
		):
			_columns, rows = execute({})
		self.assertEqual(rows[0]["billing_status"], "Not Billed")
		self.assertEqual(rows[0]["billing_lines"], 0)
		self.assertEqual(rows[0]["invoiced_lines"], 0)
