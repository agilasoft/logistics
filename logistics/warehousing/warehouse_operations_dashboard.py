# Copyright (c) 2026, Agilasoft and contributors
"""Job-operations payload for the Warehousing Home workspace (jobs, owners, open orders, SLA)."""

from __future__ import unicode_literals

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import getdate, today

from logistics.operations_dashboard.heat_map_core import (
	MAX_ALERT_ITEMS,
	parse_multi_link_param,
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
JOB_TYPES = ("Putaway", "Pick", "Move", "VAS", "Stocktake", "Cross Dock")
ORDER_DOCTYPES = (
	"Inbound Order",
	"Release Order",
	"VAS Order",
	"Transfer Order",
	"Stocktake Order",
	"Cross-Docking Order",
)
GATE_PASS_OPEN = ("Draft", "Authorized", "In Progress")
MAX_WORK_ROWS = 200
MAX_ORDER_ROWS = 40
SEV_RANK = {
	"overdue": 0,
	"at_risk": 1,
	"live": 2,
	"active": 3,
	"idle": 5,
}


def _status_filter(job_status_filter):
	key = (job_status_filter or "open").strip() or "open"
	if key in ("active", "open", "open_with_draft"):
		return ["not in", list(JOB_CLOSED)]
	if key in ("ongoing",):
		return ["not in", list(JOB_CLOSED) + ["Draft"]]
	if key in JOB_STATUSES:
		return key
	return ["not in", list(JOB_CLOSED)]


def _as_date(val):
	if not val:
		return None
	try:
		return getdate(val)
	except Exception:
		return None


def _short_date(val):
	if not val:
		return ""
	return str(val)[:10]


def classify_job(row):
	"""Clock flags for one Warehouse Job. Draft counts as active warehouse work."""
	status = (row.get("job_status") or "").strip()
	sla = (row.get("sla_status") or "").strip()
	active = status not in JOB_CLOSED
	live = status in JOB_LIVE
	overdue = bool(active and sla == "Breached")
	at_risk = bool(active and sla == "At Risk")
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
		"at_risk": at_risk,
		"idle": not active,
		"severity": severity,
	}


def count_job_kpis(rows):
	kpis = {"jobs": 0, "active": 0, "live": 0, "overdue": 0}
	for r in rows or []:
		flags = r.get("flags") or classify_job(r)
		kpis["jobs"] += 1
		if flags.get("active"):
			kpis["active"] += 1
		if flags.get("live"):
			kpis["live"] += 1
		if flags.get("overdue"):
			kpis["overdue"] += 1
	return kpis


def count_sla_kpis(rows):
	at_risk = 0
	breached = 0
	for r in rows or []:
		status = (r.get("job_status") or "").strip()
		if status in JOB_CLOSED:
			continue
		sla = (r.get("sla_status") or "").strip()
		if sla == "Breached":
			breached += 1
		elif sla == "At Risk":
			at_risk += 1
	return {"sla_at_risk": at_risk, "sla_breached": breached}


def pipeline_counts(rows):
	by_type = defaultdict(int)
	for r in rows or []:
		if (r.get("job_status") or "").strip() in JOB_CLOSED:
			continue
		key = (r.get("type") or "").strip() or _("Unspecified")
		by_type[key] += 1
	return [{"lifecycle_stage": k, "program_count": v} for k, v in sorted(by_type.items())]


def status_mix(rows):
	by = defaultdict(int)
	for r in rows or []:
		by[(r.get("job_status") or "").strip() or _("Unspecified")] += 1
	return dict(by)


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
		if (r.get("severity") or "") in ("overdue", "at_risk")
	]
	return hot[:limit]


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
	return True


def job_work_rows(rows, labels, limit=MAX_WORK_ROWS):
	enriched = []
	for r in rows or []:
		flags = r.get("flags") or classify_job(r)
		ow = (r.get("owner") or "").strip()
		enriched.append(
			{
				"name": r.get("name"),
				"title": r.get("name"),
				"doctype": "Warehouse Job",
				"type": r.get("type") or "",
				"job_status": r.get("job_status") or "",
				"customer": r.get("customer") or "",
				"reference_order_type": r.get("reference_order_type") or "",
				"reference_order": r.get("reference_order") or "",
				"job_open_date": _short_date(r.get("job_open_date")),
				"sla_target_date": _short_date(r.get("sla_target_date")),
				"sla_status": r.get("sla_status") or "",
				"owner": ow,
				"owner_label": labels.get(ow) or ow or _("Unassigned"),
				"severity": flags.get("severity") or "active",
				"overdue": flags.get("overdue"),
				"live": flags.get("live"),
				"at_risk": flags.get("at_risk"),
			}
		)
	enriched.sort(
		key=lambda r: (
			SEV_RANK.get(r["severity"], 9),
			r.get("job_open_date") or "9999",
			(r.get("name") or "").lower(),
		)
	)
	return enriched[:limit], max(0, len(enriched) - limit)


