# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
import os
from datetime import date, datetime

from frappe.tests.utils import FrappeTestCase

from logistics.time_sensitive.report.time_sensitive_case_type_performance import (
	time_sensitive_case_type_performance,
)
from logistics.time_sensitive.report.time_sensitive_coordinator_workload import (
	time_sensitive_coordinator_workload,
)
from logistics.time_sensitive.report.time_sensitive_escalation_coverage import (
	time_sensitive_escalation_coverage,
)
from logistics.time_sensitive.report.time_sensitive_escalation_watch import (
	time_sensitive_escalation_watch,
)
from logistics.time_sensitive.report.time_sensitive_service_mode_mix import (
	time_sensitive_service_mode_mix,
)
from logistics.time_sensitive.report.time_sensitive_sla_aging import time_sensitive_sla_aging
from logistics.time_sensitive.ts_reports import (
	SERVICE_MODES,
	case_type_performance_rows,
	coordinator_workload_rows,
	deadline_age_bucket,
	escalation_coverage_rows,
	escalation_reason,
	escalation_watch_rows,
	remaining_hours,
	service_mode_rows,
	sla_aging_rows,
)


def _workspace_sections():
	path = os.path.join(
		os.path.dirname(__file__), "workspace", "time_sensitive", "time_sensitive.json"
	)
	with open(path, encoding="utf-8") as handle:
		links = json.load(handle)["links"]
	sections = {}
	current = None
	for link in links:
		if link.get("type") == "Card Break":
			current = link["label"]
			sections[current] = []
		elif current:
			sections[current].append(link["label"])
	return sections


def _sidebar_sections():
	path = os.path.join(os.path.dirname(__file__), "sidebar", "time_sensitive", "time_sensitive.json")
	with open(path, encoding="utf-8") as handle:
		items = json.load(handle)["items"]
	sections = {}
	current = None
	for item in items:
		if item.get("type") == "Section Break":
			current = item["label"]
			sections[current] = []
		elif current and item.get("type") == "Link":
			sections[current].append(item["label"])
	return sections


