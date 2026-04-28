# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Tabbed form dashboard (Air Booking style) for logistics doctypes.

CSS is defined in air_booking_dashboard.AIR_BOOKING_DASH_CSS (.log-ab-dash root).
"""

from __future__ import unicode_literals

import json
import re

import frappe
from frappe.utils import escape_html, get_url


def build_freight_meta_cluster_html(doc):
	"""Two-column meta block: customer / dates / direction / service | house / shipper / consignee."""

	def _ab_meta_row(ic, val, label=None):
		span = (
			f'<span class="ab-meta-k">{escape_html(label)}:</span>{escape_html(str(val))}'
			if label
			else escape_html(str(val))
		)
		return f'<div class="ab-meta-row"><i class="fa {escape_html(ic)}"></i><span>{span}</span></div>'

	meta_primary_parts = []
	if getattr(doc, "local_customer", None):
		meta_primary_parts.append(_ab_meta_row("fa-building", doc.local_customer))
	if getattr(doc, "etd", None):
		meta_primary_parts.append(_ab_meta_row("fa-calendar", str(doc.etd)))
	if getattr(doc, "direction", None):
		meta_primary_parts.append(_ab_meta_row("fa-exchange", doc.direction, "Direction"))
	if getattr(doc, "service_level", None):
		meta_primary_parts.append(_ab_meta_row("fa-flag", doc.service_level))
	meta_primary_inner = "".join(meta_primary_parts)
	meta_primary = f'<div class="ab-summary-meta-rows">{meta_primary_inner}</div>' if meta_primary_inner else ""

	sec_lines = []
	if getattr(doc, "house_type", None):
		sec_lines.append(("fa-tag", "House type", doc.house_type))
	if getattr(doc, "shipper", None):
		sec_lines.append(("fa-user", "Shipper", doc.shipper))
	if getattr(doc, "consignee", None):
		sec_lines.append(("fa-users", "Consignee", doc.consignee))
	sec_inner = "".join(
		f'<div class="ab-sec-line"><i class="fa {escape_html(ic)}"></i>'
		f'<span class="ab-sec-val"><span class="ab-sec-k">{escape_html(lbl)}:</span>'
		f"{escape_html(str(val))}</span></div>"
		for ic, lbl, val in sec_lines
	)
	meta_secondary = f'<div class="ab-secondary-meta">{sec_inner}</div>' if sec_inner else ""

	if meta_primary and meta_secondary:
		return (
			f'<div class="log-ab-meta-cluster">'
			f'<div class="log-ab-meta-col log-ab-meta-col--primary">{meta_primary}</div>'
			f'<div class="log-ab-meta-col log-ab-meta-col--secondary">{meta_secondary}</div>'
			f"</div>"
		)
	if meta_primary:
		return (
			f'<div class="log-ab-meta-cluster">'
			f'<div class="log-ab-meta-col log-ab-meta-col--primary">{meta_primary}</div>'
			f"</div>"
		)
	if meta_secondary:
		return (
			f'<div class="log-ab-meta-cluster">'
			f'<div class="log-ab-meta-col log-ab-meta-col--secondary">{meta_secondary}</div>'
			f"</div>"
		)
	return ""


def build_airline_hero_html(doc, header_items):
	"""Airline logo or two-letter placeholder; may append Airline to header_items."""
	hero_html = ""
	attached = False
	if getattr(doc, "airline", None):
		row = frappe.db.get_value(
			"Airline", doc.airline, ["logo", "airline_name", "two_character_code"], as_dict=True
		) or {}
		logo = row.get("logo")
		aname = row.get("airline_name") or doc.airline
		if logo:
			attached = True
			src = get_url(logo)
			hero_html = f'<img class="log-ab-logo-img" src="{escape_html(src)}" alt="{escape_html(aname)}" />'
		else:
			code = (row.get("two_character_code") or doc.airline or "?")[:2].upper()
			hero_html = (
				f'<span class="log-ab-logo-ph" title="{escape_html(doc.airline)}">{escape_html(code)}</span>'
			)
		if not attached:
			header_items.append(("Airline", doc.airline))
	return hero_html


def build_shipping_line_hero_html(doc, header_items):
	"""Shipping line logo or SCAC/code placeholder; may append Shipping Line to header_items when no logo."""
	if not getattr(doc, "shipping_line", None):
		return ""
	row = frappe.db.get_value(
		"Shipping Line",
		doc.shipping_line,
		["logo", "code", "shipping_line_name", "scac"],
		as_dict=True,
	) or {}
	logo = row.get("logo")
	title = row.get("shipping_line_name") or doc.shipping_line
	ph = (row.get("scac") or row.get("code") or doc.shipping_line or "?")[:4].upper()
	if logo:
		src = get_url(logo)
		return (
			f'<img class="log-ab-logo-img" src="{escape_html(src)}" alt="{escape_html(title)}" />'
		)
	header_items.append(("Shipping Line", doc.shipping_line))
	return f'<span class="log-ab-logo-ph" title="{escape_html(title)}">{escape_html(ph)}</span>'


def build_customs_broker_hero_html(doc, header_items):
	"""Broker (Customs Broker link target) logo or code placeholder."""
	broker = getattr(doc, "customs_broker", None)
	if not broker:
		return ""
	row = frappe.db.get_value(
		"Broker", broker, ["logo", "broker_name", "code"], as_dict=True
	) or {}
	logo = row.get("logo")
	title = row.get("broker_name") or broker
	ph = (row.get("code") or broker or "?")[:4].upper()
	if logo:
		src = get_url(logo)
		return f'<img class="log-ab-logo-img" src="{escape_html(src)}" alt="{escape_html(title)}" />'
	header_items.append(("Customs Broker", broker))
	return f'<span class="log-ab-logo-ph" title="{escape_html(title)}">{escape_html(ph)}</span>'


def build_customs_authority_hero_html(doc, header_items):
	"""Customs Authority logo or code placeholder (Declaration / Declaration Order dashboard)."""
	ca = getattr(doc, "customs_authority", None)
	if not ca:
		return ""
	row = frappe.db.get_value(
		"Customs Authority",
		ca,
		["logo", "customs_authority_name", "code"],
		as_dict=True,
	) or {}
	logo = row.get("logo")
	title = row.get("customs_authority_name") or ca
	ph = (row.get("code") or ca or "?")[:4].upper()
	if logo:
		src = get_url(logo)
		return f'<img class="log-ab-logo-img" src="{escape_html(src)}" alt="{escape_html(title)}" />'
	header_items.append(("Customs Authority", ca))
	return f'<span class="log-ab-logo-ph" title="{escape_html(title)}">{escape_html(ph)}</span>'


def _transport_company_from_job_run_sheets(job_doc):
	for row in job_doc.get("legs") or []:
		rs = row.get("run_sheet")
		if not rs:
			continue
		tc = frappe.db.get_value("Run Sheet", rs, "transport_company")
		if tc:
			return tc
	return None


def _transport_company_from_order_linked_jobs(order_name):
	if not order_name:
		return None
	for job_name in frappe.get_all(
		"Transport Job",
		filters={"transport_order": order_name, "docstatus": ["!=", 2]},
		pluck="name",
		limit_page_length=25,
	):
		job_doc = frappe.get_doc("Transport Job", job_name)
		tc = _transport_company_from_job_run_sheets(job_doc)
		if tc:
			return tc
	return None


def resolve_transport_company_name_for_dashboard(doc):
	"""Explicit transport_company on order/job, else infer from Run Sheets on linked jobs."""
	tc = getattr(doc, "transport_company", None)
	if tc:
		return tc
	dt = getattr(doc, "doctype", None)
	if dt == "Transport Job":
		return _transport_company_from_job_run_sheets(doc)
	if dt == "Transport Order":
		return _transport_company_from_order_linked_jobs(doc.name)
	return None


def build_transport_company_hero_html(doc, header_items):
	"""Transport Company logo or short text placeholder."""
	tc = resolve_transport_company_name_for_dashboard(doc)
	if not tc:
		return ""
	row = frappe.db.get_value(
		"Transport Company", tc, ["logo", "full_name", "supplier"], as_dict=True
	) or {}
	logo = row.get("logo")
	title = row.get("full_name") or row.get("supplier") or tc
	ph_src = row.get("full_name") or tc
	ph = (ph_src or "?")[:4].upper()
	if logo:
		src = get_url(logo)
		return f'<img class="log-ab-logo-img" src="{escape_html(src)}" alt="{escape_html(title)}" />'
	header_items.append(("Transport Company", tc))
	return f'<span class="log-ab-logo-ph" title="{escape_html(title)}">{escape_html(ph)}</span>'


def build_transport_meta_cluster_html(doc):
	"""Customer, booking/scheduled dates, job type | packages weight style lines."""

	def _ab_meta_row(ic, val, label=None):
		span = (
			f'<span class="ab-meta-k">{escape_html(label)}:</span>{escape_html(str(val))}'
			if label
			else escape_html(str(val))
		)
		return f'<div class="ab-meta-row"><i class="fa {escape_html(ic)}"></i><span>{span}</span></div>'

	parts = []
	if getattr(doc, "customer", None):
		parts.append(_ab_meta_row("fa-building", doc.customer))
	if getattr(doc, "booking_date", None):
		parts.append(_ab_meta_row("fa-calendar", str(doc.booking_date), "Booking"))
	if getattr(doc, "scheduled_date", None):
		parts.append(_ab_meta_row("fa-clock-o", str(doc.scheduled_date), "Scheduled"))
	if getattr(doc, "transport_job_type", None):
		parts.append(_ab_meta_row("fa-truck", doc.transport_job_type, "Job type"))
	meta_primary = f'<div class="ab-summary-meta-rows">{"".join(parts)}</div>' if parts else ""

	sec = []
	n_legs = len(doc.get("legs") or [])
	sec.append(("fa-road", "Legs", str(n_legs)))
	if doc.get("packages") is not None:
		sec.append(("fa-cube", "Packages", str(len(doc.packages or []))))
	if getattr(doc, "total_weight", None) is not None:
		sec.append(
			(
				"fa-balance-scale",
				"Weight",
				frappe.format_value(doc.total_weight or 0, df=dict(fieldtype="Float")),
			)
		)
	sec_inner = "".join(
		f'<div class="ab-sec-line"><i class="fa {escape_html(ic)}"></i>'
		f'<span class="ab-sec-val"><span class="ab-sec-k">{escape_html(lbl)}:</span>'
		f"{escape_html(str(val))}</span></div>"
		for ic, lbl, val in sec
	)
	meta_secondary = f'<div class="ab-secondary-meta">{sec_inner}</div>' if sec_inner else ""

	if meta_primary and meta_secondary:
		return (
			f'<div class="log-ab-meta-cluster">'
			f'<div class="log-ab-meta-col log-ab-meta-col--primary">{meta_primary}</div>'
			f'<div class="log-ab-meta-col log-ab-meta-col--secondary">{meta_secondary}</div>'
			f"</div>"
		)
	if meta_primary:
		return (
			f'<div class="log-ab-meta-cluster">'
			f'<div class="log-ab-meta-col log-ab-meta-col--primary">{meta_primary}</div>'
			f"</div>"
		)
	if meta_secondary:
		return (
			f'<div class="log-ab-meta-cluster">'
			f'<div class="log-ab-meta-col log-ab-meta-col--secondary">{meta_secondary}</div>'
			f"</div>"
		)
	return ""


def _customs_dashboard_cell_val(val):
	if val is None or val == "":
		return "—"
	return str(val)


def _customs_dashboard_primary_row(ic, label, raw_val):
	v = _customs_dashboard_cell_val(raw_val)
	span = f'<span class="ab-meta-k">{escape_html(label)}:</span>{escape_html(v)}'
	return f'<div class="ab-meta-row"><i class="fa {escape_html(ic)}"></i><span>{span}</span></div>'


def build_customs_form_primary_meta_html(doc, date_label, date_raw):
	"""First dashboard subtext: two columns × five rows (row-paired). Left: type, date, customer, exporter, importer. Right: broker, mode, incoterm, sales quote, blank."""
	left_specs = [
		("fa-file-text", "Type", getattr(doc, "declaration_type", None)),
		("fa-calendar", date_label, date_raw),
		("fa-building", "Customer", getattr(doc, "customer", None)),
		("fa-upload", "Exporter", getattr(doc, "exporter_shipper", None)),
		("fa-download", "Importer", getattr(doc, "importer_consignee", None)),
	]
	right_specs = [
		("fa-user-secret", "Customs broker", getattr(doc, "customs_broker", None)),
		("fa-truck", "Transport mode", getattr(doc, "transport_mode", None)),
		("fa-exchange", "Incoterm", getattr(doc, "incoterm", None)),
		("fa-file-o", "Sales quote", getattr(doc, "sales_quote", None)),
	]
	while len(right_specs) < len(left_specs):
		right_specs.append((None, None, None))
	rows = []
	for i in range(len(left_specs)):
		lic, llb, lv = left_specs[i]
		ric, rlb, rv = right_specs[i]
		right_cell = (
			_customs_dashboard_primary_row(ric, rlb, rv)
			if ric
			else '<div class="ab-meta-row ab-meta-row--customs-empty" aria-hidden="true"></div>'
		)
		rows.append(
			f'<div class="log-ab-customs-primary-grid-row">'
			f'<div class="log-ab-customs-primary-grid-cell">{_customs_dashboard_primary_row(lic, llb, lv)}</div>'
			f'<div class="log-ab-customs-primary-grid-cell">{right_cell}</div>'
			f"</div>"
		)
	return f'<div class="log-ab-customs-primary-meta">{"".join(rows)}</div>'


def build_declaration_meta_cluster_html(doc):
	return build_customs_form_primary_meta_html(
		doc, "Declaration date", getattr(doc, "declaration_date", None)
	)


def build_declaration_order_meta_cluster_html(doc):
	return build_customs_form_primary_meta_html(doc, "Order date", getattr(doc, "order_date", None))


def _customs_transport_document_line(doc):
	tdn = getattr(doc, "transport_document_number", None)
	tdt = getattr(doc, "transport_document_type", None)
	if not tdn and not tdt:
		return "—"
	return " — ".join(x for x in (tdt, tdn) if x)


def _customs_sla_line(doc):
	ss = getattr(doc, "sla_status", None)
	std = getattr(doc, "sla_target_date", None)
	parts = [x for x in (ss, std) if x not in (None, "")]
	if not parts:
		return "—"
	return " — ".join(str(p) for p in parts)


def _route_panel_address_titles(doc, legs_field="legs"):
	"""Text-only route legs (pick → drop) using Address address_title when available."""
	legs = doc.get(legs_field) or []
	if not legs:
		return (
			f'<div class="log-ab-route-panel">'
			f'<div class="log-ab-route-leg"><div class="log-ab-route-leg-text">'
			f'<span class="log-ab-route-code">—</span></div></div>'
			f'<div class="log-ab-route-mid"><span class="log-ab-route-arrow-h">→</span></div>'
			f'<div class="log-ab-route-leg"><div class="log-ab-route-leg-text">'
			f'<span class="log-ab-route-code">—</span></div></div></div>'
		)
	first_pick = legs[0].get("pick_address")
	last_drop = legs[-1].get("drop_address")
	o_txt = "—"
	d_txt = "—"
	if first_pick:
		o_txt = frappe.db.get_value("Address", first_pick, "address_title") or first_pick
	if last_drop:
		d_txt = frappe.db.get_value("Address", last_drop, "address_title") or last_drop
	return (
		f'<div class="log-ab-route-panel">'
		f'<div class="log-ab-route-leg"><span class="log-ab-route-flag log-ab-route-flag--empty" aria-hidden="true"></span>'
		f'<div class="log-ab-route-leg-text"><span class="log-ab-route-code">{escape_html(o_txt)}</span></div></div>'
		f'<div class="log-ab-route-mid"><span class="log-ab-route-arrow-h">→</span></div>'
		f'<div class="log-ab-route-leg"><span class="log-ab-route-flag log-ab-route-flag--empty" aria-hidden="true"></span>'
		f'<div class="log-ab-route-leg-text"><span class="log-ab-route-code">{escape_html(d_txt)}</span></div></div>'
		f"</div>"
	)


def render_logistics_form_dashboard_html(doc, cfg):
	"""
	Build full .log-ab-dash HTML. cfg keys:

	- doctype (str), map_id_prefix (str), header_items (list of tuples)
	- meta_cluster_html (str)
	- hero_html (str, optional)
	- route_panel_html (optional str; None = UNLOCO panel from route_origin_attr / route_dest_attr)
	- route_origin_attr, route_dest_attr (default origin_port / destination_port)
	- route_supplement_html (str), get_dg_dashboard_fn (callable), get_dg_dashboard_kwargs (dict)
	- include_default_dg (bool default True if no fn)
	- milestones_field, routing_legs_field, scroll_doctype, scroll_field
	- map_points, map_segments (override lists or None to compute)
	- hide_map (bool), straight_line (bool)
	- empty_milestones_hint (HTML str)
	- milestones_tab_inner_html (optional str; replaces child-table milestone panel)
	- milestone_count_override (int for tab badge when using custom milestones tab)
	- alerts_prepend_html (str)
	- status_slug (optional str for ring), ring_status_from workflow|docstatus
	- ring_status_field when workflow (default status)
	- customs_dashboard_enhanced_layout (bool): Declaration / Declaration Order — divider + layout CSS
	"""
	from logistics.document_management.api import (
		get_dashboard_alerts,
		get_document_alerts_html,
		get_dashboard_alerts_html,
	)
	from logistics.document_management.dashboard_layout import (
		RUN_SHEET_LAYOUT_CSS,
		build_map_segments_from_routing_legs,
		get_dg_dashboard_html,
		get_unloco_coords,
		render_route_map_html,
	)
	from logistics.air_freight.doctype.air_booking.air_booking_dashboard import (
		AIR_BOOKING_DASH_CSS,
		_route_supplement_html,
		_air_booking_route_hero_html,
		_header_details_html,
		_milestones_ro_panel_html,
	)

	doctype = cfg["doctype"]
	map_id_prefix = cfg["map_id_prefix"]
	header_items = list(cfg.get("header_items") or [])
	meta_cluster_html = cfg.get("meta_cluster_html") or ""
	hero_html = cfg.get("hero_html") or ""

	route_panel_html = cfg.get("route_panel_html")
	if route_panel_html is None:
		route_panel_html = _air_booking_route_hero_html(
			doc,
			origin_attr=cfg.get("route_origin_attr", "origin_port"),
			destination_attr=cfg.get("route_dest_attr", "destination_port"),
		)

	route_supplement = (cfg.get("route_supplement_html") or "").strip()
	get_dg_fn = cfg.get("get_dg_dashboard_fn")
	get_dg_kw = cfg.get("get_dg_dashboard_kwargs") or {}
	dg_part = ""
	if get_dg_fn:
		dg_part = get_dg_fn(doc) or ""
	elif cfg.get("include_default_dg", True):
		dg_part = get_dg_dashboard_html(doc, **get_dg_kw) if get_dg_kw else get_dg_dashboard_html(doc)
	route_section = _route_supplement_html(route_supplement + dg_part)

	status_slug = cfg.get("status_slug")
	if not status_slug:
		if cfg.get("ring_status_from") == "workflow":
			st = getattr(doc, cfg.get("ring_status_field", "status"), None) or "Draft"
			status_slug = str(st).lower().replace(" ", "_").replace("/", "_")
		else:
			status_slug = (
				"submitted" if doc.docstatus == 1 else "cancelled" if doc.docstatus == 2 else "draft"
			)

	milestone_field = cfg.get("milestones_field", "milestones")
	milestone_rows = list(doc.get(milestone_field) or [])
	milestone_details = {}
	if milestone_rows:
		names = [m.milestone for m in milestone_rows if m.milestone]
		if names:
			for lm in frappe.get_all(
				"Logistics Milestone", filters={"name": ["in", names]}, fields=["name", "description"]
			):
				milestone_details[lm.name] = lm.description or lm.name

	# Embedded milestone HTML (Declaration, etc.) uses the same source as get_milestone_html:
	# child table with legacy Job Milestone fallback — keep ring/tab counts aligned.
	if cfg.get("milestones_tab_inner_html"):
		from logistics.document_management.api import get_milestone_display_rows_and_editor_doctype

		ring_rows, _ = get_milestone_display_rows_and_editor_doctype(doc)
		n_ms = len(ring_rows)
		done_ms = sum(1 for m in ring_rows if str(m.get("status") or "").strip() == "Completed")
	else:
		n_ms = cfg.get("milestone_count_override")
		if n_ms is None:
			n_ms = len(milestone_rows)
		done_ms = sum(1 for m in milestone_rows if (m.status or "") == "Completed")
	pct_ms = int(round(100.0 * done_ms / n_ms)) if n_ms else 0
	ms_label = "milestones" if n_ms != 1 else "milestone"
	ring_status_cls = {
		"draft": "ab-ring--status-draft",
		"submitted": "ab-ring--status-submitted",
		"cancelled": "ab-ring--status-cancelled",
	}.get(status_slug, "ab-ring--status-draft")
	progress_ring_html = (
		f'<div class="ab-ring-wrap" title="{done_ms}/{n_ms} completed">'
		f'<div class="ab-ring {ring_status_cls}" style="--ab-pct: {pct_ms};"></div>'
		f'<div class="ab-ring-center">'
		f'<span class="ab-ring-pct">{pct_ms}%</span>'
		f'<span class="ab-ring-cap">{n_ms} {ms_label}</span></div></div>'
	)

	if cfg.get("map_points") is not None:
		map_points = cfg.get("map_points") or []
		map_segments = cfg.get("map_segments")
	elif cfg.get("map_segments") is not None:
		map_points = []
		map_segments = cfg.get("map_segments")
	else:
		legs_field = cfg.get("routing_legs_field", "routing_legs")
		map_segments = build_map_segments_from_routing_legs(getattr(doc, legs_field) or [])
		map_points = []
		if not map_segments:
			op = getattr(doc, cfg.get("route_origin_attr", "origin_port"), None)
			dp = getattr(doc, cfg.get("route_dest_attr", "destination_port"), None)
			o = get_unloco_coords(op)
			d = get_unloco_coords(dp)
			if o:
				map_points.append(o)
			if d and (
				not map_points
				or (d.get("lat") != map_points[-1].get("lat"))
				or (d.get("lon") != map_points[-1].get("lon"))
			):
				map_points.append(d)

	hide_map = cfg.get("hide_map", False)
	straight_line = cfg.get("straight_line", True)
	map_section = render_route_map_html(
		map_id_prefix,
		map_points=map_points or [],
		map_segments=map_segments,
		straight_line=straight_line,
		hide_map=hide_map,
	)

	try:
		doc_alerts = get_document_alerts_html(doctype, doc.name or "new")
	except Exception:
		doc_alerts = ""
	alerts_html = get_dashboard_alerts_html(doctype, doc.name or "new")
	dash_alert_list = get_dashboard_alerts(doctype, doc.name or "new") or []
	alerts_section = (alerts_html or "").strip()
	if alerts_section:
		alerts_section = f'<div class="dash-alerts-section">{alerts_section}</div>'
	doc_strip = (doc_alerts or "").strip()
	prepend = (cfg.get("alerts_prepend_html") or "").strip()
	alerts_tab_inner = prepend + alerts_section + doc_strip
	if not alerts_tab_inner.strip():
		alerts_tab_inner = '<div class="text-muted ab-tab-empty">No alerts or notifications.</div>'

	# Badge = banner alerts only. Do not count doc-alert-card rows (there are always several
	# summary cards); that inflated the tab number.
	n_tab_alerts = len(dash_alert_list)
	ms_count_cls = "ab-tab-count ab-tab-count--highlight" if n_ms else "ab-tab-count"
	ms_count_html = f'<span class="{ms_count_cls}">({n_ms})</span>'
	al_count_cls = "ab-tab-count ab-tab-count--highlight" if n_tab_alerts else "ab-tab-count"
	al_count_html = f'<span class="{al_count_cls}">({n_tab_alerts})</span>'

	scroll_dt = cfg.get("scroll_doctype", doctype)
	scroll_fld = cfg.get("scroll_field", "milestones")
	empty_hint = cfg.get("empty_milestones_hint")
	if cfg.get("milestones_tab_inner_html"):
		milestones_inner = cfg["milestones_tab_inner_html"]
	else:
		milestones_inner = _milestones_ro_panel_html(
			milestone_rows,
			milestone_details,
			doc.name or "",
			scroll_doctype=scroll_dt,
			scroll_field=scroll_fld,
			empty_hint_html=empty_hint,
		)
	route_inner = (
		f'<div class="log-ab-ro-card log-ab-ro-card--flush">'
		f'<div class="ab-route-tab-inner">{map_section}</div></div>'
	)
	alerts_tab_wrapped = f'<div class="log-ab-ro-card">{alerts_tab_inner}</div>'

	safe_uid = re.sub(r"[^a-zA-Z0-9_]", "_", map_id_prefix or "lfdash")
	tid_r = f"{safe_uid}_route"
	tid_m = f"{safe_uid}_milestones"
	tid_a = f"{safe_uid}_alerts"
	tab_name = f"ab_sub_{safe_uid}"

	tab_block = f"""
		<div class="ab-tab-shell">
			<input type="radio" name="{tab_name}" id="{tid_r}" class="ab-dash-tab-input" checked>
			<input type="radio" name="{tab_name}" id="{tid_m}" class="ab-dash-tab-input">
			<input type="radio" name="{tab_name}" id="{tid_a}" class="ab-dash-tab-input">
			<div class="ab-tab-bar">
				<label for="{tid_r}" class="ab-tlabel">Route</label>
				<label for="{tid_m}" class="ab-tlabel">Milestones{ms_count_html}</label>
				<label for="{tid_a}" class="ab-tlabel">Alerts and Notifications{al_count_html}</label>
			</div>
			<div class="ab-ro-body">
				<div class="ab-tab-panels ab-ro-shell">
					<div class="ab-tab-panel ab-tab-panel-route">{route_inner}</div>
					<div class="ab-tab-panel ab-tab-panel-milestones">{milestones_inner}</div>
					<div class="ab-tab-panel ab-tab-panel-alerts">{alerts_tab_wrapped}</div>
				</div>
			</div>
		</div>
		<style>
			#{tid_r}:checked ~ .ab-tab-bar label[for="{tid_r}"],
			#{tid_m}:checked ~ .ab-tab-bar label[for="{tid_m}"],
			#{tid_a}:checked ~ .ab-tab-bar label[for="{tid_a}"] {{
				font-weight: 600; color: #212529; border-bottom-color: #212529;
			}}
			#{tid_r}:checked ~ .ab-ro-body .ab-tab-panel-route,
			#{tid_m}:checked ~ .ab-ro-body .ab-tab-panel-milestones,
			#{tid_a}:checked ~ .ab-ro-body .ab-tab-panel-alerts {{
				display: block;
			}}
		</style>
		"""

	header_details = _header_details_html(header_items)
	hero_logo = (hero_html or "").strip() or '<span class="log-ab-logo-ph">—</span>'
	customs_enh = bool(cfg.get("customs_dashboard_enhanced_layout"))
	dash_root_class = "log-ab-dash run-sheet-dash" + (" log-ab-dash--customs" if customs_enh else "")
	customs_extra_css = ""
	if customs_enh:
		customs_extra_css = """
