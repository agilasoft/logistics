# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from logistics.special_projects.special_project_operations_dashboard import (
	attention_rows,
	build_site_markers,
	classify_project,
	count_programme_kpis,
	count_sla_kpis,
	event_clock_alerts,
	merge_alert_items,
	pipeline_counts,
	project_user_workload,
	sla_alerts,
	sla_by_project,
	special_project_work_rows,
)


class TestSpecialProjectOperationsDashboardHelpers(FrappeTestCase):
	def test_classify_upcoming_live_overdue_partition_flags(self):
		today = getdate("2026-08-18")
		upcoming = classify_project(
			{"status": "Planning", "planned_start": "2026-09-01", "planned_end": "2026-09-15"},
			today_date=today,
		)
		self.assertTrue(upcoming["active"])
		self.assertTrue(upcoming["upcoming"])
		self.assertFalse(upcoming["live"])
		self.assertFalse(upcoming["overdue"])
		self.assertFalse(upcoming["start_due"])

		soon = classify_project(
			{"status": "Planning", "planned_start": "2026-08-22", "planned_end": "2026-09-01"},
			today_date=today,
		)
		self.assertTrue(soon["upcoming"])
		self.assertTrue(soon["start_due"])

		live = classify_project(
			{
				"status": "In Progress",
				"planned_start": "2026-08-10",
				"planned_end": "2026-08-20",
			},
			today_date=today,
		)
		self.assertTrue(live["live"])
		self.assertFalse(live["upcoming"])
		self.assertFalse(live["overdue"])

		overdue = classify_project(
			{"status": "Draft", "planned_start": "2026-08-01", "planned_end": "2026-08-10"},
			today_date=today,
		)
		self.assertTrue(overdue["overdue"])
		self.assertEqual(overdue["severity"], "overdue")

		scoping_overdue = classify_project(
			{"status": "Scoping", "planned_start": "2026-08-01"},
			today_date=today,
		)
		self.assertTrue(scoping_overdue["overdue"])

		done = classify_project({"status": "Completed", "planned_start": "2026-08-01"}, today_date=today)
		self.assertFalse(done["active"])

	def test_kpis_do_not_count_completed(self):
		today = getdate("2026-08-18")
		rows = [
			{"name": "A", "status": "Planning", "planned_start": "2026-09-01"},
			{"name": "B", "status": "In Progress", "planned_start": "2026-08-10", "planned_end": "2026-08-20"},
			{"name": "C", "status": "Draft", "planned_start": "2026-08-01"},
			{"name": "D", "status": "Completed", "planned_start": "2026-08-01"},
			{"name": "E", "status": "Cancelled", "planned_start": "2026-09-01"},
		]
		kpis = count_programme_kpis(rows, today_date=today)
		self.assertEqual(kpis["active"], 3)
		self.assertEqual(kpis["upcoming"], 1)
		self.assertEqual(kpis["live"], 1)
		self.assertEqual(kpis["overdue"], 1)

	def test_sla_kpis_and_by_project(self):
		tasks = [
			{"name": "J1", "special_project": "P1", "status": "In Progress", "sla_status": "Breached"},
			{"name": "J2", "special_project": "P1", "status": "Planned", "sla_status": "At Risk"},
			{"name": "J3", "special_project": "P2", "status": "Completed", "sla_status": "Breached"},
			{"name": "J4", "special_project": "P2", "status": "Planned", "sla_status": "On Track"},
		]
		self.assertEqual(count_sla_kpis(tasks), {"sla_at_risk": 1, "sla_breached": 1})
		by_p = sla_by_project(tasks)
		self.assertEqual(by_p["P1"]["breached"], 1)
		self.assertEqual(by_p["P1"]["at_risk"], 1)
		self.assertNotIn("P2", by_p)

	def test_site_markers_skip_missing_coords_and_paint_overdue_red(self):
		today = getdate("2026-08-18")
		rows = [
			{
				"name": "P-LIVE",
				"project_name": "Plant Turnaround",
				"status": "In Progress",
				"lifecycle_stage": "Execution",
				"planned_start": "2026-08-10",
				"planned_end": "2026-08-20",
			},
			{
				"name": "P-OVER",
				"project_name": "Late Scope",
				"status": "Draft",
				"lifecycle_stage": "Scoping",
				"planned_start": "2026-08-01",
			},
			{
				"name": "P-NONE",
				"status": "Planning",
				"planned_start": "2026-09-01",
			},
		]
		markers = build_site_markers(
			rows,
			sla_map={"P-LIVE": {"at_risk": 0, "breached": 2}},
			job_counts={"P-LIVE": 4},
			site_coords={
				"P-LIVE": {"lat": 14.55, "lon": 121.02, "site": "ADDR-1"},
				"P-OVER": {"lat": 14.60, "lon": 121.05, "site": "ADDR-2"},
			},
			today_date=today,
		)
		self.assertEqual(len(markers), 2)
		by_lat = {round(m["lat"], 2): m for m in markers}
		self.assertEqual(by_lat[14.55]["severity"], "overdue")
		self.assertEqual(by_lat[14.55]["projects"][0]["job_count"], 4)
		self.assertEqual(by_lat[14.55]["projects"][0]["sla_breached"], 2)
		self.assertEqual(by_lat[14.60]["severity"], "overdue")

	def test_alerts_prepend_clock_then_sla(self):
		today = getdate("2026-08-18")
		clock = event_clock_alerts(
			[{"name": "P1", "project_name": "Late", "status": "Draft", "planned_start": "2026-07-01"}],
			today_date=today,
		)
		sla = sla_alerts(
			[{"name": "SPJ-1", "status": "In Progress", "sla_status": "At Risk", "sla_target_date": "2026-08-19"}],
			"Project Job",
		)
		summary, items = merge_alert_items(clock, sla)
		self.assertGreaterEqual(summary["danger"], 1)
		self.assertGreaterEqual(summary["warning"], 1)
		self.assertEqual(items[0]["doctype"], "Special Project")
		self.assertEqual(items[1]["doctype"], "Project Job")

	def test_pipeline_skips_closed(self):
		rows = [
			{"status": "Planning", "lifecycle_stage": "Scoping"},
			{"status": "Planning", "lifecycle_stage": "Scoping"},
			{"status": "Completed", "lifecycle_stage": "Closeout"},
		]
		pipe = pipeline_counts(rows)
		self.assertEqual(pipe, [{"lifecycle_stage": "Scoping", "program_count": 2}])

	def test_project_work_rows_and_user_workload(self):
		today = getdate("2026-08-18")
		rows = [
			{
				"name": "P1",
				"project_name": "Late Site",
				"status": "Draft",
				"lifecycle_stage": "Scoping",
				"planned_start": "2026-07-01",
				"owner": "u1",
				"customer": "Acme",
			},
			{
				"name": "P2",
				"project_name": "Live Site",
				"status": "In Progress",
				"lifecycle_stage": "Delivery",
				"planned_start": "2026-08-10",
				"planned_end": "2026-08-20",
				"owner": "u2",
			},
		]
		labels = {"u1": "Alice", "u2": "Bob"}
		work, truncated = special_project_work_rows(
			rows, {"P2": {"at_risk": 1, "breached": 0}}, {"P2": 4}, labels, today_date=today
		)
		self.assertEqual(truncated, 0)
		self.assertEqual(work[0]["name"], "P1")
		self.assertEqual(work[0]["severity"], "overdue")
		self.assertEqual(work[0]["owner_label"], "Alice")
		self.assertEqual(work[1]["job_count"], 4)
		self.assertEqual(work[1]["severity"], "start_due")
		self.assertEqual(attention_rows(work)[0]["name"], "P1")
		by = {r["owner"]: r for r in project_user_workload(work)}
		self.assertEqual(by["u1"]["overdue"], 1)
		self.assertEqual(by["u2"]["live"], 1)
		self.assertEqual(by["u2"]["sla_at_risk"], 1)
