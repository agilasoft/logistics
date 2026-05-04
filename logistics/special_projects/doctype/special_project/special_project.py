# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import escape_html, flt

from logistics.utils.special_project_internal_jobs import (
	job_refs_from_internal_job_details,
	resolve_internal_job_detail_row_to_operational_ref,
)


class SpecialProject(Document):
	def validate(self):
		pass

	def autoname(self):
		"""Use ERPNext Project ID as Special Project ID (created in before_insert)."""
		if self.flags.get("erpnext_project_name"):
			self.name = self.flags.erpnext_project_name

	def before_insert(self):
		"""Create ERPNext Project first, then use its ID as this document's ID."""
		self._create_erpnext_project_before_insert()

	def on_update(self):
		"""Auto-charge scoping costs when status changes to Booked."""
		if self.has_value_changed("status") and self.status in ("Booked", "Approved", "Planning", "In Progress"):
			self._maybe_charge_scoping_costs()

	def _maybe_charge_scoping_costs(self):
		"""Charge completed scoping activities when project is booked."""
		changed = False
		for row in self.scoping_activities or []:
			if row.status == "Completed" and not row.charged_to_project:
				row.charged_to_project = 1
				row.charged_date = frappe.utils.today()
				changed = True
		# Save is handled by on_update flow

	def _create_erpnext_project_before_insert(self):
		"""Create ERPNext Project first; its ID will be used as Special Project ID via autoname."""
		if self.project:
			# Link Existing Project: use that Project's ID as our name
			self.flags.erpnext_project_name = self.project
			return

		if not frappe.db.exists("DocType", "Project"):
			return

		try:
			project = frappe.new_doc("Project")
			project.project_name = (
				self.project_name
				or f"Special Project {frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}"
			)
			project.customer = self.customer
			project.expected_start_date = self.planned_start or self.start_date
			project.expected_end_date = self.planned_end or self.end_date
			project.status = self._map_status_to_project(self.status)
			project.project_type = (
				self.project_type
				or frappe.db.get_single_value("Special Project Settings", "default_project_type")
				or frappe.db.get_value("Project Type", {"name": "External"}, "name")
			)
			project.company = frappe.defaults.get_defaults().get("company")

			project.insert(ignore_permissions=True)

			self.project = project.name
			self.flags.erpnext_project_name = project.name
		except Exception as e:
			frappe.log_error(
				title=_("Special Project: Failed to create ERPNext Project"),
				message=frappe.get_traceback(),
			)
			raise

	def _map_status_to_project(self, status):
		"""Map Special Project status to ERPNext Project status."""
		status_map = {
			"Draft": "Open",
			"Scoping": "Open",
			"Booked": "Open",
			"Planning": "Open",
			"Approved": "Open",
			"In Progress": "Open",
			"On Hold": "Open",
			"Completed": "Completed",
			"Cancelled": "Cancelled",
		}
		return status_map.get(status, "Open")


@frappe.whitelist()
def charge_scoping_costs(special_project):
	"""Charge all completed scoping activities to the project when it is booked."""
	doc = frappe.get_doc("Special Project", special_project)
	if doc.status not in ("Booked", "Approved", "Planning", "In Progress", "Completed"):
		frappe.throw(_("Project must be Booked or Approved to charge scoping costs."))

	changed = False
	for row in doc.scoping_activities or []:
		if row.status == "Completed" and not row.charged_to_project:
			row.charged_to_project = 1
			row.charged_date = frappe.utils.today()
			changed = True

	if changed:
		doc.save()
	return "Scoping costs charged."


def _job_map_payload(job_type, job_name):
	movements = _collect_movements_from_jobs([frappe._dict(job_type=job_type, job=job_name)])
	map_points = []
	for m in movements:
		oc = m.get("origin_coords")
		if oc and oc.get("lat") is not None and oc.get("lon") is not None:
			map_points.append(
				{
					"lat": float(oc["lat"]),
					"lon": float(oc["lon"]),
					"label": m.get("origin_label", "Origin"),
				}
			)
		dc = m.get("dest_coords")
		if dc and dc.get("lat") is not None and dc.get("lon") is not None:
			tup = (float(dc["lat"]), float(dc["lon"]))
			if not map_points or (map_points[-1].get("lat"), map_points[-1].get("lon")) != tup:
				map_points.append(
					{
						"lat": tup[0],
						"lon": tup[1],
						"label": m.get("dest_label", "Destination"),
					}
				)
	if not map_points:
		return {
			"map_mode": "empty",
			"map_points": [],
			"label": _("No origin/destination coordinates for this job yet."),
		}
	label = f"{job_type} {job_name}"
	road = job_type == "Transport Job"
	if len(map_points) == 1:
		return {
			"map_mode": "pin",
			"map_points": map_points,
			"straight_line": True,
			"label": label,
		}
	return {
		"map_mode": "route",
		"map_points": map_points,
		"straight_line": not road,
		"label": label,
	}


