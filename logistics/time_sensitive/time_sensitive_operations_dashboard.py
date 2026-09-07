# Copyright (c) 2026, Agilasoft and contributors
"""Aggregated data for the Time Sensitive Home workspace (SLA KPIs, alert map, alerts)."""

from __future__ import unicode_literals

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import get_datetime

from logistics.operations_dashboard.heat_map_core import (
	MAX_ALERT_ITEMS,
	operations_filter_users,
	run_heat_map_dashboard,
	session_company_context,
)
from logistics.time_sensitive.sla import format_countdown, seconds_until_deadline

TIME_SENSITIVE_STATUSES = (
	"Draft",
	"Triage",
	"Activated",
	"In Execution",
	"On Hold",
	"Delivered",
	"Closed",
	"Cancelled",
)
TIME_SENSITIVE_ONGOING_EXCLUDE = ("Delivered", "Closed", "Cancelled")
OPERATIONAL_STATUSES = ("Activated", "In Execution", "On Hold")
ALERT_SLA_STATUSES = ("At Risk", "Breached")
PRIORITY_RANK = {"Urgent": 0, "High": 1, "Critical": 0}
MAX_PRIORITY_CARD = 12


def _case_type_label(code):
	row = frappe.db.get_value("Time Sensitive Case Type", code, ["case_type_name"], as_dict=True) or {}
	name = row.get("case_type_name") or code
	return "{0} ({1})".format(name, code)


def _parse_sla_filter(sla_filter):
	key = (sla_filter or "all").strip().lower()
	if key in ("all", "at_risk", "breached", "alerts", "on_track"):
		return key
	return "all"


def _sla_extra_filters(sla_key):
	if sla_key == "breached":
		return {"sla_status": "Breached"}
	if sla_key == "at_risk":
		return {"sla_status": "At Risk"}
	if sla_key == "on_track":
		return {"sla_status": "On Track"}
	if sla_key == "alerts":
		return {"sla_status": ["in", ["At Risk", "Breached"]]}
	return None


def _sla_alert_for_row(row):
	sla = (row.get("sla_status") or "").strip()
	deadline = row.get("critical_deadline")
	title = row.get("case_title") or row.get("name") or ""
	remaining = seconds_until_deadline(deadline) if deadline else None
	clock = format_countdown(remaining) if remaining is not None else ""
	deadline_s = str(get_datetime(deadline)) if deadline else "—"
	if sla == "Breached":
		msg = _("Overdue: {0} (deadline {1}{2})").format(
			title, deadline_s, " · {0}".format(clock) if clock else ""
		)
		return {"level": "danger", "msg": msg, "shipment": row.get("name")}
	if sla == "At Risk":
		msg = _("Nearing due: {0} (deadline {1}{2})").format(
			title, deadline_s, " · {0}".format(clock) if clock else ""
		)
		return {"level": "warning", "msg": msg, "shipment": row.get("name")}
	return None


def _count_sla_kpis(rows, alert_rows=None):
	"""Ongoing/on-track from operational rows; nearing due/overdue from alert rows (incl. Draft)."""
	kpis = {
		"ongoing": 0,
		"nearing_due": 0,
		"overdue": 0,
		"on_track": 0,
		"on_hold": 0,
	}
	for r in rows or []:
		status = (r.get("status") or "").strip()
		if status not in OPERATIONAL_STATUSES:
			continue
		kpis["ongoing"] += 1
		if status == "On Hold":
			kpis["on_hold"] += 1
		if (r.get("sla_status") or "").strip() == "On Track":
			kpis["on_track"] += 1
	for r in (alert_rows if alert_rows is not None else rows) or []:
		status = (r.get("status") or "").strip()
		if status in ("Closed", "Cancelled"):
			continue
		sla = (r.get("sla_status") or "").strip()
		if sla == "Breached":
			kpis["overdue"] += 1
		elif sla == "At Risk":
			kpis["nearing_due"] += 1
	return kpis


def enrich_unloco_markers_with_sla(markers, rows):
	"""Annotate heat-map bubbles with overdue / nearing-due / ongoing counts and severity."""
	by_code = {m.get("unloco"): m for m in (markers or []) if m.get("unloco")}
	counts = defaultdict(lambda: {"overdue_count": 0, "at_risk_count": 0, "ongoing_count": 0})
	for r in rows or []:
		sla = (r.get("sla_status") or "").strip()
		bucket = "ongoing_count"
		if sla == "Breached":
			bucket = "overdue_count"
		elif sla == "At Risk":
			bucket = "at_risk_count"
		for code in ((r.get("origin") or "").strip(), (r.get("destination") or "").strip()):
			if not code:
				continue
			counts[code][bucket] += 1
	for code, m in by_code.items():
		c = counts.get(code) or {}
		overdue = int(c.get("overdue_count") or 0)
		at_risk = int(c.get("at_risk_count") or 0)
		ongoing = int(c.get("ongoing_count") or 0)
		m["overdue_count"] = overdue
		m["at_risk_count"] = at_risk
		m["ongoing_count"] = ongoing
		if overdue:
			m["severity"] = "overdue"
		elif at_risk:
			m["severity"] = "at_risk"
		else:
			m["severity"] = "ongoing"
	return markers


