# Copyright (c) 2026, Agilasoft and contributors
"""Event-operations payload for the MICE Home workspace (pipeline, clocks, owners, SLA)."""

from __future__ import unicode_literals

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import add_days, getdate, today

from logistics.operations_dashboard.heat_map_core import (
	MAX_ALERT_ITEMS,
	parse_multi_link_param,
	sanitize_link_values,
	session_company_context,
)

CLOSED_STATUSES = ("Completed", "Cancelled")
PRE_EVENT_STATUSES = ("Draft", "Booked", "Planning")
PROJECT_STATUSES = (
	"Draft",
	"Booked",
	"Planning",
	"Approved",
	"In Progress",
	"On Hold",
	"Completed",
	"Cancelled",
)
MOVE_IN_WINDOW_DAYS = 7
MAX_WORK_ROWS = 200
SEV_RANK = {
	"overdue": 0,
	"move_in_due": 1,
	"live": 2,
	"active": 3,
	"upcoming": 4,
}


def _as_date(val):
	if not val:
		return None
	try:
		return getdate(val)
	except Exception:
		return None


def classify_project(row, today_date=None):
	"""Return clock flags for one MICE Project row. Flags may overlap (move-in due vs upcoming)."""
	today_date = getdate(today_date or today())
	status = (row.get("status") or "").strip()
	active = status not in CLOSED_STATUSES
	show_open = _as_date(row.get("show_open_date"))
	show_close = _as_date(row.get("show_close_date"))
	move_in = _as_date(row.get("move_in_date"))

	upcoming = bool(active and (show_open is None or show_open > today_date))
	if active and show_open and show_close:
		live = show_open <= today_date <= show_close
	elif active and show_open and not show_close:
		live = show_open <= today_date and status not in PRE_EVENT_STATUSES
	else:
		live = False

	overdue = bool(
		active
		and status in PRE_EVENT_STATUSES
		and ((move_in and move_in < today_date) or (show_open and show_open < today_date))
	)
	horizon = add_days(today_date, MOVE_IN_WINDOW_DAYS)
	move_in_due = bool(
		active
		and move_in
		and (
			(today_date <= move_in <= horizon)
			or (move_in < today_date and status in PRE_EVENT_STATUSES)
		)
	)
	show_open_soon = bool(active and show_open and today_date <= show_open <= horizon)

	if overdue:
		severity = "overdue"
	elif move_in_due or show_open_soon:
		severity = "move_in_due"
	elif live:
		severity = "live"
	elif upcoming:
		severity = "upcoming"
	else:
		severity = "active"

	return {
		"active": active,
		"upcoming": upcoming,
		"live": live,
		"overdue": overdue,
		"move_in_due": move_in_due,
		"show_open_soon": show_open_soon,
		"severity": severity,
	}


def count_programme_kpis(rows, today_date=None):
	"""Active / Upcoming / Live / Overdue from programme rows. Move-in due is alert-only."""
	kpis = {"active": 0, "upcoming": 0, "live": 0, "overdue": 0, "move_in_due": 0}
	for r in rows or []:
		flags = classify_project(r, today_date=today_date)
		if not flags["active"]:
			continue
		kpis["active"] += 1
		if flags["upcoming"]:
			kpis["upcoming"] += 1
		if flags["live"]:
			kpis["live"] += 1
		if flags["overdue"]:
			kpis["overdue"] += 1
		if flags["move_in_due"]:
			kpis["move_in_due"] += 1
	return kpis


def count_sla_kpis(task_rows):
	at_risk = 0
	breached = 0
	for r in task_rows or []:
		status = (r.get("status") or "").strip()
		if status in CLOSED_STATUSES:
			continue
		sla = (r.get("sla_status") or "").strip()
		if sla == "Breached":
			breached += 1
		elif sla == "At Risk":
			at_risk += 1
	return {"sla_at_risk": at_risk, "sla_breached": breached}


def sla_by_project(task_rows):
	out = defaultdict(lambda: {"at_risk": 0, "breached": 0})
	for r in task_rows or []:
		exhibit = (r.get("exhibit") or "").strip()
		if not exhibit:
			continue
		status = (r.get("status") or "").strip()
		if status in CLOSED_STATUSES:
			continue
		sla = (r.get("sla_status") or "").strip()
		if sla == "Breached":
			out[exhibit]["breached"] += 1
		elif sla == "At Risk":
			out[exhibit]["at_risk"] += 1
	return dict(out)