def _format_internal_job_location(row, which):
	"""Display name for location_from / location_to (UNLOCO code or Transport Zone name)."""
	val = getattr(row, "location_from" if which == "from" else "location_to", None)
	if not val:
		return ""
	lt = (getattr(row, "location_type", None) or "").strip()
	if lt == "Transport Zone" and frappe.db.exists("Transport Zone", val):
		zn = frappe.db.get_value("Transport Zone", val, "zone_name")
		return (zn or val).strip()
	return str(val).strip()


def _map_points_from_internal_job_transport_unloco(row):
	"""When no booking: route from UNLOCO location_from → location_to (location_type must be UNLOCO)."""
	if (getattr(row, "location_type", None) or "").strip() != "UNLOCO":
		return []
	from logistics.document_management.dashboard_layout import get_unloco_coords

	map_points = []
	for loc in (getattr(row, "location_from", None), getattr(row, "location_to", None)):
		if not loc:
			continue
		c = get_unloco_coords(loc)
		if not c:
			continue
		pt = {"lat": float(c["lat"]), "lon": float(c["lon"]), "label": c.get("label") or loc}
		if (
			not map_points
			or pt["lat"] != map_points[-1]["lat"]
			or pt["lon"] != map_points[-1]["lon"]
		):
			map_points.append(pt)
	return map_points


def _transport_fallback_route_label(row):
	a = _format_internal_job_location(row, "from")
	b = _format_internal_job_location(row, "to")
	if a or b:
		return f"{a or '—'} → {b or '—'}"
	return _("Transport")


def _internal_job_card_title(row):
	st = (getattr(row, "service_type", None) or "").strip() or _("Line")
	jt = (getattr(row, "job_type", None) or "").strip()
	jn = (getattr(row, "job_no", None) or "").strip()
	if jn and jt:
		return f"{st} · {jt}: {jn}"
	if jn:
		return f"{st} · {jn}"
	if st == "Transport":
		return f"{st} · {_transport_fallback_route_label(row)}"
	if st in ("Air", "Sea"):
		op = (getattr(row, "origin_port", None) or "").strip()
		dp = (getattr(row, "destination_port", None) or "").strip()
		if op or dp:
			return f"{st} · {op or '—'} → {dp or '—'}"
	if st == "Customs" and (getattr(row, "customs_authority", None) or "").strip():
		return f"{st} · {row.customs_authority}"
	if st == "Special Project" and jn:
		return f"{st} · {jn}"
	return st


def _internal_job_card_sub(row):
	parts = []
	st = (getattr(row, "service_type", None) or "").strip()
	if st == "Air":
		for x in (
			getattr(row, "airline", None),
			getattr(row, "freight_agent", None),
			getattr(row, "load_type", None),
			getattr(row, "direction", None),
			getattr(row, "air_house_type", None),
		):
			if x:
				parts.append(str(x).strip())
	elif st == "Sea":
		for x in (
			getattr(row, "shipping_line", None),
			getattr(row, "freight_agent_sea", None),
			getattr(row, "load_type", None),
			getattr(row, "direction", None),
			getattr(row, "sea_house_type", None),
		):
			if x:
				parts.append(str(x).strip())
	elif st == "Transport":
		for x in (
			getattr(row, "transport_template", None),
			getattr(row, "vehicle_type", None),
			getattr(row, "container_type", None),
			getattr(row, "container_no", None),
			getattr(row, "pick_mode", None),
			getattr(row, "drop_mode", None),
		):
			if x:
				parts.append(str(x).strip())
		ltp = (getattr(row, "location_type", None) or "").strip()
		if ltp:
			parts.append(ltp)
		if not (getattr(row, "job_no", None) or "").strip():
			lf = _format_internal_job_location(row, "from")
			lt = _format_internal_job_location(row, "to")
			if lf or lt:
				parts.append(f"{lf or '—'} → {lt or '—'}")
	elif st == "Customs":
		for x in (
			getattr(row, "customs_broker", None),
			getattr(row, "declaration_type", None),
			getattr(row, "customs_charge_category", None),
		):
			if x:
				parts.append(str(x).strip())
	elif st == "Special Project":
		for x in (getattr(row, "sp_equipment_type", None), getattr(row, "sp_handling", None)):
			if x:
				parts.append(str(x).strip())
		sp_site = getattr(row, "sp_site", None)
		if sp_site:
			site_lbl = frappe.db.get_value("Address", sp_site, "address_title")
			parts.append((site_lbl or sp_site)[:120])
		sn = getattr(row, "sp_resource_notes", None)
		if sn:
			parts.append((sn or "")[:120])
	return " · ".join(parts) if parts else "—"


