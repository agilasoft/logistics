# Copyright (c) 2026, Agilasoft and contributors
"""Project-operations payload for the Special Projects Home workspace (pipeline, clocks, owners, SLA)."""

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
PRE_EVENT_STATUSES = ("Draft", "Scoping", "Booked", "Planning")
PROJECT_STATUSES = (
	"Draft",
	"Scoping",
	"Booked",
	"Planning",
	"Approved",
	"In Progress",
	"On Hold",
	"Completed",
	"Cancelled",
)
START_WINDOW_DAYS = 7
MAX_WORK_ROWS = 200
SEV_RANK = {
	"overdue": 0,
	"start_due": 1,
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


def _clock_start(row):
	return _as_date(row.get("planned_start") or row.get("start_date"))


def _clock_end(row):
	return _as_date(row.get("planned_end") or row.get("end_date"))


def classify_project(row, today_date=None):
	"""Return clock flags for one Special Project row. Flags may overlap (start due vs upcoming)."""
	today_date = getdate(today_date or today())
	status = (row.get("status") or "").strip()
	active = status not in CLOSED_STATUSES
	planned_start = _clock_start(row)
	planned_end = _clock_end(row)

	upcoming = bool(active and (planned_start is None or planned_start > today_date))
	if active and planned_start and planned_end:
		live = planned_start <= today_date <= planned_end
	elif active and planned_start and not planned_end:
		live = planned_start <= today_date and status not in PRE_EVENT_STATUSES
	else:
		live = False

	overdue = bool(
		active
		and status in PRE_EVENT_STATUSES
		and ((planned_start and planned_start < today_date) or (planned_end and planned_end < today_date))
	)
	horizon = add_days(today_date, START_WINDOW_DAYS)
	start_due = bool(
		active
		and planned_start
		and (
			(today_date <= planned_start <= horizon)
			or (planned_start < today_date and status in PRE_EVENT_STATUSES)
		)
	)
	end_soon = bool(active and planned_end and today_date <= planned_end <= horizon)

	if overdue:
		severity = "overdue"
	elif start_due or end_soon:
		severity = "start_due"
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
		"start_due": start_due,
		"end_soon": end_soon,
		"severity": severity,
	}


def count_programme_kpis(rows, today_date=None):
	"""Active / Upcoming / Live / Overdue from programme rows. Start due is alert-only."""
	kpis = {"active": 0, "upcoming": 0, "live": 0, "overdue": 0, "start_due": 0}
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
		if flags["start_due"]:
			kpis["start_due"] += 1
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
		project = (r.get("special_project") or "").strip()
		if not project:
			continue
		status = (r.get("status") or "").strip()
		if status in CLOSED_STATUSES:
			continue
		sla = (r.get("sla_status") or "").strip()
		if sla == "Breached":
			out[project]["breached"] += 1
		elif sla == "At Risk":
			out[project]["at_risk"] += 1
	return dict(out)


def _site_key(lat, lon):
	return (round(float(lat), 5), round(float(lon), 5))


def _valid_coords(lat, lon):
	try:
		lat_f = float(lat)
		lon_f = float(lon)
	except (TypeError, ValueError):
		return None
	if not (-90 <= lat_f <= 90 and -180 <= lon_f <= 180):
		return None
	if lat_f == 0 and lon_f == 0:
		return None
	return lat_f, lon_f


