# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Shared Run Sheet-style dashboard layout for Air Shipment, Sea Shipment,
Transport Job, Declaration, Special Project. Layout: header + sidebar (milestones/legs) + map.
"""

from __future__ import unicode_literals

import json

import frappe
from frappe import _
from frappe.utils import escape_html


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
.af-live-status { position: absolute; top: 10px; right: 10px; z-index: 1100; background: rgba(255,255,255,0.96); padding: 8px 10px; border-radius: 6px; font-size: 11px; min-width: 200px; max-width: 280px; display: flex; gap: 8px; align-items: flex-start; box-shadow: 0 2px 6px rgba(0,0,0,0.18); border-left: 4px solid #9ca3af; }
.af-live-status__dot { width: 10px; height: 10px; border-radius: 50%; background: #9ca3af; margin-top: 4px; flex: 0 0 auto; box-shadow: 0 0 0 0 rgba(156,163,175,0.55); }
.af-live-status__body { flex: 1 1 auto; min-width: 0; }
.af-live-status__head { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
.af-live-status__flight { font-weight: 700; font-size: 12px; color: #111827; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.af-live-status__state { font-size: 10px; font-weight: 700; letter-spacing: 0.04em; padding: 1px 6px; border-radius: 10px; background: #e5e7eb; color: #374151; white-space: nowrap; }
.af-live-status__route { font-size: 11px; color: #4b5563; margin-top: 2px; }
.af-live-status__meta { font-size: 10.5px; color: #6b7280; margin-top: 4px; line-height: 1.45; }
.af-live-status__meta strong { color: #111827; font-weight: 600; }
.af-live-status__metrics { display: flex; flex-wrap: wrap; gap: 4px 10px; margin-top: 3px; font-size: 10.5px; color: #374151; }
.af-live-status__metric { white-space: nowrap; }
.af-live-status__metric b { font-weight: 600; color: #111827; }
.af-live-status--live { border-left-color: #1d4ed8; }
.af-live-status--live .af-live-status__dot { background: #1d4ed8; animation: af-live-pulse 1.6s ease-out infinite; }
.af-live-status--live .af-live-status__state { background: #dbeafe; color: #1d4ed8; }
.af-live-status--ground { border-left-color: #6b7280; }
.af-live-status--ground .af-live-status__dot { background: #6b7280; }
.af-live-status--ground .af-live-status__state { background: #e5e7eb; color: #374151; }
.af-live-status--stale { border-left-color: #f59e0b; }
.af-live-status--stale .af-live-status__dot { background: #f59e0b; }
.af-live-status--stale .af-live-status__state { background: #fef3c7; color: #b45309; }
.af-live-status--nofix { border-left-color: #9ca3af; }
.af-live-status--nofix .af-live-status__dot { background: #9ca3af; }
.af-live-status--nofix .af-live-status__state { background: #f3f4f6; color: #4b5563; }
.af-live-status--error { border-left-color: #dc2626; }
.af-live-status--error .af-live-status__dot { background: #dc2626; }
.af-live-status--error .af-live-status__state { background: #fee2e2; color: #b91c1c; }
.af-live-status--loading { border-left-color: #9ca3af; opacity: 0.85; }
@keyframes af-live-pulse { 0% { box-shadow: 0 0 0 0 rgba(29,78,216,0.55); } 70% { box-shadow: 0 0 0 8px rgba(29,78,216,0); } 100% { box-shadow: 0 0 0 0 rgba(29,78,216,0); } }
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
/* Capacity metrics embedded in run-sheet-style header (payload / capacity / used %) */
.rs-cap-metrics-inline {
	display: flex; flex-direction: row; flex-wrap: wrap; align-items: flex-end;
	gap: 0; margin-left: auto; min-width: 200px;
}
.rs-cap-metric { display: flex; flex-direction: column; align-items: flex-start; padding: 0 16px 0 0; }
.rs-cap-metric + .rs-cap-metric { padding-left: 16px; border-left: 1px solid #e5e7eb; }
.rs-cap-metric-label { font-size: 10px; color: #9ca3af; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; margin-bottom: 2px; }
.rs-cap-metric-value { font-size: 15px; line-height: 1.3; white-space: nowrap; }
.rs-cap-metric-value .rs-cap-used { font-weight: 700; color: #111827; }
.rs-cap-metric-value .rs-cap-muted { color: #9ca3af; font-weight: 400; }
.rs-cap-used-row {
	display: flex; flex-direction: row; align-items: center; gap: 10px;
	width: 100%; margin-top: 10px; flex-basis: 100%;
}
.rs-cap-used-label { font-size: 11px; color: #6b7280; white-space: nowrap; flex: 0 0 auto; }
.rs-cap-used-track-wrap { display: flex; align-items: center; gap: 10px; flex: 1 1 auto; min-width: 0; }
.rs-cap-used-track { flex: 1 1 auto; height: 8px; background: #e5e7eb; border-radius: 999px; overflow: hidden; min-width: 80px; }
.rs-cap-used-fill { height: 100%; background: #2563eb; border-radius: 999px; }
.rs-cap-used-pct { font-size: 12px; font-weight: 600; color: #374151; white-space: nowrap; flex: 0 0 auto; }
/* Full run-sheet capacity header card (left meta + right metrics) */
.rs-cap-header {
	background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
	padding: 16px 20px 12px; margin-bottom: 16px; box-sizing: border-box; width: 100%;
}
.rs-cap-header__main {
	display: grid; grid-template-columns: minmax(120px, 200px) minmax(180px, 1fr) minmax(240px, 36%);
	align-items: center; column-gap: 12px; width: 100%; box-sizing: border-box;
}
.rs-cap-header__left { min-width: 0; align-self: flex-start; }
.rs-cap-header__left .section-label { font-size: 10px; color: #9ca3af; text-transform: uppercase; font-weight: 600; letter-spacing: 0.5px; margin-bottom: 2px; display: block; }
.rs-cap-primary-title { font-size: 20px; font-weight: 700; color: #007bff; line-height: 1.2; margin-bottom: 8px; }
.rs-cap-meta-list { display: flex; flex-direction: column; gap: 4px; }
.rs-cap-meta-row { font-size: 11px; color: #6b7280; display: flex; align-items: center; gap: 6px; }
.rs-cap-meta-row i { width: 14px; text-align: center; color: #9ca3af; }
.rs-cap-header__avatars { position: relative; width: 124px; height: 114px; margin-left: auto; }
.rs-cap-avatar { border-radius: 50%; display: flex; align-items: center; justify-content: center; overflow: hidden; color: #fff; }
.rs-cap-avatar--driver { width: 104px; height: 104px; background: #1e3a8a; font-size: 36px; }
.rs-cap-avatar--vehicle {
	position: absolute; right: -5px; bottom: -3px; width: 50px; height: 50px;
	background: #6b7280; border: 2px solid #fff; font-size: 18px;
}
.rs-cap-avatar img { width: 100%; height: 100%; object-fit: cover; }
.rs-cap-header__right { min-width: 0; display: flex; flex-direction: column; align-self: flex-start; padding-left: 12px; box-sizing: border-box; }
.rs-cap-header__right .rs-cap-metrics-inline { margin-left: 0; width: 100%; }
.rs-cap-header__right .rs-cap-used-row { margin-top: 14px; }
.rs-cap-vehicle-row { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.rs-cap-vehicle-name { font-size: 13px; font-weight: 700; color: #111827; text-transform: uppercase; letter-spacing: 0.35px; }
.rs-cap-status-badge {
	display: inline-flex; align-items: center; gap: 6px; padding: 5px 14px; border-radius: 999px;
	background: #f3f4f6; border: 1px solid #e5e7eb; font-size: 12px; color: #111827; font-weight: 500;
}
.rs-cap-status-dot { width: 8px; height: 8px; border-radius: 50%; flex: 0 0 auto; }
.rs-cap-header__footer {
	display: flex; flex-wrap: nowrap; align-items: center; gap: 24px; width: 100%;
	padding-top: 10px; margin-top: 8px; border-top: 1px solid #f3f4f6; font-size: 11px; color: #6b7280;
}
.rs-cap-header__footer .rs-cap-footer-value { color: #374151; font-weight: 600; }
.rs-cap-header__footer .rs-cap-footer-legs { margin-left: auto; }
@media (max-width: 900px) {
	.rs-cap-header__main { grid-template-columns: 1fr; row-gap: 16px; }
	.rs-cap-header__avatars { margin: 0 auto; }
	.rs-cap-header__right { padding-left: 0; }
}
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


def get_dashboard_map_renderer():
	"""Logistics Settings ``map_renderer``, else Transport Settings, else OpenStreetMap (same as Transport Job dashboard)."""
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
	return map_renderer


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
	vessel_tracking_map=None,
	aircraft_tracking_map=None,
):
	"""
	Build the map column HTML + init script (Leaflet / Google / MapLibre) for run-sheet and Air Booking dashboards.
	Does not depend on header route labels.

	vessel_tracking_map: optional dict with enabled (bool), sea_shipment (name), hint — enables async AIS vessel marker.
	aircraft_tracking_map: optional dict with enabled (bool), air_shipment (name), hint — enables async OpenSky/ADS-B aircraft marker rotated by heading.
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

	map_renderer = get_dashboard_map_renderer()

	map_renderer_js = json.dumps(map_renderer)
	waypoints_str = "|".join(f"{p.get('lat')},{p.get('lon')}" for p in points_for_header) if points_for_header else ""
	straight_line_js = "true" if straight_line else "false"
	vessel_tracking_json = json.dumps(vessel_tracking_map or {})
	aircraft_tracking_json = json.dumps(aircraft_tracking_map or {})

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

	aircraft_badge_html = ""
	if aircraft_tracking_map and aircraft_tracking_map.get("enabled"):
		aircraft_badge_html = (
			f'<div id="{map_id_prefix}-aircraft-status" class="af-live-status af-live-status--loading" '
			f'role="status" aria-live="polite">'
			f'<div class="af-live-status__dot"></div>'
			f'<div class="af-live-status__body">'
			f'<div class="af-live-status__head">'
			f'<span class="af-live-status__flight">Live Flight</span>'
			f'<span class="af-live-status__state">LOADING…</span>'
			f'</div>'
			f'<div class="af-live-status__meta">Resolving aircraft position…</div>'
			f'</div></div>'
		)

	# Vessel status badge — visible whenever vessel_tracking_map is provided so
	# the user can tell at a glance whether AIS is wired up. Reuses the air
	# `.af-live-status` styles (loaded site-wide) for consistency.
	vessel_badge_html = ""
	if vessel_tracking_map and (vessel_tracking_map.get("enabled") or vessel_tracking_map.get("hint")):
		if vessel_tracking_map.get("enabled"):
			initial_cls = "af-live-status--loading"
			initial_state = "LOADING…"
			initial_meta = "Fetching latest AIS position…"
		else:
			initial_cls = "af-live-status--nofix"
			initial_state = "NOT READY"
			# escape_html for the hint so a translation can't inject markup
			hint_text = frappe.utils.escape_html(vessel_tracking_map.get("hint") or "")
			initial_meta = hint_text or "Vessel tracking is not configured."
		vessel_badge_html = (
			f'<div id="{map_id_prefix}-vessel-status" class="af-live-status {initial_cls}" '
			f'role="status" aria-live="polite">'
			f'<div class="af-live-status__dot"></div>'
			f'<div class="af-live-status__body">'
			f'<div class="af-live-status__head">'
			f'<span class="af-live-status__flight">Live Vessel</span>'
			f'<span class="af-live-status__state">{initial_state}</span>'
			f'</div>'
			f'<div class="af-live-status__meta">{initial_meta}</div>'
			f'</div></div>'
		)

	if not hide_map and len(points_for_header) >= 2:
		map_section = f"""
		<div class="map-main">
			<div class="map-box" style="position: relative;">
				{legend_html}
				{aircraft_badge_html}
				{vessel_badge_html}
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
			const vesselTrackingMap = {vessel_tracking_json};
			const aircraftTrackingMap = {aircraft_tracking_json};
			function runAircraftTrackingOverlay(engine, mapInstance) {{
				if (!aircraftTrackingMap || !aircraftTrackingMap.enabled || !aircraftTrackingMap.air_shipment) return;
				function buildPopup(m) {{
					var lines = [];
					lines.push('<b>' + frappe.utils.escape_html(String(m.flight_number || m.label || 'Aircraft')) + '</b>');
					if (m.departure_iata && m.arrival_iata) {{
						lines.push('<div style="color:#444;">' + frappe.utils.escape_html(m.departure_iata + ' → ' + m.arrival_iata) + '</div>');
					}}
					var badge = m.source === 'live'
						? '<span style="color:#1d4ed8;font-weight:600;">LIVE</span>'
						: (m.source === 'stale' ? '<span style="color:#b45309;font-weight:600;">STALE' + (m.stale_minutes != null ? ' · ' + m.stale_minutes + 'm' : '') + '</span>'
						: '<span style="color:#6b7280;font-weight:600;">NO FIX</span>');
					lines.push('<div>' + badge + (m.flight_status ? ' · ' + frappe.utils.escape_html(m.flight_status) : '') + '</div>');
					if (m.altitude_m != null) lines.push('Altitude: ' + Math.round(m.altitude_m) + ' m');
					if (m.speed_kmh != null) lines.push('Speed: ' + Math.round(m.speed_kmh) + ' km/h');
					if (m.heading != null) lines.push('Heading: ' + Math.round(m.heading) + '°');
					if (m.recorded_at) lines.push('<small>Updated: ' + frappe.utils.escape_html(String(m.recorded_at)) + '</small>');
					if (m.flight_schedule) {{
						lines.push('<a href="' + frappe.utils.get_form_link('Flight Schedule', m.flight_schedule) + '">Open Flight Schedule</a>');
					}}
					return lines.join('<br/>');
				}}
				function makeLeafletIcon(headingDeg, color) {{
					var h = (typeof headingDeg === 'number' && isFinite(headingDeg)) ? headingDeg : 0;
					var html = '<div style="transform:translate(-50%,-50%) rotate(' + h + 'deg);color:' + color + ';">' +
						'<svg viewBox="0 0 24 24" width="26" height="26" fill="currentColor" stroke="rgba(0,0,0,0.55)" stroke-width="0.6">' +
						'<path d="M12 2 L13 9 L22 13 L22 15 L13 13 L13 18 L16 20 L16 21.5 L12 20.5 L8 21.5 L8 20 L11 18 L11 13 L2 15 L2 13 L11 9 Z"/></svg></div>';
					return L.divIcon({{ html: html, className: 'af-form-live-plane', iconSize: [26, 26], iconAnchor: [13, 13] }});
				}}
				function planeColor(m) {{
					if (m.source === 'live') return m.on_ground ? '#6b7280' : '#1d4ed8';
					if (m.source === 'stale') return '#f59e0b';
					return '#9ca3af';
				}}
				function placeMarker(m) {{
					var lat = parseFloat(m.lat), lon = parseFloat(m.lon);
					if (isNaN(lat) || isNaN(lon)) return;
					var color = planeColor(m);
					var pop = buildPopup(m);
					if (engine === 'leaflet') {{
						L.marker([lat, lon], {{ icon: makeLeafletIcon(m.heading, color), riseOnHover: true, zIndexOffset: 1000 }})
							.addTo(mapInstance).bindPopup(pop);
						try {{
							var b = mapInstance.getBounds();
							if (b && b.isValid()) {{ mapInstance.fitBounds(b.extend([lat, lon]).pad(0.12)); }}
						}} catch (e1) {{}}
					}} else if (engine === 'google') {{
						var pos = {{ lat: lat, lng: lon }};
						var heading = (typeof m.heading === 'number' && isFinite(m.heading)) ? m.heading : 0;
						new google.maps.Marker({{
							position: pos,
							map: mapInstance,
							title: m.flight_number || m.label || 'Aircraft',
							icon: {{
								path: 'M0 -10 L1 -3 L10 1 L10 3 L1 1 L1 6 L4 8 L4 9 L0 8 L-4 9 L-4 8 L-1 6 L-1 1 L-10 3 L-10 1 L-1 -3 Z',
								scale: 1.4,
								rotation: heading,
								fillColor: color,
								fillOpacity: 1,
								strokeColor: 'rgba(0,0,0,0.55)',
								strokeWeight: 0.6,
							}},
							zIndex: 1000,
						}});
						try {{
							var bounds = mapInstance.getBounds();
							if (bounds) {{ bounds.extend(pos); mapInstance.fitBounds(bounds); }}
						}} catch (e2) {{}}
					}} else if (engine === 'maplibre') {{
						var el = document.createElement('div');
						el.style.cssText = 'transform: rotate(' + ((typeof m.heading === 'number' && isFinite(m.heading)) ? m.heading : 0) + 'deg);color:' + color + ';';
						el.innerHTML = '<svg viewBox="0 0 24 24" width="26" height="26" fill="currentColor" stroke="rgba(0,0,0,0.55)" stroke-width="0.6"><path d="M12 2 L13 9 L22 13 L22 15 L13 13 L13 18 L16 20 L16 21.5 L12 20.5 L8 21.5 L8 20 L11 18 L11 13 L2 15 L2 13 L11 9 Z"/></svg>';
						new maplibregl.Marker({{ element: el }}).setLngLat([lon, lat]).setPopup(new maplibregl.Popup().setHTML(pop)).addTo(mapInstance);
						try {{
							var bb = mapInstance.getBounds();
							if (bb) {{ bb.extend([lon, lat]); mapInstance.fitBounds(bb, {{ padding: 50 }}); }}
						}} catch (e3) {{}}
					}}
				}}
				var leafletMarkerRef = null;
				function clearLeafletMarker() {{
					if (engine !== 'leaflet' || !leafletMarkerRef) return;
					try {{ mapInstance.removeLayer(leafletMarkerRef); }} catch (eRem) {{}}
					leafletMarkerRef = null;
				}}
				function placeMarkerTracked(m) {{
					if (engine === 'leaflet') {{
						clearLeafletMarker();
						var lat = parseFloat(m.lat), lon = parseFloat(m.lon);
						if (isNaN(lat) || isNaN(lon)) return;
						var color = planeColor(m);
						var pop = buildPopup(m);
						leafletMarkerRef = L.marker([lat, lon], {{ icon: makeLeafletIcon(m.heading, color), riseOnHover: true, zIndexOffset: 1000 }})
							.addTo(mapInstance).bindPopup(pop);
					}} else {{
						placeMarker(m);
					}}
				}}
				function statusVariant(m) {{
					if (!m) return {{ cls: 'af-live-status--error', label: 'ERROR' }};
					if (!m.success) {{
						if (m.provider_status === 'unreachable') return {{ cls: 'af-live-status--error', label: 'UNREACHABLE' }};
						if (m.provider_status === 'no_match') return {{ cls: 'af-live-status--nofix', label: 'NO ADS-B' }};
						if (m.provider_status === 'no_callsign') return {{ cls: 'af-live-status--nofix', label: 'NO CALLSIGN' }};
						if (m.provider_status === 'disabled') return {{ cls: 'af-live-status--nofix', label: 'DISABLED' }};
						if (m.provider_status === 'queued') return {{ cls: 'af-live-status--loading', label: 'FETCHING…' }};
						if (m.provider_status === 'error') return {{ cls: 'af-live-status--error', label: 'ERROR' }};
						return {{ cls: 'af-live-status--nofix', label: 'NO FIX' }};
					}}
					if (m.source === 'live') {{
						return m.on_ground
							? {{ cls: 'af-live-status--ground', label: 'ON GROUND' }}
							: {{ cls: 'af-live-status--live', label: 'LIVE' }};
					}}
					if (m.source === 'stale') {{
						return {{ cls: 'af-live-status--stale', label: 'STALE' + (m.stale_minutes != null ? ' · ' + m.stale_minutes + 'm' : '') }};
					}}
					return {{ cls: 'af-live-status--nofix', label: 'NO FIX' }};
				}}
				function fmtTimeAgo(iso) {{
					if (!iso) return '';
					var t = Date.parse(iso);
					if (isNaN(t)) return frappe.utils.escape_html(String(iso));
					var diffS = Math.max(0, Math.floor((Date.now() - t) / 1000));
					if (diffS < 60) return diffS + 's ago';
					var diffM = Math.floor(diffS / 60);
					if (diffM < 60) return diffM + 'm ago';
					var diffH = Math.floor(diffM / 60);
					if (diffH < 24) return diffH + 'h ' + (diffM % 60) + 'm ago';
					var diffD = Math.floor(diffH / 24);
					return diffD + 'd ago';
				}}
				function updateBadge(m) {{
					var badge = document.getElementById(mapId + '-aircraft-status');
					if (!badge) return;
					var variant = statusVariant(m);
					badge.className = 'af-live-status ' + variant.cls;

					var flightName = (m && (m.flight_number || m.label)) || 'Live Flight';
					var route = (m && m.departure_iata && m.arrival_iata)
						? (m.departure_iata + ' → ' + m.arrival_iata) : '';
					var metricsBits = [];
					if (m && m.altitude_m != null) metricsBits.push('<span class="af-live-status__metric"><b>Alt</b> ' + Math.round(m.altitude_m / 100) * 100 + ' m</span>');
					if (m && m.speed_kmh != null) metricsBits.push('<span class="af-live-status__metric"><b>Spd</b> ' + Math.round(m.speed_kmh) + ' km/h</span>');
					if (m && m.heading != null) metricsBits.push('<span class="af-live-status__metric"><b>Hdg</b> ' + Math.round(m.heading) + '°</span>');
					var statusLine = (m && m.flight_status) ? m.flight_status : '';
					var providerLine = '';
					if (m && m.provider) providerLine = m.provider;
					var updatedLine = '';
					if (m && m.recorded_at) updatedLine = '<strong>Updated</strong> ' + fmtTimeAgo(m.recorded_at);
					else if (m && !m.success && m.provider_error) updatedLine = frappe.utils.escape_html(String(m.provider_error));
					else if (m && !m.success && m.message) updatedLine = frappe.utils.escape_html(String(m.message));

					var fsLink = '';
					if (m && m.flight_schedule) {{
						fsLink = ' · <a href="' + frappe.utils.get_form_link('Flight Schedule', m.flight_schedule) + '" style="color:#1d4ed8;">FS</a>';
					}}

					badge.innerHTML =
						'<div class="af-live-status__dot"></div>' +
						'<div class="af-live-status__body">' +
							'<div class="af-live-status__head">' +
								'<span class="af-live-status__flight">' + frappe.utils.escape_html(String(flightName)) + '</span>' +
								'<span class="af-live-status__state">' + frappe.utils.escape_html(variant.label) + '</span>' +
							'</div>' +
							(route ? '<div class="af-live-status__route">' + frappe.utils.escape_html(route) + (statusLine ? ' · ' + frappe.utils.escape_html(statusLine) : '') + '</div>' : (statusLine ? '<div class="af-live-status__route">' + frappe.utils.escape_html(statusLine) + '</div>' : '')) +
							(metricsBits.length ? '<div class="af-live-status__metrics">' + metricsBits.join('') + '</div>' : '') +
							'<div class="af-live-status__meta">' + (updatedLine || (providerLine ? ('<strong>' + frappe.utils.escape_html(providerLine) + '</strong>') : '')) + fsLink + '</div>' +
						'</div>';
				}}
				function fetchAndRender() {{
					frappe.call({{
						method: 'logistics.air_freight.api.live_flight_tracking.get_aircraft_position_for_map',
						args: {{ air_shipment: aircraftTrackingMap.air_shipment }}
					}}).then(function(r) {{
						var m = (r && r.message) || {{ success: false }};
						updateBadge(m);
						if (m.success && m.lat != null && m.lon != null) placeMarkerTracked(m);
					}}).catch(function() {{
						updateBadge({{ success: false, provider_status: 'error', message: 'Request failed' }});
					}});
				}}
				setTimeout(fetchAndRender, 1500);
				try {{
					var refreshTimer = setInterval(function() {{
						var badge = document.getElementById(mapId + '-aircraft-status');
						if (!badge || !document.body.contains(badge)) {{ clearInterval(refreshTimer); return; }}
						if (document.hidden) return;
						fetchAndRender();
					}}, 60000);
				}} catch (eTimer) {{}}
			}}
			function runVesselTrackingOverlay(engine, mapInstance) {{
				if (!vesselTrackingMap || !vesselTrackingMap.sea_shipment || !vesselTrackingMap.enabled) {{
					// If the server gave us a hint (e.g. provider not configured, no
					// vessel master on the leg), the static badge from the server
					// already shows it — nothing more for JS to do.
					return;
				}}
				function vesselStatusVariant(m) {{
					if (!m) return {{ cls: 'af-live-status--error', label: 'ERROR' }};
					if (!m.success) {{
						var msg = String((m.message || '')).toLowerCase();
						if (msg.indexOf('not configured') !== -1 || msg.indexOf('no vessel') !== -1) return {{ cls: 'af-live-status--nofix', label: 'NOT READY' }};
						if (msg.indexOf('no position') !== -1) return {{ cls: 'af-live-status--nofix', label: 'NO FIX' }};
						return {{ cls: 'af-live-status--error', label: 'ERROR' }};
					}}
					// Server already classified this fix as stale (cached fallback).
					if (m.stale === true || m.source === 'cached') {{
						if (m.recorded_at) {{
							var ts = Date.parse(String(m.recorded_at));
							if (!isNaN(ts)) {{
								var ageMinS = (Date.now() - ts) / 60000;
								if (ageMinS > 1440) return {{ cls: 'af-live-status--stale', label: 'STALE · ' + Math.round(ageMinS / 1440) + 'd' }};
								if (ageMinS > 60) return {{ cls: 'af-live-status--stale', label: 'STALE · ' + Math.round(ageMinS / 60) + 'h' }};
								return {{ cls: 'af-live-status--stale', label: 'STALE · ' + Math.round(ageMinS) + 'm' }};
							}}
						}}
						return {{ cls: 'af-live-status--stale', label: 'STALE' }};
					}}
					if (m.source === 'cache') return {{ cls: 'af-live-status--live', label: 'LIVE (CACHE)' }};
					if (m.recorded_at) {{
						var t = Date.parse(String(m.recorded_at));
						if (!isNaN(t)) {{
							var ageMin = (Date.now() - t) / 60000;
							if (ageMin > 360) return {{ cls: 'af-live-status--stale', label: 'STALE · ' + Math.round(ageMin / 60) + 'h' }};
							if (ageMin > 60) return {{ cls: 'af-live-status--stale', label: 'STALE · ' + Math.round(ageMin) + 'm' }};
						}}
					}}
					return {{ cls: 'af-live-status--live', label: 'LIVE' }};
				}}
				function fmtVesselTimeAgo(iso) {{
					if (!iso) return '';
					var t = Date.parse(iso);
					if (isNaN(t)) return frappe.utils.escape_html(String(iso));
					var diffS = Math.max(0, Math.floor((Date.now() - t) / 1000));
					if (diffS < 60) return diffS + 's ago';
					var diffM = Math.floor(diffS / 60);
					if (diffM < 60) return diffM + 'm ago';
					var diffH = Math.floor(diffM / 60);
					if (diffH < 24) return diffH + 'h ' + (diffM % 60) + 'm ago';
					return Math.floor(diffH / 24) + 'd ago';
				}}
				function updateVesselBadge(m) {{
					var badge = document.getElementById(mapId + '-vessel-status');
					if (!badge) return;
					var variant = vesselStatusVariant(m);
					badge.className = 'af-live-status ' + variant.cls;
					var label = (m && (m.label || m.vessel)) || 'Live Vessel';
					var metricsBits = [];
					if (m && m.sog != null && m.sog !== '') metricsBits.push('<span class="af-live-status__metric"><b>SOG</b> ' + frappe.utils.escape_html(String(m.sog)) + ' kn</span>');
					if (m && m.cog != null && m.cog !== '') metricsBits.push('<span class="af-live-status__metric"><b>COG</b> ' + Math.round(Number(m.cog)) + '°</span>');
					if (m && m.heading != null && m.heading !== '') metricsBits.push('<span class="af-live-status__metric"><b>Hdg</b> ' + Math.round(Number(m.heading)) + '°</span>');
					var providerLine = (m && m.provider) ? ('<strong>' + frappe.utils.escape_html(String(m.provider)) + '</strong>') : '';
					var updatedLine = '';
					if (m && m.recorded_at) updatedLine = '<strong>Updated</strong> ' + fmtVesselTimeAgo(m.recorded_at);
					else if (m && !m.success && m.message) updatedLine = frappe.utils.escape_html(String(m.message));
					var vsLink = '';
					if (m && m.vessel_schedule) {{
						vsLink = ' · <a href="' + frappe.utils.get_form_link('Vessel Schedule', m.vessel_schedule) + '" style="color:#1d4ed8;">VS</a>';
					}}
					var meta = updatedLine || providerLine;
					if (providerLine && updatedLine) meta = updatedLine + ' · ' + providerLine;
					// On a "no fix" state, also surface which providers were tried so
					// users can tell at a glance that the wiring is OK and the vessel
					// just isn't currently broadcasting.
					if (m && !m.success && Array.isArray(m.providers_tried) && m.providers_tried.length) {{
						meta = meta + (meta ? ' · ' : '') + '<small>Tried: ' + frappe.utils.escape_html(m.providers_tried.join(', ')) + '</small>';
					}}
					// On a stale fallback, append a hint so users know it's the cached fix.
					if (m && m.success && (m.stale === true || m.source === 'cached') && m.message) {{
						meta = meta + (meta ? '<br/>' : '') + '<small>' + frappe.utils.escape_html(String(m.message)) + '</small>';
					}}
					badge.innerHTML =
						'<div class="af-live-status__dot"></div>' +
						'<div class="af-live-status__body">' +
							'<div class="af-live-status__head">' +
								'<span class="af-live-status__flight">' + frappe.utils.escape_html(String(label)) + '</span>' +
								'<span class="af-live-status__state">' + frappe.utils.escape_html(variant.label) + '</span>' +
							'</div>' +
							(metricsBits.length ? '<div class="af-live-status__metrics">' + metricsBits.join('') + '</div>' : '') +
							'<div class="af-live-status__meta">' + meta + vsLink + '</div>' +
						'</div>';
				}}
				var vesselMarkerRef = null;
				function clearVesselMarker() {{
					if (!vesselMarkerRef) return;
					try {{
						if (engine === 'leaflet') mapInstance.removeLayer(vesselMarkerRef);
						else if (engine === 'google') vesselMarkerRef.setMap(null);
						else if (engine === 'maplibre') vesselMarkerRef.remove();
					}} catch (eRm) {{}}
					vesselMarkerRef = null;
				}}
				function placeVesselMarker(m) {{
					var lat = parseFloat(m.lat), lon = parseFloat(m.lon);
					if (isNaN(lat) || isNaN(lon)) return;
					clearVesselMarker();
					var label = (m.label || m.vessel || 'Vessel');
					var pop = '<b>' + frappe.utils.escape_html(String(label)) + '</b>';
					if (m.recorded_at) pop += '<br/><small>' + frappe.utils.escape_html(String(m.recorded_at)) + '</small>';
					if (m.sog != null && m.sog !== '') pop += '<br/>SOG: ' + frappe.utils.escape_html(String(m.sog)) + ' kn';
					if (m.cog != null && m.cog !== '') pop += '<br/>COG: ' + Math.round(Number(m.cog)) + '°';
					if (m.provider) pop += '<br/><small>via ' + frappe.utils.escape_html(String(m.provider)) + '</small>';
					if (engine === 'leaflet') {{
						vesselMarkerRef = L.marker([lat, lon]).addTo(mapInstance).bindPopup(pop);
						try {{
							var b = mapInstance.getBounds();
							if (b && b.isValid()) {{ mapInstance.fitBounds(b.extend([lat, lon]).pad(0.12)); }}
						}} catch (e1) {{}}
					}} else if (engine === 'google') {{
						var pos = {{ lat: lat, lng: lon }};
						vesselMarkerRef = new google.maps.Marker({{ position: pos, map: mapInstance, title: label }});
						try {{
							var bounds = mapInstance.getBounds();
							if (bounds) {{ bounds.extend(pos); mapInstance.fitBounds(bounds); }}
						}} catch (e2) {{}}
					}} else if (engine === 'maplibre') {{
						vesselMarkerRef = new maplibregl.Marker({{ color: '#c0392b' }})
							.setLngLat([lon, lat])
							.setPopup(new maplibregl.Popup().setHTML(pop))
							.addTo(mapInstance);
						try {{
							var bb = mapInstance.getBounds();
							if (bb) {{ bb.extend([lon, lat]); mapInstance.fitBounds(bb, {{ padding: 50 }}); }}
						}} catch (e3) {{}}
					}}
				}}
				function fetchVesselAndRender() {{
					frappe.call({{
						method: 'goconnect.api.sea.get_vessel_position_for_map',
						args: {{ sea_shipment: vesselTrackingMap.sea_shipment }}
					}}).then(function(r) {{
						var m = (r && r.message) || {{ success: false, message: 'Empty response' }};
						updateVesselBadge(m);
						if (m.success && m.lat != null && m.lon != null) placeVesselMarker(m);
					}}).catch(function() {{
						updateVesselBadge({{ success: false, message: 'Request failed' }});
					}});
				}}
				setTimeout(fetchVesselAndRender, 1500);
				try {{
					var vesselRefreshTimer = setInterval(function() {{
						var badge = document.getElementById(mapId + '-vessel-status');
						if (!badge || !document.body.contains(badge)) {{ clearInterval(vesselRefreshTimer); return; }}
						if (document.hidden) return;
						fetchVesselAndRender();
					}}, 60000);
				}} catch (eTimer) {{}}
			}}
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
					runVesselTrackingOverlay('leaflet', map);
					runAircraftTrackingOverlay('leaflet', map);
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
					runVesselTrackingOverlay('google', map);
					runAircraftTrackingOverlay('google', map);
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
					runVesselTrackingOverlay('maplibre', map);
					runAircraftTrackingOverlay('maplibre', map);
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


def render_special_project_interactive_route_tab_html(
	map_id_prefix,
	map_payloads,
	cards_sidebar_html,
	pin_viewport_offset=(0, 0),
	fit_bounds_padding_top_left=(0, 0),
	fit_bounds_padding_bottom_right=(0, 0),
):
	"""
	Split Route tab: cards (left) + map (right). Uses the same map renderer as Transport Job
	(Logistics Settings / Transport Settings: OpenStreetMap → Leaflet, Google Maps, Mapbox/MapLibre).

	pin_viewport_offset: (px_right, px_down) — pin mode shifts the pin this many pixels to the
	right and down from the geometric center of the map viewport. Use this when a floating UI
	element (e.g. an overlay card) covers part of the map. Default ``(0, 0)`` keeps the existing
	centered behavior.

	fit_bounds_padding_top_left / fit_bounds_padding_bottom_right: (px, px) — padding applied
	when ``fitBounds`` is used (route mode). Default ``(0, 0)`` keeps the existing behavior.
	"""
	map_renderer = get_dashboard_map_renderer()
	map_renderer_js = json.dumps(map_renderer)
	items_json = json.dumps(map_payloads or [])
	pin_offset_x = int((pin_viewport_offset or (0, 0))[0] or 0)
	pin_offset_y = int((pin_viewport_offset or (0, 0))[1] or 0)
	fit_pad_tl_x = int((fit_bounds_padding_top_left or (0, 0))[0] or 0)
	fit_pad_tl_y = int((fit_bounds_padding_top_left or (0, 0))[1] or 0)
	fit_pad_br_x = int((fit_bounds_padding_bottom_right or (0, 0))[0] or 0)
	fit_pad_br_y = int((fit_bounds_padding_bottom_right or (0, 0))[1] or 0)
	map_el_id = f"{map_id_prefix}-view"
	fallback_id = f"{map_el_id}-fallback"
	map_links_id = f"{map_el_id}-maplinks"
	hint1 = escape_html(_("Select a task or job"))
	hint2 = escape_html(_("Map updates when you click a card"))
	return f"""
