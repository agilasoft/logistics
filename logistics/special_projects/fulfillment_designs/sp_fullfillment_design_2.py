"""sp_fullfillment_design_2 — ops-scan Fulfillment tab (image Alternative 1).

Layout:
  1. Horizontal lifecycle progress strip (per-stage counts / %)
  2. KPI row (Total / Delivered / In Progress / Delayed / Not Started) + next-actions alert
  3. Recent deliveries + filter panel
  4. Packages-at-a-glance table with actionable columns and warning tooltips

Fallback to ``sp_fullfillment_design_1`` via ``ACTIVE_FULFILLMENT_DESIGN``.
"""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, escape_html, flt, format_datetime, get_datetime, pretty_date

from logistics.special_projects.doctype.special_project.special_project import (
	_packages_fulfillment_empty_inner_html,
	_packages_fulfillment_wrap_html,
	_packages_summary_qty_label,
	_packages_summary_row_metrics,
)
from logistics.special_projects.special_project_packages import (
	POSTED_RECEIPT_STATUS,
	cint_safe,
	package_label,
)

_DESIGN_2_CSS = """
.sp-ff2 {
	width: 100%;
	box-sizing: border-box;
}
.sp-ff2-card {
	border: 1px solid #E5E7EB;
	border-radius: 12px;
	overflow: hidden;
	background: #fff;
	box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}
.sp-ff2-lifecycle {
	display: flex;
	align-items: stretch;
	gap: 0;
	overflow-x: auto;
	-webkit-overflow-scrolling: touch;
	padding: 12px 12px 0;
	margin: 0;
	background: transparent;
	border: none;
	border-radius: 0;
}
.sp-ff2-stage-wrap {
	display: flex;
	align-items: stretch;
	flex: 1 1 0;
	min-width: 128px;
	gap: 0;
}
.sp-ff2-stage-wrap:last-child { min-width: 118px; }
.sp-ff2-stage {
	flex: 1 1 auto;
	min-width: 0;
	display: flex;
	flex-direction: column;
	align-items: stretch;
	gap: 4px;
	padding: 10px 12px;
	border: 1px solid color-mix(in srgb, var(--sp-ff2-stage-color) 28%, #E5E7EB);
	border-radius: 10px;
	background: linear-gradient(
		180deg,
		color-mix(in srgb, var(--sp-ff2-stage-color) 12%, #ffffff),
		#ffffff
	);
	cursor: pointer;
	text-align: left;
	transition: box-shadow 0.12s ease, border-color 0.12s ease, transform 0.12s ease;
	--sp-ff2-stage-color: #6366F1;
}
.sp-ff2-stage:hover {
	box-shadow: 0 2px 8px color-mix(in srgb, var(--sp-ff2-stage-color) 18%, transparent);
}
.sp-ff2-stage.is-active,
.sp-ff2-stage.is-current {
	border-color: color-mix(in srgb, var(--sp-ff2-stage-color) 55%, #E5E7EB);
	box-shadow: 0 0 0 1px color-mix(in srgb, var(--sp-ff2-stage-color) 35%, transparent);
}
.sp-ff2-stage-label {
	font-size: 9px;
	font-weight: 700;
	text-transform: uppercase;
	letter-spacing: 0.06em;
	color: var(--sp-ff2-stage-color);
	line-height: 1.2;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.sp-ff2-stage-name {
	font-size: 13px;
	font-weight: 700;
	color: #111827;
	line-height: 1.2;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
	min-width: 0;
}
.sp-ff2-stage-meta {
	display: flex;
	align-items: baseline;
	gap: 4px;
	width: 100%;
	font-variant-numeric: tabular-nums;
	min-width: 0;
	margin-top: 2px;
}
.sp-ff2-stage-qty {
	font-size: 18px;
	font-weight: 800;
	color: #111827;
	line-height: 1;
}
.sp-ff2-stage-sep,
.sp-ff2-stage-req {
	font-size: 11px;
	font-weight: 600;
	color: #6B7280;
}
.sp-ff2-stage-pct {
	margin-left: auto;
	font-size: 12px;
	font-weight: 700;
	color: var(--sp-ff2-stage-color);
	white-space: nowrap;
}
.sp-ff2-stage-bar {
	margin-top: 4px;
	height: 6px;
	border-radius: 999px;
	background: color-mix(in srgb, var(--sp-ff2-stage-color) 14%, #F1F5F9);
	overflow: hidden;
}
.sp-ff2-stage-bar-fill {
	height: 100%;
	border-radius: 999px;
	background: linear-gradient(
		90deg,
		var(--sp-ff2-stage-color),
		color-mix(in srgb, var(--sp-ff2-stage-color) 40%, #10B981)
	);
	transition: width 0.35s ease;
}
.sp-ff2-stage-chevron {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	flex: 0 0 22px;
	width: 22px;
	color: #94A3B8;
	font-size: 22px;
	font-weight: 500;
	line-height: 1;
	user-select: none;
	align-self: center;
}
.sp-ff2-kpi-row {
	display: grid;
	grid-template-columns: repeat(5, minmax(0, 1fr)) minmax(180px, 1.1fr);
	gap: 10px;
	padding: 12px 14px;
	border-bottom: 1px solid #ECEEF1;
	background: #fff;
}
@media (max-width: 1100px) {
	.sp-ff2-kpi-row { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
.sp-ff2-kpi {
	border: 1px solid #E5E7EB;
	border-radius: 10px;
	padding: 10px 12px;
	background: #fff;
}
.sp-ff2-kpi-label {
	display: block;
	font-size: 10px;
	font-weight: 700;
	letter-spacing: 0.05em;
	text-transform: uppercase;
	color: #64748B;
	margin-bottom: 4px;
}
.sp-ff2-kpi-value {
	display: block;
	font-size: 22px;
	font-weight: 800;
	color: #0F172A;
	line-height: 1.1;
	font-variant-numeric: tabular-nums;
}
.sp-ff2-kpi-sub {
	display: block;
	margin-top: 4px;
	font-size: 11px;
	color: #94A3B8;
}
.sp-ff2-kpi--alert {
	border-color: #FDE68A;
	background: linear-gradient(180deg, #FFFBEB, #FFFFFF);
	display: flex;
	flex-direction: column;
	justify-content: center;
}
.sp-ff2-kpi--alert .sp-ff2-kpi-value { font-size: 14px; font-weight: 700; color: #92400E; }
.sp-ff2-kpi-link {
	margin-top: 6px;
	font-size: 12px;
	font-weight: 600;
	color: #2563EB;
	cursor: pointer;
	background: none;
	border: none;
	padding: 0;
	text-align: left;
}
.sp-ff2-kpi-link:hover { text-decoration: underline; }
.sp-ff2-mid {
	display: grid;
	grid-template-columns: minmax(0, 1.4fr) minmax(220px, 0.7fr);
	gap: 0;
	border-bottom: 1px solid #ECEEF1;
}
@media (max-width: 900px) {
	.sp-ff2-mid { grid-template-columns: 1fr; }
}
.sp-ff2-recent, .sp-ff2-filters {
	padding: 12px 14px;
	min-height: 120px;
}
.sp-ff2-recent { border-right: 1px solid #ECEEF1; }
.sp-ff2-section-title {
	font-size: 11px;
	font-weight: 800;
	letter-spacing: 0.06em;
	text-transform: uppercase;
	color: #334155;
	margin-bottom: 10px;
}
.sp-ff2-empty {
	display: flex;
	flex-direction: column;
	align-items: center;
	justify-content: center;
	gap: 8px;
	padding: 18px 12px;
	text-align: center;
	color: #64748B;
	font-size: 12px;
	background: #F8FAFC;
	border: 1px dashed #CBD5E1;
	border-radius: 10px;
}
.sp-ff2-empty-icon {
	width: 36px;
	height: 36px;
	border-radius: 10px;
	background: #E2E8F0;
	display: inline-flex;
	align-items: center;
	justify-content: center;
	color: #64748B;
	font-size: 16px;
}
.sp-ff2-delivery-list { display: flex; flex-direction: column; gap: 8px; }
.sp-ff2-delivery-row {
	display: grid;
	grid-template-columns: 1fr auto;
	gap: 8px;
	padding: 8px 10px;
	border: 1px solid #E5E7EB;
	border-radius: 8px;
	background: #fff;
}
.sp-ff2-delivery-main { min-width: 0; }
.sp-ff2-delivery-title {
	font-size: 12px;
	font-weight: 700;
	color: #0F172A;
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.sp-ff2-delivery-meta {
	font-size: 11px;
	color: #64748B;
	margin-top: 2px;
}
.sp-ff2-delivery-qty {
	font-size: 13px;
	font-weight: 800;
	color: #0F172A;
	font-variant-numeric: tabular-nums;
	align-self: center;
}
.sp-ff2-filter-group { margin-bottom: 10px; }
.sp-ff2-filter-label {
	display: block;
	font-size: 11px;
	font-weight: 600;
	color: #64748B;
	margin-bottom: 4px;
}
.sp-ff2-select {
	width: 100%;
	height: 30px;
	border: 1px solid #E5E7EB;
	border-radius: 8px;
	background: #fff;
	padding: 0 8px;
	font-size: 12px;
	color: #0F172A;
}
.sp-ff2-reset {
	margin-top: 4px;
	width: 100%;
	height: 30px;
	border: 1px solid #E5E7EB;
	border-radius: 8px;
	background: #F8FAFC;
	font-size: 12px;
	font-weight: 600;
	color: #334155;
	cursor: pointer;
}
.sp-ff2-reset:hover { background: #F1F5F9; }
.sp-ff2-packages { padding: 12px 14px 14px; }
.sp-ff2-packages-head {
	display: flex;
	align-items: baseline;
	justify-content: space-between;
	gap: 10px;
	margin-bottom: 10px;
}
.sp-ff2-table-wrap {
	overflow-x: auto;
	-webkit-overflow-scrolling: touch;
	border: 1px solid #E5E7EB;
	border-radius: 10px;
}
.sp-ff2-table {
	width: 100%;
	min-width: 1100px;
	border-collapse: collapse;
	font-size: 12px;
}
.sp-ff2-table th {
	text-align: left;
	padding: 8px 10px;
	background: #F8FAFC;
	color: #64748B;
	font-size: 10px;
	font-weight: 700;
	letter-spacing: 0.04em;
	text-transform: uppercase;
	border-bottom: 1px solid #E5E7EB;
	white-space: nowrap;
}
.sp-ff2-table td {
	padding: 9px 10px;
	border-bottom: 1px solid #F1F5F9;
	color: #0F172A;
	vertical-align: middle;
}
.sp-ff2-table tr:last-child td { border-bottom: none; }
.sp-ff2-num { font-variant-numeric: tabular-nums; color: #64748B; width: 36px; }
.sp-ff2-pkg { font-weight: 700; max-width: 160px; }
.sp-ff2-desc { color: #475569; max-width: 180px; }
.sp-ff2-ellipsis {
	white-space: nowrap;
	overflow: hidden;
	text-overflow: ellipsis;
}
.sp-ff2-stage-pill {
	display: inline-flex;
	align-items: center;
	gap: 4px;
	padding: 2px 8px;
	border-radius: 999px;
	background: #EEF2FF;
	color: #4338CA;
	font-size: 11px;
	font-weight: 700;
	white-space: nowrap;
}
.sp-ff2-status {
	display: inline-flex;
	align-items: center;
	gap: 6px;
	white-space: nowrap;
}
.sp-ff2-dot {
	width: 8px;
	height: 8px;
	border-radius: 50%;
	background: #94A3B8;
	flex: 0 0 auto;
}
.sp-ff2-dot--pending { background: #94A3B8; }
.sp-ff2-dot--in_progress { background: #3B82F6; }
.sp-ff2-dot--stalled, .sp-ff2-dot--delayed { background: #F59E0B; }
.sp-ff2-dot--complete { background: #10B981; }
.sp-ff2-dot--aa { background: #8B5CF6; }
.sp-ff2-action {
	color: #2563EB;
	font-weight: 600;
	background: none;
	border: none;
	padding: 0;
	cursor: pointer;
	font-size: 12px;
}
.sp-ff2-action:hover { text-decoration: underline; }
.sp-ff2-action.is-missing { color: #DC2626; }
.sp-ff2-warn {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	width: 18px;
	height: 18px;
	border-radius: 50%;
	font-size: 11px;
	font-weight: 800;
	line-height: 1;
	cursor: help;
	margin-right: 4px;
}
.sp-ff2-warn--missing { background: #FEE2E2; color: #DC2626; }
.sp-ff2-warn--nolink { background: #FFEDD5; color: #C2410C; }
.sp-ff2-warn--partial { background: #FEF3C7; color: #B45309; }
.sp-ff2-warn--overdue { background: #FEF3C7; color: #B45309; }
.sp-ff2-warn--awaiting { background: #DBEAFE; color: #1D4ED8; }
.sp-ff2-muted { color: #94A3B8; }
.sp-ff2-table tr.is-hidden,
.sp-ff2-table tr.is-page-hidden { display: none; }
.sp-ff2-footer {
	margin-top: 10px;
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 12px;
	flex-wrap: wrap;
	font-size: 12px;
}
.sp-ff2-paging {
	display: inline-flex;
	align-items: stretch;
	border: 1px solid #E5E7EB;
	border-radius: 8px;
	overflow: hidden;
	background: #F8FAFC;
}
.sp-ff2-paging-btn {
	appearance: none;
	border: none;
	border-right: 1px solid #E5E7EB;
	background: transparent;
	color: #334155;
	font-size: 12px;
	font-weight: 600;
	padding: 5px 12px;
	cursor: pointer;
	line-height: 1.2;
	min-width: 42px;
}
.sp-ff2-paging-btn:last-child { border-right: none; }
.sp-ff2-paging-btn:hover { background: #F1F5F9; }
.sp-ff2-paging-btn.is-active {
	background: #fff;
	color: #0F172A;
	box-shadow: inset 0 0 0 1px #CBD5E1;
}
.sp-ff2-footer-link {
	color: #2563EB;
	font-weight: 600;
	background: none;
	border: none;
	padding: 0;
	cursor: pointer;
	font-size: 12px;
}
.sp-ff2-footer-link:hover { text-decoration: underline; }
.sp-ff2-footer-link.is-expanded { color: #64748B; }
"""