def _collect_project_sites(project_names):
	"""Ordered site Address candidates per project: packages, then jobs, then orders, then lifecycle lines."""
	if not project_names:
		return {}
	ordered = defaultdict(list)
	seen = defaultdict(set)

	def _add(parent, site):
		if not parent or not site:
			return
		if site in seen[parent]:
			return
		seen[parent].add(site)
		ordered[parent].append(site)

	for i in range(0, len(project_names), 200):
		chunk = project_names[i : i + 200]
		for row in frappe.get_all(
			"Special Project Package",
			filters={"parent": ["in", chunk], "site": ["!=", ""]},
			fields=["parent", "site"],
			order_by="idx asc",
		):
			_add(row.parent, row.site)
		for row in frappe.get_all(
			"Project Job",
			filters={"special_project": ["in", chunk], "site": ["!=", ""], "docstatus": ["<", 2]},
			fields=["special_project", "site"],
			order_by="modified desc",
		):
			_add(row.special_project, row.site)
		for row in frappe.get_all(
			"Project Order",
			filters={"special_project": ["in", chunk], "site": ["!=", ""], "docstatus": ["<", 2]},
			fields=["special_project", "site"],
			order_by="modified desc",
		):
			_add(row.special_project, row.site)
		try:
			for row in frappe.get_all(
				"Lifecycle Job",
				filters={"parent": ["in", chunk], "sp_site": ["!=", ""]},
				fields=["parent", "sp_site"],
				order_by="idx asc",
			):
				_add(row.parent, row.sp_site)
		except Exception:
			pass
	return dict(ordered)


def _coords_for_sites(site_map):
	"""Map project name → {lat, lon, site} using Address custom lat/long. Skip missing coords."""
	out = {}
	names = []
	for sites in (site_map or {}).values():
		names.extend(sites or [])
	if not names:
		return out
	try:
		from logistics.transport.api_optimized import get_address_coordinates_batch

		coords = get_address_coordinates_batch(list(set(names))) or {}
	except Exception:
		coords = {}
	for project, sites in (site_map or {}).items():
		for site in sites or []:
			c = coords.get(site) or {}
			pair = _valid_coords(c.get("lat"), c.get("lon"))
			if not pair:
				continue
			out[project] = {"lat": pair[0], "lon": pair[1], "site": site}
			break
	return out