<style>
.sp-dash-split {{
	display: flex;
	flex-wrap: wrap;
	gap: 1rem;
	align-items: stretch;
	width: 100%;
	min-height: 380px;
}}
.sp-dash-cards-col {{
	flex: 1 1 340px;
	max-width: min(440px, 100%);
	min-width: 260px;
	max-height: 520px;
	overflow-y: auto;
	overflow-x: hidden;
	padding-right: 4px;
}}
.sp-dash-map-wrap {{
	flex: 1 1 280px;
	min-width: 220px;
	min-height: 380px;
}}
.sp-dash-map-wrap .map-box {{
	height: 420px !important;
	max-width: 100%;
}}
.sp-dash-card {{
	cursor: pointer;
	background: #fff;
	border: 1px solid var(--ro-border-soft, #e9ecef);
	border-radius: 8px;
	padding: 10px 12px;
	margin-bottom: 8px;
	transition: box-shadow 0.15s ease, border-color 0.15s ease;
	border-left: 4px solid #667eea;
}}
.sp-dash-card:hover {{
	box-shadow: 0 2px 8px rgba(0,0,0,0.08);
}}
.sp-dash-card.is-selected {{
	border-color: #007bff;
	box-shadow: 0 0 0 1px #007bff;
}}
.sp-dash-card .sp-dash-card-title {{
	font-weight: 600;
	font-size: 13px;
	color: #212529;
	margin: 0 0 4px 0;
	line-height: 1.3;
}}
.sp-dash-card .sp-dash-card-sub {{
	font-size: 11px;
	color: #6c757d;
	line-height: 1.35;
}}
.sp-dash-card .sp-dash-card-badge {{
	display: inline-block;
	margin-top: 6px;
	font-size: 10px;
	font-weight: 600;
	text-transform: uppercase;
	padding: 2px 6px;
	border-radius: 4px;
	background: #e9ecef;
	color: #495057;
}}
.sp-dash-lifecycle-group.collapsed .sp-dash-lifecycle-group-body {{
	display: none;
}}
.sp-dash-lifecycle-group .sp-dash-card:last-child {{
	margin-bottom: 0;
}}
</style>
<div class="sp-dash-split">
	<div class="sp-dash-cards-col">{cards_sidebar_html}</div>
	<div class="sp-dash-map-wrap">
		<div class="map-main" style="width:100%;">
			<div class="map-box" style="position: relative;">
				<div id="{map_el_id}" class="map-view" style="width:100%;height:100%;"></div>
				<div id="{fallback_id}" style="display: flex; position: absolute; top: 0; left: 0; width: 100%; height: 100%;
					background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
					align-items: center; justify-content: center; flex-direction: column; z-index: 500;">
					<div style="text-align: center; color: #6c757d; padding: 20px;">
						<i class="fa fa-map" style="font-size: 28px; margin-bottom: 10px;"></i>
						<div style="font-size: 14px; font-weight: 500;" class="sp-dash-fallback-msg">{hint1}</div>
						<div class="text-muted small" style="margin-top:6px;">{hint2}</div>
					</div>
				</div>
			</div>
			<div id="{map_links_id}" class="sp-dash-map-links"></div>
		</div>
	</div>
</div>
<script>
(function() {{
	const items = {items_json};
	const mapRenderer = {map_renderer_js};
	const mapId = {json.dumps(map_el_id)};
	const fallbackId = {json.dumps(fallback_id)};
	const mapLinksId = {json.dumps(map_links_id)};
	const pinOffsetX = {pin_offset_x};
	const pinOffsetY = {pin_offset_y};
	const fitPadTL = [{fit_pad_tl_x}, {fit_pad_tl_y}];
	const fitPadBR = [{fit_pad_br_x}, {fit_pad_br_y}];
	let engine = null;
	let mapInst = null;
	let lGroup = null;
	let gMarkers = [];
	let gPoly = null;
	let mMarkers = [];

	function hideFallback() {{
		const fb = document.getElementById(fallbackId);
		if (fb) fb.style.display = 'none';
	}}
	function showFallback(msg) {{
		const fb = document.getElementById(fallbackId);
		if (fb) {{
			fb.style.display = 'flex';
			const el = fb.querySelector('.sp-dash-fallback-msg');
			if (el && msg) el.textContent = msg;
		}}
	}}
	function updateMapLinks(pts) {{
		const el = document.getElementById(mapLinksId);
		if (!el) return;
		if (!pts || pts.length < 2) {{ el.innerHTML = ''; return; }}
		const o = pts[0], d = pts[pts.length - 1];
		const ola = o.lat, olo = o.lon, dla = d.lat, dlo = d.lon;
		el.innerHTML = '<div class="map-links" style="margin-top:10px;display:flex;gap:20px;flex-wrap:wrap;justify-content:center;">'
			+ '<a href="https://www.google.com/maps/dir/' + ola + ',' + olo + '/' + dla + ',' + dlo + '" target="_blank" rel="noopener"><i class="fa fa-external-link"></i> Google Maps</a>'
			+ '<a href="https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=' + ola + ',' + olo + ';' + dla + ',' + dlo + '" target="_blank" rel="noopener"><i class="fa fa-external-link"></i> OpenStreetMap</a>'
			+ '<a href="http://maps.apple.com/?daddr=' + dla + ',' + dlo + '&saddr=' + ola + ',' + olo + '" target="_blank" rel="noopener"><i class="fa fa-external-link"></i> Apple Maps</a>'
			+ '</div>';
	}}

	function getRouteCoords(pts, straightLine, cb) {{
		if (straightLine || !pts || pts.length < 2) {{
			cb(pts ? pts.map(function(p) {{ return [p.lat, p.lon]; }}) : []);
			return;
		}}
		const wpStr = pts.map(function(p) {{ return p.lat + ',' + p.lon; }}).join('|');
		if (wpStr.length < 3) {{ cb(pts.map(function(p) {{ return [p.lat, p.lon]; }})); return; }}
		frappe.call({{ method: 'logistics.document_management.api.get_route_geometry', args: {{ waypoints: wpStr }} }})
			.then(function(r) {{
				const coords = (r.message && r.message.success && r.message.coordinates) ? r.message.coordinates : null;
				cb(coords || pts.map(function(p) {{ return [p.lat, p.lon]; }}));
			}})
			.catch(function() {{ cb(pts.map(function(p) {{ return [p.lat, p.lon]; }})); }});
	}}

	function defaultLatLng() {{
		for (let i = 0; i < items.length; i++) {{
			const pts = items[i].map_points || [];
			if (pts.length) return {{ lat: pts[0].lat, lng: pts[0].lon }};
		}}
		return {{ lat: 20, lng: 0 }};
	}}
	function defaultLngLat() {{
		for (let i = 0; i < items.length; i++) {{
			const pts = items[i].map_points || [];
			if (pts.length) return [pts[0].lon, pts[0].lat];
		}}
		return [0, 20];
	}}
	function firstSelectableIndex() {{
		for (let i = 0; i < items.length; i++) {{
			if ((items[i].map_points || []).length > 0 && items[i].map_mode !== 'empty') return i;
		}}
		return 0;
	}}

	function clearOverlays() {{
		if (engine === 'leaflet' && lGroup) {{
			lGroup.clearLayers();
		}} else if (engine === 'google') {{
			gMarkers.forEach(function(m) {{ try {{ m.setMap(null); }} catch (e) {{}} }});
			gMarkers = [];
			if (gPoly) {{ try {{ gPoly.setMap(null); }} catch (e2) {{}} gPoly = null; }}
		}} else if (engine === 'maplibre' && mapInst) {{
			mMarkers.forEach(function(m) {{ try {{ m.remove(); }} catch (e) {{}} }});
			mMarkers = [];
			try {{
				if (mapInst.getLayer && mapInst.getLayer('spdash-route-line')) mapInst.removeLayer('spdash-route-line');
				if (mapInst.getSource && mapInst.getSource('spdash-route')) mapInst.removeSource('spdash-route');
			}} catch (e3) {{}}
		}}
	}}

	function drawItem(idx) {{
		if (!mapInst || !items.length) return;
		const item = items[idx] || items[0];
		clearOverlays();
		const mode = item.map_mode || 'empty';
		const pts = item.map_points || [];
		const straight = item.straight_line !== false;
		const pop = function(t) {{ return '<b>' + String(t || '').replace(/</g, '&lt;') + '</b>'; }};

		if (mode === 'empty' || !pts.length) {{
			showFallback(item.label || 'No location data');
			updateMapLinks(null);
			if (engine === 'leaflet') mapInst.setView([20, 0], 2);
			else if (engine === 'google') {{ mapInst.setCenter({{ lat: 20, lng: 0 }}); mapInst.setZoom(2); }}
			else if (engine === 'maplibre') {{ mapInst.jumpTo({{ center: [0, 20], zoom: 2 }}); }}
			return;
		}}
		hideFallback();

		if (mode === 'pin' || pts.length === 1) {{
			const p = pts[0];
			const title = item.label || p.label || 'Location';
			if (engine === 'leaflet') {{
				L.marker([p.lat, p.lon]).addTo(lGroup).bindPopup(pop(title));
				mapInst.setView([p.lat, p.lon], 11);
				if (pinOffsetX || pinOffsetY) {{
					try {{ mapInst.panBy([-pinOffsetX, -pinOffsetY], {{ animate: false }}); }} catch (eo1) {{}}
				}}
			}} else if (engine === 'google') {{
				const mk = new google.maps.Marker({{ position: {{ lat: p.lat, lng: p.lon }}, map: mapInst, title: title }});
				gMarkers.push(mk);
				mapInst.setCenter({{ lat: p.lat, lng: p.lon }});
				mapInst.setZoom(11);
				if (pinOffsetX || pinOffsetY) {{
					try {{ mapInst.panBy(-pinOffsetX, -pinOffsetY); }} catch (eo2) {{}}
				}}
			}} else {{
				const mk = new maplibregl.Marker({{ color: 'blue' }}).setLngLat([p.lon, p.lat]).setPopup(new maplibregl.Popup().setHTML(pop(title))).addTo(mapInst);
				mMarkers.push(mk);
				mapInst.jumpTo({{ center: [p.lon, p.lat], zoom: 11 }});
				if (pinOffsetX || pinOffsetY) {{
					try {{ mapInst.panBy([-pinOffsetX, -pinOffsetY], {{ animate: false }}); }} catch (eo3) {{}}
				}}
			}}
			updateMapLinks(pts.length >= 2 ? pts : null);
			return;
		}}

		const hasFitPad = (fitPadTL[0] || fitPadTL[1] || fitPadBR[0] || fitPadBR[1]);
		getRouteCoords(pts, straight, function(latlngs) {{
			if (engine === 'leaflet') {{
				if (latlngs && latlngs.length >= 2) {{
					L.polyline(latlngs, {{ color: '#2196f3', weight: 3 }}).addTo(lGroup);
					try {{
						const lOpts = hasFitPad ? {{ paddingTopLeft: fitPadTL, paddingBottomRight: fitPadBR }} : undefined;
						mapInst.fitBounds(L.latLngBounds(latlngs).pad(0.12), lOpts);
					}} catch (e) {{}}
				}}
				pts.forEach(function(p, i) {{
					L.marker([p.lat, p.lon]).addTo(lGroup).bindPopup(pop(p.label || ('Stop ' + (i + 1))));
				}});
			}} else if (engine === 'google') {{
				if (latlngs && latlngs.length >= 2) {{
					const path = latlngs.map(function(c) {{ return {{ lat: c[0], lng: c[1] }}; }});
					gPoly = new google.maps.Polyline({{ path: path, strokeColor: '#2196f3', strokeWeight: 3, geodesic: true, map: mapInst }});
				}}
				pts.forEach(function(p, i) {{
					gMarkers.push(new google.maps.Marker({{ position: {{ lat: p.lat, lng: p.lon }}, map: mapInst, title: p.label || ('Stop ' + (i + 1)) }}));
				}});
				if (pts.length >= 2) {{
					const bounds = new google.maps.LatLngBounds();
					pts.forEach(function(p) {{ bounds.extend({{ lat: p.lat, lng: p.lon }}); }});
					if (hasFitPad) {{
						mapInst.fitBounds(bounds, {{ top: fitPadTL[1], left: fitPadTL[0], bottom: fitPadBR[1], right: fitPadBR[0] }});
					}} else {{
						mapInst.fitBounds(bounds);
					}}
				}}
			}} else {{
				if (latlngs && latlngs.length >= 2) {{
					const coords = latlngs.map(function(c) {{ return [c[1], c[0]]; }});
					try {{
						if (mapInst.getLayer('spdash-route-line')) mapInst.removeLayer('spdash-route-line');
						if (mapInst.getSource('spdash-route')) mapInst.removeSource('spdash-route');
					}} catch (e0) {{}}
					mapInst.addSource('spdash-route', {{ type: 'geojson', data: {{ type: 'Feature', geometry: {{ type: 'LineString', coordinates: coords }} }} }});
					mapInst.addLayer({{ id: 'spdash-route-line', type: 'line', source: 'spdash-route', paint: {{ 'line-color': '#2196f3', 'line-width': 3 }} }});
				}}
				pts.forEach(function(p, i) {{
					mMarkers.push(new maplibregl.Marker({{ color: 'blue' }}).setLngLat([p.lon, p.lat]).setPopup(new maplibregl.Popup().setHTML(pop(p.label || ('Stop ' + (i + 1))))).addTo(mapInst));
				}});
				if (latlngs && latlngs.length >= 2) {{
					const lngs = latlngs.map(function(ll) {{ return ll[1]; }});
					const lats = latlngs.map(function(ll) {{ return ll[0]; }});
					const mPad = hasFitPad
						? {{ top: fitPadTL[1] || 50, left: fitPadTL[0] || 50, bottom: fitPadBR[1] || 50, right: fitPadBR[0] || 50 }}
						: 50;
					mapInst.fitBounds(
						[[Math.min.apply(null, lngs), Math.min.apply(null, lats)], [Math.max.apply(null, lngs), Math.max.apply(null, lats)]],
						{{ padding: mPad }}
					);
				}}
			}}
			updateMapLinks(pts);
		}});
	}}

	function selectCard(idx) {{
		document.querySelectorAll('.sp-dash-card').forEach(function(el) {{
			var i = parseInt(el.getAttribute('data-sp-map-idx'), 10);
			if (isNaN(i)) return;
			el.classList.toggle('is-selected', i === idx);
		}});
		drawItem(idx);
	}}
	function bindCards() {{
		document.querySelectorAll('.sp-dash-card').forEach(function(card) {{
			card.addEventListener('click', function(ev) {{
				ev.stopPropagation();
				var idx = parseInt(card.getAttribute('data-sp-map-idx'), 10);
				if (!isNaN(idx)) selectCard(idx);
			}});
		}});
		initSpDashLifecycleGroups();
		selectCard(firstSelectableIndex());
	}}
	function initSpDashLifecycleGroups() {{
		document.querySelectorAll('.sp-dash-lifecycle-group-header').forEach(function(header) {{
			if (header.getAttribute('data-sp-lifecycle-bound')) return;
			header.setAttribute('data-sp-lifecycle-bound', '1');
			header.addEventListener('click', function(ev) {{
				ev.preventDefault();
				var group = header.closest('.sp-dash-lifecycle-group');
				if (!group) return;
				var body = group.querySelector('.sp-dash-lifecycle-group-body');
				var chevron = header.querySelector('.sp-dash-lifecycle-chevron');
				var collapsed = group.classList.toggle('collapsed');
				if (body) body.style.display = collapsed ? 'none' : '';
				if (chevron) {{
					chevron.classList.toggle('fa-chevron-right', collapsed);
					chevron.classList.toggle('fa-chevron-down', !collapsed);
				}}
			}});
		}});
	}}

	function initLeaflet() {{
		const el = document.getElementById(mapId);
		if (!el) {{ setTimeout(initLeaflet, 150); return; }}
		if (!window.L) {{
			const c = document.createElement('link'); c.rel = 'stylesheet'; c.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'; document.head.appendChild(c);
			const s = document.createElement('script'); s.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'; s.onload = initLeaflet; document.head.appendChild(s);
			return;
		}}
		try {{
			const d = defaultLatLng();
			mapInst = L.map(mapId).setView([d.lat, d.lng], 4);
			L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ attribution: '© OpenStreetMap' }}).addTo(mapInst);
			lGroup = L.layerGroup().addTo(mapInst);
			engine = 'leaflet';
			bindCards();
		}} catch (e) {{ console.error('SP dash Leaflet:', e); }}
	}}

	function doGoogleMap() {{
		const el = document.getElementById(mapId);
		if (!el) {{ setTimeout(doGoogleMap, 100); return; }}
		try {{
			const d = defaultLatLng();
			mapInst = new google.maps.Map(el, {{ center: d, zoom: 8 }});
			engine = 'google';
			bindCards();
		}} catch (e) {{ console.error('SP dash Google:', e); initLeaflet(); }}
	}}
	function initGoogleMap() {{
		frappe.call({{ method: 'logistics.document_management.api.get_google_maps_api_key' }}).then(function(r) {{
			const apiKey = r.message && r.message.api_key;
			if (!apiKey || apiKey.length < 10) {{ initLeaflet(); return; }}
			if (window.google && window.google.maps) {{ doGoogleMap(); return; }}
			const s = document.createElement('script');
			s.src = 'https://maps.googleapis.com/maps/api/js?key=' + apiKey + '&libraries=geometry';
			s.async = true; s.onload = function() {{ doGoogleMap(); }};
			s.onerror = function() {{ initLeaflet(); }};
			document.head.appendChild(s);
		}}).catch(function() {{ initLeaflet(); }});
	}}

	function initMapLibre() {{
		const el = document.getElementById(mapId);
		if (!el) {{ setTimeout(initMapLibre, 150); return; }}
		if (!window.maplibregl) {{
			const css = document.createElement('link'); css.rel = 'stylesheet'; css.href = 'https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.css'; document.head.appendChild(css);
			const script = document.createElement('script'); script.src = 'https://unpkg.com/maplibre-gl@3.6.2/dist/maplibre-gl.js';
			script.onload = initMapLibre; document.head.appendChild(script);
			return;
		}}
		try {{
			const c = defaultLngLat();
			mapInst = new maplibregl.Map({{
				container: mapId,
				style: {{ version: 8, sources: {{ 'osm': {{ type: 'raster', tiles: ['https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png'], tileSize: 256 }} }}, layers: [{{ id: 'osm', type: 'raster', source: 'osm' }}] }},
				center: c,
				zoom: 4
			}});
			engine = 'maplibre';
			mapInst.on('load', function() {{ bindCards(); }});
		}} catch (e) {{ console.error('SP dash MapLibre:', e); initLeaflet(); }}
	}}

	function boot() {{
		const r = (mapRenderer || '').toLowerCase();
		if (r === 'google maps') {{ initGoogleMap(); return; }}
		if (r === 'mapbox' || r === 'maplibre') {{ initMapLibre(); return; }}
		initLeaflet();
	}}
	if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
	else boot();
}})();
</script>
"""


def render_special_project_fulfillment_route_tab_html(
	fulfillment_left_html,
	lifecycle_right_html,
	current_lifecycle_stage=None,
):
	"""
	Split Route tab: fulfillment summary (left) + lifecycle/service cards (right).

	Left: overall completion hero and current-stage throughput.
	Right: collapsible lifecycle groups with per-stage throughput in headers and job cards.
	"""
	current_stage = (current_lifecycle_stage or "").strip()
	return f"""