def append_missing_unloco_markers(markers, rows, get_coords=None):
	"""Add map bubbles for alert origins/destinations that the heat map omitted (e.g. Draft)."""
	from logistics.document_management.dashboard_layout import get_unloco_coords
	from logistics.operations_dashboard.heat_map_core import flag_emoji_from_country_code

	coord_fn = get_coords or get_unloco_coords
	markers = list(markers or [])
	by_code = {m.get("unloco"): m for m in markers if m.get("unloco")}
	needed = []
	for r in rows or []:
		for code in ((r.get("origin") or "").strip(), (r.get("destination") or "").strip()):
			if code and code not in by_code and code not in needed:
				needed.append(code)
	if not needed:
		return markers
	cc_by_unloco = {}
	try:
		for row in frappe.get_all(
			"UNLOCO",
			filters={"name": ["in", needed]},
			fields=["name", "country_code"],
		):
			cc_by_unloco[row.name] = (row.get("country_code") or "").strip().upper()
	except Exception:
		cc_by_unloco = {}
	for code in needed:
		coords = coord_fn(code)
		if not coords or coords.get("lat") is None or coords.get("lon") is None:
			continue
		cc = cc_by_unloco.get(code) or ""
		marker = {
			"unloco": code,
			"country_code": cc,
			"flag": flag_emoji_from_country_code(cc),
			"lat": float(coords["lat"]),
			"lon": float(coords["lon"]),
			"import_count": 0,
			"export_count": 0,
			"domestic_count": 0,
			"overdue_count": 0,
			"at_risk_count": 0,
			"ongoing_count": 0,
			"severity": "ongoing",
		}
		markers.append(marker)
		by_code[code] = marker
	return markers


def merge_sla_alerts(payload, rows):
	"""Prepend SLA overdue / nearing-due items onto the operations alert rollup."""
	summary = payload.get("alert_summary") or {"danger": 0, "warning": 0, "info": 0}
	items = list(payload.get("alert_items") or [])
	sla_items = []
	for r in rows or []:
		alert = _sla_alert_for_row(r)
		if not alert:
			continue
		lvl = alert["level"]
		summary[lvl] = int(summary.get(lvl) or 0) + 1
		if len(sla_items) + len(items) < MAX_ALERT_ITEMS:
			sla_items.append(alert)
	payload["alert_summary"] = summary
	payload["alert_items"] = sla_items + items[: max(0, MAX_ALERT_ITEMS - len(sla_items))]
	return payload


def priority_clock_rows(rows, limit=MAX_PRIORITY_CARD, now=None):
	"""Overdue / nearing-due cases for the map card, High/Urgent first."""
	hot = []
	for r in rows or []:
		status = (r.get("status") or "").strip()
		if status in ("Closed", "Cancelled"):
			continue
		sla = (r.get("sla_status") or "").strip()
		if sla not in ALERT_SLA_STATUSES:
			continue
		pri = (r.get("priority") or "").strip() or (r.get("severity") or "").strip() or "Urgent"
		deadline = r.get("critical_deadline")
		remaining = seconds_until_deadline(deadline, now=now) if deadline else None
		hot.append(
			{
				"name": r.get("name"),
				"title": r.get("case_title") or r.get("name") or "",
				"priority": pri,
				"sla_status": sla,
				"status": status,
				"critical_deadline": str(get_datetime(deadline)) if deadline else "",
				"remaining_seconds": remaining,
				"clock": format_countdown(remaining) if remaining is not None else "",
				"origin": (r.get("origin") or "").strip(),
				"destination": (r.get("destination") or "").strip(),
				"severity": "overdue" if sla == "Breached" else "at_risk",
			}
		)
	hot.sort(
		key=lambda row: (
			0 if row["severity"] == "overdue" else 1,
			PRIORITY_RANK.get(row["priority"], 2),
			row["remaining_seconds"] if row["remaining_seconds"] is not None else 10 ** 12,
			(row.get("name") or ""),
		)
	)
	return hot[:limit]


@frappe.whitelist()
def get_time_sensitive_operations_filter_users(job_status_filter=None, include_draft=None):
	if job_status_filter is None and frappe.utils.cint(include_draft):
		job_status_filter = "open"
	comp = (session_company_context().get("company") or "").strip()
	return operations_filter_users(
		"Time Sensitive Case",
		job_status_filter,
		"status",
		TIME_SENSITIVE_STATUSES,
		comp,
		ongoing_exclude_statuses=TIME_SENSITIVE_ONGOING_EXCLUDE,
		docstatus_filter=["<", 2],
	)