def build_fulfillment_tab_html(doc: Any, ctx: dict[str, Any] | None) -> str:
	"""Ops-scan Fulfillment tab: lifecycle strip, KPIs, recent deliveries, packages table."""
	if not ctx or ctx.get("empty"):
		empty_key = (ctx or {}).get("empty") or "no_packages"
		return _packages_fulfillment_wrap_html(
			_packages_fulfillment_empty_inner_html(empty_key),
			outer_class="sp-packages-summary sp-packages-summary--design-2",
		)

	enriched = _enrich_design2_context(doc, ctx)
	inner = (
		f'<div class="sp-ff2" data-sp-fulfillment-panel="1" data-sp-fulfillment-design="sp_fullfillment_design_2">'
		f"<style>{_DESIGN_2_CSS}</style>"
		f'<div class="sp-ff2-card">'
		f"{_lifecycle_strip_html(enriched)}"
		f"{_kpi_row_html(enriched)}"
		f"{_mid_section_html(enriched)}"
		f"{_packages_table_html(enriched)}"
		f"</div></div>"
	)
	return _packages_fulfillment_wrap_html(
		inner,
		outer_class="sp-packages-summary sp-packages-summary--design-2",
	)


def _enrich_design2_context(doc: Any, ctx: dict[str, Any]) -> dict[str, Any]:
	from logistics.special_projects.doctype.special_project.special_project import (
		_packages_summary_last_receipt_by_material,
		_packages_summary_per_stage_delivered,
	)

	materials = list(ctx.get("materials") or [])
	stages = list(ctx.get("display_stages") or ctx.get("stages") or [])
	all_stages = list(ctx.get("stages") or [])
	per_stage = _packages_summary_per_stage_delivered(doc, materials, all_stages or stages)
	last_receipts = _packages_summary_last_receipt_by_material(doc, materials)
	linked_jobs = _latest_linked_job_by_material(doc, materials)

	final_idx: int | None = None
	for i, s in enumerate(all_stages or stages):
		if cint_safe(s.get("is_closed")):
			final_idx = i
	if final_idx is None and (all_stages or stages):
		final_idx = len(all_stages or stages) - 1

	rows: list[dict[str, Any]] = []
	owners: set[str] = set()
	for i, m in enumerate(materials):
		is_aa = bool(cint_safe(getattr(m, "include_on_create", 0)))
		qtys = per_stage[i] if i < len(per_stage) else []
		last_receipt = last_receipts[i] if i < len(last_receipts) else None
		metrics = (
			{}
			if is_aa
			else _packages_summary_row_metrics(
				m, qtys, all_stages or stages, final_idx, last_receipt, is_always_along=False
			)
		)
		status_key = "aa" if is_aa else metrics.get("status_key", "pending")
		status_label = _("Always-Along") if is_aa else metrics.get("status_label", _("Pending"))
		current_stage = _("Always-Along") if is_aa else metrics.get("current_stage") or _("Not started")
		component = (
			(getattr(m, "commodity", None) or getattr(m, "warehouse_item", None) or "")
			or package_label(m)
			or "—"
		)
		description = (getattr(m, "description", None) or "") or package_label(m) or "—"
		site = getattr(m, "site", None) or "—"
		hs = getattr(m, "hs_code", None) or ""
		commodity = getattr(m, "commodity", None) or ""
		commodity_label = commodity if not hs else f"{commodity} ({hs})" if commodity else hs
		linked = linked_jobs[i] if i < len(linked_jobs) else None
		next_action, next_action_missing = _next_action_for_row(
			status_key=status_key,
			current_stage=current_stage if not is_aa else "",
			has_linked_job=bool(linked and linked.get("job_no")),
			is_partial=bool(metrics.get("is_partial")),
		)
		updated = _relative_updated(last_receipt)
		warn = _warning_for_row(
			status_key=status_key,
			is_aa=is_aa,
			next_action_missing=next_action_missing,
			has_linked_job=bool(linked and linked.get("job_no")),
			is_partial=bool(metrics.get("is_partial")),
			delivered=flt(metrics.get("delivered", 0)),
			required=flt(getattr(m, "qty_required", 0)),
		)
		rows.append(
			{
				"row_no": i + 1,
				"is_aa": is_aa,
				"component": component,
				"description": description,
				"commodity": commodity_label or "—",
				"site": site,
				"required": flt(getattr(m, "qty_required", 0)),
				"delivered": flt(metrics.get("delivered", 0)) if not is_aa else None,
				"remaining": flt(metrics.get("remaining", 0)) if not is_aa else None,
				"current_stage": current_stage,
				"status_key": status_key,
				"status_label": status_label,
				"next_action": next_action,
				"next_action_missing": next_action_missing,
				"owner": "—",
				"linked_job": linked,
				"eta": "—",
				"updated": updated,
				"warn": warn,
			}
		)

	stage_stats = _stage_package_stats(
		rows,
		stages,
		ctx.get("current_stage") or "",
		stage_throughput=ctx.get("stage_throughput") or {},
		total_required=flt(ctx.get("total_required") or 0),
	)
	attention_count = sum(
		1
		for r in rows
		if not r["is_aa"] and r["status_key"] in ("pending", "stalled", "in_progress") and r.get("warn")
	)
	recent_deliveries = _recent_deliveries(doc, materials, limit=5)

	delayed_rows = sum(1 for r in rows if not r["is_aa"] and r["status_key"] == "stalled")
	not_started = sum(1 for r in rows if not r["is_aa"] and r["status_key"] == "pending")
	in_progress = sum(1 for r in rows if not r["is_aa"] and r["status_key"] in ("in_progress", "stalled"))
	delivered_rows = sum(1 for r in rows if not r["is_aa"] and r["status_key"] == "complete")
	tracked = sum(1 for r in rows if not r["is_aa"])

	return {
		**ctx,
		"rows": rows,
		"stage_stats": stage_stats,
		"attention_count": attention_count,
		"recent_deliveries": recent_deliveries,
		"owners": sorted(owners),
		"kpi": {
			"total": tracked,
			"delivered": delivered_rows,
			"in_progress": in_progress,
			"delayed": delayed_rows,
			"not_started": not_started,
		},
	}


