# Copyright (c) 2026, Agilasoft and contributors
"""Shared UNLOCO heat map, carrier multiselect options, and alert rollup for operations dashboards."""

from __future__ import unicode_literals

import json
from collections import defaultdict

import frappe
from frappe.utils import get_url

from logistics.document_management.api import get_dashboard_alerts
from logistics.document_management.dashboard_layout import get_unloco_coords

MAX_ALERT_ITEMS = 50

DEFAULT_JOB_STATUSES = (
	"Draft",
	"Submitted",
	"In Progress",
	"Completed",
	"Closed",
	"Reopened",
	"Cancelled",
)
ONGOING_EXCLUDE_STATUS = ("Completed", "Closed", "Cancelled")


def flag_emoji_from_country_code(cc):
	if not cc or len(str(cc).strip()) != 2:
		return ""
	a, b = str(cc).strip().upper()[:2]
	if not ("A" <= a <= "Z" and "A" <= b <= "Z"):
		return ""
	return chr(ord(a) + 127397) + chr(ord(b) + 127397)


def job_status_filter_for_query(job_status_filter, valid_statuses=None):
	key = (job_status_filter or "").strip() or "ongoing"
	valid = valid_statuses or DEFAULT_JOB_STATUSES
	if key == "ongoing":
		return ("not_in", list(ONGOING_EXCLUDE_STATUS) + ["Draft"])
	if key in ("open", "open_with_draft"):
		return ("not_in", list(ONGOING_EXCLUDE_STATUS))
	if key in valid:
		return ("equals", key)
	return ("not_in", list(ONGOING_EXCLUDE_STATUS) + ["Draft"])


def parse_traffic(traffic):
	t = (traffic or "all").strip().lower()
	if t in ("all", "import", "export", "domestic"):
		return t
	return "all"


def parse_multi_link_param(raw):
	if raw is None or raw == "":
		return None
	if isinstance(raw, (list, tuple)):
		vals = [str(x).strip() for x in raw if str(x).strip()]
	elif isinstance(raw, str):
		s = raw.strip()
		if not s:
			return None
		try:
			parsed = json.loads(s)
			if isinstance(parsed, list):
				vals = [str(x).strip() for x in parsed if str(x).strip()]
			else:
				vals = []
		except Exception:
			vals = [x.strip() for x in s.split(",") if x.strip()]
	else:
		return None
	return vals or None


def sanitize_link_values(values, link_doctype):
	if not values or not link_doctype:
		return None
	out = []
	for c in values:
		if not c or not frappe.db.exists(link_doctype, c):
			continue
		out.append(c)
	return out or None


def row_matches_traffic(traffic, op, dp, cc_by_unloco):
	if traffic == "all":
		return True
	if not op or not dp:
		return traffic in ("import", "export")
	co = (cc_by_unloco.get(op) or "").strip().upper()
	cd = (cc_by_unloco.get(dp) or "").strip().upper()
	is_domestic = bool(co and cd and co == cd)
	if traffic == "domestic":
		return is_domestic
	if traffic in ("import", "export"):
		return not is_domestic
	return True


def session_company_context():
	company = frappe.defaults.get_user_default("Company") or frappe.defaults.get_global_default("default_company")
	if not company:
		try:
			company = frappe.db.get_single_value("Global Defaults", "default_company")
		except Exception:
			company = None
	if not company:
		return {"company": "", "company_name": "", "company_logo_url": ""}
	row = frappe.db.get_value(
		"Company",
		company,
		["company_name", "company_logo"],
		as_dict=True,
	) or {}
	logo = row.get("company_logo")
	return {
		"company": company,
		"company_name": row.get("company_name") or company,
		"company_logo_url": get_url(logo) if logo else "",
	}


def map_renderer():
	for dt in ("Logistics Settings", "Transport Settings"):
		try:
			doc = frappe.get_single(dt)
			mr = getattr(doc, "map_renderer", None) if doc else None
			if mr and str(mr).strip():
				return str(mr).strip()
		except Exception:
			continue
	return "OpenStreetMap"


def base_doc_filters(
	job_status_filter,
	filter_user,
	company,
	job_status_field,
	valid_statuses,
):
	mode, val = job_status_filter_for_query(job_status_filter, valid_statuses)
	filters = {"docstatus": 1}
	if mode == "not_in":
		filters[job_status_field] = ["not in", val]
	else:
		filters[job_status_field] = val
	fu = (filter_user or "").strip()
	if fu and frappe.db.exists("User", fu):
		filters["owner"] = fu
	if company:
		filters["company"] = company
	return filters