def _map_payload_from_site_address(addr_name):
	"""Single pin on the map from a linked Address (customer site), if lat/lon are set on the address."""
	if not addr_name:
		return None
	try:
		from logistics.transport.api_optimized import get_address_coordinates_batch

		c = (get_address_coordinates_batch([addr_name]) or {}).get(addr_name)
		if c and c.get("lat") is not None and c.get("lon") is not None:
			lbl = frappe.db.get_value("Address", addr_name, "address_title") or addr_name
			return {
				"map_mode": "pin",
				"map_points": [
					{"lat": float(c["lat"]), "lon": float(c["lon"]), "label": lbl},
				],
				"straight_line": True,
				"label": lbl,
			}
	except Exception:
		pass
	return None


def _internal_job_row_map_payload(row):
	"""Map payload for one Internal Job Detail row: resolved job, else ports/locations on the line."""
	op = resolve_internal_job_detail_row_to_operational_ref(row)
	if op:
		return _job_map_payload(op[0], op[1])

	st = (getattr(row, "service_type", None) or "").strip()
	if st == "Special Project":
		site = getattr(row, "sp_site", None)
		if site:
			pl = _map_payload_from_site_address(site)
			if pl:
				return pl

	if st in ("Air", "Sea"):
		try:
			from logistics.document_management.dashboard_layout import get_unloco_coords

			o_code = getattr(row, "origin_port", None)
			d_code = getattr(row, "destination_port", None)
			o = get_unloco_coords(o_code) if o_code else None
			d = get_unloco_coords(d_code) if d_code else None
			map_points = []
			if o:
				map_points.append({"lat": float(o["lat"]), "lon": float(o["lon"]), "label": o.get("label") or o_code or "Origin"})
			if d and (
				not map_points
				or float(d["lat"]) != map_points[-1].get("lat")
				or float(d["lon"]) != map_points[-1].get("lon")
			):
				map_points.append({"lat": float(d["lat"]), "lon": float(d["lon"]), "label": d.get("label") or d_code or "Destination"})
			if len(map_points) == 1:
				return {
					"map_mode": "pin",
					"map_points": map_points,
					"straight_line": True,
					"label": o_code or d_code or _("Port"),
				}
			if len(map_points) >= 2:
				lbl = f"{o_code or '—'} → {d_code or '—'}"
				return {
					"map_mode": "route",
					"map_points": map_points,
					"straight_line": True,
					"label": lbl,
				}
		except Exception:
			pass

	if st == "Transport":
		tpts = _map_points_from_internal_job_transport_unloco(row)
		lbl = _transport_fallback_route_label(row)
		if len(tpts) >= 2:
			return {
				"map_mode": "route",
				"map_points": tpts,
				"straight_line": False,
				"label": lbl,
			}
		if len(tpts) == 1:
			return {
				"map_mode": "pin",
				"map_points": tpts,
				"straight_line": True,
				"label": lbl,
			}

	return {
		"map_mode": "empty",
		"map_points": [],
		"label": _("Link a booking/order, set Air/Sea ports, or set Location From/To (UNLOCO) for Transport to see the map."),
	}


def _sp_dash_card_html(title, sub, badge, kind="task"):
	border = "#17a2b8" if kind == "job" else "#667eea"
	return (
		f'<div class="sp-dash-card" style="border-left-color: {border};" role="button" tabindex="0">'
		f'<div class="sp-dash-card-title">{escape_html(title)}</div>'
		f'<div class="sp-dash-card-sub">{escape_html(sub)}</div>'
		f'<span class="sp-dash-card-badge">{escape_html(badge)}</span></div>'
	)


