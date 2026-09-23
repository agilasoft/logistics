# Copyright (c) 2026, Agilasoft and contributors
"""Brand-operations payload for the High Value Home workspace (brands, owners, HV freight SLA)."""

from __future__ import unicode_literals

from collections import defaultdict

import frappe
from frappe import _

from logistics.document_management.dashboard_layout import get_unloco_coords
from logistics.operations_dashboard.heat_map_core import (
	MAX_ALERT_ITEMS,
	parse_multi_link_param,
	sanitize_link_values,
	session_company_context,
)

JOB_CLOSED = ("Completed", "Closed", "Cancelled")
JOB_LIVE = ("Submitted", "In Progress", "Reopened")
JOB_STATUSES = (
	"Draft",
	"Submitted",
	"In Progress",
	"Completed",
	"Closed",
	"Reopened",
	"Cancelled",
)
HV_JOB_DOCTYPES = (
	("Air Shipment", "origin_port", "destination_port"),
	("Sea Shipment", "origin_port", "destination_port"),
)
HV_SLA_DOCTYPES = ("Air Shipment", "Sea Shipment", "Transport Job")
MAX_WORK_ROWS = 200
MAX_UNASSIGNED_ROWS = 40
SEV_RANK = {
	"overdue": 0,
	"at_risk": 1,
	"live": 2,
	"active": 3,
	"idle": 5,
}


def _status_filter(job_status_filter):
	key = (job_status_filter or "ongoing").strip() or "ongoing"
	if key in ("active", "ongoing"):
		return ["not in", list(JOB_CLOSED) + ["Draft"]]
	if key in ("open", "open_with_draft"):
		return ["not in", list(JOB_CLOSED)]
	if key in JOB_STATUSES:
		return key
	return ["not in", list(JOB_CLOSED) + ["Draft"]]


def classify_brand(quote_rows, job_rows):
	"""Clock flags for one brand from its HV quotes and jobs. Flags may overlap."""
	quotes = list(quote_rows or [])
	jobs = list(job_rows or [])
	open_quotes = [q for q in quotes if int(q.get("docstatus") or 0) < 2]
	open_jobs = [j for j in jobs if (j.get("job_status") or "").strip() not in JOB_CLOSED]
	live_jobs = [j for j in open_jobs if (j.get("job_status") or "").strip() in JOB_LIVE]
	breached = [
		j
		for j in open_jobs
		if (j.get("sla_status") or "").strip() == "Breached"
	]
	at_risk = [
		j
		for j in open_jobs
		if (j.get("sla_status") or "").strip() == "At Risk"
	]
	active = bool(open_quotes or open_jobs)
	live = bool(live_jobs)
	overdue = bool(breached)
	if overdue:
		severity = "overdue"
	elif at_risk:
		severity = "at_risk"
	elif live:
		severity = "live"
	elif active:
		severity = "active"
	else:
		severity = "idle"
	return {
		"active": active,
		"live": live,
		"overdue": overdue,
		"at_risk": bool(at_risk),
		"idle": not active,
		"severity": severity,
		"quote_count": len(open_quotes),
		"job_count": len(open_jobs),
		"live_job_count": len(live_jobs),
		"sla_at_risk": len(at_risk),
		"sla_breached": len(breached),
	}


def count_brand_kpis(brand_flags):
	"""Brands / Active / Live / Overdue. SLA strip is job-level and counted separately."""
	kpis = {"brands": 0, "active": 0, "live": 0, "overdue": 0, "idle": 0}
	for flags in brand_flags or []:
		kpis["brands"] += 1
		if flags.get("active"):
			kpis["active"] += 1
		if flags.get("live"):
			kpis["live"] += 1
		if flags.get("overdue"):
			kpis["overdue"] += 1
		if flags.get("idle"):
			kpis["idle"] += 1
	return kpis


def count_sla_kpis(job_rows):
	at_risk = 0
	breached = 0
	for r in job_rows or []:
		status = (r.get("job_status") or "").strip()
		if status in JOB_CLOSED:
			continue
		sla = (r.get("sla_status") or "").strip()
		if sla == "Breached":
			breached += 1
		elif sla == "At Risk":
			at_risk += 1
	return {"sla_at_risk": at_risk, "sla_breached": breached}


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


def pick_brand_unloco(job_rows, quote_rows):
	"""Prefer destination of the newest live job, then any job, then quote dest/origin."""
	jobs = list(job_rows or [])
	live = [j for j in jobs if (j.get("job_status") or "").strip() in JOB_LIVE]
	for pool in (live, jobs, list(quote_rows or [])):
		for row in pool:
			for field in ("destination_port", "origin_port"):
				code = (row.get(field) or "").strip()
				if code:
					return code
	return ""