def carrier_multiselect_options(source_doctype, filters, carrier_field, carrier_doctype, label_getter):
	if not carrier_field or not carrier_doctype:
		return []
	try:
		codes = frappe.get_list(
			source_doctype,
			filters=filters,
			pluck=carrier_field,
			distinct=True,
			limit_page_length=0,
			order_by="%s asc" % carrier_field,
		)
	except Exception:
		codes = []
	out = []
	seen = set()
	for c in codes or []:
		if not c or c in seen:
			continue
		seen.add(c)
		label = label_getter(c) if label_getter else c
		out.append({"value": c, "label": label})
	return out


def operations_filter_users(source_doctype, job_status_filter, job_status_field, valid_statuses, company):
	filters = base_doc_filters(job_status_filter, None, company, job_status_field, valid_statuses)
	try:
		owners = frappe.get_list(
			source_doctype,
			filters=filters,
			pluck="owner",
			distinct=True,
			limit_page_length=150,
			order_by="owner asc",
		)
	except Exception:
		owners = []
	out = [{"value": "", "label": frappe._("All users")}]
	seen = set()
	for owner in owners or []:
		if not owner or owner in seen:
			continue
		seen.add(owner)
		full = frappe.db.get_value("User", owner, "full_name") or owner
		out.append({"value": owner, "label": "{0} ({1})".format(full, owner)})
	me = frappe.session.user
	if me and me != "Guest" and frappe.db.exists("User", me) and not any(x.get("value") == me for x in out):
		full = frappe.db.get_value("User", me, "full_name") or me
		out.insert(1, {"value": me, "label": "{0} ({1})".format(full, me)})
	return out


def transport_job_resolve_ports(row):
	if row.get("sea_shipment"):
		p = frappe.db.get_value(
			"Sea Shipment",
			row["sea_shipment"],
			["origin_port", "destination_port"],
			as_dict=True,
		)
		if p:
			return (p.get("origin_port") or "").strip(), (p.get("destination_port") or "").strip()
	if row.get("air_shipment"):
		p = frappe.db.get_value(
			"Air Shipment",
			row["air_shipment"],
			["origin_port", "destination_port"],
			as_dict=True,
		)
		if p:
			return (p.get("origin_port") or "").strip(), (p.get("destination_port") or "").strip()
	return "", ""