@frappe.whitelist()
def get_time_sensitive_operations_dashboard(
	limit=None,
	filter_user=None,
	alert_filter_user=None,
	traffic=None,
	airlines=None,
	job_status_filter=None,
	include_draft=None,
	sla_filter=None,
):
	"""`airlines` carries selected Time Sensitive Case Type names (client reuse)."""
	sla_key = _parse_sla_filter(sla_filter)
	extra = _sla_extra_filters(sla_key)
	payload = run_heat_map_dashboard(
		"Time Sensitive Case",
		"Time Sensitive Case",
		job_status_field="status",
		valid_job_statuses=TIME_SENSITIVE_STATUSES,
		list_fields=[
			"name",
			"origin",
			"destination",
			"status",
			"sla_status",
			"case_title",
			"critical_deadline",
			"case_type",
			"priority",
			"severity",
			"modified",
		],
		origin_field="origin",
		dest_field="destination",
		carrier_field="case_type",
		carrier_doctype="Time Sensitive Case Type",
		carrier_label_fn=_case_type_label,
		job_status_filter=job_status_filter,
		filter_user=filter_user,
		alert_filter_user=alert_filter_user,
		traffic=traffic,
		carriers_param=airlines,
		limit=limit,
		include_draft=include_draft,
		extra_filters=extra,
		ongoing_exclude_statuses=TIME_SENSITIVE_ONGOING_EXCLUDE,
		docstatus_filter=["<", 2],
	)

	rows = frappe.get_list(
		"Time Sensitive Case",
		filters=_list_filters_for_kpis(
			job_status_filter, filter_user, airlines, sla_key, include_draft
		),
		fields=[
			"name",
			"origin",
			"destination",
			"status",
			"sla_status",
			"case_title",
			"critical_deadline",
			"priority",
			"severity",
		],
		limit_page_length=0,
		order_by="critical_deadline asc",
	)
	alert_rows = _fetch_alert_cases(job_status_filter, filter_user, airlines, sla_key)
	map_rows = _merge_case_rows(rows, alert_rows)
	payload["kpis"] = _count_sla_kpis(rows, alert_rows=alert_rows)
	payload["filters_applied"]["sla_filter"] = sla_key
	markers = append_missing_unloco_markers(payload.get("unloco_markers") or [], map_rows)
	enrich_unloco_markers_with_sla(markers, map_rows)
	payload["unloco_markers"] = markers
	payload["priority_clocks"] = priority_clock_rows(map_rows)
	merge_sla_alerts(payload, alert_rows)
	return payload


def _list_filters_for_kpis(job_status_filter, filter_user, airlines, sla_key, include_draft):
	from logistics.operations_dashboard.heat_map_core import (
		base_doc_filters,
		parse_multi_link_param,
		sanitize_link_values,
	)

	if job_status_filter is None and frappe.utils.cint(include_draft):
		job_status_filter = "open"
	comp = (session_company_context().get("company") or "").strip()
	filters = base_doc_filters(
		job_status_filter,
		filter_user,
		comp,
		"status",
		TIME_SENSITIVE_STATUSES,
		ongoing_exclude_statuses=TIME_SENSITIVE_ONGOING_EXCLUDE,
		docstatus_filter=["<", 2],
	)
	extra = _sla_extra_filters(sla_key)
	if extra:
		filters.update(extra)
	safe_types = sanitize_link_values(parse_multi_link_param(airlines), "Time Sensitive Case Type")
	if safe_types:
		filters["case_type"] = ["in", safe_types]
	return filters


def _alert_sla_values(sla_key):
	if sla_key == "on_track":
		return []
	if sla_key == "at_risk":
		return ["At Risk"]
	if sla_key == "breached":
		return ["Breached"]
	return list(ALERT_SLA_STATUSES)


def _alert_status_filter(job_status_filter):
	"""Draft overdue/at-risk cases stay visible on the default ongoing Alert Map."""
	key = (job_status_filter or "").strip() or "ongoing"
	if key in ("ongoing", "open", "open_with_draft"):
		return ["not in", ["Closed", "Cancelled"]]
	if key in TIME_SENSITIVE_STATUSES:
		return key
	return ["not in", ["Closed", "Cancelled"]]


def _fetch_alert_cases(job_status_filter, filter_user, airlines, sla_key):
	from logistics.operations_dashboard.heat_map_core import (
		parse_multi_link_param,
		sanitize_link_values,
	)

	wanted = _alert_sla_values(sla_key)
	if not wanted:
		return []
	comp = (session_company_context().get("company") or "").strip()
	filters = {
		"docstatus": ["<", 2],
		"sla_status": ["in", wanted],
		"status": _alert_status_filter(job_status_filter),
	}
	fu = (filter_user or "").strip()
	if fu and frappe.db.exists("User", fu):
		filters["owner"] = fu
	if comp:
		filters["company"] = comp
	safe_types = sanitize_link_values(parse_multi_link_param(airlines), "Time Sensitive Case Type")
	if safe_types:
		filters["case_type"] = ["in", safe_types]
	return frappe.get_list(
		"Time Sensitive Case",
		filters=filters,
		fields=[
			"name",
			"origin",
			"destination",
			"status",
			"sla_status",
			"case_title",
			"critical_deadline",
			"priority",
			"severity",
		],
		limit_page_length=0,
		order_by="critical_deadline asc",
	)


def _merge_case_rows(*row_lists):
	out = []
	seen = set()
	for rows in row_lists:
		for r in rows or []:
			name = r.get("name")
			if not name or name in seen:
				continue
			seen.add(name)
			out.append(r)
	return out