def build_brand_markers(brand_rows, unloco_by_brand=None, coords_by_unloco=None):
	"""One map bubble per distinct UNLOCO. Skip brands without coordinates."""
	unloco_by_brand = unloco_by_brand or {}
	groups = {}
	skipped = 0
	for r in brand_rows or []:
		code = (unloco_by_brand.get(r.get("name")) or "").strip()
		if coords_by_unloco is not None:
			coords = coords_by_unloco.get(code)
		else:
			coords = get_unloco_coords(code) if code else None
		if not coords:
			skipped += 1
			continue
		pair = _valid_coords(coords.get("lat"), coords.get("lon"))
		if not pair:
			skipped += 1
			continue
		lat_f, lon_f = pair
		key = _site_key(lat_f, lon_f)
		flags = r.get("flags") or {}
		entry = {
			"name": r.get("name"),
			"brand_name": r.get("brand_name") or r.get("name"),
			"unloco": code,
			"quote_count": int(flags.get("quote_count") or 0),
			"job_count": int(flags.get("job_count") or 0),
			"live_job_count": int(flags.get("live_job_count") or 0),
			"sla_at_risk": int(flags.get("sla_at_risk") or 0),
			"sla_breached": int(flags.get("sla_breached") or 0),
			"severity": flags.get("severity") or "idle",
			"overdue": bool(flags.get("overdue")),
			"at_risk": bool(flags.get("at_risk")),
			"live": bool(flags.get("live")),
		}
		if entry["sla_breached"]:
			entry["severity"] = "overdue"
		elif entry["at_risk"] and entry["severity"] not in ("overdue",):
			entry["severity"] = "at_risk"
		grp = groups.setdefault(
			key,
			{"lat": lat_f, "lon": lon_f, "unloco": code, "projects": [], "severity": "active"},
		)
		grp["projects"].append(entry)
		if code and not grp.get("unloco"):
			grp["unloco"] = code
		rank = {"overdue": 3, "at_risk": 2, "live": 1, "active": 0, "idle": 0}
		if rank.get(entry["severity"], 0) > rank.get(grp["severity"], 0):
			grp["severity"] = entry["severity"]

	markers = []
	for grp in groups.values():
		overdue_n = sum(1 for p in grp["projects"] if p.get("overdue") or p.get("sla_breached"))
		soon_n = sum(1 for p in grp["projects"] if p.get("at_risk") and not p.get("overdue"))
		n = len(grp["projects"])
		markers.append(
			{
				"lat": grp["lat"],
				"lon": grp["lon"],
				"unloco": grp.get("unloco") or "",
				"severity": grp["severity"],
				"project_count": n,
				"overdue_count": overdue_n,
				"at_risk_count": soon_n,
				"ongoing_count": max(0, n - overdue_n - soon_n),
				"projects": grp["projects"],
			}
		)
	return markers, skipped


def brand_alerts(brand_rows):
	items = []
	for r in brand_rows or []:
		flags = r.get("flags") or {}
		if not flags.get("active") and not flags.get("overdue"):
			continue
		name = r.get("name")
		title = r.get("brand_name") or name
		if flags.get("overdue"):
			items.append(
				{
					"level": "danger",
					"msg": _("Brand SLA breached: {0} ({1} job(s))").format(
						title, flags.get("sla_breached") or 0
					),
					"shipment": name,
					"doctype": "HV Brands",
				}
			)
		elif flags.get("at_risk"):
			items.append(
				{
					"level": "warning",
					"msg": _("Brand SLA at risk: {0} ({1} job(s))").format(
						title, flags.get("sla_at_risk") or 0
					),
					"shipment": name,
					"doctype": "HV Brands",
				}
			)
	return items


