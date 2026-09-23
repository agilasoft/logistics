# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import timedelta

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from logistics.time_sensitive.time_sensitive_operations_dashboard import (
	_count_sla_kpis,
	_parse_sla_filter,
	_sla_extra_filters,
	enrich_unloco_markers_with_sla,
	merge_sla_alerts,
	priority_clock_rows,
)


class TestTimeSensitiveOperationsDashboardHelpers(FrappeTestCase):
	def test_parse_sla_filter(self):
		self.assertEqual(_parse_sla_filter("alerts"), "alerts")
		self.assertEqual(_parse_sla_filter("BREACHED"), "breached")
		self.assertEqual(_parse_sla_filter("nope"), "all")
		self.assertEqual(_sla_extra_filters("alerts"), {"sla_status": ["in", ["At Risk", "Breached"]]})
		self.assertIsNone(_sla_extra_filters("all"))

	def test_kpi_counts_split_ongoing_nearing_due_overdue(self):
		rows = [
			{"name": "A", "status": "Activated", "sla_status": "On Track"},
			{"name": "B", "status": "In Execution", "sla_status": "At Risk"},
			{"name": "C", "status": "On Hold", "sla_status": "Breached"},
			{"name": "D", "status": "Delivered", "sla_status": "Completed"},
			{"name": "E", "status": "Closed", "sla_status": "Breached"},
		]
		kpis = _count_sla_kpis(rows)
		self.assertEqual(kpis["ongoing"], 3)
		self.assertEqual(kpis["nearing_due"], 1)
		self.assertEqual(kpis["overdue"], 1)
		self.assertEqual(kpis["on_track"], 1)
		self.assertEqual(kpis["on_hold"], 1)

	def test_draft_alerts_count_and_turn_existing_markers_red(self):
		from logistics.time_sensitive.time_sensitive_operations_dashboard import (
			_count_sla_kpis,
			append_missing_unloco_markers,
			enrich_unloco_markers_with_sla,
		)

		ongoing_rows = [
			{"name": "TSC-ON", "status": "Activated", "sla_status": "On Track", "origin": "JPKOB", "destination": "PHMNL"},
		]
		alert_rows = [
			{"name": "TSC-OVER", "status": "Draft", "sla_status": "Breached", "origin": "JPKOB", "destination": "PHMNL"},
			{"name": "TSC-SOON", "status": "Draft", "sla_status": "At Risk", "origin": None, "destination": None},
		]
		kpis = _count_sla_kpis(ongoing_rows, alert_rows=alert_rows)
		self.assertEqual(kpis["ongoing"], 1)
		self.assertEqual(kpis["on_track"], 1)
		self.assertEqual(kpis["overdue"], 1)
		self.assertEqual(kpis["nearing_due"], 1)

		markers = [
			{"unloco": "JPKOB", "lat": 34.7, "lon": 135.2, "import_count": 1, "export_count": 0, "domestic_count": 0},
			{"unloco": "PHMNL", "lat": 14.6, "lon": 121.0, "import_count": 0, "export_count": 1, "domestic_count": 0},
		]
		markers = append_missing_unloco_markers(
			markers, ongoing_rows + alert_rows, get_coords=lambda code: None
		)
		out = enrich_unloco_markers_with_sla(markers, ongoing_rows + alert_rows)
		by_code = {m["unloco"]: m for m in out}
		self.assertEqual(by_code["JPKOB"]["severity"], "overdue")
		self.assertEqual(by_code["JPKOB"]["overdue_count"], 1)
		self.assertEqual(by_code["PHMNL"]["severity"], "overdue")

	def test_append_missing_markers_adds_alert_ports(self):
		from logistics.time_sensitive.time_sensitive_operations_dashboard import append_missing_unloco_markers

		coords = {
			"SGSIN": {"lat": 1.26, "lon": 103.85},
			"USNYC": {"lat": 40.7, "lon": -74.0},
		}
		rows = [
			{"name": "TSC-NEW", "origin": "SGSIN", "destination": "USNYC", "sla_status": "Breached"},
		]
		out = append_missing_unloco_markers([], rows, get_coords=lambda c: coords.get(c))
		codes = {m["unloco"] for m in out}
		self.assertEqual(codes, {"SGSIN", "USNYC"})

	def test_markers_use_overdue_severity_for_red_alerts(self):
		markers = [
			{"unloco": "SGSIN", "lat": 1.26, "lon": 103.85, "import_count": 1, "export_count": 0, "domestic_count": 0},
			{"unloco": "USNYC", "lat": 40.7, "lon": -74.0, "import_count": 0, "export_count": 1, "domestic_count": 0},
		]
		rows = [
			{"origin": "SGSIN", "destination": "USNYC", "sla_status": "Breached", "status": "Activated"},
			{"origin": "USNYC", "destination": "", "sla_status": "At Risk", "status": "Activated"},
		]
		out = enrich_unloco_markers_with_sla(markers, rows)
		by_code = {m["unloco"]: m for m in out}
		self.assertEqual(by_code["SGSIN"]["severity"], "overdue")
		self.assertEqual(by_code["SGSIN"]["overdue_count"], 1)
		self.assertEqual(by_code["USNYC"]["severity"], "overdue")
		self.assertEqual(by_code["USNYC"]["overdue_count"], 1)
		self.assertEqual(by_code["USNYC"]["at_risk_count"], 1)

	def test_merge_sla_alerts_prepends_overdue_and_nearing_due(self):
		now = now_datetime()
		payload = {
			"alert_summary": {"danger": 0, "warning": 0, "info": 1},
			"alert_items": [{"level": "info", "msg": "doc", "shipment": "TSC-OLD"}],
		}
		rows = [
			{
				"name": "TSC-OVER",
				"case_title": "AOG engine",
				"status": "Activated",
				"sla_status": "Breached",
				"critical_deadline": now - timedelta(hours=2),
			},
			{
				"name": "TSC-SOON",
				"case_title": "Hot shot",
				"status": "In Execution",
				"sla_status": "At Risk",
				"critical_deadline": now + timedelta(hours=1),
			},
		]
		merge_sla_alerts(payload, rows)
		self.assertGreaterEqual(payload["alert_summary"]["danger"], 1)
		self.assertGreaterEqual(payload["alert_summary"]["warning"], 1)
		self.assertEqual(payload["alert_items"][0]["shipment"], "TSC-OVER")
		self.assertEqual(payload["alert_items"][0]["level"], "danger")
		self.assertIn("Overdue", payload["alert_items"][0]["msg"])
		self.assertEqual(payload["alert_items"][1]["shipment"], "TSC-SOON")
		self.assertEqual(payload["alert_items"][1]["level"], "warning")

	def test_priority_clock_rows_filters_and_orders(self):
		now = now_datetime()
		rows = [
			{
				"name": "TSC-LOW",
				"case_title": "Skip me",
				"priority": "Normal",
				"status": "Activated",
				"sla_status": "Breached",
				"critical_deadline": now - timedelta(hours=3),
				"origin": "SGSIN",
				"destination": "USNYC",
			},
			{
				"name": "TSC-SOON",
				"case_title": "Hot shot",
				"priority": "High",
				"status": "In Execution",
				"sla_status": "At Risk",
				"critical_deadline": now + timedelta(hours=1),
				"origin": "JPKOB",
				"destination": "PHMNL",
			},
			{
				"name": "TSC-OVER",
				"case_title": "AOG engine",
				"priority": "Urgent",
				"status": "Activated",
				"sla_status": "Breached",
				"critical_deadline": now - timedelta(hours=2),
				"origin": "SGSIN",
				"destination": "USNYC",
			},
			{
				"name": "TSC-DONE",
				"case_title": "Closed overdue",
				"priority": "Urgent",
				"status": "Closed",
				"sla_status": "Breached",
				"critical_deadline": now - timedelta(hours=1),
			},
		]
		out = priority_clock_rows(rows, now=now)
		self.assertEqual([r["name"] for r in out], ["TSC-OVER", "TSC-LOW", "TSC-SOON"])
		self.assertEqual(out[0]["severity"], "overdue")
		self.assertTrue(out[0]["clock"].startswith("OVERDUE"))
		self.assertEqual(out[1]["priority"], "Normal")
		self.assertEqual(out[2]["severity"], "at_risk")
		self.assertGreater(out[2]["remaining_seconds"], 0)