def job_user_workload(rows, labels):
	by = {}
	for r in rows or []:
		flags = r.get("flags") or classify_job(r)
		ow = (r.get("owner") or "").strip() or _("Unassigned")
		if ow not in by:
			by[ow] = {
				"owner": "" if ow == _("Unassigned") else ow,
				"label": labels.get(ow) or ow,
				"jobs": 0,
				"live": 0,
				"overdue": 0,
				"sla_at_risk": 0,
				"sla_breached": 0,
			}
		b = by[ow]
		b["jobs"] += 1
		if flags.get("live"):
			b["live"] += 1
		if flags.get("overdue"):
			b["overdue"] += 1
			b["sla_breached"] += 1
		elif flags.get("at_risk"):
			b["sla_at_risk"] += 1
	out = list(by.values())
	out.sort(
		key=lambda r: (
			-r["overdue"],
			-r["sla_at_risk"],
			-r["jobs"],
			(r.get("label") or "").lower(),
		)
	)
	return out


def job_alerts(rows):
	items = []
	for r in rows or []:
		flags = r.get("flags") or classify_job(r)
		if not flags.get("overdue") and not flags.get("at_risk"):
			continue
		name = r.get("name")
		typ = r.get("type") or ""
		if flags.get("overdue"):
			items.append(
				{
					"level": "danger",
					"msg": _("SLA breached: {0} ({1}, target {2})").format(
						name, typ or _("Job"), r.get("sla_target_date") or "—"
					),
					"shipment": name,
					"doctype": "Warehouse Job",
				}
			)
		else:
			items.append(
				{
					"level": "warning",
					"msg": _("SLA at risk: {0} ({1}, target {2})").format(
						name, typ or _("Job"), r.get("sla_target_date") or "—"
					),
					"shipment": name,
					"doctype": "Warehouse Job",
				}
			)
	return items