def _venue_key(lat, lon):
	return (round(float(lat), 5), round(float(lon), 5))


def build_venue_markers(rows, sla_map=None, docket_counts=None, today_date=None):
	"""One map bubble per distinct venue (lat/lon). Skip rows without coordinates."""
	sla_map = sla_map or {}
	docket_counts = docket_counts or {}
	groups = {}
	for r in rows or []:
		lat = r.get("venue_latitude")
		lon = r.get("venue_longitude")
		if lat is None or lon is None:
			continue
		try:
			lat_f = float(lat)
			lon_f = float(lon)
		except (TypeError, ValueError):
			continue
		if not (-90 <= lat_f <= 90 and -180 <= lon_f <= 180):
			continue
		if lat_f == 0 and lon_f == 0:
			continue
		key = _venue_key(lat_f, lon_f)
		flags = classify_project(r, today_date=today_date)
		name = r.get("name")
		sla = sla_map.get(name) or {"at_risk": 0, "breached": 0}
		entry = {
			"name": name,
			"project_name": r.get("project_name") or name,
			"status": r.get("status"),
			"lifecycle_stage": r.get("lifecycle_stage"),
			"show_open_date": str(r.get("show_open_date") or ""),
			"show_close_date": str(r.get("show_close_date") or ""),
			"move_in_date": str(r.get("move_in_date") or ""),
			"docket_count": int(docket_counts.get(name) or 0),
			"sla_at_risk": int(sla.get("at_risk") or 0),
			"sla_breached": int(sla.get("breached") or 0),
			"severity": flags["severity"],
			"overdue": flags["overdue"],
			"move_in_due": flags["move_in_due"] or flags["show_open_soon"],
		}
		if sla["breached"]:
			entry["severity"] = "overdue"
		elif sla["at_risk"] and entry["severity"] not in ("overdue",):
			entry["severity"] = "move_in_due"
		grp = groups.setdefault(
			key,
			{"lat": lat_f, "lon": lon_f, "projects": [], "severity": "upcoming"},
		)
		grp["projects"].append(entry)
		rank = {"overdue": 3, "move_in_due": 2, "live": 1, "upcoming": 0, "active": 0}
		if rank.get(entry["severity"], 0) > rank.get(grp["severity"], 0):
			grp["severity"] = entry["severity"]

	markers = []
	for grp in groups.values():
		overdue_n = sum(1 for p in grp["projects"] if p.get("overdue") or p.get("sla_breached"))
		soon_n = sum(1 for p in grp["projects"] if p.get("move_in_due") and not p.get("overdue"))
		n = len(grp["projects"])
		markers.append(
			{
				"lat": grp["lat"],
				"lon": grp["lon"],
				"severity": grp["severity"],
				"project_count": n,
				"overdue_count": overdue_n,
				"at_risk_count": soon_n,
				"ongoing_count": max(0, n - overdue_n - soon_n),
				"projects": grp["projects"],
			}
		)
	return markers


def event_clock_alerts(rows, today_date=None):
	today_date = getdate(today_date or today())
	items = []
	for r in rows or []:
		flags = classify_project(r, today_date=today_date)
		if not flags["active"]:
			continue
		name = r.get("name")
		title = r.get("project_name") or name
		if flags["overdue"]:
			items.append(
				{
					"level": "danger",
					"msg": _("Overdue event clock: {0} (move-in {1}, show open {2})").format(
						title, r.get("move_in_date") or "—", r.get("show_open_date") or "—"
					),
					"shipment": name,
					"doctype": "MICE Project",
				}
			)
		elif flags["move_in_due"] or flags["show_open_soon"]:
			items.append(
				{
					"level": "warning",
					"msg": _("Move-in / show open due soon: {0} (move-in {1}, show open {2})").format(
						title, r.get("move_in_date") or "—", r.get("show_open_date") or "—"
					),
					"shipment": name,
					"doctype": "MICE Project",
				}
			)
	return items


