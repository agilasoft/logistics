# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt
"""Shared loaders and aggregations for High Value script reports."""

from __future__ import unicode_literals

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, date_diff, flt, getdate, nowdate

from logistics.high_value.high_value_operations_dashboard import (
	JOB_CLOSED,
	JOB_LIVE,
	_brand_lookups,
	classify_brand,
	owner_labels,
	resolve_quote_brand,
)

HV_JOB_DOCTYPES = ("Air Shipment", "Sea Shipment", "Transport Job")
MODALITY_DOCTYPES = (
	("Quotes", "Sales Quote"),
	("Air", "Air Shipment"),
	("Sea", "Sea Shipment"),
	("Transport", "Transport Job"),
	("Customs", "Declaration"),
	("Warehouse", "Warehouse Job"),
)
MODALITY_TO_DOCTYPE = {label: dt for label, dt in MODALITY_DOCTYPES if label != "Quotes"}
DOCTYPE_TO_MODALITY = {dt: label for label, dt in MODALITY_DOCTYPES}

AGING_BUCKETS = (
	"Overdue",
	"Due today",
	"1-3 days",
	"4-7 days",
	"8+ days",
	"No target",
)

SLA_RANK = {"Breached": 0, "At Risk": 1, "On Track": 2, "Not Applicable": 3}


def sla_age_bucket(target, as_on=None):
	"""Bucket a job SLA target date relative to as_on (default today)."""
	as_on = getdate(as_on or nowdate())
	if not target:
		return "No target"
	try:
		due = getdate(target)
	except Exception:
		return "No target"
	days = date_diff(due, as_on)
	if days < 0:
		return "Overdue"
	if days == 0:
		return "Due today"
	if days <= 3:
		return "1-3 days"
	if days <= 7:
		return "4-7 days"
	return "8+ days"


def _safe_get_list(doctype, filters, fields, order_by="modified desc"):
	try:
		rows = frappe.get_list(
			doctype,
			filters=filters,
			fields=fields,
			limit_page_length=0,
			order_by=order_by,
		)
	except Exception:
		return []
	return [dict(r) for r in rows or []]


def load_brands(selected=None):
	filters = {}
	if selected:
		names = selected if isinstance(selected, (list, tuple)) else [selected]
		names = [n for n in names if n]
		if names:
			filters["name"] = ["in", names]
	return frappe.get_all(
		"HV Brands",
		filters=filters or None,
		fields=["name", "brand_name"],
		limit_page_length=0,
		order_by="brand_name asc",
	)


def load_hv_quotes(filters=None):
	"""HV Sales Quotes with brand/amount fields. Brand filter applied after resolve."""
	filters = frappe._dict(filters or {})
	meta = frappe.get_meta("Sales Quote")
	flt = {"docstatus": ["<", 2], "is_high_value": 1}
	company = (filters.get("company") or "").strip()
	if company and meta.has_field("company"):
		flt["company"] = company
	status = (filters.get("status") or "").strip()
	if status:
		flt["status"] = status

	fields = [
		"name",
		"customer",
		"status",
		"docstatus",
		"owner",
		"date",
		"valid_until",
		"creation",
	]
	for fname in (
		"hv_brand",
		"company",
		"origin_port",
		"destination_port",
		"total_estimated_revenue",
		"total_estimated_cost",
		"estimated_profit",
		"estimated_margin_pct",
	):
		if meta.has_field(fname):
			fields.append(fname)

	rows = _safe_get_list("Sales Quote", flt, fields, order_by="modified desc")
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	if from_date or to_date:
		from_d = getdate(from_date) if from_date else None
		to_d = getdate(to_date) if to_date else None
		kept = []
		for q in rows:
			d = getdate(q.get("date") or q.get("creation"))
			if from_d and d < from_d:
				continue
			if to_d and d > to_d:
				continue
			kept.append(q)
		rows = kept
	return rows


def load_hv_jobs(filters=None):
	"""HV Air / Sea / Transport jobs. Status default is ongoing (not closed, not draft)."""
	filters = frappe._dict(filters or {})
	company = (filters.get("company") or "").strip()
	modality = (filters.get("modality") or "").strip()
	job_status_filter = (filters.get("job_status_filter") or "ongoing").strip() or "ongoing"
	if (filters.get("job_status") or "").strip():
		job_status_filter = "all"
	wanted = HV_JOB_DOCTYPES
	if modality:
		dt = MODALITY_TO_DOCTYPE.get(modality) or modality
		wanted = (dt,) if dt in HV_JOB_DOCTYPES else ()

	out = []
	for doctype in wanted:
		out.extend(_load_jobs_for(doctype, company, job_status_filter))
	return out


