# Copyright (c) 2026, Agilasoft and contributors
"""Job + accounting monitor for the Job Management Home workspace."""

from __future__ import unicode_literals

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt

from logistics.operations_dashboard.heat_map_core import (
	MAX_ALERT_ITEMS,
	parse_multi_link_param,
	session_company_context,
)

JOB_TYPES = (
	"Air Shipment",
	"Sea Shipment",
	"Transport Job",
	"Warehouse Job",
	"Declaration",
	"General Job",
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
BILLING_OVERDUE = frozenset({"Overdue"})
BILLING_OPEN = frozenset({"Not Billed", "Pending", "To Bill", "Partially Billed"})
MAX_WORK_ROWS = 200
MAX_EXCEPTION_ROWS = 40
SEV_RANK = {
	"overdue": 0,
	"at_risk": 1,
	"live": 2,
	"active": 3,
	"idle": 5,
}

CUSTOMER_FIELD = {
	"Air Shipment": "local_customer",
	"Sea Shipment": "local_customer",
}


def _as_float(val):
	return flt(val or 0)


def _short_date(val):
	if not val:
		return ""
	return str(val)[:10]


def _meta_field(doctype, name):
	try:
		return frappe.get_meta(doctype).has_field(name)
	except Exception:
		return False


def status_field_for(doctype):
	if _meta_field(doctype, "job_status"):
		return "job_status"
	if _meta_field(doctype, "status"):
		return "status"
	return None


def billing_field_for(doctype):
	if _meta_field(doctype, "billing_status"):
		return "billing_status"
	if _meta_field(doctype, "payment_status"):
		return "payment_status"
	return None


def customer_field_for(doctype):
	preferred = CUSTOMER_FIELD.get(doctype)
	if preferred and _meta_field(doctype, preferred):
		return preferred
	if _meta_field(doctype, "customer"):
		return "customer"
	return None


def wip_status_of(row):
	if _as_float(row.get("wip_amount")) > 0:
		return "Open"
	if _as_float(row.get("recognized_revenue")) > 0:
		return "Recognized"
	return "Not Started"


def accrual_status_of(row):
	if _as_float(row.get("accrual_amount")) > 0:
		return "Open"
	if _as_float(row.get("recognized_costs")) > 0:
		return "Recognized"
	return "Not Started"


def job_status_of(row):
	status = (row.get("job_status") or "").strip()
	if status:
		return status
	docstatus = int(row.get("docstatus") or 0)
	if docstatus == 0:
		return "Draft"
	if docstatus == 2:
		return "Cancelled"
	return "Submitted"


def classify_job(row):
	"""Clock + accounting flags for one operational job."""
	status = job_status_of(row)
	billing = (row.get("billing_status") or "").strip()
	wip_status = wip_status_of(row)
	accrual_status = accrual_status_of(row)
	active = status not in JOB_CLOSED
	live = status in JOB_LIVE
	wip_open = wip_status == "Open"
	accrual_open = accrual_status == "Open"
	closed_open_balance = (not active) and (wip_open or accrual_open)
	billing_overdue = billing in BILLING_OVERDUE
	unbilled = billing in BILLING_OPEN
	wip_enabled = row.get("wip_recognition_enabled")
	accrual_enabled = row.get("accrual_recognition_enabled")
	wip_pending = bool(
		active
		and (wip_enabled in (None, 1, True, "1"))
		and _as_float(row.get("estimated_revenue")) > 0
		and wip_status == "Not Started"
	)
	accrual_pending = bool(
		active
		and (accrual_enabled in (None, 1, True, "1"))
		and _as_float(row.get("estimated_costs")) > 0
		and accrual_status == "Not Started"
	)
	overdue = bool(closed_open_balance or billing_overdue)
	at_risk = bool(not overdue and (wip_pending or accrual_pending or (wip_open and unbilled)))
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
		"wip_open": wip_open,
		"accrual_open": accrual_open,
		"wip_status": wip_status,
		"accrual_status": accrual_status,
		"wip_pending": wip_pending,
		"accrual_pending": accrual_pending,
		"closed_open_balance": closed_open_balance,
		"billing_overdue": billing_overdue,
		"unbilled": unbilled,
		"severity": severity,
		"job_status": status,
	}


