# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Air Booking form dashboard: RO-style summary, airline logo, Route / Milestones (n) / Alerts and Notifications (n).
Map HTML is shared via logistics.document_management.dashboard_layout.render_route_map_html.
"""

from __future__ import unicode_literals

import json
import frappe
from frappe.utils import escape_html


# Scoped root: .log-ab-dash (Repair Order–aligned tokens)
AIR_BOOKING_DASH_CSS = """
.log-ab-dash.run-sheet-dash {
	--ro-green: #28a745;
	--ro-amber: #ffc107;
	--ro-red: #dc3545;
	--ro-gray-ring: #868e96;
	--ro-blue: #007bff;
	--ro-bg-muted: #F4F7F9;
	--ro-header-bg: #ffffff;
	--ro-text: #333333;
	--ro-text-strong: #212529;
	--ro-label: #868e96;
	--ro-label-2: #6c757d;
	--ro-muted: #495057;
	--ro-border: #dee2e6;
	--ro-border-soft: #e9ecef;
	--ro-fill-light: #f8f9fa;
	--ro-service-title: #3d5a6c;
	--ro-shadow-card: 0 1px 2px rgba(0,0,0,0.04);
	font-family: "Inter", "Segoe UI", system-ui, sans-serif;
	font-size: 0.85rem;
	line-height: 1.4;
	color: var(--ro-text);
	width: 100%;
	max-width: 100%;
	margin: 0 0 2.5rem 0;
	border-radius: 12px;
	overflow: hidden;
	background: var(--ro-bg-muted);
	box-shadow: var(--ro-shadow-card);
}
.log-ab-dash .log-ab-top { background: var(--ro-header-bg); padding: 1.35rem 1.5rem 0; }
.log-ab-dash .log-ab-head.run-sheet-header {
	background: transparent; border: none; border-radius: 0; box-shadow: none;
	padding: 0 0 1rem 0; margin: 0;
}
.log-ab-dash .log-ab-head-stack { display: flex; flex-direction: column; gap: 0.75rem; }
.log-ab-dash .log-ab-top-row {
	display: flex; align-items: flex-start; justify-content: space-between; gap: 1rem 1.5rem;
	flex-wrap: nowrap;
}
.log-ab-dash .ab-summary-aside { flex-shrink: 0; }
.log-ab-dash .log-ab-body-block { width: 100%; }
.log-ab-dash .log-ab-hero-col {
	display: flex; flex-direction: column; align-items: flex-start; gap: 0.45rem;
	flex-shrink: 0; min-width: 0;
}
.log-ab-dash .log-ab-main-block {
	flex: 1; min-width: 0; align-self: stretch;
	display: flex; flex-direction: column; align-items: flex-start; gap: 0.45rem;
}
.log-ab-dash .log-ab-meta-cluster {
	width: 100%;
	min-width: 0; align-self: stretch;
	display: flex; flex-direction: row; flex-wrap: wrap; align-items: flex-start;
	gap: 0.75rem 2.25rem;
}
.log-ab-dash .log-ab-meta-col { flex: 1 1 11rem; min-width: 0; max-width: 100%; }
.log-ab-dash .log-ab-meta-cluster .ab-summary-meta-rows { margin: 0; }
.log-ab-dash .log-ab-meta-cluster .ab-secondary-meta { max-width: none; width: 100%; }
.log-ab-dash .log-ab-logo-img {
	display: block; width: auto; height: auto; max-height: 112px; max-width: min(280px, 100%);
	object-fit: contain; object-position: left center;
	background: transparent; border: none; box-shadow: none; flex-shrink: 0; border-radius: 0;
}
.log-ab-dash .log-ab-logo-ph {
	display: inline-flex; align-items: center; justify-content: center;
	min-width: 2.75rem; min-height: 2.75rem; padding: 0.35rem 0.5rem; border-radius: 8px;
	background: var(--ro-fill-light);
	font-size: 1.35rem; font-weight: 700; color: var(--ro-label); flex-shrink: 0;
}
.log-ab-dash .log-ab-route-panel {
	display: flex; flex-direction: row; flex-wrap: wrap; align-items: flex-end;
	gap: 0.35rem 0.85rem; width: 100%; min-width: 0; padding-bottom: 0.15rem;
}
.log-ab-dash .log-ab-route-leg {
	display: flex; flex-direction: row; align-items: flex-start; gap: 0.45rem;
	min-width: 0; max-width: min(42vw, 20rem);
}
.log-ab-dash .log-ab-route-flag {
	font-size: 1.55rem; line-height: 1; flex-shrink: 0; margin-top: 0.08rem;
	font-family: "Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji", sans-serif;
}
.log-ab-dash .log-ab-route-flag--empty { width: 1.55rem; }
.log-ab-dash .log-ab-route-leg-text {
	display: flex; flex-direction: column; align-items: flex-start; gap: 0.08rem;
	min-width: 0;
}
.log-ab-dash .log-ab-route-panel .log-ab-route-code {
	font-size: 1.35rem; font-weight: 600; color: var(--ro-blue); letter-spacing: 0.02em;
	white-space: nowrap;
}
.log-ab-dash .log-ab-route-sub {
	font-size: 0.75rem; font-weight: 500; color: var(--ro-label); line-height: 1.25;
	word-wrap: break-word; overflow-wrap: break-word; max-width: 100%;
}
.log-ab-dash .log-ab-route-mid {
	display: flex; align-items: center; align-self: center; flex-shrink: 0;
	padding: 0 0.15rem 0.35rem;
}
.log-ab-dash .log-ab-route-arrow-h {
	font-size: 1.35rem; font-weight: 600; color: var(--ro-blue); line-height: 1;
}
.log-ab-dash .ab-summary-center { flex: 1; min-width: 200px; }
.log-ab-dash .ab-summary-meta-cols {
	display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
	gap: 1rem 1.5rem; align-items: start; margin: 0.75rem 0 0.5rem 0;
}
.log-ab-dash .ab-summary-meta-cols .ab-summary-meta-rows { margin: 0; }
.log-ab-dash .ab-summary-meta-cols .ab-secondary-meta { max-width: none; width: 100%; }
.log-ab-dash .ab-summary-meta-rows { display: flex; flex-direction: column; gap: 0.5rem; margin: 0.75rem 0 0.5rem 0; }
.log-ab-dash .ab-meta-row { display: flex; align-items: center; gap: 0.65rem; font-size: 0.82rem; color: var(--ro-muted); line-height: 1.45; }
.log-ab-dash .ab-meta-row i { width: 1.1rem; text-align: center; color: var(--ro-label); }
.log-ab-dash .ab-meta-row .ab-meta-k { font-weight: 600; color: var(--ro-label-2); margin-right: 0.25rem; }
.log-ab-dash .header-details { gap: 1rem; }
.log-ab-dash .header-item label {
	font-size: 0.62rem; font-weight: 700; letter-spacing: 0.04em; text-transform: uppercase; color: var(--ro-label);
}
.log-ab-dash .header-item span { font-size: 0.78rem; color: var(--ro-text-strong); font-weight: 500; }
.log-ab-dash .log-ab-top-row .ab-summary-aside { display: flex; flex-direction: column; align-items: center; justify-content: flex-start; min-width: 112px; }
.log-ab-dash .ab-secondary-meta { font-size: 0.75rem; color: var(--ro-label-2); width: 100%; max-width: 220px; }
.log-ab-dash .ab-secondary-meta .ab-sec-line { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
.log-ab-dash .ab-secondary-meta .ab-sec-line i { color: #adb5bd; flex-shrink: 0; }
.log-ab-dash .ab-secondary-meta .ab-sec-val { font-size: 0.82rem; color: var(--ro-muted); line-height: 1.45; }
.log-ab-dash .ab-secondary-meta .ab-sec-k { font-weight: 600; color: var(--ro-label-2); margin-right: 0.25rem; }
.log-ab-dash .ab-secondary-meta .ab-sec-line.ab-sec-line--sub { margin-top: 0.1rem; margin-bottom: 0.4rem; }
.log-ab-dash .ab-secondary-meta .ab-sec-line.ab-sec-line--sub i { font-size: 0.7rem; opacity: 0.85; }
.log-ab-dash .ab-secondary-meta .ab-sec-val.ab-sec-val--sub { font-size: 0.76rem; color: var(--ro-label-2); line-height: 1.35; }
.log-ab-dash .ab-ring-wrap { position: relative; width: 112px; height: 112px; flex-shrink: 0; }
.log-ab-dash .ab-ring {
	width: 100%; height: 100%; border-radius: 50%;
	background: conic-gradient(var(--ro-ring-fill, var(--ro-blue)) calc(var(--ab-pct, 0) * 1%), var(--ro-gray-ring) 0);
}
/* Progress ring arc color matches document status */
.log-ab-dash .ab-ring.ab-ring--status-draft { --ro-ring-fill: #e6495c; }
.log-ab-dash .ab-ring.ab-ring--status-submitted { --ro-ring-fill: #0d6efd; }
.log-ab-dash .ab-ring.ab-ring--status-cancelled { --ro-ring-fill: #6c757d; }
.log-ab-dash .ab-ring-center {
	position: absolute; inset: 10px; border-radius: 50%; background: var(--ro-header-bg);
	display: flex; flex-direction: column; align-items: center; justify-content: center;
	box-shadow: inset 0 0 0 1px var(--ro-border-soft); transform: translateY(-2px);
}
.log-ab-dash .ab-ring-center .ab-ring-pct { font-size: 0.88rem; font-weight: 700; color: var(--ro-text-strong); line-height: 1.1; }
.log-ab-dash .ab-ring-center .ab-ring-cap { font-size: 0.58rem; color: var(--ro-label); margin-top: 1px; text-align: center; line-height: 1.2; }
.log-ab-dash .ab-dash-tab-input { position: absolute; opacity: 0; width: 0; height: 0; margin: 0; pointer-events: none; }
.log-ab-dash .ab-tab-shell { position: relative; padding: 0 1.5rem; background: var(--ro-header-bg); }
.log-ab-dash .ab-tab-bar {
	display: flex; flex-wrap: wrap; gap: 0.25rem; margin: 0; padding: 0;
	background: var(--ro-header-bg); border-bottom: 1px solid var(--ro-border);
	-webkit-tap-highlight-color: transparent;
}
.log-ab-dash .ab-tab-bar .ab-tlabel {
	padding: 0.65rem 0.85rem 0.5rem; margin-bottom: -1px; cursor: pointer; font-size: 0.72rem; font-weight: 600;
	letter-spacing: 0.06em; color: var(--ro-label); border-bottom: 3px solid transparent; border-radius: 2px 2px 0 0;
	transition: color 0.15s ease, border-color 0.15s ease; user-select: none; touch-action: manipulation;
	min-height: 40px; display: inline-flex; align-items: center;
}
.log-ab-dash .ab-tab-bar .ab-tlabel:hover { color: var(--ro-muted); }
.log-ab-dash .ab-tab-count { font-weight: 600; color: var(--ro-muted); margin-left: 0.15rem; }
.log-ab-dash .ab-tlabel .ab-tab-count--highlight { color: var(--ro-blue); }
.log-ab-dash .ab-ro-body { background: var(--ro-bg-muted); margin: 0 -1.5rem; padding: 1rem 1.5rem 1.5rem; }
.log-ab-dash .ab-tab-panels.ab-ro-shell {
	background: transparent; border: none; border-radius: 0; padding: 0; box-shadow: none; min-height: 80px;
}
.log-ab-dash .ab-tab-panel { display: none; }
.log-ab-dash .ab-tab-empty { padding: 1.5rem; text-align: center; color: var(--ro-label-2); font-size: 0.82rem; }
.log-ab-dash .log-ab-ro-card {
	background: var(--ro-header-bg); border: 1px solid var(--ro-border-soft); border-radius: 12px;
	box-shadow: var(--ro-shadow-card); padding: 1.25rem 1.35rem;
}
.log-ab-dash .log-ab-ro-card--flush { padding: 0; overflow: hidden; }
.log-ab-dash .log-ab-ro-card--empty { padding: 2rem 1.5rem; }
.log-ab-dash .ab-route-tab-inner .map-main { flex: 1; max-width: 100%; width: 100%; }
.log-ab-dash .ab-route-tab-inner .map-box {
	height: 460px; border: none; border-radius: 0; box-shadow: none;
}
.log-ab-dash .log-ab-ro-card--flush .map-links { padding: 0.65rem 1rem; background: var(--ro-fill-light); border-top: 1px solid var(--ro-border-soft); }
.log-ab-dash .ab-route-tab-inner .map-links a { color: var(--ro-blue); font-size: 0.78rem; }
.log-ab-dash .log-ab-jc-grid {
	display: grid;
	grid-template-columns: minmax(100px, 1.8fr) minmax(72px, 0.85fr) minmax(88px, 1.05fr) minmax(88px, 1.05fr) 2rem;
	gap: 0.4rem 0.85rem; align-items: start;
}
.log-ab-dash .log-ab-jc-head {
	font-size: 0.62rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; color: var(--ro-label);
	padding-bottom: 0.5rem; border-bottom: 1px solid var(--ro-border-soft); margin-bottom: 0.15rem;
}
.log-ab-dash .log-ab-jc-head > div { line-height: 1.3; }
.log-ab-dash .log-ab-jc-grid.log-ab-jc-row {
	font-size: 0.8rem; color: var(--ro-text-strong); padding: 0.65rem 0; border-bottom: 1px solid #f1f3f5;
	align-items: center;
}
.log-ab-dash .log-ab-jc-row:last-of-type { border-bottom: none; }
.log-ab-dash .log-ab-jc-ms-title { font-weight: 600; color: var(--ro-service-title); line-height: 1.35; }
.log-ab-dash .log-ab-jc-status { font-weight: 600; color: var(--ro-text-strong); }
.log-ab-dash .log-ab-jc-dt { font-size: 0.78rem; color: var(--ro-muted); line-height: 1.4; }
.log-ab-dash .log-ab-jc-idx { font-size: 0.72rem; color: var(--ro-label); text-align: right; }
.log-ab-dash .log-ab-jc-foot {
	margin-top: 0.85rem; padding-top: 1rem; border-top: 1px solid var(--ro-border-soft);
}
.log-ab-dash .log-ab-jc-foot-lbl {
	font-size: 0.62rem; font-weight: 700; letter-spacing: 0.06em; color: var(--ro-label); text-transform: uppercase;
}
.log-ab-dash .log-ab-jc-foot-title {
	font-size: 1rem; font-weight: 600; color: var(--ro-service-title); margin: 0.4rem 0 0.45rem; line-height: 1.25;
}
.log-ab-dash .log-ab-text-link {
	color: var(--ro-blue); font-size: 0.82rem; font-weight: 500; text-decoration: none; cursor: pointer; border: none; background: none; padding: 0;
}
.log-ab-dash .log-ab-text-link:hover { text-decoration: underline; }
@media (max-width: 640px) {
	.log-ab-dash.run-sheet-dash {
		border-radius: 10px;
		margin-bottom: 1.75rem;
		font-size: 0.8125rem;
	}
	.log-ab-dash .log-ab-top { padding: 1rem 0.75rem 0; }
	.log-ab-dash .log-ab-head.run-sheet-header { padding-bottom: 0.85rem; }
	/* Stack: logo → progress ring → route & meta (clear story on small screens) */
	.log-ab-dash .log-ab-top-row {
		flex-direction: column;
		align-items: stretch;
		flex-wrap: nowrap;
		gap: 1rem;
	}
	.log-ab-dash .log-ab-hero-col {
		order: 1;
		align-items: center;
		align-self: center;
		width: 100%;
	}
	.log-ab-dash .log-ab-top-row .ab-summary-aside {
		order: 2;
		margin-left: 0 !important;
		align-self: center;
		min-width: 0;
	}
	.log-ab-dash .log-ab-main-block {
		order: 3;
		flex: 1 1 100%;
		min-width: 0;
		width: 100%;
		align-items: stretch;
	}
	.log-ab-dash .log-ab-logo-img {
		max-height: 76px;
		max-width: min(240px, 88vw);
		margin: 0 auto;
	}
	.log-ab-dash .log-ab-logo-ph {
		min-width: 2.5rem;
		min-height: 2.5rem;
		font-size: 1.15rem;
	}
	.log-ab-dash .ab-ring-wrap { width: 100px; height: 100px; }
	.log-ab-dash .ab-ring-center { inset: 9px; }
	.log-ab-dash .ab-ring-center .ab-ring-pct { font-size: 0.82rem; }
	.log-ab-dash .ab-summary-meta-cols { grid-template-columns: 1fr; }
	.log-ab-dash .log-ab-meta-cluster {
		flex: 1 1 100%;
		flex-direction: column;
		gap: 0.85rem;
	}
	.log-ab-dash .log-ab-meta-col { flex: 1 1 auto; max-width: 100%; }
	.log-ab-dash .ab-secondary-meta { max-width: 100%; }
	/* Route: vertical flow, full-width legs */
	.log-ab-dash .log-ab-route-panel {
		flex-direction: column;
		align-items: stretch;
		gap: 0.5rem;
	}
	.log-ab-dash .log-ab-route-leg {
		max-width: 100%;
		align-items: center;
	}
	.log-ab-dash .log-ab-route-mid {
		align-self: center;
		padding: 0.1rem 0;
	}
	.log-ab-dash .log-ab-route-arrow-h {
		display: inline-block;
		transform: rotate(90deg);
		font-size: 1.15rem;
	}
	.log-ab-dash .log-ab-route-panel .log-ab-route-code,
	.log-ab-dash .log-ab-route-arrow-h { white-space: normal; }
	.log-ab-dash .log-ab-route-panel .log-ab-route-code { font-size: 1.15rem; }
	.log-ab-dash .log-ab-route-sub { font-size: 0.72rem; }
	/* KPI strip: two columns, readable density */
	.log-ab-dash .log-ab-body-block .header-details {
		display: grid;
		grid-template-columns: repeat(2, minmax(0, 1fr));
		gap: 0.55rem 0.85rem;
		width: 100%;
	}
	.log-ab-dash .log-ab-body-block .header-details .header-item {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 0.15rem;
		min-width: 0;
		padding: 0.4rem 0;
		border-bottom: 1px solid var(--ro-border-soft);
	}
	.log-ab-dash .log-ab-body-block .header-details .header-item label { font-size: 0.58rem; }
	.log-ab-dash .log-ab-body-block .header-details .header-item span {
		font-size: 0.74rem;
		word-break: break-word;
		line-height: 1.35;
	}
	/* Tabs: equal columns, comfortable tap targets */
	.log-ab-dash .ab-tab-shell { padding: 0 0.65rem; }
	.log-ab-dash .ab-tab-bar {
		flex-wrap: nowrap;
		gap: 0;
		border-bottom: 1px solid var(--ro-border);
	}
	.log-ab-dash .ab-tab-bar .ab-tlabel {
		flex: 1 1 0;
		min-width: 0;
		justify-content: center;
		text-align: center;
		font-size: 0.62rem;
		line-height: 1.25;
		padding: 0.75rem 0.35rem 0.65rem;
		min-height: 48px;
		hyphens: auto;
		-webkit-hyphens: auto;
	}
	.log-ab-dash .ab-ro-body {
		margin: 0 -0.65rem;
		padding: 0.85rem 0.65rem 1.15rem;
		padding-bottom: calc(1.15rem + env(safe-area-inset-bottom, 0px));
	}
	.log-ab-dash .log-ab-ro-card { padding: 0.95rem 0.75rem; border-radius: 10px; }
	.log-ab-dash .ab-route-tab-inner .map-box {
		height: min(42vh, 270px);
		min-height: 200px;
	}
	.log-ab-dash .log-ab-ro-card--flush .map-links { padding: 0.55rem 0.75rem; }
	/* Milestones: hide table header, card-style rows */
	.log-ab-dash .log-ab-jc-grid.log-ab-jc-head { display: none; }
	.log-ab-dash .log-ab-jc-grid.log-ab-jc-row {
		display: grid;
		grid-template-columns: 1fr auto;
		grid-auto-rows: auto;
		gap: 0.35rem 0.5rem;
		padding: 0.85rem 0.75rem;
		margin-bottom: 0.55rem;
		background: var(--ro-fill-light);
		border: 1px solid var(--ro-border-soft);
		border-radius: 10px;
		border-bottom: none;
		align-items: start;
	}
	.log-ab-dash .log-ab-jc-ms-title { grid-column: 1; grid-row: 1; line-height: 1.3; }
	.log-ab-dash .log-ab-jc-row .log-ab-jc-idx {
		grid-column: 2;
		grid-row: 1;
		justify-self: end;
		align-self: start;
	}
	.log-ab-dash .log-ab-jc-status { grid-column: 1 / -1; grid-row: 2; }
	.log-ab-dash .log-ab-jc-row > :nth-child(3) { grid-column: 1 / -1; grid-row: 3; }
	.log-ab-dash .log-ab-jc-row > :nth-child(4) { grid-column: 1 / -1; grid-row: 4; }
	.log-ab-dash .log-ab-jc-foot { margin-top: 0.65rem; padding-top: 0.85rem; }
	.log-ab-dash .log-ab-jc-foot-title { font-size: 0.92rem; }
}
@media (max-width: 380px) {
	.log-ab-dash .ab-tab-bar .ab-tlabel { font-size: 0.58rem; padding-left: 0.25rem; padding-right: 0.25rem; }
	.log-ab-dash .log-ab-body-block .header-details { grid-template-columns: 1fr; }
}
"""


def _route_supplement_html(route_below_html):
	"""Optional DG (or other) HTML below the header row; ports are shown beside the logo."""
	return (route_below_html or "").strip()


def _flag_emoji_from_country_code(cc):
	"""Regional-indicator pair for ISO 3166-1 alpha-2 (e.g. JP → 🇯🇵), or empty."""
	if not cc or len(str(cc).strip()) != 2:
		return ""
	a, b = str(cc).strip().upper()[:2]
	if not ("A" <= a <= "Z" and "A" <= b <= "Z"):
		return ""
	return chr(ord(a) + 127397) + chr(ord(b) + 127397)


def _unloco_route_leg_data(code):
	"""UN/LOCODE leg for route panel: code, subline (e.g. Kobe, Japan), flag emoji."""
	if not code:
		return {"code": "—", "sub": "", "flag": ""}
	row = (
		frappe.db.get_value(
			"UNLOCO",
			code,
			["location_name", "city", "country", "country_code"],
			as_dict=True,
		)
		or {}
	)
	city_part = (row.get("city") or "").strip() or (row.get("location_name") or "").strip()
	country = (row.get("country") or "").strip()
	if city_part and country:
		sub = f"{city_part}, {country}"
	elif country:
		sub = country
	else:
		sub = city_part
	cc = (row.get("country_code") or "").strip()
	return {
		"code": str(code),
		"sub": sub,
		"flag": _flag_emoji_from_country_code(cc),
	}


def _air_booking_route_leg_html(leg):
	flag = leg.get("flag") or ""
	flag_html = (
		f'<span class="log-ab-route-flag">{flag}</span>'
		if flag
		else '<span class="log-ab-route-flag log-ab-route-flag--empty" aria-hidden="true"></span>'
	)
	code_e = escape_html(leg.get("code") or "—")
	sub = leg.get("sub") or ""
	sub_html = (
		f'<span class="log-ab-route-sub">{escape_html(sub)}</span>' if sub else ""
	)
	return (
		f'<div class="log-ab-route-leg">'
		f"{flag_html}"
		f'<div class="log-ab-route-leg-text">'
		f'<span class="log-ab-route-code">{code_e}</span>'
		f"{sub_html}"
		f"</div></div>"
	)


def _air_booking_route_hero_html(doc, origin_attr="origin_port", destination_attr="destination_port"):
	"""Route row above meta: flag + code + city/country, arrow, same for destination."""
	o = getattr(doc, origin_attr, None)
	d = getattr(doc, destination_attr, None)
	leg_o = _unloco_route_leg_data(o)
	leg_d = _unloco_route_leg_data(d)
	return (
		f'<div class="log-ab-route-panel">'
		f"{_air_booking_route_leg_html(leg_o)}"
		f'<div class="log-ab-route-mid"><span class="log-ab-route-arrow-h">→</span></div>'
		f"{_air_booking_route_leg_html(leg_d)}"
		f"</div>"
	)


def _header_details_html(header_items):
	rows = []
	for label, value in header_items or []:
		if label in ("Origin", "Destination"):
			continue
		rows.append(
			f'<div class="header-item"><label>{escape_html(str(label))}:</label>'
			f"<span>{escape_html(str(value))}</span></div>"
		)
	return "".join(rows)


def _milestones_ro_panel_html(
	milestone_rows,
	milestone_details,
	docname,
	scroll_doctype="Air Booking",
	scroll_field="milestones",
	empty_hint_html=None,
):
	"""Repair Order–style job card: column headers + one row per milestone + footer."""
	if not milestone_rows:
		hint = (
			empty_hint_html
			or '<p class="text-muted ab-tab-empty" style="margin:0;">No milestones. Use <strong>Get Milestones</strong> in Actions to generate from template.</p>'
		)
		return f'<div class="log-ab-ro-card log-ab-ro-card--empty">{hint}</div>'
	head = """
			<div class="log-ab-jc-grid log-ab-jc-head">
				<div>Milestone</div>
				<div>Status</div>
				<div>Planned end</div>
				<div>Actual end</div>
				<div>#</div>
			</div>"""
	rows_html = []
	for i, m in enumerate(milestone_rows, 1):
		desc = milestone_details.get(m.milestone, m.milestone or "Milestone")
		planned = frappe.utils.format_datetime(m.planned_end) if m.planned_end else "—"
		actual = frappe.utils.format_datetime(m.actual_end) if m.actual_end else "—"
		st = m.status or "Planned"
		rows_html.append(
			f'<div class="log-ab-jc-grid log-ab-jc-row">'
			f'<div class="log-ab-jc-ms-title">{escape_html(desc)}</div>'
			f'<div class="log-ab-jc-status">{escape_html(st)}</div>'
			f'<div class="log-ab-jc-dt">{escape_html(str(planned))}</div>'
			f'<div class="log-ab-jc-dt">{escape_html(str(actual))}</div>'
			f'<div class="log-ab-jc-idx">{i}</div>'
			f"</div>"
		)
	n = len(milestone_rows)
	dt_js = json.dumps(scroll_doctype or "")
	fld_js = json.dumps(scroll_field or "milestones")
	# No docname in the handler: apostrophes in names break single-quoted onclick; double-quoted breaks on doctype.
	scroll_js = (
		"try{if(window.cur_frm&&cur_frm.doctype===" + dt_js + "&&cur_frm.doc&&"
		"cur_frm.scroll_to_field)cur_frm.scroll_to_field(" + fld_js + ");"
		"}catch(e){}return false;"
	)
	# Single-quoted onclick: JSON uses double quotes for JS strings; double-quoted onclick breaks on \"Air Booking\" etc.
	foot = f"""
			<div class="log-ab-jc-foot">
				<div class="log-ab-jc-foot-lbl">Your milestones ({n})</div>
				<div class="log-ab-jc-foot-title">Operational milestones</div>
				<a class="log-ab-text-link" href="#" onclick='{scroll_js}'>View details</a>
			</div>"""
	return f'<div class="log-ab-ro-card">{head}{"".join(rows_html)}{foot}</div>'


def render_air_booking_dashboard_html(doc):
	"""Full dashboard HTML for an Air Booking document (tabs, map, milestones, alerts)."""
	from logistics.document_management.logistics_form_dashboard import (
		build_air_booking_dashboard_config,
		render_logistics_form_dashboard_html,
	)

	return render_logistics_form_dashboard_html(doc, build_air_booking_dashboard_config(doc))