def _status_clause(job_status_filter):
	key = (job_status_filter or "ongoing").strip() or "ongoing"
	if key in ("active", "ongoing"):
		return ["not in", list(JOB_CLOSED) + ["Draft"]]
	if key in ("open", "open_with_draft"):
		return ["not in", list(JOB_CLOSED)]
	if key == "all":
		return None
	return key


def _load_jobs_for(doctype, company, job_status_filter):
	if not frappe.db.exists("DocType", doctype):
		return []
	meta = frappe.get_meta(doctype)
	if not meta.has_field("is_high_value"):
		return []
	status_field = "job_status" if meta.has_field("job_status") else "status"
	if not meta.has_field(status_field):
		return []
	flt = {"docstatus": ["<", 2], "is_high_value": 1}
	clause = _status_clause(job_status_filter)
	if clause is not None:
		flt[status_field] = clause
	if company and meta.has_field("company"):
		flt["company"] = company

	fields = ["name", status_field, "owner", "modified"]
	for fname in (
		"sla_status",
		"sla_target_date",
		"sales_quote",
		"customer",
		"company",
		"origin_port",
		"destination_port",
	):
		if meta.has_field(fname) and fname not in fields:
			fields.append(fname)

	rows = _safe_get_list(doctype, flt, fields)
	out = []
	for r in rows:
		r["doctype"] = doctype
		if status_field != "job_status":
			r["job_status"] = r.get(status_field)
		r["modality"] = DOCTYPE_TO_MODALITY.get(doctype) or doctype
		out.append(r)
	return out


def enrich_quotes_and_jobs(quotes, jobs, brands=None):
	"""Resolve hv_brand on quotes, copy brand/customer onto jobs."""
	brands = list(brands) if brands is not None else load_brands()
	by_name, by_label = _brand_lookups(brands)
	brand_title = {}
	for b in brands:
		code = b.get("name") if isinstance(b, dict) else b.name
		title = (b.get("brand_name") if isinstance(b, dict) else b.brand_name) or code
		brand_title[code] = title

	quote_brand = {}
	quote_customer = {}
	for q in quotes or []:
		code = resolve_quote_brand(q, by_name, by_label)
		q["hv_brand"] = code
		q["brand_name"] = brand_title.get(code) or code
		if q.get("name"):
			quote_brand[q["name"]] = code
			quote_customer[q["name"]] = q.get("customer") or ""

	for j in jobs or []:
		sq = (j.get("sales_quote") or "").strip()
		code = quote_brand.get(sq) or ""
		j["hv_brand"] = code
		j["brand_name"] = brand_title.get(code) or code
		if not (j.get("customer") or "").strip():
			j["customer"] = quote_customer.get(sq) or ""
	return quotes, jobs, brands


def apply_job_filters(jobs, filters=None):
	filters = frappe._dict(filters or {})
	sla = (filters.get("sla_status") or "").strip()
	status = (filters.get("job_status") or "").strip()
	brand = (filters.get("hv_brand") or filters.get("brand") or "").strip()
	live_only = cint(filters.get("live_only"))
	out = []
	for j in jobs or []:
		if live_only and (j.get("job_status") or "").strip() not in JOB_LIVE:
			continue
		if sla and (j.get("sla_status") or "").strip() != sla:
			continue
		if status and (j.get("job_status") or "").strip() != status:
			continue
		if brand and (j.get("hv_brand") or "").strip() != brand:
			continue
		out.append(j)
	return out


def apply_quote_filters(quotes, filters=None):
	filters = frappe._dict(filters or {})
	brand = (filters.get("hv_brand") or filters.get("brand") or "").strip()
	if not brand:
		return list(quotes or [])
	return [q for q in (quotes or []) if (q.get("hv_brand") or "").strip() == brand]


def load_report_context(filters=None):
	"""Quotes + jobs with brands resolved. Does not apply brand/SLA row filters."""
	filters = frappe._dict(filters or {})
	brands = load_brands()
	quotes = load_hv_quotes(filters)
	jobs = load_hv_jobs(filters)
	quotes, jobs, brands = enrich_quotes_and_jobs(quotes, jobs, brands)
	return brands, quotes, jobs