def _stage_package_stats(
	rows: list[dict[str, Any]],
	stages: list[dict[str, Any]],
	current_stage: str,
	*,
	stage_throughput: dict[str, Any] | None = None,
	total_required: float = 0.0,
) -> list[dict[str, Any]]:
	tracked = [r for r in rows if not r["is_aa"]]
	not_started_labels = {_("Not started"), "Not started", ""}
	throughput = stage_throughput or {}
	stats: list[dict[str, Any]] = []
	for i, stage in enumerate(stages):
		name = (stage.get("name") or "").strip()
		# Packages currently sitting at this stage (or not-started on first stage).
		in_stage = 0
		done = 0
		for r in tracked:
			stage_name = (r.get("current_stage") or "").strip()
			if stage_name == name or (i == 0 and stage_name in not_started_labels):
				in_stage += 1
				if r.get("status_key") == "complete":
					done += 1
		# Denominator prefers packages currently in stage; fall back to tracked total for empty.
		denom = in_stage or (len(tracked) if name == (current_stage or "").strip() else 0)
		if denom == 0 and name == (current_stage or "").strip():
			denom = len(tracked)
		tp = throughput.get(name) or {}
		qty = flt(tp.get("qty", 0))
		req = flt(tp.get("required", total_required))
		if tp:
			pct = flt(tp.get("pct", 0))
		elif req > 0:
			pct = min(100.0, qty / req * 100.0)
		else:
			pct = 0.0 if denom <= 0 else min(100.0, done / denom * 100.0)
		raw_color = (stage.get("color") or "").strip()
		stats.append(
			{
				"name": name,
				"done": done,
				"total": denom if denom else in_stage,
				"in_stage": in_stage,
				"qty": qty,
				"required": req if req > 0 else flt(total_required),
				"pct": pct,
				"is_current": name == (current_stage or "").strip(),
				"color": raw_color or "#6366F1",
			}
		)
	# If every stage total is 0, show tracked count on the current (or first) stage.
	if tracked and all(s["total"] == 0 for s in stats):
		target = next((s for s in stats if s["is_current"]), stats[0] if stats else None)
		if target:
			target["total"] = len(tracked)
			target["in_stage"] = len(tracked)
	return stats