@frappe.whitelist()
def get_dashboard_html(special_project):
	"""Dashboard tab: Transport Job style header/tabs; Route = internal job lines + map (ports or shipment route)."""
	if not special_project:
		return "<div class='alert alert-info'>Save the project to view the dashboard.</div>"
	try:
		from logistics.air_freight.doctype.air_booking.air_booking_dashboard import _milestones_ro_panel_html
		from logistics.document_management.dashboard_layout import render_special_project_interactive_route_tab_html
		from logistics.document_management.logistics_form_dashboard import (
			build_customer_hero_html,
			build_special_project_meta_cluster_html,
			build_special_project_route_panel_html,
			render_logistics_form_dashboard_html,
		)
		from logistics.utils.sales_quote_validity import get_sales_quote_validity_dashboard_html

		doc = frappe.get_doc("Special Project", special_project)
		quote_html = get_sales_quote_validity_dashboard_html(doc) or ""

		status = doc.status or "Draft"
		job_rows = doc.get("internal_job_details") or []
		job_refs = job_refs_from_internal_job_details(doc)
		billings = doc.get("billings") or []
		deliveries = doc.get("deliveries") or []
		planned_cost = sum(flt(a.planned_cost or 0) for a in job_rows)
		actual_cost = sum(flt(a.actual_cost or 0) for a in job_rows)
		actual_rev = sum(flt(a.actual_revenue or 0) for a in job_rows)

		def fmt(v):
			return frappe.format_value(v, df={"fieldtype": "Currency"}) if v is not None else "—"

		header_items = [
			("Status", status),
			("Job lines", str(len(job_rows))),
			("Logistics jobs", str(len(job_refs))),
			("Budget", fmt(planned_cost)),
			("Actual Revenue", fmt(actual_rev)),
			("Deliveries", str(len(deliveries))),
			("Billings", str(len(billings))),
		]
		if doc.priority:
			header_items.append(("Priority", doc.priority))

		header_items_for_hero = list(header_items)
		hero_html = build_customer_hero_html(doc, header_items_for_hero)
		route_panel_html = build_special_project_route_panel_html(doc)
		meta_cluster_html = build_special_project_meta_cluster_html(doc)

		# Aggregated milestones from linked logistics jobs
		all_milestones = []
		for row in job_refs:
			jt = (row.job_type or "").strip()
			jn = (row.job or "").strip()
			if not jt or not jn:
				continue
			ms = frappe.get_all(
				"Job Milestone",
				filters={"job_type": jt, "job_number": jn},
				fields=["name", "milestone", "status", "planned_start", "planned_end", "actual_start", "actual_end"],
				order_by="planned_start",
			)
			for m in ms:
				all_milestones.append(frappe._dict(m))
		all_milestones.sort(key=lambda x: (x.planned_start or frappe.utils.now_datetime(), x.name or ""))

		milestone_details = {}
		if all_milestones:
			names = [m.milestone for m in all_milestones if m.milestone]
			if names:
				for lm in frappe.get_all(
					"Logistics Milestone", filters={"name": ["in", names]}, fields=["name", "description"]
				):
					milestone_details[lm.name] = lm.description or lm.name

		milestone_rows = list(all_milestones)
		ms_inner = _milestones_ro_panel_html(
			milestone_rows,
			milestone_details,
			doc.name or "",
			scroll_doctype="Special Project",
			scroll_field="milestone_html",
			empty_hint_html='<p class="text-muted ab-tab-empty" style="margin:0;">'
			+ _("No milestones from linked logistics jobs. Add jobs under <strong>Jobs</strong>.")
			+ "</p>",
		)
		n_ms = len(milestone_rows)
		done_ms = sum(1 for m in milestone_rows if str(m.status or "").strip() == "Completed")

		cards_parts = []
		map_payloads = []

		lines_ordered = sorted(job_rows, key=lambda r: int(getattr(r, "idx", None) or 0))
		for row in lines_ordered:
			payload = _internal_job_row_map_payload(row)
			map_payloads.append(payload)
			title = _internal_job_card_title(row)[:200]
			sub = _internal_job_card_sub(row)
			pc = getattr(row, "planned_cost", None)
			pr = getattr(row, "planned_revenue", None)
			if pc or pr:
				bits = []
				if pc:
					bits.append(_("Planned cost {0}").format(fmt(pc)))
				if pr:
					bits.append(_("Planned revenue {0}").format(fmt(pr)))
				fin = " · ".join(bits)
				if sub and sub != "—":
					sub = sub + " · " + fin
				else:
					sub = fin
			op = resolve_internal_job_detail_row_to_operational_ref(row)
			badge = (
				_("{0} (linked)").format(op[0])
				if op
				else (getattr(row, "service_type", None) or _("Job line"))
			)
			kind = "job" if op or (payload.get("map_points") or []) else "task"
			cards_parts.append(
				_sp_dash_card_html(
					title[:200],
					sub,
					badge,
					kind=kind,
				)
			)

		if not cards_parts:
			cards_parts.append(
				f'<div class="text-muted" style="padding:8px;">{escape_html(_("Add lines under Project jobs to see them here."))}</div>'
			)
			map_payloads.append({"map_mode": "empty", "map_points": [], "label": _("Nothing to show on the map yet.")})

		route_tab_override_html = render_special_project_interactive_route_tab_html(
			"sp-form-dash",
			map_payloads,
			"".join(cards_parts),
		)

		cfg = {
			"doctype": "Special Project",
			"map_id_prefix": "sp-form-dash",
			"header_items": header_items_for_hero,
			"hero_html": hero_html,
			"route_panel_html": route_panel_html,
			"meta_cluster_html": meta_cluster_html,
			"route_tab_override_html": route_tab_override_html,
			"milestones_tab_inner_html": ms_inner,
			"milestone_count_override": n_ms,
			"milestone_done_override": done_ms,
			"scroll_doctype": "Special Project",
			"scroll_field": "milestone_html",
			"ring_status_from": "workflow",
			"ring_status_field": "status",
			"include_default_dg": False,
			"map_points": [],
			"map_segments": None,
		}
		dash = render_logistics_form_dashboard_html(doc, cfg)
		return quote_html + dash
	except Exception as e:
		frappe.log_error(f"Special Project get_dashboard_html: {str(e)}", "Special Project Dashboard")
		return "<div class='alert alert-warning'>Error loading dashboard.</div>"