def sla_alerts(task_rows, doctype):
	items = []
	for r in task_rows or []:
		status = (r.get("status") or "").strip()
		if status in CLOSED_STATUSES:
			continue
		sla = (r.get("sla_status") or "").strip()
		name = r.get("name")
		if sla == "Breached":
			items.append(
				{
					"level": "danger",
					"msg": _("SLA breached: {0} (target {1})").format(
						name, r.get("sla_target_date") or "—"
					),
					"shipment": name,
					"doctype": doctype,
				}
			)
		elif sla == "At Risk":
			items.append(
				{
					"level": "warning",
					"msg": _("SLA at risk: {0} (target {1})").format(
						name, r.get("sla_target_date") or "—"
					),
					"shipment": name,
					"doctype": doctype,
				}
			)
	return items


def merge_alert_items(*groups):
	summary = {"danger": 0, "warning": 0, "info": 0}
	items = []
	for group in groups:
		for a in group or []:
			lvl = a.get("level") or "info"
			if lvl not in summary:
				lvl = "info"
			summary[lvl] += 1
			if len(items) < MAX_ALERT_ITEMS:
				items.append(a)
	return summary, items


def _matches_attention(flags, attention):
	key = (attention or "all").strip().lower() or "all"
	if key in ("", "all"):
		return True
	if key == "overdue":
		return flags["overdue"]
	if key in ("move_in_due", "alerts"):
		return flags["overdue"] or flags["move_in_due"] or flags["show_open_soon"]
	if key == "live":
		return flags["live"]
	if key == "upcoming":
		return flags["upcoming"]
	return True


def _status_filter(job_status_filter):
	key = (job_status_filter or "active").strip() or "active"
	if key in ("active", "ongoing"):
		return ["not in", list(CLOSED_STATUSES)]
	if key in ("open", "open_with_draft"):
		return ["not in", list(CLOSED_STATUSES)]
	if key in PROJECT_STATUSES:
		return key
	return ["not in", list(CLOSED_STATUSES)]


def _project_filters(job_status_filter, filter_user, organizers, company):
	filters = {
		"docstatus": ["<", 2],
		"status": _status_filter(job_status_filter),
	}
	fu = (filter_user or "").strip()
	if fu and frappe.db.exists("User", fu):
		filters["owner"] = fu
	if company:
		filters["company"] = company
	safe = sanitize_link_values(parse_multi_link_param(organizers), "MICE Organizer")
	if safe:
		filters["organizer"] = ["in", safe]
	return filters


def _organizer_options(filters):
	try:
		codes = frappe.get_list(
			"MICE Project",
			filters=filters,
			pluck="organizer",
			distinct=True,
			limit_page_length=0,
			order_by="organizer asc",
		)
	except Exception:
		codes = []
	out = []
	seen = set()
	for c in codes or []:
		if not c or c in seen:
			continue
		seen.add(c)
		label = frappe.db.get_value("MICE Organizer", c, "organizer_name") or c
		out.append({"value": c, "label": "{0} ({1})".format(label, c)})
	return out


def _docket_counts(project_names):
	if not project_names:
		return {}
	counts = defaultdict(int)
	for i in range(0, len(project_names), 200):
		chunk = project_names[i : i + 200]
		for row in frappe.get_all(
			"Docket",
			filters={"exhibit": ["in", chunk], "docstatus": ["<", 2]},
			fields=["exhibit"],
		):
			if row.exhibit:
				counts[row.exhibit] += 1
	return dict(counts)


def _task_rows(doctype, project_names, filter_user, company):
	if not project_names:
		return []
	filters = {
		"docstatus": ["<", 2],
		"exhibit": ["in", project_names],
		"status": ["not in", list(CLOSED_STATUSES)],
	}
	fu = (filter_user or "").strip()
	if fu and frappe.db.exists("User", fu):
		filters["owner"] = fu
	if company:
		filters["company"] = company
	try:
		return frappe.get_list(
			doctype,
			filters=filters,
			fields=["name", "exhibit", "status", "sla_status", "sla_target_date"],
			limit_page_length=0,
			order_by="modified desc",
		)
	except Exception:
		return []


def pipeline_counts(rows):
	by_stage = defaultdict(int)
	for r in rows or []:
		if (r.get("status") or "").strip() in CLOSED_STATUSES:
			continue
		stage = (r.get("lifecycle_stage") or "").strip() or _("Unspecified")
		by_stage[stage] += 1
	return [{"lifecycle_stage": k, "program_count": v} for k, v in sorted(by_stage.items())]


