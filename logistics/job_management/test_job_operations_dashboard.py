# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

from frappe.tests.utils import FrappeTestCase

from logistics.job_management.job_operations_dashboard import (
	accounting_mix,
	attention_rows,
	classify_job,
	count_job_kpis,
	exception_rows,
	job_alerts,
	job_user_workload,
	job_work_rows,
	merge_alert_items,
	pipeline_counts,
)


class TestJobOperationsDashboardHelpers(FrappeTestCase):
	def test_classify_wip_accrual_and_billing(self):
		live = classify_job(
			{
				"job_status": "In Progress",
				"wip_amount": 0,
				"accrual_amount": 0,
				"estimated_revenue": 0,
				"estimated_costs": 0,
			}
		)
		self.assertTrue(live["live"])
		self.assertEqual(live["wip_status"], "Not Started")
		self.assertEqual(live["severity"], "live")

		wip_open = classify_job({"job_status": "Submitted", "wip_amount": 1200, "billing_status": "Not Billed"})
		self.assertTrue(wip_open["wip_open"])
		self.assertTrue(wip_open["at_risk"])
		self.assertEqual(wip_open["severity"], "at_risk")

		closed_wip = classify_job({"job_status": "Completed", "wip_amount": 500, "accrual_amount": 0})
		self.assertTrue(closed_wip["closed_open_balance"])
		self.assertTrue(closed_wip["overdue"])
		self.assertEqual(closed_wip["severity"], "overdue")

		from logistics.job_management.job_operations_dashboard import _matches_status_filter

		self.assertTrue(_matches_status_filter(closed_wip, "open"))

		overdue_bill = classify_job({"job_status": "In Progress", "billing_status": "Overdue", "wip_amount": 0})
		self.assertTrue(overdue_bill["billing_overdue"])
		self.assertEqual(overdue_bill["severity"], "overdue")

	def test_wip_pending_respects_recognition_flag(self):
		pending = classify_job(
			{
				"job_status": "Submitted",
				"estimated_revenue": 800,
				"wip_amount": 0,
				"recognized_revenue": 0,
			}
		)
		self.assertTrue(pending["wip_pending"])
		self.assertEqual(pending["severity"], "at_risk")

		disabled = classify_job(
			{
				"job_status": "Submitted",
				"estimated_revenue": 800,
				"wip_amount": 0,
				"wip_recognition_enabled": 0,
			}
		)
		self.assertFalse(disabled["wip_pending"])
		self.assertEqual(disabled["severity"], "live")

	def test_kpis_pipeline_and_mix(self):
		rows = [
			{
				"job_type": "Air Shipment",
				"job_status": "Draft",
				"flags": classify_job({"job_status": "Draft"}),
			},
			{
				"job_type": "Sea Shipment",
				"job_status": "In Progress",
				"wip_amount": 100,
				"billing_status": "Not Billed",
				"flags": classify_job(
					{"job_status": "In Progress", "wip_amount": 100, "billing_status": "Not Billed"}
				),
			},
			{
				"job_type": "Air Shipment",
				"job_status": "Completed",
				"wip_amount": 40,
				"flags": classify_job({"job_status": "Completed", "wip_amount": 40}),
			},
		]
		kpis = count_job_kpis(rows)
		self.assertEqual(kpis["jobs"], 3)
		self.assertEqual(kpis["active"], 2)
		self.assertEqual(kpis["live"], 1)
		self.assertEqual(kpis["wip_open"], 2)
		self.assertEqual(kpis["overdue"], 1)
		self.assertEqual(kpis["wip_amount"], 140)
		pipe = {p["lifecycle_stage"]: p["program_count"] for p in pipeline_counts(rows)}
		self.assertEqual(pipe["Air Shipment"], 1)
		self.assertEqual(pipe["Sea Shipment"], 1)
		mix = accounting_mix(rows)
		self.assertEqual(mix["wip"]["Open"], 2)
		self.assertEqual(mix["statuses"]["Draft"], 1)

	def test_work_rows_exceptions_and_alerts(self):
		rows = [
			{
				"name": "AIR-1",
				"job_type": "Air Shipment",
				"owner": "alice@example.com",
				"job_status": "Completed",
				"wip_amount": 25,
				"customer": "Acme",
				"flags": classify_job({"job_status": "Completed", "wip_amount": 25}),
			},
			{
				"name": "SEA-1",
				"job_type": "Sea Shipment",
				"owner": "bob@example.com",
				"job_status": "Submitted",
				"estimated_revenue": 300,
				"wip_amount": 0,
				"flags": classify_job({"job_status": "Submitted", "estimated_revenue": 300, "wip_amount": 0}),
			},
		]
		labels = {"alice@example.com": "Alice", "bob@example.com": "Bob"}
		work, extra = job_work_rows(rows, labels)
		self.assertEqual(extra, 0)
		self.assertEqual(work[0]["name"], "AIR-1")
		self.assertTrue(work[0]["closed_open_balance"])
		self.assertEqual(len(attention_rows(work)), 2)
		self.assertEqual(len(exception_rows(work)), 2)
		users = job_user_workload(rows, labels)
		self.assertEqual(users[0]["overdue"], 1)
		summary, items = merge_alert_items(job_alerts(rows))
		self.assertGreaterEqual(summary["danger"], 1)
		self.assertGreaterEqual(summary["warning"], 1)
		self.assertTrue(items)