@frappe.whitelist()
def get_milestone_html(special_project):
	"""Generate HTML for Milestones tab: aggregated milestones from linked jobs."""
	if not special_project:
		return "<div class='alert alert-info'>Save the project to view milestones.</div>"
	try:
		from logistics.document_management.milestone_html import build_milestone_html

		doc = frappe.get_doc("Special Project", special_project)
		job_refs = job_refs_from_internal_job_details(doc)

		# Aggregate Job Milestones from all linked logistics jobs
		all_milestones = []
		for row in job_refs:
			job_type = (row.job_type or "").strip()
			job_name = (row.job or "").strip()
			if not job_type or not job_name:
				continue
			milestones = frappe.get_all(
				"Job Milestone",
				filters={"job_type": job_type, "job_number": job_name},
				fields=["name", "milestone", "status", "planned_start", "planned_end", "actual_start", "actual_end"],
				order_by="planned_start",
			)
			for m in milestones:
				all_milestones.append(frappe._dict(m))

		# Sort by planned_start
		all_milestones.sort(key=lambda x: (x.planned_start or frappe.utils.now_datetime(), x.name or ""))

		def format_dt(dt):
			return frappe.utils.format_datetime(dt) if dt else None

		detail_items = [
			("Status", doc.status or ""),
			("Project", doc.project_name or doc.name),
			("Logistics jobs", str(len(job_refs))),
		]
		detail_items = [(l, v) for l, v in detail_items if v]

		milestones_as_dicts = [
			{
				"name": m.name,
				"milestone": m.milestone,
				"status": m.status,
				"planned_start": m.planned_start,
				"planned_end": m.planned_end,
				"actual_start": m.actual_start,
				"actual_end": m.actual_end,
			}
			for m in all_milestones
		]

		return build_milestone_html(
			doctype="Special Project",
			docname=doc.name or "new",
			origin_name="Project",
			destination_name=doc.project_name or doc.name or "Milestones",
			detail_items=detail_items,
			milestones=milestones_as_dicts,
			format_datetime_fn=format_dt,
			include_doc_alerts=False,
			refresh_method="logistics.special_projects.doctype.special_project.special_project.get_milestone_html",
			refresh_arg_name="special_project",
		)
	except Exception as e:
		frappe.log_error(f"Special Project get_milestone_html: {str(e)}", "Special Project Milestones")
		return "<div class='alert alert-warning'>Error loading milestones.</div>"