def sla_alerts(job_rows):
	items = []
	for r in job_rows or []:
		status = (r.get("job_status") or "").strip()
		if status in JOB_CLOSED:
			continue
		sla = (r.get("sla_status") or "").strip()
		name = r.get("name")
		dt = r.get("doctype") or "Air Shipment"
		brand = (r.get("hv_brand") or "").strip()
		prefix = "{0}: ".format(brand) if brand else ""
		if sla == "Breached":
			items.append(
				{
					"level": "danger",
					"msg": _("SLA breached: {0}{1} (target {2})").format(
						prefix, name, r.get("sla_target_date") or "—"
					),
					"shipment": name,
					"doctype": dt,
				}
			)
		elif sla == "At Risk":
			items.append(
				{
					"level": "warning",
					"msg": _("SLA at risk: {0}{1} (target {2})").format(
						prefix, name, r.get("sla_target_date") or "—"
					),
					"shipment": name,
					"doctype": dt,
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
	if key in ("alerts", "at_risk"):
		return flags["overdue"] or flags["at_risk"]
	if key == "live":
		return flags["live"]
	if key == "active":
		return flags["active"]
	if key == "idle":
		return flags["idle"]
	return True


def _brand_lookups(brands):
	by_name = {}
	by_label = {}
	for b in brands or []:
		code = (b.get("name") or "").strip()
		label = (b.get("brand_name") or "").strip()
		if code:
			by_name[code] = code
			by_name[code.lower()] = code
		if label:
			by_label[label] = code
			by_label[label.lower()] = code
	return by_name, by_label


def resolve_quote_brand(quote, by_name, by_label):
	explicit = (quote.get("hv_brand") or "").strip()
	if explicit and (explicit in by_name or explicit.lower() in by_name):
		return by_name.get(explicit) or by_name.get(explicit.lower())
	cust = (quote.get("customer") or "").strip()
	if cust and (cust in by_name or cust.lower() in by_name):
		return by_name.get(cust) or by_name.get(cust.lower())
	if cust and (cust in by_label or cust.lower() in by_label):
		return by_label.get(cust) or by_label.get(cust.lower())
	return ""


def pipeline_counts(brand_rows):
	by_sev = defaultdict(int)
	for r in brand_rows or []:
		sev = ((r.get("flags") or {}).get("severity") or "idle").strip()
		by_sev[sev] += 1
	return [{"lifecycle_stage": k, "program_count": v} for k, v in sorted(by_sev.items())]


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


def brand_work_rows(brand_rows, quotes_by_brand, jobs_by_brand, labels, limit=MAX_WORK_ROWS):
	ranked = sorted(
		brand_rows or [],
		key=lambda r: (
			SEV_RANK.get((r.get("flags") or {}).get("severity") or "idle", 9),
			(r.get("brand_name") or r.get("name") or "").lower(),
		),
	)
	out = []
	for r in ranked[:limit]:
		code = r.get("name")
		flags = r.get("flags") or {}
		owners = []
		seen = set()
		for src in (quotes_by_brand.get(code) or []) + (jobs_by_brand.get(code) or []):
			ow = (src.get("owner") or "").strip()
			if ow and ow not in seen:
				seen.add(ow)
				owners.append({"value": ow, "label": labels.get(ow) or ow})
		out.append(
			{
				"name": code,
				"title": r.get("brand_name") or code,
				"doctype": "HV Brands",
				"severity": flags.get("severity") or "idle",
				"quote_count": flags.get("quote_count") or 0,
				"job_count": flags.get("job_count") or 0,
				"live_job_count": flags.get("live_job_count") or 0,
				"sla_at_risk": flags.get("sla_at_risk") or 0,
				"sla_breached": flags.get("sla_breached") or 0,
				"owners": owners,
				"owner_label": ", ".join(o["label"] for o in owners) or _("Unassigned"),
			}
		)
	return out, max(0, len(ranked) - limit)


def hv_user_workload(quotes, jobs, labels):
	by = {}

	def bucket(owner):
		ow = (owner or "").strip() or _("Unassigned")
		if ow not in by:
			by[ow] = {
				"owner": "" if ow == _("Unassigned") else ow,
				"label": labels.get(ow) or ow,
				"brands": set(),
				"quotes": 0,
				"jobs": 0,
				"live": 0,
				"sla_at_risk": 0,
				"sla_breached": 0,
			}
		return by[ow]

	for q in quotes or []:
		b = bucket(q.get("owner"))
		b["quotes"] += 1
		code = (q.get("hv_brand") or "").strip()
		if code:
			b["brands"].add(code)
	for j in jobs or []:
		b = bucket(j.get("owner"))
		b["jobs"] += 1
		code = (j.get("hv_brand") or "").strip()
		if code:
			b["brands"].add(code)
		status = (j.get("job_status") or "").strip()
		if status in JOB_LIVE:
			b["live"] += 1
		if status not in JOB_CLOSED:
			sla = (j.get("sla_status") or "").strip()
			if sla == "Breached":
				b["sla_breached"] += 1
			elif sla == "At Risk":
				b["sla_at_risk"] += 1
	out = []
	for b in by.values():
		row = dict(b)
		row["brand_count"] = len(row.pop("brands"))
		out.append(row)
	out.sort(
		key=lambda r: (
			-r["sla_breached"],
			-r["sla_at_risk"],
			-r["jobs"],
			-r["quotes"],
			(r.get("label") or "").lower(),
		)
	)
	return out


def unassigned_work_rows(jobs, labels, limit=MAX_UNASSIGNED_ROWS):
	rows = []
	for j in jobs or []:
		ow = (j.get("owner") or "").strip()
		rows.append(
			{
				"name": j.get("name"),
				"doctype": j.get("doctype") or "Air Shipment",
				"job_status": j.get("job_status") or "",
				"sla_status": j.get("sla_status") or "",
				"owner": ow,
				"owner_label": labels.get(ow) or ow or _("Unassigned"),
				"sales_quote": j.get("sales_quote") or "",
			}
		)
	rows.sort(
		key=lambda r: (
			0 if (r.get("sla_status") or "") == "Breached" else 1 if (r.get("sla_status") or "") == "At Risk" else 2,
			r.get("name") or "",
		)
	)
	return rows[:limit]


def job_mix_counts(quotes, jobs):
	mix = {"quotes": len(quotes or []), "air": 0, "sea": 0, "transport": 0}
	for j in jobs or []:
		dt = (j.get("doctype") or "").strip()
		if dt == "Air Shipment":
			mix["air"] += 1
		elif dt == "Sea Shipment":
			mix["sea"] += 1
		elif dt == "Transport Job":
			mix["transport"] += 1
	return mix


def _load_brands(selected):
	filters = {}
	if selected:
		filters["name"] = ["in", selected]
	return frappe.get_all(
		"HV Brands",
		filters=filters or None,
		fields=["name", "brand_name"],
		limit_page_length=0,
		order_by="brand_name asc",
	)


def _load_quotes(company, filter_user, selected_brands):
	filters = {"docstatus": ["<", 2], "is_high_value": 1}
	if company:
		filters["company"] = company
	fu = (filter_user or "").strip()
	if fu and frappe.db.exists("User", fu):
		filters["owner"] = fu
	fields = ["name", "customer", "status", "docstatus", "owner", "origin_port", "destination_port"]
	meta = frappe.get_meta("Sales Quote")
	if meta.has_field("hv_brand"):
		fields.append("hv_brand")
	try:
		rows = frappe.get_list(
			"Sales Quote",
			filters=filters,
			fields=fields,
			limit_page_length=0,
			order_by="modified desc",
		)
	except Exception:
		return []
	if selected_brands and meta.has_field("hv_brand"):
		wanted = set(selected_brands)
		rows = [
			r
			for r in rows
			if (r.get("hv_brand") or "").strip() in wanted or (r.get("customer") or "").strip() in wanted
		]
	return rows


def _load_jobs(doctype, company, filter_user, job_status_filter, quote_names):
	meta = frappe.get_meta(doctype)
	status_field = "job_status" if meta.has_field("job_status") else "status"
	if not meta.has_field(status_field):
		return []
	filters = {
		"docstatus": ["<", 2],
		"is_high_value": 1,
		status_field: _status_filter(job_status_filter),
	}
	if company:
		filters["company"] = company
	fu = (filter_user or "").strip()
	if fu and frappe.db.exists("User", fu):
		filters["owner"] = fu
	fields = ["name", status_field, "owner", "modified"]
	if meta.has_field("sla_status"):
		fields.extend(["sla_status", "sla_target_date"] if meta.has_field("sla_target_date") else ["sla_status"])
	if meta.has_field("sales_quote"):
		fields.append("sales_quote")
	if meta.has_field("origin_port"):
		fields.append("origin_port")
	if meta.has_field("destination_port"):
		fields.append("destination_port")
	try:
		rows = frappe.get_list(
			doctype,
			filters=filters,
			fields=fields,
			limit_page_length=0,
			order_by="modified desc",
		)
	except Exception:
		return []
	out = []
	for r in rows:
		d = dict(r)
		d["doctype"] = doctype
		if status_field != "job_status":
			d["job_status"] = d.get(status_field)
		out.append(d)
	return out


def _attach_brands_to_jobs(jobs, quote_brand):
	for j in jobs:
		sq = (j.get("sales_quote") or "").strip()
		j["hv_brand"] = quote_brand.get(sq) or ""
	return jobs


@frappe.whitelist()
def get_high_value_operations_filter_users(job_status_filter=None):
	comp = (session_company_context().get("company") or "").strip()
	filters = {"docstatus": ["<", 2], "is_high_value": 1}
	if comp:
		filters["company"] = comp
	try:
		owners = frappe.get_list(
			"Sales Quote",
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
def get_high_value_operations_dashboard(
	limit=None,
	filter_user=None,
	alert_filter_user=None,
	airlines=None,
	job_status_filter=None,
	include_draft=None,
	attention=None,
):
	"""`airlines` carries selected HV Brands names (client reuse)."""
	ctx = session_company_context()
	comp = (ctx.get("company") or "").strip()
	selected = sanitize_link_values(parse_multi_link_param(airlines), "HV Brands")
	brands = _load_brands(selected)
	by_name, by_label = _brand_lookups(brands)
	quotes = _load_quotes(comp, filter_user, selected)
	quote_brand = {}
	quotes_by_brand = defaultdict(list)
	for q in quotes:
		code = resolve_quote_brand(q, by_name, by_label)
		q["hv_brand"] = code
		if q.get("name"):
			quote_brand[q.name] = code
		if code:
			quotes_by_brand[code].append(q)

	jobs = []
	for dt, _o, _d in HV_JOB_DOCTYPES:
		jobs.extend(_load_jobs(dt, comp, filter_user, job_status_filter, list(quote_brand)))
	try:
		jobs.extend(_load_jobs("Transport Job", comp, filter_user, job_status_filter, list(quote_brand)))
	except Exception:
		pass
	_attach_brands_to_jobs(jobs, quote_brand)
	jobs_by_brand = defaultdict(list)
	unassigned = []
	for j in jobs:
		code = (j.get("hv_brand") or "").strip()
		if code:
			jobs_by_brand[code].append(j)
		else:
			unassigned.append(j)

	alert_fu = alert_filter_user if alert_filter_user is not None else filter_user
	if (alert_fu or "").strip() != (filter_user or "").strip():
		alert_jobs = []
		for dt, _o, _d in HV_JOB_DOCTYPES:
			alert_jobs.extend(_load_jobs(dt, comp, alert_fu, job_status_filter, list(quote_brand)))
		try:
			alert_jobs.extend(_load_jobs("Transport Job", comp, alert_fu, job_status_filter, list(quote_brand)))
		except Exception:
			pass
		_attach_brands_to_jobs(alert_jobs, quote_brand)
	else:
		alert_jobs = jobs

	brand_rows = []
	for b in brands:
		code = b.name
		flags = classify_brand(quotes_by_brand.get(code), jobs_by_brand.get(code))
		brand_rows.append(
			{
				"name": code,
				"brand_name": b.brand_name or code,
				"flags": flags,
			}
		)

	attn = (attention or "all").strip().lower() or "all"
	if attn not in ("", "all"):
		brand_rows = [r for r in brand_rows if _matches_attention(r["flags"], attn)]

	owner_ids = [q.get("owner") for q in quotes] + [j.get("owner") for j in jobs]
	labels = owner_labels(owner_ids)
	work_rows, truncated = brand_work_rows(brand_rows, quotes_by_brand, jobs_by_brand, labels)
	mix = job_mix_counts(quotes, jobs)
	mix["unassigned"] = len(unassigned)
	kpis = count_brand_kpis([r["flags"] for r in brand_rows])
	kpis.update(count_sla_kpis(jobs))
	summary, items = merge_alert_items(brand_alerts(brand_rows), sla_alerts(alert_jobs))
	airline_options = [
		{"value": b.name, "label": "{0} ({1})".format(b.brand_name or b.name, b.name)}
		for b in _load_brands(None)
	]
	out = {
		"kpis": kpis,
		"pipeline": pipeline_counts(brand_rows),
		"work_rows": work_rows,
		"work_truncated": truncated,
		"user_workload": hv_user_workload(quotes, jobs, labels),
		"attention_rows": attention_rows(work_rows),
		"unassigned_rows": unassigned_work_rows(unassigned, labels),
		"mix": mix,
		"alert_summary": summary,
		"alert_items": items,
		"airline_options": airline_options,
		"limits_applied": {
			"max_shipments": None,
			"shipment_count": kpis["brands"],
		},
		"filters_applied": {
			"job_status_filter": (job_status_filter or "").strip() or "ongoing",
			"attention": attn,
			"company": comp or None,
		},
		"unassigned_jobs": len(unassigned),
	}
	out.update(ctx)
	return out
