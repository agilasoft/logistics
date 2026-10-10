# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Customs Control Tower native dashboard cards and module snapshot."""

from frappe.tests.utils import FrappeTestCase

from logistics.customs.customs_control_tower import number_card_value
from logistics.customs.report.cct_module_snapshot.cct_module_snapshot import execute


class TestCustomsControlTowerDashboard(FrappeTestCase):
	def test_each_card_opens_its_detail_report(self):
		expected = {
			"open_job_files_count": ("CCT Job Files Detail", "Int", "Open"),
			"avg_age_open_jobs": ("CCT Job Files Detail", "Float", "Open"),
			"jobs_handled_count": ("CCT Job Files Detail", "Int", "Handled"),
			"avg_lead_time_per_milestone": ("CCT Milestone Lead Time", "Float", None),
			"returned_billings_count": ("CCT Returned Billings", "Int", None),
		}
		for metric, (report, fieldtype, scope) in expected.items():
			result = number_card_value({"metric": metric, "company": ""})
			self.assertEqual(result["fieldtype"], fieldtype)
			self.assertEqual(result["route"], ["query-report", report])
			self.assertIn("from_date", result["route_options"])
			self.assertIn("to_date", result["route_options"])
			if scope:
				self.assertEqual(result["route_options"].get("scope"), scope)
			else:
				self.assertNotIn("scope", result["route_options"])

	def test_unknown_metric_is_zero(self):
		result = number_card_value({"metric": "not_a_metric"})
		self.assertEqual(result["value"], 0)

	def test_module_snapshot_report_shape(self):
		columns, data, message, chart, summary = execute({"company": ""})
		self.assertIsNone(message)
		self.assertEqual([c["fieldname"] for c in columns], ["module", "open", "open_avg_age", "handled"])
		self.assertEqual(chart["type"], "bar")
		self.assertEqual(len(chart["data"]["datasets"]), 2)
		self.assertTrue(summary)
		self.assertIsInstance(data, list)
		self.assertEqual(data[0]["module"], "Declaration")
