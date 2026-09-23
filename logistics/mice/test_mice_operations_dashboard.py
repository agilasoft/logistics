# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate

from logistics.mice.mice_operations_dashboard import (
	attention_rows,
	build_venue_markers,
	classify_project,
	count_programme_kpis,
	count_sla_kpis,
	event_clock_alerts,
	merge_alert_items,
	pipeline_counts,
	programme_work_rows,
	project_user_workload,
	sla_alerts,
	sla_by_project,
)


class TestMiceOperationsDashboardHelpers(FrappeTestCase):
	def test_classify_upcoming_live_overdue_partition_flags(self):
		today = getdate("2026-08-18")
		upcoming = classify_project(
			{"status": "Planning", "show_open_date": "2026-09-01", "move_in_date": "2026-08-22"},
			today_date=today,
		)
		self.assertTrue(upcoming["active"])
		self.assertTrue(upcoming["upcoming"])
		self.assertFalse(upcoming["live"])
		self.assertFalse(upcoming["overdue"])
		self.assertTrue(upcoming["move_in_due"])

		live = classify_project(
			{
				"status": "In Progress",
				"show_open_date": "2026-08-10",
				"show_close_date": "2026-08-20",
			},
			today_date=today,
		)
		self.assertTrue(live["live"])
		self.assertFalse(live["upcoming"])
		self.assertFalse(live["overdue"])

		overdue = classify_project(
			{"status": "Draft", "show_open_date": "2026-08-01", "move_in_date": "2026-07-28"},
			today_date=today,
		)
		self.assertTrue(overdue["overdue"])
		self.assertEqual(overdue["severity"], "overdue")

		done = classify_project({"status": "Completed", "show_open_date": "2026-08-01"}, today_date=today)
		self.assertFalse(done["active"])

	def test_kpis_do_not_count_completed(self):
		today = getdate("2026-08-18")
		rows = [
			{"name": "A", "status": "Planning", "show_open_date": "2026-09-01"},
			{"name": "B", "status": "In Progress", "show_open_date": "2026-08-10", "show_close_date": "2026-08-20"},
			{"name": "C", "status": "Draft", "show_open_date": "2026-08-01", "move_in_date": "2026-07-01"},
			{"name": "D", "status": "Completed", "show_open_date": "2026-08-01"},
			{"name": "E", "status": "Cancelled", "show_open_date": "2026-09-01"},
		]
		kpis = count_programme_kpis(rows, today_date=today)
		self.assertEqual(kpis["active"], 3)
		self.assertEqual(kpis["upcoming"], 1)
		self.assertEqual(kpis["live"], 1)
		self.assertEqual(kpis["overdue"], 1)

	def test_sla_kpis_and_by_project(self):
		tasks = [
			{"name": "O1", "exhibit": "P1", "status": "In Progress", "sla_status": "Breached"},
			{"name": "O2", "exhibit": "P1", "status": "Confirmed", "sla_status": "At Risk"},
			{"name": "J1", "exhibit": "P2", "status": "Completed", "sla_status": "Breached"},
			{"name": "J2", "exhibit": "P2", "status": "Planned", "sla_status": "On Track"},
		]
		self.assertEqual(count_sla_kpis(tasks), {"sla_at_risk": 1, "sla_breached": 1})
		by_p = sla_by_project(tasks)
		self.assertEqual(by_p["P1"]["breached"], 1)
		self.assertEqual(by_p["P1"]["at_risk"], 1)
		self.assertNotIn("P2", by_p)

	def test_venue_markers_skip_missing_coords_and_paint_overdue_red(self):
		today = getdate("2026-08-18")
		rows = [
			{
				"name": "P-LIVE",
				"project_name": "Tokyo Show",
				"status": "In Progress",
				"lifecycle_stage": "Show",
				"show_open_date": "2026-08-10",
				"show_close_date": "2026-08-20",
				"move_in_date": "2026-08-08",
				"venue_latitude": 35.68,
				"venue_longitude": 139.76,
			},
			{
				"name": "P-OVER",
				"project_name": "Osaka Late",
				"status": "Draft",
				"lifecycle_stage": "Pre-Show",
				"show_open_date": "2026-08-01",
				"move_in_date": "2026-07-20",
				"venue_latitude": 34.69,
				"venue_longitude": 135.50,
			},
			{
				"name": "P-NONE",
				"status": "Planning",
				"show_open_date": "2026-09-01",
				"venue_latitude": None,
				"venue_longitude": None,
			},
		]
		markers = build_venue_markers(
			rows,
			sla_map={"P-LIVE": {"at_risk": 0, "breached": 2}},
			docket_counts={"P-LIVE": 4},
			today_date=today,
		)
		self.assertEqual(len(markers), 2)
		by_lat = {round(m["lat"], 2): m for m in markers}
		self.assertEqual(by_lat[35.68]["severity"], "overdue")
		self.assertEqual(by_lat[35.68]["projects"][0]["docket_count"], 4)
		self.assertEqual(by_lat[35.68]["projects"][0]["sla_breached"], 2)
		self.assertEqual(by_lat[34.69]["severity"], "overdue")

	def test_alerts_prepend_clock_then_sla(self):
		today = getdate("2026-08-18")
		clock = event_clock_alerts(
			[{"name": "P1", "project_name": "Late", "status": "Draft", "move_in_date": "2026-07-01"}],
			today_date=today,
		)
		sla = sla_alerts(
			[{"name": "EPO-1", "status": "In Progress", "sla_status": "At Risk", "sla_target_date": "2026-08-19"}],
			"MICE Order",
		)
		summary, items = merge_alert_items(clock, sla)
		self.assertGreaterEqual(summary["danger"], 1)
		self.assertGreaterEqual(summary["warning"], 1)
		self.assertEqual(items[0]["doctype"], "MICE Project")
		self.assertEqual(items[1]["doctype"], "MICE Order")

	def test_pipeline_skips_closed(self):
		rows = [
			{"status": "Planning", "lifecycle_stage": "Pre-Show"},
			{"status": "Planning", "lifecycle_stage": "Pre-Show"},
			{"status": "Completed", "lifecycle_stage": "Post-Show"},
		]
		pipe = pipeline_counts(rows)
		self.assertEqual(pipe, [{"lifecycle_stage": "Pre-Show", "program_count": 2}])

	def test_programme_work_rows_and_user_workload(self):
		today = getdate("2026-08-18")
		rows = [
			{
				"name": "P1",
				"project_name": "Overdue Show",
				"status": "Draft",
				"lifecycle_stage": "Pre-Show",
				"show_open_date": "2026-08-01",
				"move_in_date": "2026-07-01",
				"owner": "u1",
				"organizer": "Org",
			},
			{
				"name": "P2",
				"project_name": "Live Show",
				"status": "In Progress",
				"lifecycle_stage": "Show",
				"show_open_date": "2026-08-10",
				"show_close_date": "2026-08-20",
				"owner": "u2",
			},
		]
		labels = {"u1": "Alice", "u2": "Bob"}
		work, truncated = programme_work_rows(
			rows, {"P2": {"at_risk": 1, "breached": 0}}, {}, {"P2": 3}, labels, today_date=today
		)
		self.assertEqual(truncated, 0)
		self.assertEqual(work[0]["name"], "P1")
		self.assertEqual(work[0]["severity"], "overdue")
		self.assertEqual(work[0]["owner_label"], "Alice")
		self.assertEqual(work[1]["task_count"], 3)
		self.assertEqual(work[1]["severity"], "move_in_due")
		self.assertEqual(attention_rows(work)[0]["name"], "P1")
		by = {r["owner"]: r for r in project_user_workload(work)}
		self.assertEqual(by["u1"]["overdue"], 1)
		self.assertEqual(by["u2"]["live"], 1)
		self.assertEqual(by["u2"]["sla_at_risk"], 1)