def build_site_markers(rows, sla_map=None, job_counts=None, site_coords=None, today_date=None):
	"""One map bubble per distinct site (lat/lon). Skip rows without coordinates."""
	sla_map = sla_map or {}
	job_counts = job_counts or {}
	site_coords = site_coords or {}
	groups = {}
	for r in rows or []:
		name = r.get("name")
		loc = site_coords.get(name) or {}
		pair = _valid_coords(loc.get("lat"), loc.get("lon"))
		if not pair:
			continue
		lat_f, lon_f = pair
		key = _site_key(lat_f, lon_f)
		flags = classify_project(r, today_date=today_date)
		sla = sla_map.get(name) or {"at_risk": 0, "breached": 0}
		entry = {
			"name": name,
			"project_name": r.get("project_name") or name,
			"status": r.get("status"),
			"lifecycle_stage": r.get("lifecycle_stage"),
			"planned_start": str(_clock_start(r) or r.get("planned_start") or ""),
			"planned_end": str(_clock_end(r) or r.get("planned_end") or ""),
			"site": loc.get("site") or "",
			"job_count": int(job_counts.get(name) or 0),
			"sla_at_risk": int(sla.get("at_risk") or 0),
			"sla_breached": int(sla.get("breached") or 0),
			"severity": flags["severity"],
			"overdue": flags["overdue"],
			"start_due": flags["start_due"] or flags["end_soon"],
		}
		if sla["breached"]:
			entry["severity"] = "overdue"
		elif sla["at_risk"] and entry["severity"] not in ("overdue",):
			entry["severity"] = "start_due"
		grp = groups.setdefault(
			key,
			{"lat": lat_f, "lon": lon_f, "projects": [], "severity": "upcoming"},
		)
		grp["projects"].append(entry)
		rank = {"overdue": 3, "start_due": 2, "live": 1, "upcoming": 0, "active": 0}
		if rank.get(entry["severity"], 0) > rank.get(grp["severity"], 0):
			grp["severity"] = entry["severity"]

	markers = []
	for grp in groups.values():
		overdue_n = sum(1 for p in grp["projects"] if p.get("overdue") or p.get("sla_breached"))
		soon_n = sum(1 for p in grp["projects"] if p.get("start_due") and not p.get("overdue"))
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
		start = _clock_start(r) or r.get("planned_start") or "—"
		end = _clock_end(r) or r.get("planned_end") or "—"
		if flags["overdue"]:
			items.append(
				{
					"level": "danger",
					"msg": _("Overdue project clock: {0} (start {1}, end {2})").format(title, start, end),
					"shipment": name,
					"doctype": "Special Project",
				}
			)
		elif flags["start_due"] or flags["end_soon"]:
			items.append(
				{
					"level": "warning",
					"msg": _("Start / end due soon: {0} (start {1}, end {2})").format(title, start, end),
					"shipment": name,
					"doctype": "Special Project",
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
					"msg": _("SLA breached: {0} (target {1})").format(name, r.get("sla_target_date") or "—"),
					"shipment": name,
					"doctype": doctype,
				}
			)
		elif sla == "At Risk":
			items.append(
				{
					"level": "warning",
					"msg": _("SLA at risk: {0} (target {1})").format(name, r.get("sla_target_date") or "—"),
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
	if key in ("start_due", "move_in_due", "alerts"):
		return flags["overdue"] or flags["start_due"] or flags["end_soon"]
	if key == "live":
		return flags["live"]
	if key == "upcoming":
		return flags["upcoming"]
	return True


def _status_filter(job_status_filter):
	key = (job_status_filter or "active").strip() or "active"
	if key in ("active", "ongoing", "open", "open_with_draft"):
		return ["not in", list(CLOSED_STATUSES)]
	if key in PROJECT_STATUSES:
		return key
	return ["not in", list(CLOSED_STATUSES)]


def _project_filters(job_status_filter, filter_user, customers, company):
	filters = {
		"docstatus": ["<", 2],
		"status": _status_filter(job_status_filter),
	}
	fu = (filter_user or "").strip()
	if fu and frappe.db.exists("User", fu):
		filters["owner"] = fu
	if company:
		filters["company"] = company
	safe = sanitize_link_values(parse_multi_link_param(customers), "Customer")
	if safe:
		filters["customer"] = ["in", safe]
	return filters


def _customer_options(filters):
	try:
		codes = frappe.get_list(
			"Special Project",
			filters=filters,
			pluck="customer",
			distinct=True,
			limit_page_length=0,
			order_by="customer asc",
		)
	except Exception:
		codes = []
	out = []
	seen = set()
	for c in codes or []:
		if not c or c in seen:
			continue
		seen.add(c)
		label = frappe.db.get_value("Customer", c, "customer_name") or c
		out.append({"value": c, "label": "{0} ({1})".format(label, c)})
	return out


def _job_counts(project_names):
	if not project_names:
		return {}
	counts = defaultdict(int)
	for i in range(0, len(project_names), 200):
		chunk = project_names[i : i + 200]
		for row in frappe.get_all(
			"Project Job",
			filters={"special_project": ["in", chunk], "docstatus": ["<", 2]},
			fields=["special_project"],
		):
			if row.special_project:
				counts[row.special_project] += 1
	return dict(counts)


def _task_rows(project_names, filter_user, company):
	if not project_names:
		return []
	filters = {
		"docstatus": ["<", 2],
		"special_project": ["in", project_names],
		"status": ["not in", list(CLOSED_STATUSES)],
	}
	fu = (filter_user or "").strip()
	if fu and frappe.db.exists("User", fu):
		filters["owner"] = fu
	if company:
		filters["company"] = company
	try:
		return frappe.get_list(
			"Project Job",
			filters=filters,
			fields=["name", "special_project", "status", "sla_status", "sla_target_date"],
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


def _short_date(val):
	if not val:
		return ""
	return str(val)[:10]


def special_project_work_rows(rows, sla_map, job_counts, labels, today_date=None, limit=MAX_WORK_ROWS):
	enriched = []
	for r in rows or []:
		flags = classify_project(r, today_date=today_date)
		name = r.get("name")
		sla = sla_map.get(name) or {"at_risk": 0, "breached": 0}
		severity = flags["severity"]
		if sla.get("breached"):
			severity = "overdue"
		elif sla.get("at_risk") and severity not in ("overdue",):
			severity = "start_due"
		ow = (r.get("owner") or "").strip()
		enriched.append(
			{
				"name": name,
				"title": r.get("project_name") or name,
				"doctype": "Special Project",
				"status": r.get("status") or "",
				"lifecycle_stage": r.get("lifecycle_stage") or "",
				"customer": r.get("customer") or "",
				"planned_start": _short_date(r.get("planned_start") or r.get("start_date")),
				"planned_end": _short_date(r.get("planned_end") or r.get("end_date")),
				"owner": ow,
				"owner_label": labels.get(ow) or ow or _("Unassigned"),
				"severity": severity,
				"job_count": int((job_counts or {}).get(name) or 0),
				"sla_at_risk": int(sla.get("at_risk") or 0),
				"sla_breached": int(sla.get("breached") or 0),
				"overdue": flags["overdue"],
				"live": flags["live"],
				"upcoming": flags["upcoming"],
				"start_due": flags["start_due"] or flags["end_soon"],
			}
		)
	enriched.sort(
		key=lambda r: (
			SEV_RANK.get(r["severity"], 9),
			r.get("planned_start") or "9999",
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
		if r.get("start_due") or r.get("move_in_due"):
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
def get_special_project_operations_filter_users(job_status_filter=None):
	comp = (session_company_context().get("company") or "").strip()
	filters = _project_filters(job_status_filter, None, None, comp)
	try:
		owners = frappe.get_list(
			"Special Project",
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
def get_special_project_operations_dashboard(
	limit=None,
	filter_user=None,
	alert_filter_user=None,
	airlines=None,
	job_status_filter=None,
	include_draft=None,
	attention=None,
):
	"""`airlines` carries selected Customer names (client reuse)."""
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
			"customer",
			"planned_start",
			"planned_end",
			"start_date",
			"end_date",
			"owner",
		],
		"order_by": "planned_start asc",
		"limit_page_length": 0,
	}
	if limit is not None and str(limit).strip() != "":
		try:
			lim_val = int(limit)
			if lim_val > 0:
				list_kwargs["limit_page_length"] = lim_val
		except Exception:
			pass
	rows = frappe.get_list("Special Project", **list_kwargs)
	attn = (attention or "all").strip().lower() or "all"
	if attn not in ("", "all"):
		rows = [r for r in rows if _matches_attention(classify_project(r), attn)]
	names = [r.name for r in rows]
	jobs = _task_rows(names, filter_user, comp)
	alert_fu = alert_filter_user if alert_filter_user is not None else filter_user
	if (alert_fu or "").strip() != (filter_user or "").strip():
		alert_jobs = _task_rows(names, alert_fu, comp)
	else:
		alert_jobs = jobs

	sla_map = sla_by_project(jobs)
	job_counts = _job_counts(names)
	labels = owner_labels([r.get("owner") for r in rows])
	work_all, _ignored = special_project_work_rows(
		rows, sla_map, job_counts, labels, limit=10 ** 6
	)
	truncated = max(0, len(work_all) - MAX_WORK_ROWS)
	work_rows = work_all[:MAX_WORK_ROWS]
	kpis = count_programme_kpis(rows)
	kpis.update(count_sla_kpis(jobs))
	clock = event_clock_alerts(rows)
	summary, items = merge_alert_items(clock, sla_alerts(alert_jobs, "Project Job"))
	option_filters = _project_filters(job_status_filter, None, None, comp)
	out = {
		"kpis": kpis,
		"pipeline": pipeline_counts(rows),
		"work_rows": work_rows,
		"work_truncated": truncated,
		"user_workload": project_user_workload(work_all),
		"attention_rows": attention_rows(work_rows),
		"mix": {
			"projects": kpis.get("active") or 0,
			"jobs": len(jobs or []),
		},
		"alert_summary": summary,
		"alert_items": items,
		"airline_options": _customer_options(option_filters),
		"limits_applied": {
			"max_shipments": list_kwargs.get("limit_page_length") or None,
			"shipment_count": kpis["active"],
		},
		"filters_applied": {
			"job_status_filter": (job_status_filter or "").strip() or "active",
			"attention": attn,
			"company": comp or None,
		},
	}
	out.update(ctx)
	return out
