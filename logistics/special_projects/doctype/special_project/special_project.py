# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt


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
			project.project_type = frappe.db.get_single_value(
				"Special Project Settings", "default_project_type"
			) or frappe.db.get_value("Project Type", {"name": "External"}, "name")
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


@frappe.whitelist()
def get_dashboard_html(special_project):
	"""Generate HTML for Dashboard tab: Run Sheet layout with map, milestones."""
	if not special_project:
		return "<div class='alert alert-info'>Save the project to view the dashboard.</div>"
	try:
		from logistics.document_management.dashboard_layout import build_run_sheet_style_dashboard
		from logistics.document_management.api import get_dashboard_alerts_html

		doc = frappe.get_doc("Special Project", special_project)
		status = doc.status or "Draft"
		jobs = doc.get("jobs") or []
		resources = doc.get("resources") or []
		billings = doc.get("billings") or []
		deliveries = doc.get("deliveries") or []
		planned_cost = sum(flt(j.planned_cost or 0) for j in jobs)
		actual_cost = sum(flt(j.actual_cost or 0) for j in jobs)
		planned_rev = sum(flt(j.planned_revenue or 0) for j in jobs)
		actual_rev = sum(flt(j.actual_revenue or 0) for j in jobs)

		def fmt(v):
			return frappe.format_value(v, df={"fieldtype": "Currency"}) if v is not None else "—"

		header_items = [
			("Status", status),
			("Jobs", str(len(jobs))),
			("Resources", str(len(resources))),
			("Budget", fmt(planned_cost)),
			("Actual Revenue", fmt(actual_rev)),
			("Deliveries", str(len(deliveries))),
			("Billings", str(len(billings))),
		]
		if doc.priority:
			header_items.append(("Priority", doc.priority))

		# Aggregated milestones from linked jobs
		all_milestones = []
		for row in jobs:
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
				for lm in frappe.get_all("Logistics Milestone", filters={"name": ["in", names]}, fields=["name", "description"]):
					milestone_details[lm.name] = lm.description or lm.name

		cards_html = ""
		for i, m in enumerate(all_milestones[:15], 1):
			st = (m.status or "Planned").lower().replace(" ", "-")
			desc = milestone_details.get(m.milestone, m.milestone or "Milestone")
			planned = frappe.utils.format_datetime(m.planned_end) if m.planned_end else "—"
			actual = frappe.utils.format_datetime(m.actual_end) if m.actual_end else "—"
			cards_html += f"""
			<div class="dash-card {st}">
				<div class="card-header"><h5>{desc}</h5><span class="card-num">#{i}</span></div>
				<div class="card-details">Planned: {planned}<br>Actual: {actual}</div>
				<span class="card-badge {st}">{m.status or "Planned"}</span>
			</div>"""

		# Map points from movements
		movements = _collect_movements_from_jobs(jobs)
		valid = [m for m in movements if m.get("origin_coords") or m.get("dest_coords")]
		map_points = []
		seen = set()
		for m in valid:
			for key, label in [("origin_coords", m.get("origin_label", "Origin")), ("dest_coords", m.get("dest_label", "Dest"))]:
				c = m.get(key)
				if c and c.get("lat") is not None and c.get("lon") is not None:
					tup = (c["lat"], c["lon"])
					if tup not in seen:
						seen.add(tup)
						map_points.append({"lat": float(c["lat"]), "lon": float(c["lon"]), "label": label})

		alerts_html = get_dashboard_alerts_html("Special Project", special_project)
		return build_run_sheet_style_dashboard(
			header_title=doc.project_name or doc.name or "Special Project",
			header_subtitle="Special Project",
			header_items=header_items,
			cards_html=cards_html or "<div class=\"text-muted\">No milestones. Link jobs to see aggregated milestones.</div>",
			map_points=map_points,
			map_id_prefix="sp-dash-map",
			doc_alerts_html="",
			alerts_html=alerts_html,
		)
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
		jobs = doc.get("jobs") or []

		# Aggregate Job Milestones from all linked jobs
		all_milestones = []
		for row in jobs:
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
			("Jobs", str(len(jobs))),
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
	"""Collect movement points (origin/dest) from jobs with movements. Returns list of dicts."""
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
		movements = _collect_movements_from_jobs(doc.get("jobs") or [])

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
	"""Return HTML for Cost & Revenue Summary from jobs table."""
	if not special_project:
		return ""
	doc = frappe.get_doc("Special Project", special_project)
	jobs = doc.get("jobs") or []

	planned_cost = sum((j.planned_cost or 0) for j in jobs)
	actual_cost = sum((j.actual_cost or 0) for j in jobs)
	planned_revenue = sum((j.planned_revenue or 0) for j in jobs)
	actual_revenue = sum((j.actual_revenue or 0) for j in jobs)
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