.log-ab-dash.log-ab-dash--customs .log-ab-customs-primary-meta { width: 100%; display: flex; flex-direction: column; gap: 0.12rem; }
.log-ab-dash.log-ab-dash--customs .log-ab-customs-primary-grid-row {
	display: grid; grid-template-columns: 1fr 1fr; gap: 0.35rem 2rem; align-items: start; width: 100%;
}
.log-ab-dash.log-ab-dash--customs .log-ab-customs-primary-grid-cell { min-width: 0; }
.log-ab-dash.log-ab-dash--customs .ab-meta-row--customs-empty { min-height: 1.35rem; margin: 0; padding: 0; border: none; }
.log-ab-dash.log-ab-dash--customs .log-ab-customs-secondary-kpis {
	border-top: 1px solid var(--ro-border-soft); margin-top: 0.55rem; padding-top: 0.7rem; width: 100%;
}
"""
	header_body = (
		f'<div class="log-ab-customs-secondary-kpis"><div class="header-details">{header_details}</div></div>'
		if customs_enh
		else f'<div class="header-details">{header_details}</div>'
	)

	return f"""
	<div class="{dash_root_class}">
		<style>{RUN_SHEET_LAYOUT_CSS}{AIR_BOOKING_DASH_CSS}{customs_extra_css}</style>
		<div class="log-ab-top">
			<div class="run-sheet-header log-ab-head ab-summary-header-card">
				<div class="log-ab-head-stack">
					<div class="log-ab-top-row">
						<div class="log-ab-hero-col">{hero_logo}</div>
						<div class="log-ab-main-block">
							{route_panel_html}
							{meta_cluster_html}
						</div>
						<div class="ab-summary-aside">{progress_ring_html}</div>
					</div>
					{route_section}
					<div class="log-ab-body-block">
						{header_body}
					</div>
				</div>
			</div>
		</div>
		{tab_block}
	</div>
	"""


def build_air_booking_dashboard_config(doc):
	"""Dashboard cfg dict for Air Booking."""
	status = "Submitted" if doc.docstatus == 1 else "Cancelled" if doc.docstatus == 2 else "Draft"
	header_items = [
		("ETD", str(doc.etd) if doc.etd else "—"),
		("ETA", str(doc.eta) if doc.eta else "—"),
		("Incoterms", str(doc.incoterm) if getattr(doc, "incoterm", None) else "—"),
		("Packages", str(len(doc.packages or []))),
		("Weight", frappe.format_value(doc.total_weight or 0, df=dict(fieldtype="Float"))),
	]
	hero_html = build_airline_hero_html(doc, header_items)
	return {
		"doctype": "Air Booking",
		"map_id_prefix": "air-booking-dash-map",
		"header_items": header_items,
		"hero_html": hero_html,
		"meta_cluster_html": build_freight_meta_cluster_html(doc),
		"scroll_doctype": "Air Booking",
		"status_slug": status.lower().replace(" ", "_"),
	}


def _declaration_importer_classification_html(doc):
	if not getattr(doc, "importer_consignee", None):
		return ""
	classification = frappe.db.get_value(
		"Consignee", doc.importer_consignee, "customs_importer_classification"
	)
	if not classification or classification == "Not Classified":
		return ""
	cls_lower = (classification or "").lower().replace(" ", "_")
	card_class = (
		"sgl"
		if "sgl" in cls_lower
		else "gl"
		if "gl" in cls_lower or "green" in cls_lower
		else "yellow"
		if "yellow" in cls_lower
		else "red"
		if "red" in cls_lower
		else ""
	)
	return (
		f'<div class="importer-classification-card {card_class}" style="margin-left: 0;">'
		f'<div class="classification-label">Importer Classification</div>'
		f'<div class="classification-value">{escape_html(classification)}</div>'
		f"</div>"
	)


def build_air_shipment_dashboard_config(doc):
	status = "Submitted" if doc.docstatus == 1 else "Cancelled" if doc.docstatus == 2 else "Draft"
	header_items = [
		("Status", status),
		("ETD", str(doc.etd) if doc.etd else "—"),
		("ETA", str(doc.eta) if doc.eta else "—"),
		("Incoterms", str(doc.incoterm) if getattr(doc, "incoterm", None) else "—"),
		("Packages", str(len(doc.packages or []))),
		("Weight", frappe.format_value(doc.total_weight or 0, df=dict(fieldtype="Float"))),
	]
	hero_html = build_airline_hero_html(doc, header_items)
	from logistics.document_management.dashboard_layout import get_dg_dashboard_html

	return {
		"doctype": "Air Shipment",
		"map_id_prefix": "air-shipment-dash-map",
		"header_items": header_items,
		"hero_html": hero_html,
		"meta_cluster_html": build_freight_meta_cluster_html(doc),
		"scroll_doctype": "Air Shipment",
		"status_slug": status.lower().replace(" ", "_"),
		"get_dg_dashboard_fn": lambda d: get_dg_dashboard_html(
			d, get_compliance_fn=d.check_dg_compliance
		),
		"include_default_dg": False,
	}


def build_sea_consolidation_meta_cluster_html(doc):
	"""Two-column meta: type, date, ETD, ETA, priority | agent, routes, shipments, packages, weight, MBL, vessel."""

	def _ab_meta_row(ic, val, label=None):
		span = (
			f'<span class="ab-meta-k">{escape_html(label)}:</span>{escape_html(str(val))}'
			if label
			else escape_html(str(val))
		)
		return f'<div class="ab-meta-row"><i class="fa {escape_html(ic)}"></i><span>{span}</span></div>'

	meta_primary_parts = []
	if getattr(doc, "consolidation_type", None):
		meta_primary_parts.append(_ab_meta_row("fa-sitemap", doc.consolidation_type, "Type"))
	if getattr(doc, "consolidation_date", None):
		meta_primary_parts.append(_ab_meta_row("fa-calendar", str(doc.consolidation_date), "Date"))
	if getattr(doc, "etd", None):
		meta_primary_parts.append(_ab_meta_row("fa-ship", str(doc.etd), "ETD"))
	if getattr(doc, "eta", None):
		meta_primary_parts.append(_ab_meta_row("fa-anchor", str(doc.eta), "ETA"))
	if getattr(doc, "priority", None) and str(doc.priority).strip() and str(doc.priority) != "Normal":
		meta_primary_parts.append(_ab_meta_row("fa-flag", doc.priority, "Priority"))
	meta_primary_inner = "".join(meta_primary_parts)
	meta_primary = f'<div class="ab-summary-meta-rows">{meta_primary_inner}</div>' if meta_primary_inner else ""

	routes = doc.get("consolidation_routes") or []
	n_att = len(doc.get("attached_sea_shipments") or [])
	sec_lines = []
	if getattr(doc, "consolidation_agent", None):
		sec_lines.append(("fa-user", "Agent", doc.consolidation_agent))
	sec_lines.append(("fa-road", "Routes", str(len(routes))))
	sec_lines.append(("fa-link", "Shipments", str(n_att)))
	if doc.get("total_packages") is not None:
		sec_lines.append(("fa-cube", "Packages", str(doc.total_packages or 0)))
	if getattr(doc, "total_weight", None) is not None:
		sec_lines.append(
			(
				"fa-balance-scale",
				"Weight",
				frappe.format_value(doc.total_weight or 0, df=dict(fieldtype="Float")),
			)
		)
	if getattr(doc, "master_bill", None):
		sec_lines.append(("fa-file-text-o", "MBL", doc.master_bill))
	if getattr(doc, "vessel_name", None):
		vv = doc.vessel_name
		if getattr(doc, "voyage_number", None):
			vv = f"{vv} / {doc.voyage_number}"
		sec_lines.append(("fa-ship", "Vessel", vv))
	sec_inner = "".join(
		f'<div class="ab-sec-line"><i class="fa {escape_html(ic)}"></i>'
		f'<span class="ab-sec-val"><span class="ab-sec-k">{escape_html(lbl)}:</span>'
		f"{escape_html(str(val))}</span></div>"
		for ic, lbl, val in sec_lines
	)
	meta_secondary = f'<div class="ab-secondary-meta">{sec_inner}</div>' if sec_inner else ""

	if meta_primary and meta_secondary:
		return (
			f'<div class="log-ab-meta-cluster">'
			f'<div class="log-ab-meta-col log-ab-meta-col--primary">{meta_primary}</div>'
			f'<div class="log-ab-meta-col log-ab-meta-col--secondary">{meta_secondary}</div>'
			f"</div>"
		)
	if meta_primary:
		return (
			f'<div class="log-ab-meta-cluster">'
			f'<div class="log-ab-meta-col log-ab-meta-col--primary">{meta_primary}</div>'
			f"</div>"
		)
	if meta_secondary:
		return (
			f'<div class="log-ab-meta-cluster">'
			f'<div class="log-ab-meta-col log-ab-meta-col--secondary">{meta_secondary}</div>'
			f"</div>"
		)
	return ""


def _sea_consolidation_routes_as_map_legs(doc):
	"""Child rows -> load_port/discharge_port dicts for build_map_segments_from_routing_legs."""
	routes = getattr(doc, "consolidation_routes", None) or []
	out = []
	for i, r in enumerate(routes, 1):
		out.append(
			{
				"idx": i,
				"load_port": getattr(r, "origin_port", None),
				"discharge_port": getattr(r, "destination_port", None),
				"type": getattr(r, "route_type", None) or "Direct",
			}
		)
	return out


def build_sea_consolidation_dashboard_config(doc):
	from logistics.document_management.dashboard_layout import build_map_segments_from_routing_legs

	status = doc.get("status") or "Draft"
	pkgs = doc.total_packages
	if pkgs is None:
		pkgs = sum(getattr(p, "package_count", 0) or 0 for p in (doc.consolidation_packages or []))
	header_items = [
		("Status", status),
		("ETD", str(doc.etd) if doc.etd else "—"),
		("ETA", str(doc.eta) if doc.eta else "—"),
		("Type", doc.consolidation_type or "—"),
		("Packages", str(pkgs or 0)),
		("Weight", frappe.format_value(doc.total_weight or 0, df=dict(fieldtype="Float"))),
	]
	hero_html = build_shipping_line_hero_html(doc, header_items)
	map_segments = build_map_segments_from_routing_legs(_sea_consolidation_routes_as_map_legs(doc))
	cfg = {
		"doctype": "Sea Consolidation",
		"map_id_prefix": "sea-consolidation-dash-map",
		"header_items": header_items,
		"hero_html": hero_html,
		"meta_cluster_html": build_sea_consolidation_meta_cluster_html(doc),
		"scroll_doctype": "Sea Consolidation",
		"ring_status_from": "workflow",
		"ring_status_field": "status",
		"include_default_dg": False,
	}
	if map_segments:
		cfg["map_points"] = []
		cfg["map_segments"] = map_segments
	return cfg


def build_sea_shipment_dashboard_config(doc):
	status = doc.get("status") or (
		"Submitted" if doc.docstatus == 1 else "Cancelled" if doc.docstatus == 2 else "Draft"
	)
	header_items = [
		("Status", status),
		("ETD", str(doc.etd) if doc.etd else "—"),
		("ETA", str(doc.eta) if doc.eta else "—"),
		("Incoterms", str(doc.incoterm) if getattr(doc, "incoterm", None) else "—"),
		("Packages", str(len(doc.packages or []))),
		("Weight", frappe.format_value(doc.total_weight or 0, df=dict(fieldtype="Float"))),
	]
	hero_html = build_shipping_line_hero_html(doc, header_items)
	return {
		"doctype": "Sea Shipment",
		"map_id_prefix": "sea-shipment-dash-map",
		"header_items": header_items,
		"hero_html": hero_html,
		"meta_cluster_html": build_freight_meta_cluster_html(doc),
		"scroll_doctype": "Sea Shipment",
		"ring_status_from": "workflow",
		"ring_status_field": "status",
	}


def build_sea_booking_dashboard_config(doc):
	status = doc.get("shipping_status")
	if not status:
		status = "Submitted" if doc.docstatus == 1 else "Cancelled" if doc.docstatus == 2 else "Draft"
	header_items = [
		("Status", status),
		("ETD", str(doc.etd) if doc.etd else "—"),
		("ETA", str(doc.eta) if doc.eta else "—"),
		("Incoterms", str(doc.incoterm) if getattr(doc, "incoterm", None) else "—"),
		("Packages", str(len(doc.packages or []))),
		("Weight", frappe.format_value(doc.total_weight or 0, df=dict(fieldtype="Float"))),
	]
	hero_html = build_shipping_line_hero_html(doc, header_items)
	return {
		"doctype": "Sea Booking",
		"map_id_prefix": "sea-booking-dash-map",
		"header_items": header_items,
		"hero_html": hero_html,
		"meta_cluster_html": build_freight_meta_cluster_html(doc),
		"scroll_doctype": "Sea Booking",
		"ring_status_from": "workflow",
		"ring_status_field": "shipping_status",
	}


def build_transport_order_dashboard_config(doc):
	status = (
		"Submitted"
		if doc.docstatus == 1
		else "Cancelled"
		if doc.docstatus == 2
		else "Draft"
	)
	legs = doc.get("legs") or []
	header_items = [
		("Status", status),
		("Booking Date", str(doc.booking_date) if doc.booking_date else "—"),
		("Customer", doc.customer or "—"),
		("Scheduled", str(doc.scheduled_date) if doc.scheduled_date else "—"),
		("Legs", str(len(legs))),
		("Packages", str(len(doc.packages or []))),
		("Weight", frappe.format_value(doc.total_weight or 0, df=dict(fieldtype="Float"))),
	]
	if getattr(doc, "transport_job_type", None):
		header_items.append(("Job Type", doc.transport_job_type))
	hero_html = build_transport_company_hero_html(doc, header_items)
	from logistics.transport.api_optimized import get_address_coordinates_batch

	addr_names = []
	for leg in legs:
		if leg.get("pick_address"):
			addr_names.append(leg.pick_address)
		if leg.get("drop_address"):
			addr_names.append(leg.drop_address)
	addr_coords = get_address_coordinates_batch(list(set(addr_names))) or {} if addr_names else {}
	map_points = []
	for leg in legs:
		for addr_field in ("pick_address", "drop_address"):
			addr = leg.get(addr_field)
			if addr:
				c = addr_coords.get(addr) if addr_coords else None
				if c and c.get("lat") is not None and c.get("lon") is not None:
					map_points.append({"lat": float(c["lat"]), "lon": float(c["lon"]), "label": addr})
	return {
		"doctype": "Transport Order",
		"map_id_prefix": "tro-dash-map",
		"header_items": header_items,
		"hero_html": hero_html,
		"route_panel_html": _route_panel_address_titles(doc, "legs"),
		"meta_cluster_html": build_transport_meta_cluster_html(doc),
		"scroll_doctype": "Transport Order",
		"map_points": map_points,
		"map_segments": None,
	}


def build_transport_job_dashboard_config(doc):
	status = doc.status or "Draft"
	legs = doc.get("legs") or []
	header_items = [
		("Status", status),
		("Booking Date", str(doc.booking_date) if doc.booking_date else "—"),
		("Customer", doc.customer or "—"),
		("Scheduled", str(doc.scheduled_date) if doc.scheduled_date else "—"),
		("Legs", str(len(legs))),
		("Packages", str(len(doc.packages or []))),
		("Weight", frappe.format_value(doc.total_weight or 0, df=dict(fieldtype="Float"))),
	]
	if getattr(doc, "transport_job_type", None):
		header_items.append(("Job Type", doc.transport_job_type))
	hero_html = build_transport_company_hero_html(doc, header_items)
	from logistics.transport.api_optimized import get_address_coordinates_batch

	addr_names = []
	for leg in legs:
		if leg.get("pick_address"):
			addr_names.append(leg.pick_address)
		if leg.get("drop_address"):
			addr_names.append(leg.drop_address)
	addr_coords = get_address_coordinates_batch(list(set(addr_names))) or {} if addr_names else {}
	map_points = []
	for leg in legs:
		for addr_field in ("pick_address", "drop_address"):
			addr = leg.get(addr_field)
			if addr:
				c = addr_coords.get(addr) if addr_coords else None
				if c and c.get("lat") is not None and c.get("lon") is not None:
					map_points.append({"lat": float(c["lat"]), "lon": float(c["lon"]), "label": addr})
	return {
		"doctype": "Transport Job",
		"map_id_prefix": "tj-dash-map",
		"header_items": header_items,
		"hero_html": hero_html,
		"route_panel_html": _route_panel_address_titles(doc, "legs"),
		"meta_cluster_html": build_transport_meta_cluster_html(doc),
		"scroll_doctype": "Transport Job",
		"ring_status_from": "workflow",
		"ring_status_field": "status",
		"map_points": map_points,
		"map_segments": None,
	}


def _declaration_port_pair_map_points(doc):
	"""Map markers from UNLOCO port_of_loading → port_of_discharge only (no routing legs)."""
	from logistics.document_management.dashboard_layout import get_unloco_coords

	pol = getattr(doc, "port_of_loading", None)
	pod = getattr(doc, "port_of_discharge", None)
	o = get_unloco_coords(pol)
	d = get_unloco_coords(pod)
	out = []
	if o:
		out.append(o)
	if d and (
		not out
		or (d.get("lat") != out[-1].get("lat"))
		or (d.get("lon") != out[-1].get("lon"))
	):
		out.append(d)
	return out


def build_declaration_dashboard_config(doc):
	from logistics.document_management.api import get_milestone_html

	status = "Cancelled" if doc.docstatus == 2 else (doc.status or "Draft")
	currency = doc.inv_currency or frappe.db.get_default("currency") or "PHP"
	amount = frappe.utils.flt(doc.declaration_value or 0)
	value_display = f"{frappe.utils.fmt_money(amount, precision=2)} {currency}"
	header_items = [
		("Status", status),
		("ETD", str(doc.etd) if doc.etd else "—"),
		("ETA", str(doc.eta) if doc.eta else "—"),
		("Value", value_display),
		("Vessel / flight", getattr(doc, "vessel_flight_number", None) or "—"),
		("Transport document", _customs_transport_document_line(doc)),
		("SLA", _customs_sla_line(doc)),
	]
	hero_html = build_customs_authority_hero_html(doc, list(header_items))
	route_supplement = _declaration_importer_classification_html(doc)
	milestone_html = ""
	if doc.name and not doc.is_new():
		milestone_html = get_milestone_html("Declaration", doc.name)
	else:
		milestone_html = '<div class="alert alert-info">Save the document to view milestones.</div>'
	alerts_prepend = ""
	if doc.name and not doc.is_new():
		try:
			alerts = doc.get_delay_penalty_alerts()
		except Exception:
			alerts = []
		if alerts:
			icons = {"danger": "fa-exclamation-circle", "warning": "fa-exclamation-triangle", "info": "fa-info-circle"}
			items = []
			for a in alerts:
				level = a.get("level") or "info"
				icon = icons.get(level, "fa-info-circle")
				items.append(
					f'<div class="dash-alert-item {level}"><i class="fa {icon}"></i>'
					f'<span>{escape_html(a.get("msg", ""))}</span></div>'
				)
			alerts_prepend = "\n".join(items)
	status_slug = "cancelled" if doc.docstatus == 2 else str(status).lower().replace(" ", "_").replace("/", "_")
	return {
		"doctype": "Declaration",
		"map_id_prefix": "decl-dash-map",
		"header_items": header_items,
		"hero_html": hero_html,
		"route_origin_attr": "port_of_loading",
		"route_dest_attr": "port_of_discharge",
		"map_points": _declaration_port_pair_map_points(doc),
		"map_segments": None,
		"meta_cluster_html": build_declaration_meta_cluster_html(doc),
		"route_supplement_html": route_supplement,
		"include_default_dg": False,
		"milestones_tab_inner_html": f'<div class="log-ab-ro-card" style="overflow:auto;">{milestone_html}</div>',
		"alerts_prepend_html": alerts_prepend,
		"status_slug": status_slug,
		"scroll_doctype": "Declaration",
		"scroll_field": "milestones",
		"customs_dashboard_enhanced_layout": True,
	}


def build_declaration_order_dashboard_config(doc):
	from logistics.document_management.api import get_milestone_html

	status = doc.status or "Draft"
	currency = doc.inv_currency or frappe.db.get_default("currency") or "PHP"
	try:
		amt = frappe.utils.flt(doc.inv_total_amount or 0)
		value_str = f"{frappe.utils.fmt_money(amt, precision=2)} {currency}"
	except Exception:
		value_str = str(doc.inv_total_amount) if doc.inv_total_amount is not None else "—"
	header_items = [
		("Status", status),
		("ETD", str(doc.etd) if doc.etd else "—"),
		("ETA", str(doc.eta) if doc.eta else "—"),
		("Value", value_str),
		("Vessel / flight", getattr(doc, "vessel_flight_number", None) or "—"),
		("Transport document", _customs_transport_document_line(doc)),
		("SLA", _customs_sla_line(doc)),
	]
	hero_html = build_customs_authority_hero_html(doc, list(header_items))
	route_supplement = _declaration_importer_classification_html(doc)
	milestone_html = ""
	if doc.name and not doc.is_new():
		try:
			milestone_html = get_milestone_html("Declaration Order", doc.name)
		except Exception:
			milestone_html = '<div class="alert alert-warning">Could not load milestones.</div>'
	else:
		milestone_html = '<div class="alert alert-info">Save the document to view milestones.</div>'
	alerts_prepend = ""
	if doc.name and not doc.is_new():
		try:
			alerts = doc.get_delay_penalty_alerts()
		except Exception:
			alerts = []
		if alerts:
			icons = {"danger": "fa-exclamation-circle", "warning": "fa-exclamation-triangle", "info": "fa-info-circle"}
			items = []
			for a in alerts:
				level = a.get("level") or "info"
				icon = icons.get(level, "fa-info-circle")
				items.append(
					f'<div class="dash-alert-item {level}"><i class="fa {icon}"></i>'
					f'<span>{escape_html(a.get("msg", ""))}</span></div>'
				)
			alerts_prepend = "\n".join(items)
	status_slug = str(status).lower().replace(" ", "_")
	return {
		"doctype": "Declaration Order",
		"map_id_prefix": "dco-dash-map",
		"header_items": header_items,
		"hero_html": hero_html,
		"route_origin_attr": "port_of_loading",
		"route_dest_attr": "port_of_discharge",
		"map_points": _declaration_port_pair_map_points(doc),
		"map_segments": None,
		"meta_cluster_html": build_declaration_order_meta_cluster_html(doc),
		"route_supplement_html": route_supplement,
		"include_default_dg": False,
		"milestones_tab_inner_html": f'<div class="log-ab-ro-card" style="overflow:auto;">{milestone_html}</div>',
		"alerts_prepend_html": alerts_prepend,
		"status_slug": status_slug,
		"scroll_doctype": "Declaration Order",
		"scroll_field": "milestones",
		"customs_dashboard_enhanced_layout": True,
	}
