# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Shared shaping for Time Sensitive script reports.

Workspace sections are Operations, Setup, and Service Modes. Report rows are
built here so each script report stays a thin ``execute`` wrapper.
"""

from __future__ import annotations

from datetime import date, datetime

import frappe
from frappe.utils import cint

AGING_BUCKETS = ("Overdue", "Due today", "1-3 days", "4-7 days", "8+ days", "No deadline")
ONGOING_STATUSES = ("Activated", "In Execution", "On Hold")
CLOSED_STATUSES = ("Closed", "Cancelled")
WATCH_SKIP_STATUSES = ("Delivered", "Closed", "Cancelled")

# Service Modes card on the Time Sensitive workspace, in the same order.
SERVICE_MODES = (
	{"service_mode": "Air Booking", "doctype": "Air Booking", "service_type": "Air"},
	{"service_mode": "Sea Booking", "doctype": "Sea Booking", "service_type": "Sea"},
	{"service_mode": "Transport Order", "doctype": "Transport Order", "service_type": "Transport"},
	{"service_mode": "Declaration Order", "doctype": "Declaration Order", "service_type": "Customs"},
	{"service_mode": "Inbound Order", "doctype": "Inbound Order", "service_type": "Warehousing"},
)

_CASE_COLUMNS = """
	name, case_title, case_type, case_type_name, customer, status, sla_status,
	severity, priority, critical_deadline, coordinator, escalation_contact,
	activated_on, acknowledged_on, next_checkpoint, response_due_on, company,
	sales_quote, billing_status, origin, destination
