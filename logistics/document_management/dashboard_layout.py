# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Shared Run Sheet-style dashboard layout for Air Shipment, Sea Shipment,
Transport Job, Declaration, Special Project. Layout: header + sidebar (milestones/legs) + map.
"""

from __future__ import unicode_literals

import json
import frappe


def get_unloco_coords(unloco_code):
	"""Get (lat, lon) for UNLOCO code, or None."""
	if not unloco_code:
		return None
	try:
		coords = frappe.db.get_value("UNLOCO", unloco_code, ["latitude", "longitude"], as_dict=True)
		if coords and coords.latitude is not None and coords.longitude is not None:
			lat = float(coords.latitude)
			lon = float(coords.longitude)
			if -90 <= lat <= 90 and -180 <= lon <= 180:
				return {"lat": lat, "lon": lon, "label": unloco_code}
	except Exception:
		pass
	return None


def build_map_segments_from_routing_legs(routing_legs, get_coords_fn=None):
	"""
	Build map_segments from routing legs for Air/Sea Shipment dashboard.
	routing_legs: list of child table rows with load_port, discharge_port, type
	get_coords_fn: optional fn(unloco_code) -> {lat, lon, label}; defaults to get_unloco_coords
	Returns list of {"type": str, "points": [...]} for build_run_sheet_style_dashboard.
	"""
	if not routing_legs:
		return None
	get_coords = get_coords_fn or get_unloco_coords
	segments = []
	for leg in sorted(routing_legs, key=lambda r: int(r.get("idx") or 0)):
		load_port = leg.get("load_port")
		discharge_port = leg.get("discharge_port")
		leg_type = leg.get("type") or "Main"
		o = get_coords(load_port) if load_port else None
		d = get_coords(discharge_port) if discharge_port else None
		pts = []
		if o:
			pts.append(o)
		if d and (not pts or (d.get("lat") != pts[-1].get("lat")) or (d.get("lon") != pts[-1].get("lon"))):
			pts.append(d)
		if len(pts) >= 2:
			segments.append({"type": leg_type, "points": pts})
	if not segments:
		return None
	return segments


RUN_SHEET_LAYOUT_CSS = """
.run-sheet-dash { font-family: inherit; font-size: 13px; }
.run-sheet-header { background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; margin-bottom: 20px; padding: 12px 16px; }
.header-main { display: flex; justify-content: space-between; align-items: center; gap: 20px; flex-wrap: wrap; }
.header-primary { display: flex; flex-direction: column; gap: 2px; }
.section-label { font-size: 10px; color: #6c757d; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; }
.primary-title { font-size: 18px; font-weight: 700; color: #007bff; }
.header-details { display: flex; gap: 15px; align-items: center; flex-wrap: wrap; }
.header-item { display: flex; align-items: baseline; gap: 5px; }
.header-item label { font-size: 10px; color: #6c757d; font-weight: 600; }
.header-item span { font-size: 11px; color: #2c3e50; font-weight: 500; }
.route-container { display: flex; gap: 20px; margin: 20px 0; align-items: flex-start; }
.cards-sidebar { flex: 1; max-width: 320px; min-width: 0; }
/* Collapsible milestone/leg column (details/summary — no JS, always shows a control) */
.run-sheet-cards-panel { margin: 0; border: 1px solid #e0e0e0; border-radius: 6px; background: #fff; overflow: hidden; }
.run-sheet-cards-panel-summary {
	list-style: none;
	cursor: pointer;
	user-select: none;
	padding: 10px 12px;
	font-size: 12px;
	font-weight: 600;
	color: #333;
	display: flex;
	align-items: center;
	gap: 8px;
	background: #f8f9fa;
	border-bottom: 1px solid #e9ecef;
}
.run-sheet-cards-panel-summary::-webkit-details-marker { display: none; }
.run-sheet-cards-panel-summary::before {
	content: "";
	display: inline-block;
	width: 0;
	height: 0;
	border-left: 5px solid transparent;
	border-right: 5px solid transparent;
	border-top: 6px solid #6c757d;
	transition: transform 0.2s ease;
	flex-shrink: 0;
}
.run-sheet-cards-panel[open] > .run-sheet-cards-panel-summary::before { transform: rotate(180deg); }
.run-sheet-cards-panel .card-list { padding: 8px; }
.run-sheet-cards-panel:not([open]) > .run-sheet-cards-panel-summary { border-bottom: none; }
.cards-sidebar:has(.run-sheet-cards-panel:not([open])) { flex: 0 0 auto; max-width: 100%; }
.map-main { flex: 2; align-self: flex-start; position: relative; z-index: 1; }
.map-box { width: 100%; height: 500px; border: 1px solid #ddd; border-radius: 4px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1); position: relative; }
.map-view { width: 100%; height: 100%; }
.map-links { margin-top: 10px; display: flex; gap: 20px; align-items: center; justify-content: center; }
.map-links a { text-decoration: none; color: #6c757d; font-size: 12px; }
.map-legend { position: absolute; top: 10px; left: 10px; z-index: 1000; background: rgba(255,255,255,0.95); padding: 8px 12px; border-radius: 4px; font-size: 11px; display: flex; gap: 12px; flex-wrap: wrap; box-shadow: 0 1px 3px rgba(0,0,0,0.15); }
.map-legend-item { display: inline-flex; align-items: center; gap: 4px; }
.card-list { display: flex; flex-direction: column; gap: 8px; }
.dash-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-left: 4px solid #667eea; }
.dash-card.completed { border-left-color: #28a745; }
.dash-card.delayed { border-left-color: #dc3545; }
.dash-card.planned { border-left-color: #6c757d; }
.dash-card.started { border-left-color: #007bff; }
.card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; }
.card-header h5 { margin: 0; font-size: 14px; font-weight: 600; color: #333; }
.card-num { background: #667eea; color: white; padding: 2px 8px; border-radius: 10px; font-size: 10px; font-weight: 600; }
.card-details { font-size: 11px; color: #6c757d; line-height: 1.4; }
.card-badge { padding: 2px 6px; border-radius: 10px; font-size: 10px; font-weight: 500; text-transform: uppercase; }
.card-badge.completed { background: #d4edda; color: #155724; }
.card-badge.delayed { background: #f8d7da; color: #721c24; }
.card-badge.planned { background: #e2e3e5; color: #6c757d; }
.card-badge.started { background: #cfe2ff; color: #084298; }
/* Document alerts number cards */
.doc-alerts-cards-wrapper { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 16px; }
.doc-alerts-cards { display: flex; flex-wrap: wrap; gap: 12px; align-items: stretch; }
.doc-alert-card { min-width: 80px; flex: 1; background: #fff; border-radius: 6px; border: 1px solid #e0e0e0; padding: 12px 16px; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.08); transition: box-shadow 0.15s ease; }
.doc-alert-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.12); }
.doc-alert-card-value { font-size: 24px; font-weight: 700; line-height: 1.2; }
.doc-alert-card-title { font-size: 11px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; font-weight: 600; }
.doc-alert-card-warning .doc-alert-card-value { color: #856404; }
.doc-alert-card-warning { border-left: 4px solid #ffc107; }
.doc-alert-card-danger .doc-alert-card-value { color: #721c24; }
.doc-alert-card-danger { border-left: 4px solid #dc3545; }
.doc-alert-card-info .doc-alert-card-value { color: #0c5460; }
.doc-alert-card-info { border-left: 4px solid #17a2b8; }
.doc-alert-card-success .doc-alert-card-value { color: #155724; }
.doc-alert-card-success { border-left: 4px solid #28a745; }
.doc-alert-card-secondary .doc-alert-card-value { color: #383d41; }
.doc-alert-card-secondary { border-left: 4px solid #6c757d; }
.doc-alert-card-permits { border-left: 4px solid #ff9800; }
.doc-alert-card-permits .doc-alert-card-value { color: #e65100; }
.doc-alert-card-exemptions { border-left: 4px solid #9c27b0; }
.doc-alert-card-exemptions .doc-alert-card-value { color: #7b1fa2; }
.doc-management-section .section-label { display: block; margin-bottom: 8px; }
.header-route { display: flex; gap: 40px; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid #e9ecef; }
.header-route.no-border { border-bottom: none; padding-bottom: 0; margin-bottom: 0; }
.header-route .route-column { flex: 1; }
.header-route .route-location { font-size: 16px; font-weight: 600; color: #007bff; }
/* Card wrapper for header details (Status, Type, Date, Port of Loading, etc.) - full width, no top/bottom lines */
.header-details-card { background: #f8f9fa; padding: 12px 16px; display: flex; gap: 15px; align-items: center; flex-wrap: wrap; width: 100%; }
.header-details-full-width { flex-basis: 100%; width: 100%; }
/* Status badge in dashboard header */
.dash-status-badge { display: inline-block; padding: 6px 14px; border-radius: 6px; font-size: 13px; font-weight: 600; margin-left: 12px; }
.dash-status-badge.draft { background: #e2e3e5; color: #383d41; }
.dash-status-badge.submitted { background: #cfe2ff; color: #084298; }
.dash-status-badge.under_review { background: #fff3cd; color: #856404; }
.dash-status-badge.cleared { background: #d4edda; color: #155724; }
.dash-status-badge.released { background: #d4edda; color: #155724; }
.dash-status-badge.rejected { background: #f8d7da; color: #721c24; }
.dash-status-badge.cancelled { background: #e2e3e5; color: #6c757d; }
/* Delay/penalty alerts section - per-level collapsible groups only */
.dash-alerts-section { margin-bottom: 16px; }
.dash-alert-item { padding: 8px 12px; border-radius: 6px; margin-bottom: 6px; font-size: 12px; display: flex; align-items: flex-start; gap: 8px; }
.dash-alert-item.danger { background: #f8d7da; color: #721c24; border-left: 4px solid #dc3545; }
.dash-alert-item.warning { background: #fff3cd; color: #856404; border-left: 4px solid #ffc107; }
.dash-alert-item.info { background: #d1ecf1; color: #0c5460; border-left: 4px solid #17a2b8; }
.dash-alert-item i { margin-top: 1px; }
/* Collapsible alert groups per level (Critical, Warnings, Information) */
.dash-alert-group { margin-bottom: 12px; border-radius: 6px; overflow: hidden; border: 1px solid rgba(0,0,0,0.08); }
.dash-alert-group-header { padding: 8px 12px; font-size: 12px; font-weight: 600; cursor: pointer; display: flex; align-items: center; gap: 8px; user-select: none; }
.dash-alert-group-header:hover { opacity: 0.9; }
.dash-alert-group.dash-alert-group-danger .dash-alert-group-header { background: #f8d7da; color: #721c24; }
.dash-alert-group.dash-alert-group-warning .dash-alert-group-header { background: #fff3cd; color: #856404; }
.dash-alert-group.dash-alert-group-info .dash-alert-group-header { background: #d1ecf1; color: #0c5460; }
.dash-alert-group-chevron { font-size: 10px; transition: transform 0.2s ease; }
.run-sheet-dash .dash-alert-group-body,
.dash-alert-group-body { padding: 6px 12px 12px; min-height: 0; max-height: 300px; overflow-y: auto; overflow-x: hidden; -webkit-overflow-scrolling: touch; }
.dash-alert-group.collapsed .dash-alert-group-body { display: none; }
/* Dangerous Goods under origin/destination: green = compliant, red = non-compliant */
.dg-alert-compliant { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
.dg-alert-non-compliant { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
.dg-alert-pending { background: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
/* Importer classification card (below Importer in Declaration dashboard) */
.importer-classification-card { background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 6px; padding: 10px 14px; margin-top: 10px; display: inline-block; }
.importer-classification-card .classification-label { font-size: 10px; color: #6c757d; text-transform: uppercase; font-weight: 600; }
.importer-classification-card .classification-value { font-size: 14px; font-weight: 600; color: #2c3e50; }
.importer-classification-card.sgl { border-left: 4px solid #28a745; }
.importer-classification-card.gl { border-left: 4px solid #17a2b8; }
.importer-classification-card.yellow { border-left: 4px solid #ffc107; }
.importer-classification-card.red { border-left: 4px solid #dc3545; }
@media (max-width: 768px) { .route-container { flex-direction: column; } .cards-sidebar { max-width: none; } .map-box { height: 400px; } .doc-alert-card { min-width: 70px; } .header-route { flex-direction: column; gap: 8px; } }
"""


def get_dg_dashboard_html(doc, get_compliance_fn=None):
	"""
	Build DG status HTML for dashboard, shown under origin/destination (Transport Job, Air Shipment, Sea Shipment).
	Returns a single HTML string. Red when non-compliance, green when complied.
	doc: document with contains_dangerous_goods and optionally dg_compliance_status.
	get_compliance_fn: optional callable(doc) -> {"status": "Compliant"|"Non-Compliant"|...} (e.g. Air Shipment check_dg_compliance).
	"""
	contains_dg = getattr(doc, "contains_dangerous_goods", False)
	if not contains_dg:
		return ""

	# Resolve status: use get_compliance_fn if provided, else doc.dg_compliance_status
	if get_compliance_fn and callable(get_compliance_fn):
		try:
			result = get_compliance_fn()
			status = (result or {}).get("status") or ""
		except Exception:
			status = getattr(doc, "dg_compliance_status", None) or ""
	else:
		status = (getattr(doc, "dg_compliance_status", None) or "").strip()

	# Normalize: Compliant = green, Non-Compliant = red, rest = pending (orange)
	status_lower = (status or "").lower()
	is_compliant = status_lower == "compliant"
	is_non_compliant = status_lower == "non-compliant"
	if is_compliant:
		alert_class = "dg-alert-compliant"
		alert_icon = "fa-check-circle"
		alert_text = "DG: Complied"
	elif is_non_compliant:
		alert_class = "dg-alert-non-compliant"
		alert_icon = "fa-exclamation-triangle"
		alert_text = "DG: Non-compliance"
	else:
		alert_class = "dg-alert-pending"
		alert_icon = "fa-clock-o"
		alert_text = "DG: " + (status or "Pending")

	return (
		f'<div class="alert {alert_class}" style="border-radius: 6px; padding: 10px 14px; margin-top: 10px;">'
		f'<i class="fa {alert_icon}"></i> <strong>{frappe.utils.escape_html(alert_text)}</strong></div>'
	)


# Leg type colors for routing map (Pre-carriage, Main, On-forwarding, Other)
LEG_TYPE_COLORS = {
	"Pre-carriage": "#ff9800",   # orange
	"Main": "#2196f3",           # blue
	"On-forwarding": "#9c27b0", # purple
	"Other": "#607d8b",          # grey
}


def _normalize_map_input(map_points=None, map_segments=None):
	"""
	Normalize map input: map_segments takes precedence. If only map_points given,
	convert to a single Main segment for backward compatibility.
	Returns (segments, all_points, has_segments).
	"""
	if map_segments and len(map_segments) > 0:
		all_pts = []
		for seg in map_segments:
			pts = seg.get("points") or []
			if len(pts) >= 2:
				all_pts.extend(pts)
		return map_segments, all_pts, True
	# Legacy: single segment from map_points
	if map_points and len(map_points) >= 2:
		return [{"type": "Main", "points": map_points}], map_points, False
	return [], map_points or [], False


def render_route_map_html(
	map_id_prefix,
	map_points=None,
	map_segments=None,
	straight_line=True,
	hide_map=False,
):
	"""
	Build the map column HTML + init script (Leaflet / Google / MapLibre) for run-sheet and Air Booking dashboards.
	Does not depend on header route labels.
	"""
	segments, all_points, use_segments = _normalize_map_input(map_points, map_segments)
	points_for_header = all_points if all_points else (map_points or [])

	points_json = json.dumps([p for p in points_for_header]) if points_for_header else "[]"
	segments_json = json.dumps(segments) if segments else "[]"
	leg_colors_json = json.dumps(LEG_TYPE_COLORS)

	mf_origin = points_for_header[0].get("label", "Origin") if points_for_header else "Origin"
	mf_dest = points_for_header[-1].get("label", "Destination") if len(points_for_header) > 1 else "Destination"
	origin_lat = points_for_header[0].get("lat", 0) if points_for_header else 0
	origin_lon = points_for_header[0].get("lon", 0) if points_for_header else 0
	dest_lat = points_for_header[-1].get("lat", 0) if len(points_for_header) > 1 else 0
	dest_lon = points_for_header[-1].get("lon", 0) if len(points_for_header) > 1 else 0

	map_renderer = None
	try:
		ls = frappe.get_single("Logistics Settings")
		map_renderer = getattr(ls, "map_renderer", None) if ls else None
	except Exception:
		pass
	if not map_renderer or not str(map_renderer).strip():
		try:
			ts = frappe.get_single("Transport Settings")
			map_renderer = getattr(ts, "map_renderer", None) if ts else None
		except Exception:
			pass
	if not map_renderer or not str(map_renderer).strip():
		map_renderer = "OpenStreetMap"

	map_renderer_js = json.dumps(map_renderer)
	waypoints_str = "|".join(f"{p.get('lat')},{p.get('lon')}" for p in points_for_header) if points_for_header else ""
	straight_line_js = "true" if straight_line else "false"

	map_section = ""
	legend_html = ""
	if use_segments and len(segments) >= 1:
		legend_items = []
		seen = set()
		for seg in segments:
			t = seg.get("type") or "Other"
			if t not in seen:
				seen.add(t)
				c = LEG_TYPE_COLORS.get(t, LEG_TYPE_COLORS["Other"])
				legend_items.append(f'<span class="map-legend-item"><i style="background:{c};width:12px;height:12px;display:inline-block;border-radius:2px;vertical-align:middle;"></i> {t}</span>')
		if legend_items:
			legend_html = f'<div class="map-legend">{chr(10).join(legend_items)}</div>'

	if not hide_map and len(points_for_header) >= 2:
		map_section = f"""
		<div class="map-main">
			<div class="map-box" style="position: relative;">
				{legend_html}
				<div id="{map_id_prefix}" class="map-view"></div>
				<div id="{map_id_prefix}-fallback" style="display: flex; position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); align-items: center; justify-content: center; flex-direction: column;">
					<div style="text-align: center; color: #6c757d;">
						<i class="fa fa-map" style="font-size: 32px; margin-bottom: 15px;"></i>
						<div style="font-size: 18px; font-weight: 500;">Route Map</div>
						<div style="font-size: 14px; margin-top: 10px;">Loading...</div>
					</div>
				</div>
			</div>
			<div class="map-links">
				<a href="https://www.google.com/maps/dir/{origin_lat},{origin_lon}/{dest_lat},{dest_lon}" target="_blank" rel="noopener"><i class="fa fa-external-link"></i> Google Maps</a>
				<a href="https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route={origin_lat},{origin_lon};{dest_lat},{dest_lon}" target="_blank" rel="noopener"><i class="fa fa-external-link"></i> OpenStreetMap</a>
				<a href="http://maps.apple.com/?daddr={dest_lat},{dest_lon}&saddr={origin_lat},{origin_lon}" target="_blank" rel="noopener"><i class="fa fa-external-link"></i> Apple Maps</a>
			</div>
		</div>
		<script>
		(function() {{
			const points = {points_json};
			const segments = {segments_json};
			const legColors = {leg_colors_json};
			const mapId = '{map_id_prefix}';
			const mapRenderer = {map_renderer_js};
			const waypointsStr = {json.dumps(waypoints_str)};
			const straightLine = {straight_line_js};
			const useSegments = {json.dumps(use_segments)};
			function hideFallback() {{ const fb = document.getElementById(mapId + '-fallback'); if (fb) fb.style.display = 'none'; }}
			function showFallback() {{ const fb = document.getElementById(mapId + '-fallback'); if (fb) fb.style.display = 'flex'; }}
			function getRouteCoords(pts, cb) {{
				if (straightLine || !pts || pts.length < 2) {{ cb(pts ? pts.map(function(p) {{ return [p.lat, p.lon]; }}) : []); return; }}
				const wpStr = pts.map(function(p) {{ return p.lat + ',' + p.lon; }}).join('|');
				if (wpStr.length < 3) {{ cb(pts.map(function(p) {{ return [p.lat, p.lon]; }})); return; }}
				frappe.call({{ method: 'logistics.document_management.api.get_route_geometry', args: {{ waypoints: wpStr }} }}).then(function(r) {{
					const coords = (r.message && r.message.success && r.message.coordinates) ? r.message.coordinates : null;
					cb(coords || pts.map(function(p) {{ return [p.lat, p.lon]; }}));
				}}).catch(function() {{ cb(pts.map(function(p) {{ return [p.lat, p.lon]; }})); }});
			}}
			function drawSegments(map, addMarker, addPolyline, fitBounds) {{
				const allBounds = [];
				const drawnMarkers = {{}};
				function addPointMarker(p, idx) {{
					const key = (p.lat || 0) + '_' + (p.lon || 0);
					if (!drawnMarkers[key]) {{ addMarker(p, idx); drawnMarkers[key] = true; }}
				}}
				if (useSegments && segments && segments.length > 0) {{
					let pending = 0;
					segments.forEach(function(seg) {{
						const pts = seg.points || [];
						const segType = seg.type || 'Main';
						const color = legColors[segType] || legColors['Other'];
						pts.forEach(function(p, i) {{ addPointMarker(p, i); }});
						if (pts.length >= 2) {{
							pending++;
							getRouteCoords(pts, function(latlngs) {{
								if (latlngs && latlngs.length >= 2) {{
									addPolyline(latlngs, color);
									latlngs.forEach(function(ll) {{ allBounds.push(ll); }});
								}}
								pending--;
								if (pending <= 0) fitBounds(allBounds);
							}});
						}}
					}});
					if (pending === 0 && allBounds.length >= 2) fitBounds(allBounds);
				}} else {{
					points.forEach(function(p, i) {{ addPointMarker(p, i); }});
					if (points.length >= 2) {{
						getRouteCoords(points, function(latlngs) {{
							addPolyline(latlngs, legColors['Main'] || '#2196f3');
							if (latlngs) allBounds.push.apply(allBounds, latlngs);
							fitBounds(allBounds);
						}});
					}}
				}}
			}}
			function initLeaflet() {{
				const el = document.getElementById(mapId);
				if (!el) {{ setTimeout(initLeaflet, 100); return; }}
				if (!window.L) {{
					const c = document.createElement('link'); c.rel='stylesheet'; c.href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'; document.head.appendChild(c);
					const s = document.createElement('script'); s.src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'; s.onload=initLeaflet; document.head.appendChild(s);
					return;
				}}
				try {{
					const map = L.map(mapId).setView([points[0].lat, points[0].lon], 10);
					L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ attribution: '© OpenStreetMap' }}).addTo(map);
					const addMarker = function(p, i) {{ L.marker([p.lat, p.lon]).addTo(map).bindPopup('<b>' + (p.label || 'Stop ' + (i+1)) + '</b>'); }};
					const addPolyline = function(latlngs, color) {{ L.polyline(latlngs, {{ color: color || '#2196f3', weight: 3 }}).addTo(map); }};
					const fitBounds = function(b) {{ if (b && b.length >= 2) map.fitBounds(L.latLngBounds(b).pad(0.1)); }};
					drawSegments(map, addMarker, addPolyline, fitBounds);
					hideFallback();
				}} catch (e) {{ console.error('Map init error:', e); showFallback(); }}
			}}
			function initGoogleMap() {{
				frappe.call({{ method: 'logistics.document_management.api.get_google_maps_api_key' }}).then(function(r) {{
					const apiKey = r.message && r.message.api_key;
					if (!apiKey || apiKey.length < 10) {{ initLeaflet(); return; }}
					if (window.google && window.google.maps) {{ doGoogleMap(apiKey); return; }}
					const s = document.createElement('script');
					s.src = 'https://maps.googleapis.com/maps/api/js?key=' + apiKey + '&libraries=geometry';
					s.async = true; s.onload = function() {{ doGoogleMap(apiKey); }};
					s.onerror = function() {{ initLeaflet(); }};
					document.head.appendChild(s);
				}}).catch(function() {{ initLeaflet(); }});
			}}
			function doGoogleMap(apiKey) {{
				const el = document.getElementById(mapId);
				if (!el) {{ setTimeout(function() {{ doGoogleMap(apiKey); }}, 100); return; }}
				try {{
					const map = new google.maps.Map(el, {{ center: {{ lat: points[0].lat, lng: points[0].lon }}, zoom: 10 }});
					const addMarker = function(p, i) {{
						const pos = {{ lat: p.lat, lng: p.lon }};
						new google.maps.Marker({{ position: pos, map: map, title: p.label || 'Stop ' + (i+1) }});
						return pos;
					}};
					const addPolyline = function(latlngs, color) {{
						const path = latlngs.map(function(c) {{ return {{ lat: c[0], lng: c[1] }}; }});
						new google.maps.Polyline({{ path: path, strokeColor: color || '#0066ff', strokeWeight: 3, geodesic: true, map: map }});
						return path;
					}};
					const fitBounds = function(b) {{
						if (b && b.length >= 2) {{ const bounds = new google.maps.LatLngBounds(); b.forEach(function(ll) {{ bounds.extend({{ lat: ll[0], lng: ll[1] }}); }}); map.fitBounds(bounds); }}
					}};
					drawSegments(map, addMarker, addPolyline, fitBounds);
					hideFallback();
				}} catch (e) {{ console.error('Google Map init error:', e); initLeaflet(); }}
			}}
			function initMapLibre() {{
				const el = document.getElementById(mapId);
				if (!el) {{ setTimeout(initMapLibre, 100); return; }}
				if (!window.maplibregl) {{
					const css = document.createElement('link'); css.rel='stylesheet'; css.href='https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css'; document.head.appendChild(css);
					const script = document.createElement('script'); script.src='https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js';
					script.onload = initMapLibre; document.head.appendChild(script);
					return;
				}}
				try {{
					const centerLat = points.reduce(function(s,p){{return s+p.lat;}},0)/points.length;
					const centerLon = points.reduce(function(s,p){{return s+p.lon;}},0)/points.length;
					const map = new maplibregl.Map({{ container: mapId, style: {{ version: 8, sources: {{ 'osm': {{ type: 'raster', tiles: ['https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png'], tileSize: 256 }} }}, layers: [{{ id: 'osm', type: 'raster', source: 'osm' }}] }}, center: [centerLon, centerLat], zoom: 8 }});
					const addMarker = function(p, i) {{ new maplibregl.Marker({{ color: 'blue' }}).setLngLat([p.lon, p.lat]).setPopup(new maplibregl.Popup().setHTML('<b>' + (p.label||'') + '</b>')).addTo(map); }};
					const addPolyline = function(latlngs, color) {{
						if (latlngs && latlngs.length >= 2) {{
							const coords = latlngs.map(function(c) {{ return [c[1], c[0]]; }});
							const id = 'route-' + Math.random().toString(36).slice(2);
							map.addSource(id, {{ type: 'geojson', data: {{ type: 'Feature', geometry: {{ type: 'LineString', coordinates: coords }} }} }});
							map.addLayer({{ id: id, type: 'line', source: id, paint: {{ 'line-color': color || '#2196f3', 'line-width': 3 }} }});
						}}
					}};
					const fitBounds = function(b) {{
						if (b && b.length >= 2) {{
							const lngs = b.map(function(ll){{return ll[1];}});
							const lats = b.map(function(ll){{return ll[0];}});
							map.fitBounds([[Math.min.apply(null,lngs),Math.min.apply(null,lats)],[Math.max.apply(null,lngs),Math.max.apply(null,lats)]], {{ padding: 50 }});
						}}
					}};
					drawSegments(map, addMarker, addPolyline, fitBounds);
					hideFallback();
				}} catch (e) {{ initLeaflet(); }}
			}}
			function init() {{
				const renderer = (mapRenderer || '').toLowerCase();
				if (renderer === 'google maps') {{ initGoogleMap(); return; }}
				if (renderer === 'mapbox' || renderer === 'maplibre') {{ initMapLibre(); return; }}
				initLeaflet();
			}}
			if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
		}})();
		</script>
		"""
	elif not hide_map and points_for_header:
		map_section = f'<div class="map-main"><div class="alert alert-info">At least two points with coordinates needed for map. Origin: {mf_origin}</div></div>'
	elif not hide_map:
		map_section = '<div class="map-main"><div class="alert alert-info">Add origin and destination (or routing legs) to view the route map.</div></div>'
	else:
		map_section = ""

	return map_section


def build_run_sheet_style_dashboard(
	header_title,
	header_subtitle,
	header_items,
	cards_html,
	map_points,
	map_id_prefix="dash-map",
	doc_alerts_html="",
	straight_line=False,
	map_segments=None,
	origin_label=None,
	destination_label=None,
	route_below_html="",
	doc_management_position="before",
	cards_full_width=False,
	origin_section_label=None,
	destination_section_label=None,
	hide_map=False,
	merge_header_with_cards=False,
	header_items_in_card=False,
	status_badge_html="",
	alerts_html="",
):
	"""
	Build dashboard HTML with Run Sheet layout: header + sidebar cards + map.

	header_items: list of (label, value) for header details
	cards_html: HTML string for milestone/leg cards
	map_points: list of {"lat": float, "lon": float, "label": str} (legacy, used when map_segments not provided)
	map_segments: list of {"type": "Main"|"Pre-carriage"|"On-forwarding"|"Other", "points": [...]} for colored legs
	straight_line: if True, draw straight lines between points (for air/sea); else use road-following route
	origin_label: optional display label for origin (shown in first section)
	destination_label: optional display label for destination (shown in first section)
	"""
	# Exclude Origin/Destination from header_items when passed separately
	_filtered_items = []
	for h in (header_items or []):
		if h[0] in ("Origin", "Destination"):
			continue
		_filtered_items.append(h)
	header_details_html = "".join(
		f'<div class="header-item"><label>{h[0]}:</label><span>{h[1]}</span></div>'
		for h in _filtered_items
	)
	if header_items_in_card and header_details_html:
		header_details = f'<div class="header-details-card">{header_details_html}</div>'
	else:
		header_details = header_details_html
	header_details_class = "header-details header-details-full-width" if header_items_in_card else "header-details"

	# Route section (ORIGIN | DESTINATION or custom labels like Exporter | Importer) and optional content below (e.g. DG status)
	route_section = ""
	if origin_label is not None or destination_label is not None:
		o = frappe.utils.escape_html(origin_label or "—")
		d = frappe.utils.escape_html(destination_label or "—")
		route_below = (route_below_html or "").strip()
		orig_lbl = origin_section_label or "ORIGIN"
		dest_lbl = destination_section_label or "DESTINATION"
		route_class = "header-route no-border" if header_items_in_card else "header-route"
		route_section = f"""
		<div class="{route_class}">
			<div class="route-column">
				<label class="section-label">{orig_lbl}</label>
				<div class="route-location">{o}</div>
			</div>
			<div class="route-column">
				<label class="section-label">{dest_lbl}</label>
				<div class="route-location">{d}</div>
			</div>
		</div>
		{route_below}"""

	map_section = render_route_map_html(
		map_id_prefix,
		map_points=map_points,
		map_segments=map_segments,
		straight_line=straight_line,
		hide_map=hide_map,
	)

	alerts_section = (alerts_html or "").strip()
	if alerts_section:
		alerts_section = f'<div class="dash-alerts-section">{alerts_section}</div>'

	# Document Management section removed from dashboard (cards no longer shown here)
	doc_management_section = ""
	merged_cards_content = ""
	if merge_header_with_cards:
		merged_cards_content = f"""
			<div class="merged-cards-content" style="margin-top: 20px; padding-top: 16px;">
				{cards_html or '<div class="text-muted">No milestones or legs</div>'}
			</div>
		"""
	if cards_full_width:
		cards_block = f"""
			<div class="cards-full-width" style="width: 100%; margin-bottom: 20px;">
				{cards_html or '<div class="text-muted">No milestones or legs</div>'}
			</div>
		"""
		if merge_header_with_cards:
			route_container = ""
		else:
			route_container = f"""
		<div class="route-container" style="flex-direction: column;">
			{cards_block}
			{map_section}
		</div>
	"""
	else:
		route_container = f"""
		<div class="route-container">
			<div class="cards-sidebar">
				<details class="run-sheet-cards-panel" open>
					<summary class="run-sheet-cards-panel-summary">
						<span class="run-sheet-cards-panel-title">Milestones &amp; legs</span>
					</summary>
					<div class="card-list">{cards_html or '<div class="text-muted">No milestones or legs</div>'}</div>
				</details>
			</div>
			{map_section}
		</div>
	"""
	# Alerts at top (no label); doc_management_position "before" = above header, "after" = below body
	top_alerts = (alerts_section or "").strip()
	if merge_header_with_cards:
		body_content = ""
	else:
		body_content = route_container
	status_badge = (status_badge_html or "").strip()
	doc_above_header = doc_management_section if (doc_management_section and doc_management_position == "before") else ""
	doc_below_body = doc_management_section if (doc_management_section and doc_management_position != "before") else ""
	html = f"""
	<div class="run-sheet-dash">
		<style>{RUN_SHEET_LAYOUT_CSS}</style>
		{top_alerts}
		{doc_above_header}
		<div class="run-sheet-header">
			<div class="header-main">
				<div class="header-primary">
					<label class="section-label">{header_subtitle or ''}</label>
					<div class="primary-title" style="display: flex; align-items: center; flex-wrap: wrap; gap: 8px;">{header_title or 'Dashboard'}{status_badge}</div>
				</div>
				{route_section}
				<div class="{header_details_class}">{header_details}</div>
			</div>
			{merged_cards_content}
		</div>
		{body_content}
		{doc_below_body}
	</div>
	"""
	return html