<style>
.sp-dash-split.sp-dash-split--fulfillment {{
	display: flex;
	flex-wrap: wrap;
	gap: 1rem;
	align-items: stretch;
	width: 100%;
	min-height: 380px;
}}
.sp-dash-split--fulfillment .sp-dash-fulfillment-col {{
	flex: 0 1 340px;
	max-width: min(360px, 100%);
	min-width: 260px;
	max-height: 560px;
	overflow-y: auto;
	overflow-x: hidden;
}}
.sp-dash-split--fulfillment .sp-dash-cards-col {{
	flex: 1 1 380px;
	min-width: 280px;
	max-height: 560px;
	overflow-y: auto;
	overflow-x: hidden;
	padding-right: 4px;
}}
.sp-dash-lifecycle-group.collapsed .sp-dash-lifecycle-group-body {{
	display: none;
}}
.sp-dash-lifecycle-group.is-stage-filter .sp-dash-lifecycle-group-header {{
	background: #EEF2FF;
}}
.sp-dash-lifecycle-group.is-stage-filter {{
	border-color: #C7D2FE !important;
}}
</style>
<div class="sp-dash-split sp-dash-split--fulfillment" data-sp-fulfillment-dash="1" data-sp-current-stage="{escape_html(current_stage)}">
	<div class="sp-dash-fulfillment-col">{fulfillment_left_html}</div>
	<div class="sp-dash-cards-col">{lifecycle_right_html}</div>