"""


def deadline_age_bucket(deadline, as_on):
	"""Bucket a critical deadline against a calendar day."""
	target = _as_date(deadline)
	anchor = _as_date(as_on)
	if not target or not anchor:
		return "No deadline"
	days = (target - anchor).days
	if days < 0:
		return "Overdue"
	if days == 0:
		return "Due today"
	if days <= 3:
		return "1-3 days"
	if days <= 7:
		return "4-7 days"
	return "8+ days"


def remaining_hours(deadline, now):
	"""Whole hours until the deadline. Negative when the deadline has passed."""
	target = _as_datetime(deadline)
	current = _as_datetime(now)
	if not target or not current:
		return None
	return int((target - current).total_seconds() // 3600)


def escalation_reason(case, now):
	"""Why an open case belongs on the escalation watch, or None."""
	status = (case.get("status") or "").strip()
	if status in WATCH_SKIP_STATUSES:
		return None
	sla = (case.get("sla_status") or "").strip()
	if sla == "Breached":
		return "Deadline breach"
	current = _as_datetime(now)
	checkpoint = _as_datetime(case.get("next_checkpoint"))
	if checkpoint and current and checkpoint < current and status in ONGOING_STATUSES:
		return "Checkpoint missed"
	due = _as_datetime(case.get("response_due_on"))
	if (
		status in ("Activated", "In Execution")
		and not case.get("acknowledged_on")
		and due
		and current
		and due < current
	):
		return "Unacknowledged"
	if sla == "At Risk":
		return "At risk"
	return None


def sla_aging_rows(cases, as_on, now=None):
	now = now or as_on
	rows = []
	for case in cases or []:
		row = dict(case)
		row["age_bucket"] = deadline_age_bucket(case.get("critical_deadline"), as_on)
		row["remaining_hours"] = remaining_hours(case.get("critical_deadline"), now)
		rows.append(row)
	order = {name: index for index, name in enumerate(AGING_BUCKETS)}
	rows.sort(
		key=lambda row: (
			order.get(row.get("age_bucket"), 99),
			str(row.get("critical_deadline") or ""),
			row.get("name") or "",
		)
	)
	return rows


def coordinator_workload_rows(cases):
	"""Open-case load per coordinator. Closed and cancelled cases are omitted."""
	buckets = {}
	for case in cases or []:
		status = (case.get("status") or "").strip()
		if status in CLOSED_STATUSES:
			continue
		key = (case.get("coordinator") or "").strip()
		row = buckets.setdefault(
			key,
			{
				"coordinator": key or None,
				"coordinator_label": key or "Unassigned",
				"open_cases": 0,
				"ongoing": 0,
				"nearing_due": 0,
				"overdue": 0,
				"on_hold": 0,
				"critical": 0,
			},
		)
		row["open_cases"] += 1
		if status in ONGOING_STATUSES:
			row["ongoing"] += 1
		if status == "On Hold":
			row["on_hold"] += 1
		sla = (case.get("sla_status") or "").strip()
		if sla == "At Risk":
			row["nearing_due"] += 1
		elif sla == "Breached":
			row["overdue"] += 1
		if (case.get("severity") or "").strip() == "Critical":
			row["critical"] += 1
	rows = list(buckets.values())
	rows.sort(
		key=lambda row: (
			-row["overdue"],
			-row["nearing_due"],
			-row["open_cases"],
			row["coordinator_label"],
		)
	)
	return rows


def escalation_watch_rows(cases, now):
	rows = []
	for case in cases or []:
		reason = escalation_reason(case, now)
		if not reason:
			continue
		row = dict(case)
		row["watch_reason"] = reason
		row["remaining_hours"] = remaining_hours(case.get("critical_deadline"), now)
		rows.append(row)
	rank = {
		"Deadline breach": 0,
		"Checkpoint missed": 1,
		"Unacknowledged": 2,
		"At risk": 3,
	}
	rows.sort(
		key=lambda row: (
			rank.get(row.get("watch_reason"), 9),
			str(row.get("critical_deadline") or ""),
			row.get("name") or "",
		)
	)
	return rows


def case_type_performance_rows(cases):
	buckets = {}
	for case in cases or []:
		code = (case.get("case_type") or "").strip()
		row = buckets.setdefault(
			code,
			{
				"case_type": code or None,
				"case_type_name": case.get("case_type_name") or code or "Unspecified",
				"cases": 0,
				"ongoing": 0,
				"nearing_due": 0,
				"overdue": 0,
				"closed": 0,
				"cancelled": 0,
			},
		)
		status = (case.get("status") or "").strip()
		row["cases"] += 1
		if status in ONGOING_STATUSES:
			row["ongoing"] += 1
		if status == "Closed":
			row["closed"] += 1
		elif status == "Cancelled":
			row["cancelled"] += 1
		sla = (case.get("sla_status") or "").strip()
		if sla == "At Risk" and status not in CLOSED_STATUSES:
			row["nearing_due"] += 1
		elif sla == "Breached" and status not in CLOSED_STATUSES:
			row["overdue"] += 1
	rows = list(buckets.values())
	rows.sort(key=lambda row: (-row["overdue"], -row["nearing_due"], -row["cases"], row["case_type_name"]))
	return rows


def escalation_coverage_rows(case_types, rules):
	"""One row per case type. A rule with no case type covers every type."""
	typed = {}
	global_rules = []
	for rule in rules or []:
		case_type = (rule.get("case_type") or "").strip()
		if case_type:
			typed.setdefault(case_type, []).append(rule)
		else:
			global_rules.append(rule)

	rows = []
	for case_type in case_types or []:
		code = case_type.get("name")
		own = typed.get(code, [])
		enabled = [rule for rule in own + global_rules if cint(rule.get("enabled"))]
		triggers = sorted({(rule.get("trigger_event") or "").strip() for rule in enabled if rule.get("trigger_event")})
		targets = []
		for rule in enabled:
			target = (rule.get("escalate_to_user") or rule.get("escalate_to_role") or "").strip()
			if target and target not in targets:
				targets.append(target)
		rows.append(
			{
				"case_type": code,
				"case_type_name": case_type.get("case_type_name") or code,
				"type_enabled": "Yes" if cint(case_type.get("enabled")) else "No",
				"enabled_rules": len(enabled),
				"triggers": ", ".join(triggers),
				"escalate_to": ", ".join(targets),
				"covered": "Yes" if enabled else "No",
			}
		)
	rows.sort(key=lambda row: (row["covered"] == "Yes", (row.get("case_type_name") or "").lower()))
	return rows


def service_mode_rows(counts):
	"""Always emit the five workspace service modes, even when the count is zero."""
	rows = []
	for mode in SERVICE_MODES:
		found = (counts or {}).get(mode["doctype"]) or {}
		rows.append(
			{
				"service_mode": mode["service_mode"],
				"doctype": mode["doctype"],
				"service_type": mode["service_type"],
				"documents": int(found.get("documents") or 0),
				"cases": int(found.get("cases") or 0),
			}
		)
	return rows


def fetch_cases(filters=None):
	filters = filters or {}
	conds = ["docstatus < 2"]
	values = {}
	for key in ("status", "sla_status", "case_type", "customer", "coordinator", "company"):
		if filters.get(key):
			conds.append(f"{key} = %({key})s")
			values[key] = filters.get(key)
	if cint(filters.get("open_only")):
		conds.append("status not in ('Closed', 'Cancelled')")
	return frappe.db.sql(
		f"""
		SELECT {_CASE_COLUMNS}
		FROM `tabTime Sensitive Case`
		WHERE {" AND ".join(conds)}
		ORDER BY
			FIELD(sla_status, 'Breached', 'At Risk', 'On Track', 'Completed'),
			critical_deadline ASC
		LIMIT 2000
		""",
		values,
		as_dict=True,
	)


def fetch_case_types():
	return frappe.db.sql(
		"""
		SELECT name, case_type_name, enabled
		FROM `tabTime Sensitive Case Type`
		ORDER BY case_type_name ASC
		""",
		as_dict=True,
	)


def fetch_escalation_rules():
	return frappe.db.sql(
		"""
		SELECT name, rule_name, case_type, enabled, trigger_event,
		       escalate_to_role, escalate_to_user, severity
		FROM `tabTime Sensitive Escalation Rule`
		WHERE docstatus < 2
		""",
		as_dict=True,
	)


def count_service_modes(filters=None):
	"""Count time-sensitive documents for each workspace service mode."""
	filters = filters or {}
	case_names = None
	if any(filters.get(key) for key in ("status", "sla_status", "case_type", "customer", "coordinator", "company")):
		case_names = [row.name for row in fetch_cases(filters)]
	counts = {}
	for mode in SERVICE_MODES:
		counts[mode["doctype"]] = _count_mode_documents(mode["doctype"], case_names)
	return counts


def _count_mode_documents(doctype, case_names):
	if doctype not in {mode["doctype"] for mode in SERVICE_MODES}:
		return {"documents": 0, "cases": 0}
	if not frappe.db.exists("DocType", doctype):
		return {"documents": 0, "cases": 0}
	meta = frappe.get_meta(doctype)
	if not meta.has_field("time_sensitive_case"):
		return {"documents": 0, "cases": 0}
	if case_names is not None and not case_names:
		return {"documents": 0, "cases": 0}

	conds = ["ifnull(`time_sensitive_case`, '') != ''"]
	values = {}
	if meta.is_submittable:
		conds.append("docstatus < 2")
	if case_names is not None:
		conds.append("`time_sensitive_case` in %(cases)s")
		values["cases"] = case_names
	row = frappe.db.sql(
		f"""
		SELECT count(*) AS documents, count(distinct `time_sensitive_case`) AS cases
		FROM `tab{doctype}`
		WHERE {" AND ".join(conds)}
		""",
		values,
		as_dict=True,
	)[0]
	return {"documents": int(row.documents or 0), "cases": int(row.cases or 0)}


def _as_date(value):
	current = _as_datetime(value)
	return current.date() if current else None


def _as_datetime(value):
	if value is None or value == "":
		return None
	if isinstance(value, datetime):
		return value
	if isinstance(value, date):
		return datetime(value.year, value.month, value.day)
	text = str(value).strip()
	if not text:
		return None
	for fmt, size in (("%Y-%m-%d %H:%M:%S.%f", 26), ("%Y-%m-%d %H:%M:%S", 19), ("%Y-%m-%d", 10)):
		try:
			return datetime.strptime(text[:size], fmt)
		except ValueError:
			continue
	return None