def open_order_alerts(order_rows, today_date=None):
	today_date = getdate(today_date or today())
	items = []
	for r in order_rows or []:
		due = _as_date(r.get("due_date"))
		name = r.get("name")
		dt = r.get("doctype")
		if due and due < today_date:
			items.append(
				{
					"level": "danger",
					"msg": _("Order past due with no warehouse job: {0} (due {1})").format(
						name, r.get("due_date") or "—"
					),
					"shipment": name,
					"doctype": dt,
				}
			)
		elif due and due == today_date:
			items.append(
				{
					"level": "warning",
					"msg": _("Order due today with no warehouse job: {0}").format(name),
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


def _parse_types(airlines):
	raw = parse_multi_link_param(airlines)
	out = []
	for v in raw or []:
		val = (v or "").strip()
		if val in JOB_TYPES:
			out.append(val)
	return out


def _load_jobs(company, filter_user, job_status_filter, selected_types):
	filters = {
		"docstatus": ["<", 2],
		"job_status": _status_filter(job_status_filter),
	}
	if company:
		filters["company"] = company
	fu = (filter_user or "").strip()
	if fu and frappe.db.exists("User", fu):
		filters["owner"] = fu
	if selected_types:
		filters["type"] = ["in", selected_types]
	try:
		rows = frappe.get_list(
			"Warehouse Job",
			filters=filters,
			fields=[
				"name",
				"type",
				"job_status",
				"customer",
				"owner",
				"job_open_date",
				"reference_order_type",
				"reference_order",
				"sla_status",
				"sla_target_date",
			],
			limit_page_length=0,
			order_by="job_open_date desc",
		)
	except Exception:
		return []
	out = []
	for r in rows:
		d = dict(r)
		d["flags"] = classify_job(d)
		out.append(d)
	return out


def _linked_order_names(doctype):
	try:
		rows = frappe.get_all(
			"Warehouse Job",
			filters={"reference_order_type": doctype},
			fields=["reference_order"],
			limit_page_length=0,
		)
	except Exception:
		return set()
	return {(r.reference_order or "").strip() for r in rows if (r.reference_order or "").strip()}


def classify_open_order(row, today_date=None):
	today_date = getdate(today_date or today())
	due = _as_date(row.get("due_date"))
	overdue = bool(due and due < today_date)
	due_today = bool(due and due == today_date)
	if overdue:
		severity = "overdue"
	elif due_today:
		severity = "at_risk"
	else:
		severity = "active"
	return {"overdue": overdue, "due_today": due_today, "severity": severity}


def _load_open_orders(company, filter_user, today_date=None):
	today_date = getdate(today_date or today())
	fu = (filter_user or "").strip()
	out = []
	for dt in ORDER_DOCTYPES:
		filters = {"docstatus": ["<", 2]}
		if company:
			filters["company"] = company
		if fu and frappe.db.exists("User", fu):
			filters["owner"] = fu
		fields = ["name", "customer", "owner", "due_date", "planned_date"]
		meta = frappe.get_meta(dt)
		if meta.has_field("priority"):
			fields.append("priority")
		try:
			rows = frappe.get_list(
				dt,
				filters=filters,
				fields=fields,
				limit_page_length=0,
				order_by="due_date asc",
			)
		except Exception:
			rows = []
		linked = _linked_order_names(dt)
		for r in rows or []:
			if (r.get("name") or "") in linked:
				continue
			d = dict(r)
			d["doctype"] = dt
			flags = classify_open_order(d, today_date=today_date)
			d.update(flags)
			out.append(d)
	out.sort(
		key=lambda r: (
			0 if r.get("overdue") else 1 if r.get("due_today") else 2,
			_short_date(r.get("due_date")) or "9999",
			r.get("name") or "",
		)
	)
	return out


def open_order_rows(order_rows, labels, limit=MAX_ORDER_ROWS):
	out = []
	for r in (order_rows or [])[:limit]:
		ow = (r.get("owner") or "").strip()
		out.append(
			{
				"name": r.get("name"),
				"doctype": r.get("doctype"),
				"customer": r.get("customer") or "",
				"due_date": _short_date(r.get("due_date")),
				"planned_date": _short_date(r.get("planned_date")),
				"priority": r.get("priority") or "",
				"owner": ow,
				"owner_label": labels.get(ow) or ow or _("Unassigned"),
				"severity": r.get("severity") or "active",
			}
		)
	return out


def _gate_pass_open_count(company):
	filters = {"docstatus": ["<", 2], "status": ["in", list(GATE_PASS_OPEN)]}
	if company:
		filters["company"] = company
	try:
		return len(frappe.get_all("Gate Pass", filters=filters, pluck="name")) or 0
	except Exception:
		return 0


@frappe.whitelist()
def get_warehouse_operations_filter_users(job_status_filter=None):
	comp = (session_company_context().get("company") or "").strip()
	filters = {
		"docstatus": ["<", 2],
		"job_status": _status_filter(job_status_filter),
	}
	if comp:
		filters["company"] = comp
	try:
		owners = frappe.get_list(
			"Warehouse Job",
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
def get_warehouse_operations_dashboard(
	limit=None,
	filter_user=None,
	alert_filter_user=None,
	airlines=None,
	job_status_filter=None,
	include_draft=None,
	attention=None,
):
	"""`airlines` carries selected Warehouse Job types (client reuse)."""
	ctx = session_company_context()
	comp = (ctx.get("company") or "").strip()
	selected_types = _parse_types(airlines)
	jobs = _load_jobs(comp, filter_user, job_status_filter, selected_types)
	attn = (attention or "all").strip().lower() or "all"
	if attn not in ("", "all"):
		jobs = [r for r in jobs if _matches_attention(r["flags"], attn)]
	if limit is not None and str(limit).strip() != "":
		try:
			lim_val = int(limit)
			if lim_val > 0:
				jobs = jobs[:lim_val]
		except Exception:
			pass

	alert_fu = alert_filter_user if alert_filter_user is not None else filter_user
	if (alert_fu or "").strip() != (filter_user or "").strip():
		alert_jobs = _load_jobs(comp, alert_fu, job_status_filter, selected_types)
		if attn not in ("", "all"):
			alert_jobs = [r for r in alert_jobs if _matches_attention(r["flags"], attn)]
		alert_orders = _load_open_orders(comp, alert_fu)
	else:
		alert_jobs = jobs
		alert_orders = _load_open_orders(comp, filter_user)

	open_orders = alert_orders if (alert_fu or "").strip() == (filter_user or "").strip() else _load_open_orders(comp, filter_user)

	owner_ids = [j.get("owner") for j in jobs] + [o.get("owner") for o in open_orders]
	labels = owner_labels(owner_ids)
	work_all, _ignored = job_work_rows(jobs, labels, limit=10 ** 6)
	truncated = max(0, len(work_all) - MAX_WORK_ROWS)
	work_rows = work_all[:MAX_WORK_ROWS]
	kpis = count_job_kpis(jobs)
	kpis.update(count_sla_kpis(jobs))
	kpis["open_orders"] = len(open_orders)
	mix = status_mix(jobs)
	type_mix = {p["lifecycle_stage"]: p["program_count"] for p in pipeline_counts(jobs)}
	summary, items = merge_alert_items(job_alerts(alert_jobs), open_order_alerts(alert_orders))
	out = {
		"kpis": kpis,
		"pipeline": pipeline_counts(jobs),
		"work_rows": work_rows,
		"work_truncated": truncated,
		"user_workload": job_user_workload(jobs, labels),
		"attention_rows": attention_rows(work_rows),
		"open_order_rows": open_order_rows(open_orders, labels),
		"open_orders": len(open_orders),
		"mix": {
			"jobs": kpis.get("jobs") or 0,
			"open_orders": len(open_orders),
			"gate_passes": _gate_pass_open_count(comp),
			"types": type_mix,
			"statuses": mix,
		},
		"alert_summary": summary,
		"alert_items": items,
		"airline_options": [{"value": t, "label": t} for t in JOB_TYPES],
		"limits_applied": {
			"max_shipments": None,
			"shipment_count": kpis["jobs"],
		},
		"filters_applied": {
			"job_status_filter": (job_status_filter or "").strip() or "open",
			"attention": attn,
			"company": comp or None,
		},
	}
	out.update(ctx)
	return out