def _get_unloco_coords(unloco_code):
	"""Get (lat, lon) for UNLOCO code, or None."""
	if not unloco_code:
		return None
	try:
		coords = frappe.db.get_value("UNLOCO", unloco_code, ["latitude", "longitude"], as_dict=True)
		if coords and coords.latitude is not None and coords.longitude is not None:
			lat = float(coords.latitude)
			lon = float(coords.longitude)
			if -90 <= lat <= 90 and -180 <= lon <= 180:
				return (lat, lon)
	except Exception:
		pass
	return None


def _collect_movements_from_jobs(jobs):
	"""Collect movement points (origin/dest) from logistics job refs. Each row: job_type (DocType), job (name)."""
	movements = []
	address_names = []

	for row in jobs or []:
		job_type = (row.job_type or "").strip()
		job_name = (row.job or "").strip()
		if not job_type or not job_name:
			continue

		try:
			if job_type == "Transport Job":
				job_doc = frappe.get_doc("Transport Job", job_name)
				legs = job_doc.get("legs") or []
				for leg in legs:
					pa = leg.get("pick_address")
					da = leg.get("drop_address")
					if pa:
						address_names.append(pa)
					if da:
						address_names.append(da)
					if pa or da:
						movements.append({
							"job_type": job_type,
							"job_name": job_name,
							"origin_addr": pa,
							"dest_addr": da,
							"origin_label": pa or "Pick",
							"dest_label": da or "Drop",
						})
			elif job_type == "Air Shipment":
				vals = frappe.db.get_value(
					"Air Shipment", job_name,
					["origin_port", "destination_port"],
					as_dict=True
				)
				if vals and (vals.origin_port or vals.destination_port):
					movements.append({
						"job_type": job_type,
						"job_name": job_name,
						"origin_unloco": vals.origin_port,
						"dest_unloco": vals.destination_port,
						"origin_label": vals.origin_port or "Origin",
						"dest_label": vals.destination_port or "Destination",
					})
			elif job_type == "Sea Shipment":
				vals = frappe.db.get_value(
					"Sea Shipment", job_name,
					["origin_port", "destination_port"],
					as_dict=True
				)
				if vals and (vals.origin_port or vals.destination_port):
					movements.append({
						"job_type": job_type,
						"job_name": job_name,
						"origin_unloco": vals.origin_port,
						"dest_unloco": vals.destination_port,
						"origin_label": vals.origin_port or "Origin",
						"dest_label": vals.destination_port or "Destination",
					})
			elif job_type == "Declaration":
				vals = frappe.db.get_value(
					"Declaration", job_name,
					["port_of_loading", "port_of_discharge"],
					as_dict=True
				)
				if vals and (vals.port_of_loading or vals.port_of_discharge):
					movements.append({
						"job_type": job_type,
						"job_name": job_name,
						"origin_unloco": vals.port_of_loading,
						"dest_unloco": vals.port_of_discharge,
						"origin_label": vals.port_of_loading or "Port of Loading",
						"dest_label": vals.port_of_discharge or "Port of Discharge",
					})
		except Exception:
			continue

	# Resolve UNLOCO coords
	for m in movements:
		if m.get("origin_unloco"):
			c = _get_unloco_coords(m["origin_unloco"])
			m["origin_coords"] = {"lat": c[0], "lon": c[1]} if c else None
		else:
			m["origin_coords"] = None
		if m.get("dest_unloco"):
			c = _get_unloco_coords(m["dest_unloco"])
			m["dest_coords"] = {"lat": c[0], "lon": c[1]} if c else None
		else:
			m["dest_coords"] = None

	# Batch resolve address coords (dedupe for efficiency)
	addr_coords = {}
	if address_names:
		try:
			from logistics.transport.api_optimized import get_address_coordinates_batch
			addr_coords = get_address_coordinates_batch(list(set(address_names))) or {}
		except Exception:
			addr_coords = {}

	for m in movements:
		if m.get("origin_addr"):
			c = addr_coords.get(m["origin_addr"]) if addr_coords else None
			m["origin_coords"] = c
		if m.get("dest_addr"):
			c = addr_coords.get(m["dest_addr"]) if addr_coords else None
			m["dest_coords"] = c

	return movements