def run_heat_map_dashboard(
	source_doctype,
	link_doctype,
	*,
	job_status_field="job_status",
	valid_job_statuses=None,
	list_fields=None,
	origin_field="origin_port",
	dest_field="destination_port",
	carrier_field=None,
	carrier_doctype=None,
	carrier_label_fn=None,
	resolve_ports=None,
	job_status_filter=None,
	filter_user=None,
	traffic=None,
	carriers_param=None,
	limit=None,
	include_draft=None,
	extra_filters=None,
):
	"""
	Generic heat map + alerts payload for a submitted document type with two UNLOCO ports.

	:param resolve_ports: optional callable(row_dict) -> (origin, dest); default uses origin_field/dest_field.
	:param carrier_label_fn: optional fn(code) -> display label for multiselect.
	:param extra_filters: merged into base filters (e.g. per module).
	"""
	if job_status_filter is None and frappe.utils.cint(include_draft):
		job_status_filter = "open"
	valid_job_statuses = valid_job_statuses or DEFAULT_JOB_STATUSES
	ctx = session_company_context()
	comp = (ctx.get("company") or "").strip()
	traffic_mode = parse_traffic(traffic)
	raw_carriers = parse_multi_link_param(carriers_param)

	if list_fields is None:
		list_fields = ["name", origin_field, dest_field, job_status_field, "modified"]
	if carrier_field:
		list_fields = list(list_fields) + [carrier_field]

	filters = base_doc_filters(job_status_filter, filter_user, comp, job_status_field, valid_job_statuses)
	option_filters = dict(filters)
	if extra_filters:
		filters.update(extra_filters)
		option_filters.update(extra_filters)

	safe_carriers = sanitize_link_values(raw_carriers, carrier_doctype) if carrier_doctype else None
	if carrier_field and safe_carriers:
		filters[carrier_field] = ["in", safe_carriers]

	list_kwargs = {
		"filters": filters,
		"fields": list_fields,
		"order_by": "modified desc",
	}
	if limit is not None and str(limit).strip() != "":
		try:
			lim_val = int(limit)
			if lim_val > 0:
				list_kwargs["limit_page_length"] = lim_val
			else:
				list_kwargs["limit_page_length"] = 0
		except Exception:
			list_kwargs["limit_page_length"] = 0
	else:
		list_kwargs["limit_page_length"] = 0

	rows = frappe.get_list(source_doctype, **list_kwargs)

	def ports_for(r):
		if resolve_ports:
			return resolve_ports(r)
		op = (r.get(origin_field) or "").strip()
		dp = (r.get(dest_field) or "").strip()
		return op, dp

	origin_intl = defaultdict(int)
	dest_intl = defaultdict(int)
	origin_dom = defaultdict(int)
	dest_dom = defaultdict(int)
	visible = set()

	port_codes = set()
	for r in rows:
		op, dp = ports_for(r)
		if op:
			port_codes.add(op)
		if dp:
			port_codes.add(dp)

	cc_by_unloco = {}
	if port_codes:
		codes_list = list(port_codes)
		for i in range(0, len(codes_list), 200):
			chunk = codes_list[i : i + 200]
			for row in frappe.get_all(
				"UNLOCO",
				filters={"name": ["in", chunk]},
				fields=["name", "country_code"],
			):
				cc_by_unloco[row.name] = (row.get("country_code") or "").strip().upper()

	for r in rows:
		name = r.name
		op, dp = ports_for(r)
		if not row_matches_traffic(traffic_mode, op, dp, cc_by_unloco):
			continue
		if not op and not dp:
			continue
		if not op or not dp:
			if op:
				origin_intl[op] += 1
				visible.add(name)
			if dp:
				dest_intl[dp] += 1
				visible.add(name)
			continue
		co = cc_by_unloco.get(op, "")
		cd = cc_by_unloco.get(dp, "")
		is_domestic = bool(co and cd and co == cd)
		if is_domestic:
			origin_dom[op] += 1
			dest_dom[dp] += 1
		else:
			origin_intl[op] += 1
			dest_intl[dp] += 1
		visible.add(name)

	total = len(visible)
	all_ports = set(origin_intl) | set(dest_intl) | set(origin_dom) | set(dest_dom)
	unloco_markers = []
	skipped_unloco_no_coords = 0
	for code in sorted(all_ports):
		imp = int(origin_intl.get(code, 0) or 0)
		exp = int(dest_intl.get(code, 0) or 0)
		dom = int(origin_dom.get(code, 0) or 0) + int(dest_dom.get(code, 0) or 0)
		if imp == 0 and exp == 0 and dom == 0:
			continue
		coords = get_unloco_coords(code)
		if not coords or coords.get("lat") is None or coords.get("lon") is None:
			skipped_unloco_no_coords += 1
			continue
		cc_raw = (cc_by_unloco.get(code) or "").strip()
		if traffic_mode == "import":
			exp = dom = 0
		elif traffic_mode == "export":
			imp = dom = 0
		elif traffic_mode == "domestic":
			imp = exp = 0
		unloco_markers.append(
			{
				"unloco": code,
				"country_code": cc_raw.upper(),
				"flag": flag_emoji_from_country_code(cc_raw),
				"lat": float(coords["lat"]),
				"lon": float(coords["lon"]),
				"import_count": imp,
				"export_count": exp,
				"domestic_count": dom,
			}
		)

	def _carrier_label(code):
		if not carrier_label_fn:
			return code
		try:
			return carrier_label_fn(code)
		except Exception:
			return code

	carrier_options = []
	if carrier_field and carrier_doctype:
		carrier_options = carrier_multiselect_options(
			source_doctype, option_filters, carrier_field, carrier_doctype, _carrier_label
		)

	alert_summary = {"danger": 0, "warning": 0, "info": 0}
	alert_items = []
	for r in rows:
		op, dp = ports_for(r)
		if not row_matches_traffic(traffic_mode, op, dp, cc_by_unloco):
			continue
		if not op and not dp:
			continue
		try:
			alerts = get_dashboard_alerts(link_doctype, r.name)
		except Exception:
			alerts = []
		for a in alerts:
			lvl = a.get("level") or "info"
			if lvl not in alert_summary:
				lvl = "info"
			alert_summary[lvl] += 1
			if len(alert_items) < MAX_ALERT_ITEMS:
				alert_items.append(
					{
						"level": lvl,
						"msg": a.get("msg") or "",
						"shipment": r.name,
					}
				)

	max_applied = list_kwargs.get("limit_page_length")
	if max_applied == 0:
		max_applied = None
	out = {
		"unloco_markers": unloco_markers,
		"airlines": [],
		"airline_options": carrier_options,
		"alert_summary": alert_summary,
		"alert_items": alert_items,
		"map_renderer": map_renderer(),
		"limits_applied": {"max_shipments": max_applied, "shipment_count": total},
		"skipped_unloco_no_coords": skipped_unloco_no_coords,
		"filters_applied": {
			"traffic": traffic_mode,
			"company": comp or None,
			"job_status_filter": ((job_status_filter or "").strip() or "ongoing"),
		},
	}
	out.update(session_company_context())
	return out