def _next_action_for_row(
	*,
	status_key: str,
	current_stage: str,
	has_linked_job: bool,
	is_partial: bool,
) -> tuple[str, bool]:
	if status_key == "aa":
		return (_("Always-along"), False)
	if status_key == "complete":
		return (_("Complete"), False)
	if not has_linked_job and status_key == "pending":
		stage = (current_stage or "").lower()
		if "sea" in stage or "port" in stage or "logistics" in stage:
			return (_("Create Sea Booking"), False)
		if "transport" in stage or "delivery" in stage:
			return (_("Plan Transport"), False)
		if "air" in stage:
			return (_("Create Air Booking"), False)
		return (_("Create Booking / Order"), False)
	if is_partial:
		return (_("View deliveries"), False)
	if status_key == "stalled":
		return (_("Escalate / update"), False)
	if has_linked_job:
		return (_("Track linked job"), False)
	return (_("Define next action"), True)


def _warning_for_row(
	*,
	status_key: str,
	is_aa: bool,
	next_action_missing: bool,
	has_linked_job: bool,
	is_partial: bool,
	delivered: float,
	required: float,
) -> dict[str, str] | None:
	if is_aa or status_key == "complete":
		return None
	if next_action_missing:
		return {
			"key": "missing",
			"icon": "×",
			"tip": _(
				"No next action is defined for this package. Create or link the next operational step."
			),
		}
	if not has_linked_job and status_key in ("pending", "in_progress", "stalled"):
		return {
			"key": "nolink",
			"icon": "!",
			"tip": _(
				"This package is not linked to any job or order. Create or link a job to track execution."
			),
		}
	if is_partial:
		return {
			"key": "partial",
			"icon": "|",
			"tip": _(
				"Partial delivery recorded. {0} of {1} delivered. View deliveries to see details."
			).format(
				_packages_summary_qty_label(delivered),
				_packages_summary_qty_label(required),
			),
		}
	if status_key == "pending":
		return {
			"key": "awaiting",
			"icon": "i",
			"tip": _(
				"Delivered qty updates only when an execution job is submitted (Shipment / Transport / Project Job)."
			),
		}
	return None