def count_job_kpis(rows):
	kpis = {
		"jobs": 0,
		"active": 0,
		"live": 0,
		"overdue": 0,
		"wip_open": 0,
		"accrual_open": 0,
		"billing_overdue": 0,
		"unbilled": 0,
		"wip_amount": 0.0,
		"accrual_amount": 0.0,
	}
	for r in rows or []:
		flags = r.get("flags") or classify_job(r)
		kpis["jobs"] += 1
		if flags.get("active"):
			kpis["active"] += 1
		if flags.get("live"):
			kpis["live"] += 1
		if flags.get("overdue"):
			kpis["overdue"] += 1
		if flags.get("wip_open"):
			kpis["wip_open"] += 1
			kpis["wip_amount"] += _as_float(r.get("wip_amount"))
		if flags.get("accrual_open"):
			kpis["accrual_open"] += 1
			kpis["accrual_amount"] += _as_float(r.get("accrual_amount"))
		if flags.get("billing_overdue"):
			kpis["billing_overdue"] += 1
		if flags.get("unbilled"):
			kpis["unbilled"] += 1
	kpis["wip_amount"] = flt(kpis["wip_amount"], 2)
	kpis["accrual_amount"] = flt(kpis["accrual_amount"], 2)
	return kpis


def pipeline_counts(rows):
	by_type = defaultdict(int)
	for r in rows or []:
		if job_status_of(r) in JOB_CLOSED:
			continue
		key = (r.get("job_type") or "").strip() or _("Unspecified")
		by_type[key] += 1
	return [{"lifecycle_stage": k, "program_count": v} for k, v in sorted(by_type.items())]


def _count_map(rows, keyfn):
	by = defaultdict(int)
	for r in rows or []:
		by[keyfn(r)] += 1
	return dict(by)


def accounting_mix(rows):
	return {
		"wip": _count_map(rows, lambda r: (r.get("flags") or classify_job(r)).get("wip_status") or "Not Started"),
		"accrual": _count_map(
			rows, lambda r: (r.get("flags") or classify_job(r)).get("accrual_status") or "Not Started"
		),
		"billing": _count_map(rows, lambda r: (r.get("billing_status") or "").strip() or _("None")),
		"statuses": _count_map(rows, job_status_of),
	}


def owner_labels(user_ids):
	ids = sorted({(x or "").strip() for x in (user_ids or []) if (x or "").strip()})
	if not ids:
		return {}
	rows = frappe.get_all("User", filters={"name": ["in", ids]}, fields=["name", "full_name"])
	return {r.name: (r.full_name or r.name) for r in rows}


def _matches_status_filter(flags, job_status_filter):
	key = (job_status_filter or "open").strip() or "open"
	status = flags.get("job_status") or ""
	if key in ("active", "open", "open_with_draft"):
		return status not in JOB_CLOSED or flags.get("closed_open_balance")
	if key in ("ongoing",):
		return (status not in JOB_CLOSED and status != "Draft") or flags.get("closed_open_balance")
	if key in JOB_STATUSES:
		return status == key
	return status not in JOB_CLOSED


def _matches_attention(flags, attention):
	key = (attention or "all").strip().lower() or "all"
	if key in ("", "all"):
		return True
	if key == "overdue":
		return flags["overdue"]
	if key in ("alerts", "at_risk"):
		return flags["overdue"] or flags["at_risk"]
	if key == "wip":
		return flags["wip_open"] or flags["wip_pending"]
	if key == "accrual":
		return flags["accrual_open"] or flags["accrual_pending"]
	if key in ("billing", "unbilled"):
		return flags["billing_overdue"] or flags["unbilled"]
	if key == "live":
		return flags["live"]
	if key == "active":
		return flags["active"]
	return True


def attention_rows(work_rows, limit=8):
	hot = [r for r in (work_rows or []) if (r.get("severity") or "") in ("overdue", "at_risk")]
	return hot[:limit]


def exception_rows(work_rows, limit=MAX_EXCEPTION_ROWS):
	hot = [
		r
		for r in (work_rows or [])
		if r.get("closed_open_balance")
		or r.get("billing_overdue")
		or r.get("wip_pending")
		or r.get("accrual_pending")
	]
	return hot[:limit]