def _get_movement_map_html_fragment(special_project):
	"""Return map HTML fragment for embedding in dashboard. Used by get_dashboard_html and get_movement_map_html."""
	if not special_project:
		return "<div class='alert alert-info'>Save the project to view the map.</div>"
	try:
		doc = frappe.get_doc("Special Project", special_project)
		movements = _collect_movements_from_jobs(job_refs_from_internal_job_details(doc))

		# Filter to movements that have at least one valid coordinate
		valid_movements = [
			m for m in movements
			if (m.get("origin_coords") or m.get("dest_coords"))
		]
		if not valid_movements:
			return """
			<div class="map-container" style="padding: 20px;">
				<div class="alert alert-info">
					<i class="fa fa-map"></i> No movement jobs with coordinates found.
					Add Transport Jobs, Air Shipments, Sea Shipments, or Declarations with origin/destination locations.
				</div>
			</div>
			"""

		# Build JSON for client
		import json
		movements_json = json.dumps(valid_movements)

		# Map renderer from Logistics Settings, fallback to Transport Settings (same as dashboard_layout)
		map_renderer = None
		try:
			ls = frappe.get_single("Logistics Settings")
			if ls:
				map_renderer = getattr(ls, "map_renderer", None)
			if not map_renderer or not str(map_renderer).strip():
				ts = frappe.get_single("Transport Settings")
				if ts:
					map_renderer = getattr(ts, "map_renderer", None)
		except Exception:
			pass
		if not map_renderer or not str(map_renderer).strip():
			map_renderer = "OpenStreetMap"

		html = f"""
		<div class="map-container" style="margin: 10px 0;">
			<div style="width: 100%; height: 450px; border: 1px solid #ddd; border-radius: 4px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); position: relative;">
				<div id="sp-movement-map" style="width: 100%; height: 100%;"></div>
				<div id="sp-movement-map-fallback" style="display: none; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); display: flex; align-items: center; justify-content: center; flex-direction: column;">
					<div style="text-align: center; color: #6c757d;">
						<i class="fa fa-map" style="font-size: 32px; margin-bottom: 15px;"></i>
						<div style="font-size: 18px; font-weight: 500; margin-bottom: 10px;">Movement Map</div>
						<div style="font-size: 12px; color: #999;">Loading map...</div>
					</div>
				</div>
			</div>
			<div class="text-muted small" style="margin-top: 10px;">Jobs with movements: Transport, Air, Sea, Declaration</div>
		</div>
		<script>
		(function() {{
			const movements = {movements_json};
			const mapRenderer = {json.dumps(map_renderer)};
			const mapId = 'sp-movement-map';
			const fallbackId = 'sp-movement-map-fallback';

			function showFallback() {{
				const fallback = document.getElementById(fallbackId);
				if (fallback) fallback.style.display = 'flex';
			}}
			function hideFallback() {{
				const fallback = document.getElementById(fallbackId);
				if (fallback) fallback.style.display = 'none';
			}}

			function initMap() {{
				const el = document.getElementById(mapId);
				if (!el) {{ setTimeout(initMap, 100); return; }}
				try {{
					const points = [];
					movements.forEach(function(m) {{
						if (m.origin_coords) points.push([m.origin_coords.lat, m.origin_coords.lon, m.origin_label || 'Origin', m.job_type, m.job_name]);
						if (m.dest_coords) points.push([m.dest_coords.lat, m.dest_coords.lon, m.dest_label || 'Dest', m.job_type, m.job_name]);
					}});
					if (points.length === 0) {{ showFallback(); return; }}

					const renderer = (mapRenderer || '').toLowerCase();
					if (renderer === 'google maps') {{
						initGoogleMap(el, points); return;
					}}
					if (renderer === 'mapbox' || renderer === 'maplibre') {{
						initMapLibre(el, points); return;
					}}
					initLeaflet(el, points);
				}} catch (e) {{
					console.error('Movement map init error:', e);
					showFallback();
				}}
			}}

			function initLeaflet(el, points) {{
				if (!window.L) {{
					const css = document.createElement('link');
					css.rel = 'stylesheet';
					css.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
					document.head.appendChild(css);
					const script = document.createElement('script');
					script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
					script.onload = function() {{ initLeaflet(el, points); }};
					document.head.appendChild(script);
					return;
				}}
				const map = L.map(mapId).setView([points[0][0], points[0][1]], 4);
				L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ attribution: '© OpenStreetMap contributors' }}).addTo(map);
				const group = [];
				points.forEach(function(p) {{
					const m = L.marker([p[0], p[1]]).addTo(map);
					m.bindPopup('<b>' + (p[2] || '') + '</b><br>' + (p[3] || '') + ': ' + (p[4] || ''));
					group.push(m);
				}});
				if (group.length) {{
					const bounds = L.latLngBounds(group.map(function(m) {{ return m.getLatLng(); }}));
					map.fitBounds(bounds.pad(0.1));
				}}
				hideFallback();
			}}

			function initMapLibre(el, points) {{
				if (!window.maplibregl) {{
					const css = document.createElement('link');
					css.rel = 'stylesheet';
					css.href = 'https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css';
					document.head.appendChild(css);
					const script = document.createElement('script');
					script.src = 'https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js';
					script.onload = function() {{ initMapLibre(el, points); }};
					document.head.appendChild(script);
					return;
				}}
				const centerLat = points.reduce(function(s, p) {{ return s + p[0]; }}, 0) / points.length;
				const centerLon = points.reduce(function(s, p) {{ return s + p[1]; }}, 0) / points.length;
				const map = new maplibregl.Map({{
					container: mapId,
					style: {{ version: 8, sources: {{ 'osm': {{ type: 'raster', tiles: ['https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png'], tileSize: 256 }} }}, layers: [{{ id: 'osm', type: 'raster', source: 'osm' }}] }},
					center: [centerLon, centerLat],
					zoom: 4
				}});
				points.forEach(function(p) {{
					const marker = new maplibregl.Marker({{ color: 'blue' }}).setLngLat([p[1], p[0]]).setPopup(new maplibregl.Popup().setHTML('<b>' + (p[2] || '') + '</b><br>' + (p[3] || '') + ': ' + (p[4] || ''))).addTo(map);
				}});
				if (points.length > 1) {{
					const lngs = points.map(function(p) {{ return p[1]; }});
					const lats = points.map(function(p) {{ return p[0]; }});
					map.fitBounds([[Math.min.apply(null, lngs), Math.min.apply(null, lats)], [Math.max.apply(null, lngs), Math.max.apply(null, lats)]], {{ padding: 50 }});
				}}
				hideFallback();
			}}

			function initGoogleMap(el, points) {{
				showFallback();
			}}

			if (document.readyState === 'loading') {{
				document.addEventListener('DOMContentLoaded', initMap);
			}} else {{
				initMap();
			}}
		}})();
		</script>
		"""
		return html
	except Exception as e:
		frappe.log_error(f"Special Project get_movement_map_html: {str(e)}", "Special Project Map")
		return "<div class='alert alert-warning'>Error loading map.</div>"