def owner_labels(user_ids):
	ids = sorted({(x or "").strip() for x in (user_ids or []) if (x or "").strip()})
	if not ids:
		return {}
	rows = frappe.get_all("User", filters={"name": ["in", ids]}, fields=["name", "full_name"])
	return {r.name: (r.full_name or r.name) for r in rows}


def attention_rows(work_rows, limit=8):
	hot = [
		r
		for r in (work_rows or [])
		if (r.get("severity") or "") in ("overdue", "at_risk", "move_in_due", "start_due")
	]
	return hot[:limit]


def _task_counts(task_rows, key="exhibit"):
	counts = defaultdict(int)
	for r in task_rows or []:
		k = (r.get(key) or "").strip()
		if k:
			counts[k] += 1
	return dict(counts)


def _short_date(val):
	if not val:
		return ""
	return str(val)[:10]


def programme_work_rows(rows, sla_map, docket_counts, task_counts, labels, today_date=None, limit=MAX_WORK_ROWS):
	enriched = []
	for r in rows or []:
		flags = classify_project(r, today_date=today_date)
		name = r.get("name")
		sla = sla_map.get(name) or {"at_risk": 0, "breached": 0}
		severity = flags["severity"]
		if sla.get("breached"):
			severity = "overdue"
		elif sla.get("at_risk") and severity not in ("overdue",):
			severity = "move_in_due"
		ow = (r.get("owner") or "").strip()
		enriched.append(
			{
				"name": name,
				"title": r.get("project_name") or name,
				"doctype": "MICE Project",
				"status": r.get("status") or "",
				"lifecycle_stage": r.get("lifecycle_stage") or "",
				"organizer": r.get("organizer") or "",
				"venue_name": r.get("venue_name") or "",
				"show_open_date": _short_date(r.get("show_open_date")),
				"show_close_date": _short_date(r.get("show_close_date")),
				"move_in_date": _short_date(r.get("move_in_date")),
				"owner": ow,
				"owner_label": labels.get(ow) or ow or _("Unassigned"),
				"severity": severity,
				"docket_count": int((docket_counts or {}).get(name) or 0),
				"task_count": int((task_counts or {}).get(name) or 0),
				"sla_at_risk": int(sla.get("at_risk") or 0),
				"sla_breached": int(sla.get("breached") or 0),
				"overdue": flags["overdue"],
				"live": flags["live"],
				"upcoming": flags["upcoming"],
				"move_in_due": flags["move_in_due"] or flags["show_open_soon"],
			}
		)
	enriched.sort(
		key=lambda r: (
			SEV_RANK.get(r["severity"], 9),
			r.get("show_open_date") or "9999",
			(r.get("title") or "").lower(),
		)
	)
	return enriched[:limit], max(0, len(enriched) - limit)


def project_user_workload(work_rows):
	by = {}
	for r in work_rows or []:
		ow = (r.get("owner") or "").strip() or _("Unassigned")
		if ow not in by:
			by[ow] = {
				"owner": r.get("owner") or "",
				"label": r.get("owner_label") or ow,
				"active": 0,
				"upcoming": 0,
				"live": 0,
				"overdue": 0,
				"due_soon": 0,
				"sla_at_risk": 0,
				"sla_breached": 0,
			}
		b = by[ow]
		b["active"] += 1
		if r.get("upcoming"):
			b["upcoming"] += 1
		if r.get("live"):
			b["live"] += 1
		if r.get("overdue") or r.get("severity") == "overdue":
			b["overdue"] += 1
		if r.get("move_in_due") or r.get("start_due"):
			b["due_soon"] += 1
		b["sla_at_risk"] += int(r.get("sla_at_risk") or 0)
		b["sla_breached"] += int(r.get("sla_breached") or 0)
	out = list(by.values())
	out.sort(
		key=lambda r: (
			-r["overdue"],
			-r["sla_breached"],
			-r["due_soon"],
			-r["active"],
			(r.get("label") or "").lower(),
		)
	)
	return out