def job_work_rows(rows, labels, limit=MAX_WORK_ROWS):
	enriched = []
	for r in rows or []:
		flags = r.get("flags") or classify_job(r)
		ow = (r.get("owner") or "").strip()
		enriched.append(
			{
				"name": r.get("name"),
				"title": r.get("name"),
				"doctype": r.get("job_type") or r.get("doctype"),
				"job_type": r.get("job_type") or "",
				"job_status": flags.get("job_status") or "",
				"billing_status": r.get("billing_status") or "",
				"customer": r.get("customer") or "",
				"job_open_date": _short_date(r.get("job_open_date")),
				"wip_amount": flt(r.get("wip_amount") or 0, 2),
				"accrual_amount": flt(r.get("accrual_amount") or 0, 2),
				"wip_status": flags.get("wip_status"),
				"accrual_status": flags.get("accrual_status"),
				"owner": ow,
				"owner_label": labels.get(ow) or ow or _("Unassigned"),
				"severity": flags.get("severity") or "active",
				"overdue": flags.get("overdue"),
				"live": flags.get("live"),
				"at_risk": flags.get("at_risk"),
				"wip_open": flags.get("wip_open"),
				"accrual_open": flags.get("accrual_open"),
				"wip_pending": flags.get("wip_pending"),
				"accrual_pending": flags.get("accrual_pending"),
				"closed_open_balance": flags.get("closed_open_balance"),
				"billing_overdue": flags.get("billing_overdue"),
				"unbilled": flags.get("unbilled"),
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
				"wip_open": 0,
				"accrual_open": 0,
				"billing_overdue": 0,
			}
		b = by[ow]
		b["jobs"] += 1
		if flags.get("live"):
			b["live"] += 1
		if flags.get("overdue"):
			b["overdue"] += 1
		if flags.get("wip_open"):
			b["wip_open"] += 1
		if flags.get("accrual_open"):
			b["accrual_open"] += 1
		if flags.get("billing_overdue"):
			b["billing_overdue"] += 1
	out = list(by.values())
	out.sort(
		key=lambda r: (
			-r["overdue"],
			-r["wip_open"],
			-r["accrual_open"],
			-r["jobs"],
			(r.get("label") or "").lower(),
		)
	)
	return out


def job_alerts(rows):
	items = []
	for r in rows or []:
		flags = r.get("flags") or classify_job(r)
		name = r.get("name")
		dt = r.get("job_type") or r.get("doctype") or "Job Number"
		typ = r.get("job_type") or ""
		if flags.get("closed_open_balance"):
			parts = []
			if flags.get("wip_open"):
				parts.append(_("WIP {0}").format(flt(r.get("wip_amount") or 0, 2)))
			if flags.get("accrual_open"):
				parts.append(_("Accrual {0}").format(flt(r.get("accrual_amount") or 0, 2)))
			items.append(
				{
					"level": "danger",
					"msg": _("Closed job still open in accounts: {0} ({1}) — {2}").format(
						name, typ or dt, ", ".join(parts) or _("open balance")
					),
					"shipment": name,
					"doctype": dt,
				}
			)
		if flags.get("billing_overdue"):
			items.append(
				{
					"level": "danger",
					"msg": _("Billing overdue: {0} ({1})").format(name, typ or dt),
					"shipment": name,
					"doctype": dt,
				}
			)
		if flags.get("wip_pending"):
			items.append(
				{
					"level": "warning",
					"msg": _("WIP not started: {0} ({1}, est. revenue {2})").format(
						name, typ or dt, flt(r.get("estimated_revenue") or 0, 2)
					),
					"shipment": name,
					"doctype": dt,
				}
			)
		if flags.get("accrual_pending"):
			items.append(
				{
					"level": "warning",
					"msg": _("Accrual not started: {0} ({1}, est. cost {2})").format(
						name, typ or dt, flt(r.get("estimated_costs") or 0, 2)
					),
					"shipment": name,
					"doctype": dt,
				}
			)
		if flags.get("wip_open") and flags.get("unbilled") and not flags.get("closed_open_balance"):
			items.append(
				{
					"level": "info",
					"msg": _("Open WIP, not billed: {0} ({1})").format(name, typ or dt),
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
	types = selected_types or list(JOB_TYPES)
	fu = (filter_user or "").strip()
	out = []
	for dt in types:
		if not frappe.db.exists("DocType", dt):
			continue
		meta = frappe.get_meta(dt)
		if not meta.has_field("wip_amount"):
			continue
		filters = {}
		want_cancelled = (job_status_filter or "").strip() == "Cancelled"
		filters["docstatus"] = 2 if want_cancelled else ["<", 2]
		if company and meta.has_field("company"):
			filters["company"] = company
		if fu and frappe.db.exists("User", fu):
			filters["owner"] = fu
		sf = status_field_for(dt)
		bf = billing_field_for(dt)
		cf = customer_field_for(dt)
		fields = ["name", "owner", "docstatus"]
		for fname in (
			sf,
			bf,
			cf,
			"job_open_date",
			"estimated_revenue",
			"estimated_costs",
			"wip_amount",
			"accrual_amount",
			"recognized_revenue",
			"recognized_costs",
			"wip_recognition_enabled",
			"accrual_recognition_enabled",
			"wip_closed",
			"accrual_closed",
		):
			if fname and meta.has_field(fname) and fname not in fields:
				fields.append(fname)
		try:
			rows = frappe.get_list(
				dt,
				filters=filters,
				fields=fields,
				limit_page_length=0,
				order_by="modified desc",
			)
		except Exception:
			rows = []
		for r in rows or []:
			d = dict(r)
			d["job_type"] = dt
			d["doctype"] = dt
			if sf and sf != "job_status":
				d["job_status"] = d.get(sf) or ""
			if bf and bf != "billing_status":
				d["billing_status"] = d.get(bf) or ""
			if cf and cf != "customer":
				d["customer"] = d.get(cf) or ""
			d["flags"] = classify_job(d)
			if not _matches_status_filter(d["flags"], job_status_filter):
				continue
			out.append(d)
	return out


def _collect_owners(company, job_status_filter):
	seen = []
	found = set()
	for dt in JOB_TYPES:
		if not frappe.db.exists("DocType", dt):
			continue
		meta = frappe.get_meta(dt)
		if not meta.has_field("wip_amount"):
			continue
		filters = {"docstatus": ["<", 2]}
		if company and meta.has_field("company"):
			filters["company"] = company
		try:
			owners = frappe.get_list(
				dt,
				filters=filters,
				pluck="owner",
				distinct=True,
				limit_page_length=80,
				order_by="owner asc",
			)
		except Exception:
			owners = []
		for owner in owners or []:
			if not owner or owner in found:
				continue
			found.add(owner)
			seen.append(owner)
			if len(seen) >= 150:
				return seen
	return seen


@frappe.whitelist()
def get_job_operations_filter_users(job_status_filter=None):
	comp = (session_company_context().get("company") or "").strip()
	owners = _collect_owners(comp, job_status_filter)
	out = [{"value": "", "label": _("All users")}]
	for owner in owners:
		full = frappe.db.get_value("User", owner, "full_name") or owner
		out.append({"value": owner, "label": "{0} ({1})".format(full, owner)})
	return out


@frappe.whitelist()
def get_job_operations_dashboard(
	limit=None,
	filter_user=None,
	alert_filter_user=None,
	airlines=None,
	job_status_filter=None,
	include_draft=None,
	attention=None,
):
	"""`airlines` carries selected job DocTypes (client reuse)."""
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
	else:
		alert_jobs = jobs

	labels = owner_labels([j.get("owner") for j in jobs])
	work_all, _ignored = job_work_rows(jobs, labels, limit=10 ** 6)
	truncated = max(0, len(work_all) - MAX_WORK_ROWS)
	work_rows = work_all[:MAX_WORK_ROWS]
	kpis = count_job_kpis(jobs)
	mix = accounting_mix(jobs)
	summary, items = merge_alert_items(job_alerts(alert_jobs))
	out = {
		"kpis": kpis,
		"pipeline": pipeline_counts(jobs),
		"work_rows": work_rows,
		"work_truncated": truncated,
		"user_workload": job_user_workload(jobs, labels),
		"attention_rows": attention_rows(work_rows),
		"exception_rows": exception_rows(work_all),
		"mix": {
			"jobs": kpis.get("jobs") or 0,
			"wip_open": kpis.get("wip_open") or 0,
			"accrual_open": kpis.get("accrual_open") or 0,
			"unbilled": kpis.get("unbilled") or 0,
			"billing_overdue": kpis.get("billing_overdue") or 0,
			"wip_amount": kpis.get("wip_amount") or 0,
			"accrual_amount": kpis.get("accrual_amount") or 0,
			"wip": mix["wip"],
			"accrual": mix["accrual"],
			"billing": mix["billing"],
			"statuses": mix["statuses"],
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
