# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from logistics.warehousing.warehouse_operations_dashboard import (
	attention_rows,
	classify_job,
	classify_open_order,
	count_job_kpis,
	count_sla_kpis,
	job_alerts,
	job_user_workload,
	job_work_rows,
	merge_alert_items,
	open_order_alerts,
	pipeline_counts,
	status_mix,
)


class TestWarehouseOperationsDashboardHelpers(FrappeTestCase):
	def test_classify_draft_is_active_not_live(self):
		draft = classify_job({"job_status": "Draft", "sla_status": "Not Applicable"})
		self.assertTrue(draft["active"])
		self.assertFalse(draft["live"])
		self.assertEqual(draft["severity"], "active")

		live = classify_job({"job_status": "In Progress", "sla_status": "On Track"})
		self.assertTrue(live["live"])
		self.assertEqual(live["severity"], "live")

		overdue = classify_job({"job_status": "Submitted", "sla_status": "Breached"})
		self.assertTrue(overdue["overdue"])
		self.assertEqual(overdue["severity"], "overdue")

		closed = classify_job({"job_status": "Completed", "sla_status": "Breached"})
		self.assertFalse(closed["active"])
		self.assertFalse(closed["overdue"])

	def test_kpis_and_pipeline_by_type(self):
		rows = [
			{"job_status": "Draft", "type": "Putaway", "flags": classify_job({"job_status": "Draft"})},
			{
				"job_status": "In Progress",
				"type": "Pick",
				"flags": classify_job({"job_status": "In Progress", "sla_status": "Breached"}),
			},
			{
				"job_status": "Completed",
				"type": "Putaway",
				"flags": classify_job({"job_status": "Completed"}),
			},
		]
		kpis = count_job_kpis(rows)
		self.assertEqual(kpis["jobs"], 3)
		self.assertEqual(kpis["active"], 2)
		self.assertEqual(kpis["live"], 1)
		self.assertEqual(kpis["overdue"], 1)
		pipe = pipeline_counts(rows)
		by = {p["lifecycle_stage"]: p["program_count"] for p in pipe}
		self.assertEqual(by["Putaway"], 1)
		self.assertEqual(by["Pick"], 1)
		self.assertEqual(status_mix(rows)["Draft"], 1)

	def test_sla_kpis_skip_closed(self):
		jobs = [
			{"job_status": "In Progress", "sla_status": "At Risk"},
			{"job_status": "Submitted", "sla_status": "Breached"},
			{"job_status": "Completed", "sla_status": "Breached"},
		]
		self.assertEqual(count_sla_kpis(jobs), {"sla_at_risk": 1, "sla_breached": 1})

	def test_work_rows_and_user_workload(self):
		rows = [
			{
				"name": "WJ-1",
				"type": "Putaway",
				"job_status": "Submitted",
				"sla_status": "Breached",
				"owner": "u1",
				"customer": "Acme",
				"flags": classify_job({"job_status": "Submitted", "sla_status": "Breached"}),
			},
			{
				"name": "WJ-2",
				"type": "Pick",
				"job_status": "Draft",
				"owner": "u2",
				"flags": classify_job({"job_status": "Draft"}),
			},
		]
		labels = {"u1": "Alice", "u2": "Bob"}
		work, truncated = job_work_rows(rows, labels)
		self.assertEqual(truncated, 0)
		self.assertEqual(work[0]["name"], "WJ-1")
		self.assertEqual(work[0]["severity"], "overdue")
		self.assertEqual(work[0]["owner_label"], "Alice")
		self.assertEqual(attention_rows(work)[0]["name"], "WJ-1")
		by = {r["owner"]: r for r in job_user_workload(rows, labels)}
		self.assertEqual(by["u1"]["overdue"], 1)
		self.assertEqual(by["u2"]["jobs"], 1)

	def test_open_order_due_flags_and_alerts(self):
		today = getdate("2026-08-18")
		past = classify_open_order({"due_date": "2026-08-01"}, today_date=today)
		self.assertTrue(past["overdue"])
		self.assertEqual(past["severity"], "overdue")
		due_today = classify_open_order({"due_date": "2026-08-18"}, today_date=today)
		self.assertTrue(due_today["due_today"])
		future = classify_open_order({"due_date": "2026-08-20"}, today_date=today)
		self.assertFalse(future["overdue"])

		alerts = open_order_alerts(
			[
				{"name": "WIO-1", "doctype": "Inbound Order", "due_date": "2026-08-01"},
				{"name": "WRO-1", "doctype": "Release Order", "due_date": "2026-08-18"},
			],
			today_date=today,
		)
		jobs = job_alerts(
			[{"name": "WJ-9", "type": "Pick", "flags": classify_job({"job_status": "Submitted", "sla_status": "At Risk"}), "sla_target_date": "2026-08-19"}]
		)
		summary, items = merge_alert_items(job_alerts([{"name": "WJ-8", "type": "Putaway", "flags": classify_job({"job_status": "Submitted", "sla_status": "Breached"}), "sla_target_date": "2026-08-01"}]), alerts, jobs)
		self.assertGreaterEqual(summary["danger"], 2)
		self.assertGreaterEqual(summary["warning"], 1)
		self.assertEqual(items[0]["doctype"], "Warehouse Job")