@frappe.whitelist()
def get_mice_operations_filter_users(job_status_filter=None):
	comp = (session_company_context().get("company") or "").strip()
	filters = _project_filters(job_status_filter, None, None, comp)
	try:
		owners = frappe.get_list(
			"MICE Project",
			filters=filters,
			pluck="owner",
			distinct=True,
			limit_page_length=150,
			order_by="owner asc",
		)
	except Exception:
		owners = []
	out = [{"value": "", "label": _("All users")}]
	seen = set()
	for owner in owners or []:
		if not owner or owner in seen:
			continue
		seen.add(owner)
		full = frappe.db.get_value("User", owner, "full_name") or owner
		out.append({"value": owner, "label": "{0} ({1})".format(full, owner)})
	return out


@frappe.whitelist()
def get_mice_operations_dashboard(
	limit=None,
	filter_user=None,
	alert_filter_user=None,
	airlines=None,
	job_status_filter=None,
	include_draft=None,
	attention=None,
):
	"""`airlines` carries selected MICE Organizer names (client reuse)."""
	ctx = session_company_context()
	comp = (ctx.get("company") or "").strip()
	filters = _project_filters(job_status_filter, filter_user, airlines, comp)
	list_kwargs = {
		"filters": filters,
		"fields": [
			"name",
			"project_name",
			"status",
			"lifecycle_stage",
			"organizer",
			"show_open_date",
			"show_close_date",
			"move_in_date",
			"move_out_date",
			"venue_name",
			"venue_latitude",
			"venue_longitude",
			"owner",
		],
		"order_by": "show_open_date asc",
		"limit_page_length": 0,
	}
	if limit is not None and str(limit).strip() != "":
		try:
			lim_val = int(limit)
			if lim_val > 0:
				list_kwargs["limit_page_length"] = lim_val
		except Exception:
			pass
	rows = frappe.get_list("MICE Project", **list_kwargs)
	attn = (attention or "all").strip().lower() or "all"
	if attn not in ("", "all"):
		rows = [r for r in rows if _matches_attention(classify_project(r), attn)]
	names = [r.name for r in rows]
	orders = _task_rows("MICE Order", names, filter_user, comp)
	jobs = _task_rows("MICE Job", names, filter_user, comp)
	alert_fu = alert_filter_user if alert_filter_user is not None else filter_user
	if (alert_fu or "").strip() != (filter_user or "").strip():
		alert_orders = _task_rows("MICE Order", names, alert_fu, comp)
		alert_jobs = _task_rows("MICE Job", names, alert_fu, comp)
	else:
		alert_orders = orders
		alert_jobs = jobs

	sla_map = sla_by_project(list(orders) + list(jobs))
	dockets = _docket_counts(names)
	task_counts = _task_counts(list(orders) + list(jobs))
	labels = owner_labels([r.get("owner") for r in rows])
	work_all, _ignored = programme_work_rows(
		rows, sla_map, dockets, task_counts, labels, limit=10 ** 6
	)
	truncated = max(0, len(work_all) - MAX_WORK_ROWS)
	work_rows = work_all[:MAX_WORK_ROWS]
	kpis = count_programme_kpis(rows)
	kpis.update(count_sla_kpis(list(orders) + list(jobs)))
	clock = event_clock_alerts(rows)
	summary, items = merge_alert_items(
		clock,
		sla_alerts(alert_orders, "MICE Order"),
		sla_alerts(alert_jobs, "MICE Job"),
	)
	option_filters = _project_filters(job_status_filter, None, None, comp)
	out = {
		"kpis": kpis,
		"pipeline": pipeline_counts(rows),
		"work_rows": work_rows,
		"work_truncated": truncated,
		"user_workload": project_user_workload(work_all),
		"attention_rows": attention_rows(work_rows),
		"mix": {
			"events": kpis.get("active") or 0,
			"orders": len(orders or []),
			"jobs": len(jobs or []),
			"dockets": sum((dockets or {}).values()),
		},
		"alert_summary": summary,
		"alert_items": items,
		"airline_options": _organizer_options(option_filters),
		"limits_applied": {"max_shipments": list_kwargs.get("limit_page_length") or None, "shipment_count": kpis["active"]},
		"filters_applied": {
			"job_status_filter": (job_status_filter or "").strip() or "active",
			"attention": attn,
			"company": comp or None,
		},
	}
	out.update(ctx)
	return out