def brand_board_rows(brands, quotes, jobs):
	"""One analytics row per HV Brand."""
	quotes_by = defaultdict(list)
	jobs_by = defaultdict(list)
	for q in quotes or []:
		code = (q.get("hv_brand") or "").strip()
		if code:
			quotes_by[code].append(q)
	for j in jobs or []:
		code = (j.get("hv_brand") or "").strip()
		if code:
			jobs_by[code].append(j)

	owner_ids = [q.get("owner") for q in (quotes or [])] + [j.get("owner") for j in (jobs or [])]
	labels = owner_labels(owner_ids)

	rows = []
	for b in brands or []:
		code = b.get("name") if isinstance(b, dict) else b.name
		title = (b.get("brand_name") if isinstance(b, dict) else b.brand_name) or code
		bq = quotes_by.get(code) or []
		bj = jobs_by.get(code) or []
		flags = classify_brand(bq, bj)
		owners = []
		seen = set()
		for src in bq + bj:
			ow = (src.get("owner") or "").strip()
			if ow and ow not in seen:
				seen.add(ow)
				owners.append(labels.get(ow) or ow)
		rows.append(
			{
				"name": code,
				"brand_name": title,
				"severity": flags.get("severity") or "idle",
				"quote_count": flags.get("quote_count") or 0,
				"job_count": flags.get("job_count") or 0,
				"live_job_count": flags.get("live_job_count") or 0,
				"sla_at_risk": flags.get("sla_at_risk") or 0,
				"sla_breached": flags.get("sla_breached") or 0,
				"estimated_revenue": sum(flt(q.get("total_estimated_revenue")) for q in bq),
				"estimated_profit": sum(flt(q.get("estimated_profit")) for q in bq),
				"owners": ", ".join(owners) or _("Unassigned"),
			}
		)
	rows.sort(
		key=lambda r: (
			{"overdue": 0, "at_risk": 1, "live": 2, "active": 3, "idle": 5}.get(r["severity"], 9),
			(r.get("brand_name") or "").lower(),
		)
	)
	return rows


def count_modality(filters=None):
	"""HV-tagged document counts by modality. Brand uses Sales Quote join where possible."""
	filters = frappe._dict(filters or {})
	company = (filters.get("company") or "").strip()
	brand = (filters.get("hv_brand") or filters.get("brand") or "").strip()
	quote_names = None
	if brand:
		qfilters = frappe._dict({"company": company, "hv_brand": brand})
		quotes = load_hv_quotes(qfilters)
		_, quotes, _ = enrich_quotes_and_jobs(quotes, [], load_brands())
		quotes = apply_quote_filters(quotes, qfilters)
		quote_names = [q["name"] for q in quotes if q.get("name")]

	rows = []
	for label, doctype in MODALITY_DOCTYPES:
		if not frappe.db.exists("DocType", doctype):
			rows.append({"modality": label, "doctype": doctype, "documents": 0})
			continue
		meta = frappe.get_meta(doctype)
		if not meta.has_field("is_high_value"):
			rows.append({"modality": label, "doctype": doctype, "documents": 0})
			continue
		flt = {"is_high_value": 1, "docstatus": ["<", 2]}
		if company and meta.has_field("company"):
			flt["company"] = company
		if brand:
			if doctype == "Sales Quote" and meta.has_field("hv_brand"):
				if quote_names:
					flt["name"] = ["in", quote_names]
				else:
					rows.append({"modality": label, "doctype": doctype, "documents": 0})
					continue
			elif meta.has_field("sales_quote"):
				if not quote_names:
					rows.append({"modality": label, "doctype": doctype, "documents": 0})
					continue
				flt["sales_quote"] = ["in", quote_names]
			else:
				rows.append({"modality": label, "doctype": doctype, "documents": 0})
				continue
		try:
			n = frappe.db.count(doctype, flt)
		except Exception:
			n = 0
		rows.append({"modality": label, "doctype": doctype, "documents": cint(n)})
	return rows


def sort_jobs_by_sla(jobs):
	return sorted(
		jobs or [],
		key=lambda r: (
			SLA_RANK.get((r.get("sla_status") or "").strip(), 9),
			r.get("sla_target_date") or "9999-12-31",
			r.get("name") or "",
		),
	)