def _relative_updated(last_receipt: Any) -> str:
	if not last_receipt:
		return "—"
	try:
		return pretty_date(get_datetime(last_receipt))
	except Exception:
		try:
			return format_datetime(last_receipt)
		except Exception:
			return str(last_receipt)


def _latest_linked_job_by_material(doc: Any, materials: list) -> list[dict[str, Any] | None]:
	out: list[dict[str, Any] | None] = [None] * len(materials)
	idx_to_pos = {i + 1: i for i in range(len(materials))}
	for rc in getattr(doc, "deliveries", None) or []:
		status = getattr(rc, "status", None) or POSTED_RECEIPT_STATUS
		if status != POSTED_RECEIPT_STATUS:
			continue
		job_type = getattr(rc, "source_job_type", None) or ""
		job_no = getattr(rc, "source_job_no", None) or ""
		if not job_no:
			continue
		row_idx = cint_safe(getattr(rc, "package_row", None))
		pos = idx_to_pos.get(row_idx)
		if pos is None:
			continue
		out[pos] = {"job_type": job_type, "job_no": job_no}
	return out


def _recent_deliveries(doc: Any, materials: list, *, limit: int = 5) -> list[dict[str, Any]]:
	idx_to_mat = {i + 1: m for i, m in enumerate(materials)}
	items: list[dict[str, Any]] = []
	for rc in getattr(doc, "deliveries", None) or []:
		status = getattr(rc, "status", None) or POSTED_RECEIPT_STATUS
		if status != POSTED_RECEIPT_STATUS:
			continue
		qty = flt(getattr(rc, "qty_received", 0))
		if qty <= 0:
			continue
		row_idx = cint_safe(getattr(rc, "package_row", None))
		mat = idx_to_mat.get(row_idx)
		label = package_label(mat) if mat is not None else (getattr(rc, "description", None) or "—")
		job_type = getattr(rc, "source_job_type", None) or ""
		job_no = getattr(rc, "source_job_no", None) or ""
		stage = getattr(rc, "lifecycle_stage", None) or ""
		receipt_date = getattr(rc, "receipt_date", None)
		items.append(
			{
				"label": label,
				"qty": qty,
				"job": f"{job_type} {job_no}".strip() or "—",
				"stage": stage or "—",
				"when": _relative_updated(receipt_date),
				"sort": str(receipt_date or ""),
			}
		)
	items.sort(key=lambda x: x["sort"], reverse=True)
	return items[:limit]