@frappe.whitelist()
def get_movement_map_html(special_project):
	"""Whitelisted API: returns map HTML (same as dashboard-embedded fragment)."""
	return _get_movement_map_html_fragment(special_project)


@frappe.whitelist()
def get_cost_revenue_summary(special_project):
	"""Return HTML for Cost & Revenue Summary from project job lines."""
	if not special_project:
		return ""
	doc = frappe.get_doc("Special Project", special_project)
	rows = doc.get("internal_job_details") or []

	planned_cost = sum((a.planned_cost or 0) for a in rows)
	actual_cost = sum((a.actual_cost or 0) for a in rows)
	planned_revenue = sum((a.planned_revenue or 0) for a in rows)
	actual_revenue = sum((a.actual_revenue or 0) for a in rows)
	planned_margin = planned_revenue - planned_cost if planned_revenue or planned_cost else None
	actual_margin = actual_revenue - actual_cost if actual_revenue or actual_cost else None

	def fmt(v):
		return frappe.format_value(v, df={"fieldtype": "Currency"}) if v is not None else "—"

	rows = [
		f"<tr><td>{_('Planned Cost')}</td><td class='text-right'>{fmt(planned_cost)}</td>"
		f"<td>{_('Planned Revenue')}</td><td class='text-right'>{fmt(planned_revenue)}</td></tr>",
		f"<tr><td>{_('Actual Cost')}</td><td class='text-right'>{fmt(actual_cost)}</td>"
		f"<td>{_('Actual Revenue')}</td><td class='text-right'>{fmt(actual_revenue)}</td></tr>",
		f"<tr><td>{_('Planned Margin')}</td><td class='text-right'>{fmt(planned_margin)}</td>"
		f"<td>{_('Actual Margin')}</td><td class='text-right'>{fmt(actual_margin)}</td></tr>",
	]
	html = f'<table class="table table-bordered table-sm" style="max-width: 500px;"><tbody>{"".join(rows)}</tbody></table>'
	return html