class TestTimeSensitiveReportHelpers(FrappeTestCase):
	def test_deadline_age_bucket(self):
		as_on = date(2026, 10, 8)
		self.assertEqual(deadline_age_bucket(None, as_on), "No deadline")
		self.assertEqual(deadline_age_bucket("", as_on), "No deadline")
		self.assertEqual(deadline_age_bucket("2026-10-07 18:00:00", as_on), "Overdue")
		self.assertEqual(deadline_age_bucket("2026-10-08 23:00:00", as_on), "Due today")
		self.assertEqual(deadline_age_bucket("2026-10-09", as_on), "1-3 days")
		self.assertEqual(deadline_age_bucket("2026-10-11", as_on), "1-3 days")
		self.assertEqual(deadline_age_bucket("2026-10-12", as_on), "4-7 days")
		self.assertEqual(deadline_age_bucket("2026-10-15", as_on), "4-7 days")
		self.assertEqual(deadline_age_bucket("2026-10-16", as_on), "8+ days")

	def test_remaining_hours(self):
		now = datetime(2026, 10, 8, 12, 0, 0)
		self.assertIsNone(remaining_hours(None, now))
		self.assertEqual(remaining_hours("2026-10-08 15:30:00", now), 3)
		self.assertEqual(remaining_hours("2026-10-08 10:00:00", now), -2)

	def test_sla_aging_sorts_overdue_first(self):
		as_on = date(2026, 10, 8)
		rows = sla_aging_rows(
			[
				{"name": "LATER", "critical_deadline": "2026-10-20 00:00:00"},
				{"name": "LATE", "critical_deadline": "2026-10-01 00:00:00"},
				{"name": "NONE", "critical_deadline": None},
			],
			as_on,
			datetime(2026, 10, 8, 12, 0, 0),
		)
		self.assertEqual([row["name"] for row in rows], ["LATE", "LATER", "NONE"])
		self.assertEqual(rows[0]["age_bucket"], "Overdue")
		self.assertLess(rows[0]["remaining_hours"], 0)

	def test_coordinator_workload_skips_closed(self):
		rows = coordinator_workload_rows(
			[
				{"coordinator": "ada@example.com", "status": "In Execution", "sla_status": "Breached", "severity": "Critical"},
				{"coordinator": "ada@example.com", "status": "On Hold", "sla_status": "At Risk", "severity": "High"},
				{"coordinator": "", "status": "Triage", "sla_status": "On Track", "severity": "Normal"},
				{"coordinator": "ada@example.com", "status": "Closed", "sla_status": "Breached", "severity": "Critical"},
				{"coordinator": "ada@example.com", "status": "Cancelled", "sla_status": "Breached", "severity": "Critical"},
			]
		)
		by_label = {row["coordinator_label"]: row for row in rows}
		self.assertEqual(by_label["ada@example.com"]["open_cases"], 2)
		self.assertEqual(by_label["ada@example.com"]["ongoing"], 2)
		self.assertEqual(by_label["ada@example.com"]["overdue"], 1)
		self.assertEqual(by_label["ada@example.com"]["nearing_due"], 1)
		self.assertEqual(by_label["ada@example.com"]["on_hold"], 1)
		self.assertEqual(by_label["ada@example.com"]["critical"], 1)
		self.assertEqual(by_label["Unassigned"]["open_cases"], 1)
		self.assertEqual(rows[0]["coordinator_label"], "ada@example.com")

	def test_escalation_reason_priority(self):
		now = datetime(2026, 10, 8, 12, 0, 0)
		self.assertIsNone(
			escalation_reason({"status": "Closed", "sla_status": "Breached"}, now)
		)
		self.assertEqual(
			escalation_reason(
				{"status": "In Execution", "sla_status": "Breached", "next_checkpoint": "2026-10-01 00:00:00"},
				now,
			),
			"Deadline breach",
		)
		self.assertEqual(
			escalation_reason(
				{"status": "In Execution", "sla_status": "On Track", "next_checkpoint": "2026-10-07 00:00:00"},
				now,
			),
			"Checkpoint missed",
		)
		self.assertEqual(
			escalation_reason(
				{
					"status": "Activated",
					"sla_status": "On Track",
					"acknowledged_on": None,
					"response_due_on": "2026-10-08 09:00:00",
				},
				now,
			),
			"Unacknowledged",
		)
		self.assertEqual(
			escalation_reason({"status": "Triage", "sla_status": "At Risk"}, now),
			"At risk",
		)
		self.assertIsNone(
			escalation_reason({"status": "In Execution", "sla_status": "On Track"}, now)
		)

	def test_escalation_watch_filters_quiet_cases(self):
		now = datetime(2026, 10, 8, 12, 0, 0)
		rows = escalation_watch_rows(
			[
				{"name": "OK", "status": "In Execution", "sla_status": "On Track"},
				{"name": "LATE", "status": "In Execution", "sla_status": "Breached", "critical_deadline": "2026-10-01"},
				{"name": "RISK", "status": "Triage", "sla_status": "At Risk", "critical_deadline": "2026-10-09"},
			],
			now,
		)
		self.assertEqual([row["name"] for row in rows], ["LATE", "RISK"])

	def test_case_type_performance(self):
		rows = case_type_performance_rows(
			[
				{"case_type": "AOG", "case_type_name": "Aircraft on Ground", "status": "In Execution", "sla_status": "Breached"},
				{"case_type": "AOG", "case_type_name": "Aircraft on Ground", "status": "Closed", "sla_status": "Completed"},
				{"case_type": "OTHER", "case_type_name": "Other", "status": "Cancelled", "sla_status": "Breached"},
			]
		)
		by_code = {row["case_type"]: row for row in rows}
		self.assertEqual(by_code["AOG"]["cases"], 2)
		self.assertEqual(by_code["AOG"]["ongoing"], 1)
		self.assertEqual(by_code["AOG"]["overdue"], 1)
		self.assertEqual(by_code["AOG"]["closed"], 1)
		self.assertEqual(by_code["OTHER"]["cancelled"], 1)
		self.assertEqual(by_code["OTHER"]["overdue"], 0)
		self.assertEqual(rows[0]["case_type"], "AOG")

	def test_escalation_coverage_uses_global_rules(self):
		rows = escalation_coverage_rows(
			[
				{"name": "AOG", "case_type_name": "Aircraft on Ground", "enabled": 1},
				{"name": "OTHER", "case_type_name": "Other", "enabled": 1},
			],
			[
				{"case_type": "AOG", "enabled": 1, "trigger_event": "Deadline Breach", "escalate_to_user": "lead@example.com"},
				{"case_type": "", "enabled": 1, "trigger_event": "At Risk", "escalate_to_role": "Time Sensitive Manager"},
				{"case_type": "OTHER", "enabled": 0, "trigger_event": "Activation", "escalate_to_role": "Time Sensitive Manager"},
			],
		)
		by_code = {row["case_type"]: row for row in rows}
		self.assertEqual(by_code["AOG"]["covered"], "Yes")
		self.assertEqual(by_code["AOG"]["enabled_rules"], 2)
		self.assertIn("Deadline Breach", by_code["AOG"]["triggers"])
		self.assertIn("At Risk", by_code["AOG"]["triggers"])
		self.assertEqual(by_code["OTHER"]["covered"], "Yes")
		self.assertEqual(by_code["OTHER"]["enabled_rules"], 1)
		self.assertEqual(by_code["OTHER"]["triggers"], "At Risk")

	def test_service_mode_rows_follow_workspace_order(self):
		rows = service_mode_rows({"Air Booking": {"documents": 2, "cases": 1}})
		self.assertEqual([row["service_mode"] for row in rows], [mode["service_mode"] for mode in SERVICE_MODES])
		self.assertEqual(rows[0]["documents"], 2)
		self.assertEqual(rows[0]["cases"], 1)
		self.assertEqual(rows[1]["documents"], 0)

	def test_execute_returns_columns_and_rows(self):
		modules = (
			time_sensitive_sla_aging,
			time_sensitive_coordinator_workload,
			time_sensitive_escalation_watch,
			time_sensitive_case_type_performance,
			time_sensitive_escalation_coverage,
			time_sensitive_service_mode_mix,
		)
		for module in modules:
			result = module.execute({})
			self.assertGreaterEqual(len(result), 2)
			columns, data = result[0], result[1]
			self.assertTrue(columns)
			self.assertIsInstance(data, list)
			self.assertTrue(all("fieldname" in column for column in columns))

	def test_sidebar_matches_workspace_sections(self):
		workspace = _workspace_sections()
		sidebar = _sidebar_sections()
		self.assertEqual(list(sidebar), ["Operations", "Setup", "Service Modes"])
		self.assertEqual(sidebar, workspace)