def _lifecycle_strip_html(ctx: dict[str, Any]) -> str:
	stages = ctx.get("stage_stats") or []
	if not stages:
		return ""
	parts: list[str] = []
	for i, s in enumerate(stages, start=1):
		name = escape_html(s["name"])
		color = escape_html((s.get("color") or "#6366F1").strip() or "#6366F1")
		active = " is-active is-current" if s.get("is_current") else ""
		if not s.get("is_current") and i == 1 and not any(x.get("is_current") for x in stages):
			active = " is-active"
		qty = _packages_summary_qty_label(flt(s.get("qty", 0)))
		req = _packages_summary_qty_label(flt(s.get("required", 0)))
		pct_val = flt(s.get("pct", 0))
		pct = f"{pct_val:.0f}%"
		label = escape_html(_("Stage throughput"))
		chevron = (
			'<span class="sp-ff2-stage-chevron" aria-hidden="true">&rsaquo;</span>'
			if i < len(stages)
			else ""
		)
		parts.append(
			f'<div class="sp-ff2-stage-wrap">'
			f'<button type="button" class="sp-ff2-stage{active}" data-ff2-stage="{name}" '
			f'style="--sp-ff2-stage-color:{color}" title="{name}">'
			f'<span class="sp-ff2-stage-label">{label}</span>'
			f'<span class="sp-ff2-stage-name">{name}</span>'
			f'<span class="sp-ff2-stage-meta">'
			f'<span class="sp-ff2-stage-qty">{escape_html(qty)}</span>'
			f'<span class="sp-ff2-stage-sep">/</span>'
			f'<span class="sp-ff2-stage-req">{escape_html(req)}</span>'
			f'<span class="sp-ff2-stage-pct">{escape_html(pct)}</span>'
			f"</span>"
			f'<span class="sp-ff2-stage-bar">'
			f'<span class="sp-ff2-stage-bar-fill" style="width:{pct_val:.2f}%"></span>'
			f"</span>"
			f"</button>"
			f"{chevron}"
			f"</div>"
		)
	return f'<div class="sp-ff2-lifecycle" role="list">{"".join(parts)}</div>'