</div>
"""


def _fmt_capacity_num(value, precision=0):
	"""Format a capacity number with thin-space thousands separators."""
	try:
		n = float(value or 0)
	except (TypeError, ValueError):
		n = 0.0
	if precision <= 0:
		text = frappe.format_value(int(round(n)), {"fieldtype": "Int"})
	else:
		text = frappe.format_value(n, {"fieldtype": "Float", "precision": precision})
	return str(text).replace(",", "\u00a0")


def _capacity_pair_html(used, max_value, unit, used_precision=0):
	used_str = _fmt_capacity_num(used, used_precision)
	try:
		max_n = float(max_value or 0)
	except (TypeError, ValueError):
		max_n = 0.0
	max_str = _fmt_capacity_num(max_n, 0) if max_n > 0 else "—"
	unit_text = f" {unit}" if unit else ""
	return (
		f'<span class="rs-cap-used">{escape_html(used_str)}</span>'
		f'<span class="rs-cap-muted"> / </span>'
		f'<span class="rs-cap-muted">{escape_html(max_str)}</span>'
		f'<span class="rs-cap-muted">{escape_html(unit_text)}</span>'
	)


def _status_dot_color(status):
	s = (status or "").lower()
	if s in ("dispatched", "completed"):
		return "#22c55e"
	if s in ("in-progress", "started", "in progress"):
		return "#2563eb"
	if s in ("hold", "cancelled"):
		return "#ef4444"
	if s == "draft":
		return "#9ca3af"
	return "#22c55e"


def compute_capacity_pct(used_weight, max_weight, used_volume, max_volume):
	"""Return estimated used-capacity % as max(weight%, volume%)."""
	try:
		uw, mw = float(used_weight or 0), float(max_weight or 0)
		uv, mv = float(used_volume or 0), float(max_volume or 0)
	except (TypeError, ValueError):
		return 0.0
	weight_pct = (uw / mw) * 100.0 if mw > 0 else 0.0
	volume_pct = (uv / mv) * 100.0 if mv > 0 else 0.0
	return max(0.0, min(100.0, max(weight_pct, volume_pct)))


def build_capacity_metrics_html(
	used_weight=0,
	max_weight=0,
	used_volume=0,
	max_volume=0,
	capacity_pct=None,
	used_label="Estimated used capacity",
	compact=False,
):
	"""
	Build Payload / Capacity / estimated used-capacity bar HTML for embedding in headers.
	compact=True: metrics row only (for simple dashboard headers).
	compact=False: metrics + progress bar block for the rich run-sheet header right column.
	"""
	if capacity_pct is None:
		capacity_pct = compute_capacity_pct(used_weight, max_weight, used_volume, max_volume)
	pct = max(0.0, min(100.0, float(capacity_pct or 0)))
	pct_str = _fmt_capacity_num(pct, 0)
	metrics = f"""
		<div class="rs-cap-metrics-inline">
			<div class="rs-cap-metric">
				<span class="rs-cap-metric-label">Payload</span>
				<div class="rs-cap-metric-value">{_capacity_pair_html(used_weight, max_weight, "kg")}</div>
			</div>
			<div class="rs-cap-metric">
				<span class="rs-cap-metric-label">Capacity</span>
				<div class="rs-cap-metric-value">{_capacity_pair_html(used_volume, max_volume, "m\u00b3", 3)}</div>
			</div>
		</div>
		<div class="rs-cap-used-row">
			<span class="rs-cap-used-label">{escape_html(used_label)}</span>
			<div class="rs-cap-used-track-wrap">
				<div class="rs-cap-used-track">
					<div class="rs-cap-used-fill" style="width:{pct:.1f}%"></div>
				</div>
				<span class="rs-cap-used-pct">{escape_html(pct_str)}%</span>
			</div>
		</div>
	"""
	if compact:
		return f'<div class="rs-cap-metrics-block" style="width:100%;margin-top:8px;">{metrics}</div>'
	return metrics


def build_run_sheet_capacity_header_html(
	vehicle_type_label="Vehicle type",
	primary_title="New",
	transport_company="Not assigned",
	driver_name="Not assigned",
	run_sheet_id="—",
	vehicle_display_name="Not assigned",
	status="Draft",
	run_date="Not set",
	leg_count=0,
	driver_image_url="",
	vehicle_image_url="",
	used_weight=0,
	max_weight=0,
	used_volume=0,
	max_volume=0,
	capacity_pct=None,
	used_capacity_label="Estimated used capacity",
	include_style=True,
):
	"""
	Build a Run Sheet-style header card with payload / capacity / used-capacity in the header
	(not a separate dashboard panel).
	"""
	if capacity_pct is None:
		capacity_pct = compute_capacity_pct(used_weight, max_weight, used_volume, max_volume)
	status_color = _status_dot_color(status)
	driver_avatar = (
		f'<img src="{escape_html(driver_image_url)}" alt="" />'
		if driver_image_url
		else '<i class="fa fa-user"></i>'
	)
	vehicle_avatar = (
		f'<img src="{escape_html(vehicle_image_url)}" alt="" />'
		if vehicle_image_url
		else '<i class="fa fa-truck"></i>'
	)
	metrics_html = build_capacity_metrics_html(
		used_weight=used_weight,
		max_weight=max_weight,
		used_volume=used_volume,
		max_volume=max_volume,
		capacity_pct=capacity_pct,
		used_label=used_capacity_label,
		compact=False,
	)
	style_block = f"<style>{RUN_SHEET_LAYOUT_CSS}</style>" if include_style else ""
	return f"""
	{style_block}
	<div class="rs-cap-header">
		<div class="rs-cap-header__main">
			<div class="rs-cap-header__left">
				<label class="section-label">{escape_html(vehicle_type_label or "Vehicle type")}</label>
				<div class="rs-cap-primary-title">{escape_html(primary_title or "New")}</div>
				<div class="rs-cap-meta-list">
					<div class="rs-cap-meta-row"><i class="fa fa-building"></i><span>{escape_html(transport_company or "Not assigned")}</span></div>
					<div class="rs-cap-meta-row"><i class="fa fa-user"></i><span>{escape_html(driver_name or "Not assigned")}</span></div>
					<div class="rs-cap-meta-row"><i class="fa fa-file-text-o"></i><span>{escape_html(run_sheet_id or "—")}</span></div>
				</div>
			</div>
			<div class="rs-cap-header__avatars" title="{escape_html(driver_name or "")}">
				<div class="rs-cap-avatar rs-cap-avatar--driver">{driver_avatar}</div>
				<div class="rs-cap-avatar rs-cap-avatar--vehicle" title="{escape_html(vehicle_display_name or "")}">{vehicle_avatar}</div>
			</div>
			<div class="rs-cap-header__right">
				<div class="rs-cap-vehicle-row">
					<span class="rs-cap-vehicle-name">{escape_html(vehicle_display_name or "Not assigned")}</span>
					<span class="rs-cap-status-badge">
						<span class="rs-cap-status-dot" style="background:{status_color}"></span>
						{escape_html(status or "Draft")}
					</span>
				</div>
				{metrics_html}
			</div>
		</div>
		<div class="rs-cap-header__footer">
			<span><i class="fa fa-calendar" style="color:#9ca3af;margin-right:6px;"></i>Run Date: <span class="rs-cap-footer-value">{escape_html(run_date or "Not set")}</span></span>
			<span class="rs-cap-footer-legs">Legs: <span class="rs-cap-footer-value">{int(leg_count or 0)}</span></span>
		</div>
	</div>
	"""


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
	capacity_metrics=None,
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
	capacity_metrics: optional dict with used_weight, max_weight, used_volume, max_volume, capacity_pct
		— rendered inside the header (not a separate dashboard).
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
	capacity_block = ""
	if capacity_metrics and isinstance(capacity_metrics, dict):
		capacity_block = build_capacity_metrics_html(
			used_weight=capacity_metrics.get("used_weight", 0),
			max_weight=capacity_metrics.get("max_weight", 0),
			used_volume=capacity_metrics.get("used_volume", 0),
			max_volume=capacity_metrics.get("max_volume", 0),
			capacity_pct=capacity_metrics.get("capacity_pct"),
			used_label=capacity_metrics.get("used_label") or "Estimated used capacity",
			compact=True,
		)
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
				{capacity_block}
			</div>
			{merged_cards_content}
		</div>
		{body_content}
		{doc_below_body}
	</div>
	"""
	return html