def _kpi_row_html(ctx: dict[str, Any]) -> str:
	kpi = ctx.get("kpi") or {}
	total = cint(kpi.get("total", 0))
	delivered = cint(kpi.get("delivered", 0))
	in_progress = cint(kpi.get("in_progress", 0))
	delayed = cint(kpi.get("delayed", 0))
	not_started = cint(kpi.get("not_started", 0))

	def _pct(n: int) -> str:
		if total <= 0:
			return "—"
		return f"{min(100.0, n / total * 100.0):.0f}%"

	attention = cint(ctx.get("attention_count", 0))
	if attention:
		alert = (
			f'<div class="sp-ff2-kpi sp-ff2-kpi--alert">'
			f'<span class="sp-ff2-kpi-label">{escape_html(_("Next actions"))}</span>'
			f'<span class="sp-ff2-kpi-value">'
			f'{escape_html(_("You have {0} items requiring action.").format(attention))}'
			f"</span>"
			f'<button type="button" class="sp-ff2-kpi-link" data-ff2-scroll-packages="1">'
			f'{escape_html(_("View next actions →"))}</button>'
			f"</div>"
		)
	else:
		alert = (
			f'<div class="sp-ff2-kpi sp-ff2-kpi--alert">'
			f'<span class="sp-ff2-kpi-label">{escape_html(_("Next actions"))}</span>'
			f'<span class="sp-ff2-kpi-value">{escape_html(_("No actions pending"))}</span>'
			f"</div>"
		)

	cards = [
		(_("Total Packages"), total, ""),
		(_("Delivered"), delivered, _pct(delivered)),
		(_("In Progress"), in_progress, _pct(in_progress)),
		(_("Delayed"), delayed, _pct(delayed)),
		(_("Not Started"), not_started, _pct(not_started)),
	]
	html = []
	for label, value, sub in cards:
		sub_html = f'<span class="sp-ff2-kpi-sub">{escape_html(sub)}</span>' if sub else ""
		html.append(
			f'<div class="sp-ff2-kpi">'
			f'<span class="sp-ff2-kpi-label">{escape_html(label)}</span>'
			f'<span class="sp-ff2-kpi-value">{value}</span>'
			f"{sub_html}"
			f"</div>"
		)
	return f'<div class="sp-ff2-kpi-row">{"".join(html)}{alert}</div>'


def _mid_section_html(ctx: dict[str, Any]) -> str:
	return (
		f'<div class="sp-ff2-mid">'
		f"{_recent_deliveries_html(ctx)}"
		f"{_filters_html(ctx)}"
		f"</div>"
	)


def _recent_deliveries_html(ctx: dict[str, Any]) -> str:
	items = ctx.get("recent_deliveries") or []
	title = escape_html(_("Recent Deliveries"))
	if not items:
		body = (
			f'<div class="sp-ff2-empty">'
			f'<span class="sp-ff2-empty-icon" aria-hidden="true">▣</span>'
			f'<span>{escape_html(_("No deliveries yet. Delivered quantities update when execution jobs are submitted."))}</span>'
			f"</div>"
		)
	else:
		rows = []
		for it in items:
			rows.append(
				f'<div class="sp-ff2-delivery-row">'
				f'<div class="sp-ff2-delivery-main">'
				f'<div class="sp-ff2-delivery-title" title="{escape_html(it["label"])}">{escape_html(it["label"])}</div>'
				f'<div class="sp-ff2-delivery-meta">'
				f'{escape_html(it["job"])} · {escape_html(it["stage"])} · {escape_html(it["when"])}'
				f"</div></div>"
				f'<div class="sp-ff2-delivery-qty">+{_packages_summary_qty_label(it["qty"])}</div>'
				f"</div>"
			)
		body = f'<div class="sp-ff2-delivery-list">{"".join(rows)}</div>'
	return f'<div class="sp-ff2-recent"><div class="sp-ff2-section-title">{title}</div>{body}</div>'


def _filters_html(ctx: dict[str, Any]) -> str:
	stages = [s.get("name") for s in (ctx.get("display_stages") or ctx.get("stages") or []) if s.get("name")]
	status_opts = [
		("all", _("All statuses")),
		("pending", _("Not Started")),
		("in_progress", _("In Progress")),
		("stalled", _("Delayed")),
		("complete", _("Delivered")),
	]
	stage_opts = "".join(
		f'<option value="{escape_html(s)}">{escape_html(s)}</option>' for s in stages
	)
	status_html = "".join(
		f'<option value="{escape_html(k)}">{escape_html(lbl)}</option>' for k, lbl in status_opts
	)
	return (
		f'<div class="sp-ff2-filters">'
		f'<div class="sp-ff2-section-title">{escape_html(_("Filters"))}</div>'
		f'<div class="sp-ff2-filter-group">'
		f'<label class="sp-ff2-filter-label">{escape_html(_("Lifecycle Stage"))}</label>'
		f'<select class="sp-ff2-select" data-ff2-filter="stage">'
		f'<option value="">{escape_html(_("All stages"))}</option>{stage_opts}</select>'
		f"</div>"
		f'<div class="sp-ff2-filter-group">'
		f'<label class="sp-ff2-filter-label">{escape_html(_("Status"))}</label>'
		f'<select class="sp-ff2-select" data-ff2-filter="status">{status_html}</select>'
		f"</div>"
		f'<button type="button" class="sp-ff2-reset" data-ff2-reset="1">{escape_html(_("Reset Filters"))}</button>'
		f"</div>"
	)


def _packages_table_html(ctx: dict[str, Any]) -> str:
	rows = ctx.get("rows") or []
	tracked = sum(1 for r in rows if not r.get("is_aa"))
	title = escape_html(_("Packages at a glance ({0})").format(tracked))
	headers = [
		_("No."),
		_("Package / Component"),
		_("Item / Description"),
		_("Commodity (HS)"),
		_("Site"),
		_("Req."),
		_("Delivered"),
		_("Remaining"),
		_("Stage"),
		_("Status"),
		_("Next Action"),
		_("Owner"),
		_("Linked Job / Order"),
		_("ETA"),
		_("Updated"),
	]
	head = "".join(f"<th>{escape_html(h)}</th>" for h in headers)
	body_rows = []
	for r in rows:
		warn = r.get("warn")
		warn_html = ""
		if warn:
			warn_html = (
				f'<span class="sp-ff2-warn sp-ff2-warn--{escape_html(warn["key"])}" '
				f'title="{escape_html(warn["tip"])}">{escape_html(warn["icon"])}</span>'
			)
		delivered = "—" if r["delivered"] is None else _packages_summary_qty_label(r["delivered"])
		remaining = "—" if r["remaining"] is None else _packages_summary_qty_label(r["remaining"])
		linked = r.get("linked_job") or {}
		linked_label = linked.get("job_no") or "—"
		linked_html = (
			f'<span class="sp-ff2-muted">—</span>'
			if linked_label == "—"
			else f'<span title="{escape_html((linked.get("job_type") or "") + " " + linked_label)}">'
			f"{escape_html(linked_label)}</span>"
		)
		action_cls = "sp-ff2-action is-missing" if r.get("next_action_missing") else "sp-ff2-action"
		status_key = escape_html(r["status_key"])
		body_rows.append(
			f'<tr class="sp-ff2-pkg-row" data-status="{status_key}" data-row-index="{r["row_no"]}" '
			f'data-lifecycle-stage="{escape_html(r["current_stage"])}" data-owner="">'
			f'<td class="sp-ff2-num">{r["row_no"]}</td>'
			f'<td class="sp-ff2-pkg"><div class="sp-ff2-ellipsis" title="{escape_html(r["component"])}">'
			f'{warn_html}{escape_html(r["component"])}</div></td>'
			f'<td class="sp-ff2-desc"><div class="sp-ff2-ellipsis" title="{escape_html(r["description"])}">'
			f'{escape_html(r["description"])}</div></td>'
			f'<td><div class="sp-ff2-ellipsis" title="{escape_html(r["commodity"])}">{escape_html(r["commodity"])}</div></td>'
			f'<td><div class="sp-ff2-ellipsis" title="{escape_html(str(r["site"]))}">{escape_html(str(r["site"]))}</div></td>'
			f'<td>{_packages_summary_qty_label(r["required"])}</td>'
			f"<td>{delivered}</td>"
			f"<td>{remaining}</td>"
			f'<td><span class="sp-ff2-stage-pill">{escape_html(r["current_stage"])}</span></td>'
			f'<td><span class="sp-ff2-status"><span class="sp-ff2-dot sp-ff2-dot--{status_key}"></span>'
			f'{escape_html(r["status_label"])}</span></td>'
			f'<td><button type="button" class="{action_cls}">{escape_html(r["next_action"])}</button></td>'
			f'<td class="sp-ff2-muted">{escape_html(r["owner"])}</td>'
			f"<td>{linked_html}</td>"
			f'<td class="sp-ff2-muted">{escape_html(r["eta"])}</td>'
			f'<td class="sp-ff2-muted">{escape_html(r["updated"])}</td>'
			f"</tr>"
		)

	total_rows = len(rows)
	default_page = 20
	paging_btns = "".join(
		f'<button type="button" class="sp-ff2-paging-btn{" is-active" if n == default_page else ""}" '
		f'data-ff2-page-size="{n}">{n}</button>'
		for n in (20, 100, 500, 2500)
	)
	footer = (
		f'<div class="sp-ff2-footer" data-ff2-total-rows="{total_rows}">'
		f'<div class="sp-ff2-paging" role="group" aria-label="{escape_html(_("Rows per page"))}">'
		f"{paging_btns}"
		f"</div>"
		f'<button type="button" class="sp-ff2-footer-link" data-ff2-show-all="1" '
		f'data-ff2-show-label="{escape_html(_("Show all {0} packages").format(total_rows))}" '
		f'data-ff2-hide-label="{escape_html(_("Hide all"))}">'
		f'{escape_html(_("Show all {0} packages").format(total_rows))}</button>'
		f"</div>"
	)
	return (
		f'<div class="sp-ff2-packages" id="sp-ff2-packages" data-ff2-page-size="{default_page}">'
		f'<div class="sp-ff2-packages-head"><div class="sp-ff2-section-title">{title}</div></div>'
		f'<div class="sp-ff2-table-wrap"><table class="sp-ff2-table">'
		f"<thead><tr>{head}</tr></thead>"
		f'<tbody>{"".join(body_rows)}</tbody>'
		f"</table></div>{footer}</div>"
	)
