# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Opportunity value attainment dashboard payload and HTML."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import escape_html, flt, fmt_money, formatdate, today

from logistics.pricing_center.utils.opportunity_scopes import (
	get_customer_service_ytd_profitability,
	get_scope_ytd_profitability,
	resolve_opportunity_company,
	resolve_opportunity_customer,
)

DASH_ROOT = "log-opp-dash"

DASH_CSS = """
.{root} {{ font-family: var(--font-stack); color: var(--text-color); min-height: 120px; box-sizing: border-box; width: 100%; padding: 16px 28px 32px; }}
@media (max-width: 767px) {{ .{root} {{ padding: 12px 16px 24px; }} }}
.{root}__header {{ display:flex; justify-content:space-between; align-items:flex-start; gap:20px; flex-wrap:wrap; margin-bottom:22px; padding-bottom:4px; }}
.{root}__title {{ font-size:16px; font-weight:600; margin:0 0 6px; }}
.{root}__subtitle {{ font-size:12px; color: var(--text-muted); margin:0; line-height:1.45; }}
.{root}__toggle {{ display:inline-flex; background: var(--control-bg); border:1px solid var(--border-color); border-radius:999px; padding:3px; flex-shrink:0; }}
.{root}__toggle button {{ border:0; background:transparent; padding:6px 14px; border-radius:999px; font-size:12px; font-weight:600; cursor:pointer; color: var(--text-muted); }}
.{root}__toggle button.is-active {{ background: var(--fg-color); color: var(--text-color); box-shadow: 0 1px 2px rgba(0,0,0,.08); }}
.{root}__grid {{ display:grid; grid-template-columns: minmax(260px, 360px) 1fr; gap:20px; margin-bottom:20px; }}
@media (max-width: 991px) {{ .{root}__grid {{ grid-template-columns: 1fr; }} }}
.{root}__card {{ background: var(--card-bg); border:1px solid var(--border-color); border-radius:12px; padding:20px; box-shadow: 0 1px 2px rgba(15,23,42,.04); }}
.{root}__hero {{ display:flex; gap:18px; align-items:center; }}
.{root}__ring {{ width:96px; height:96px; transform: rotate(-90deg); flex-shrink:0; }}
.{root}__ring-bg {{ fill:none; stroke: var(--gray-200, #e5e7eb); stroke-width:8; }}
.{root}__ring-fg {{ fill:none; stroke-width:8; stroke-linecap:round; }}
.{root}__ring-text {{ transform: rotate(90deg); transform-origin: 50% 50%; font-size:16px; font-weight:700; fill: var(--text-color); text-anchor:middle; dominant-baseline:middle; }}
.{root}__kpi-label {{ font-size:11px; text-transform:uppercase; letter-spacing:.04em; color: var(--text-muted); margin-bottom:6px; }}
.{root}__kpi-value {{ font-size:22px; font-weight:700; line-height:1.2; }}
.{root}__kpi-sub {{ font-size:12px; color: var(--text-muted); margin-top:8px; line-height:1.45; }}
.{root}__badge {{ display:inline-block; padding:2px 8px; border-radius:999px; font-size:11px; font-weight:600; }}
.{root}__badge.is-success {{ background:#dcfce7; color:#166534; }}
.{root}__badge.is-warning {{ background:#fef3c7; color:#92400e; }}
.{root}__badge.is-danger {{ background:#fee2e2; color:#991b1b; }}
.{root}__services {{ display:grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap:16px; margin-bottom:20px; }}
.{root}__service-title {{ font-size:13px; font-weight:700; margin:0 0 8px; }}
.{root}__service-meta {{ font-size:11px; color: var(--text-muted); margin-bottom:12px; line-height:1.45; }}
.{root}__bar-row {{ margin-bottom:12px; }}
.{root}__bar-row:last-child {{ margin-bottom:0; }}
.{root}__bar-head {{ display:flex; justify-content:space-between; gap:8px; font-size:11px; margin-bottom:5px; color: var(--text-muted); }}
.{root}__bar-track {{ height:8px; border-radius:999px; background: var(--gray-200, #e5e7eb); overflow:hidden; }}
.{root}__bar-fill {{ height:100%; border-radius:999px; background: linear-gradient(90deg, #3b82f6, #6366f1); }}
.{root}__scopes {{ margin-top:4px; }}
.{root}__scopes h4 {{ font-size:13px; font-weight:700; margin:0 0 12px; }}
.{root}__table-wrap {{ overflow-x:auto; margin:0 -4px; padding:0 4px; }}
.{root} table {{ width:100%; border-collapse:collapse; font-size:12px; min-width:720px; }}
.{root} th, .{root} td {{ padding:10px 12px; border-bottom:1px solid var(--border-color); text-align:left; vertical-align:middle; }}
.{root} th:first-child, .{root} td:first-child {{ padding-left:4px; }}
.{root} th:last-child, .{root} td:last-child {{ padding-right:4px; }}
.{root} th {{ color: var(--text-muted); font-weight:600; white-space:nowrap; }}
.{root} tbody tr:last-child td {{ border-bottom:0; }}
.{root}__empty {{ padding:28px 20px; text-align:center; color: var(--text-muted); background: var(--control-bg); border-radius:12px; }}
""".format(root=DASH_ROOT)


def get_default_dashboard_metric() -> str:
	metric = (
		frappe.db.get_single_value("CRM Settings", "custom_opportunity_dashboard_default_metric") or "Revenue"
	).strip()
	return metric if metric in ("Revenue", "Profit") else "Revenue"


def _attainment_pct(actual: float, target: float) -> float:
	if not target:
		return 0.0
	return flt(flt(actual) / flt(target) * 100.0, 1)


def _metric_row(target: float, actual_revenue: float, actual_profit: float) -> dict[str, float]:
	return {
		"target": flt(target),
		"actual_revenue": flt(actual_revenue),
		"actual_profit": flt(actual_profit),
		"revenue_attainment_pct": _attainment_pct(actual_revenue, target),
		"profit_attainment_pct": _attainment_pct(actual_profit, target),
		"revenue_gap": flt(target) - flt(actual_revenue),
		"profit_gap": flt(target) - flt(actual_profit),
	}


def _scope_lane_fields(row: Any) -> dict[str, str]:
	"""Origin, destination, and load type labels for dashboard / detail views."""
	service_type = (getattr(row, "service_type", None) or "").strip()
	if service_type == "Transport":
		origin = (getattr(row, "location_from", None) or "").strip()
		destination = (getattr(row, "location_to", None) or "").strip()
	else:
		origin = (getattr(row, "origin_port", None) or "").strip()
		destination = (getattr(row, "destination_port", None) or "").strip()
	return {
		"origin": origin,
		"destination": destination,
		"load_type": (getattr(row, "load_type", None) or "").strip(),
	}


def build_opportunity_dashboard_payload(doc: Any) -> dict[str, Any]:
	"""Overall and per-service annual target vs YTD actuals for the Opportunity dashboard."""
	scopes = getattr(doc, "custom_opportunity_scopes", None) or []
	customer = resolve_opportunity_customer(doc)
	company = resolve_opportunity_company(doc)
	currency = (getattr(doc, "currency", None) or "").strip()
	if not currency and company:
		currency = frappe.get_cached_value("Company", company, "default_currency") or ""

	fiscal_label = _fiscal_year_label(company)

	service_targets: dict[str, float] = defaultdict(float)
	scope_rows: list[dict[str, Any]] = []
	for row in scopes:
		service_type = (getattr(row, "service_type", None) or "").strip() or _("Unspecified")
		target = flt(getattr(row, "opportunity_value", 0))
		service_targets[service_type] += target
		actuals = get_scope_ytd_profitability(row, doc)
		metrics = _metric_row(target, actuals.get("revenue", 0), actuals.get("gross_profit", 0))
		scope_rows.append(
			{
				"name": getattr(row, "name", None),
				"scope_title": (getattr(row, "scope_title", None) or "").strip() or service_type,
				"service_type": service_type,
				**_scope_lane_fields(row),
				**metrics,
			}
		)

	total_target = flt(sum(service_targets.values()))
	overall_actuals = get_customer_service_ytd_profitability(customer, company, None)
	overall = _metric_row(
		total_target,
		overall_actuals.get("revenue", 0),
		overall_actuals.get("gross_profit", 0),
	)

	services: list[dict[str, Any]] = []
	for service_type in sorted(service_targets.keys(), key=lambda s: service_targets[s], reverse=True):
		target = flt(service_targets[service_type])
		actuals = get_customer_service_ytd_profitability(customer, company, service_type)
		services.append(
			{
				"service_type": service_type,
				"scope_count": sum(1 for r in scope_rows if r["service_type"] == service_type),
				**_metric_row(target, actuals.get("revenue", 0), actuals.get("gross_profit", 0)),
			}
		)

	return {
		"currency": currency,
		"customer": customer,
		"company": company,
		"fiscal_label": fiscal_label,
		"default_metric": get_default_dashboard_metric(),
		"has_scopes": bool(scopes),
		"overall": overall,
		"services": services,
		"scopes": scope_rows,
	}


def _fiscal_year_label(company: str | None) -> str:
	try:
		from erpnext.accounts.utils import get_fiscal_year

		fy = get_fiscal_year(today(), company=company, raise_on_missing=False)
		if fy:
			return _("FY {0} YTD ({1})").format(fy[0], formatdate(today()))
	except Exception:
		pass
	return _("YTD ({0})").format(formatdate(today()))


def _format_money(value: float, currency: str | None) -> str:
	return fmt_money(flt(value), currency=currency or None)


def _attainment_class(pct: float) -> str:
	if pct >= 100:
		return "is-success"
	if pct >= 70:
		return "is-warning"
	return "is-danger"


def _metric_values(row: dict[str, Any], metric: str) -> dict[str, Any]:
	if metric == "Profit":
		return {
			"actual": row.get("actual_profit", 0),
			"pct": row.get("profit_attainment_pct", 0),
			"label": _("Actual Profit (YTD)"),
		}
	return {
		"actual": row.get("actual_revenue", 0),
		"pct": row.get("revenue_attainment_pct", 0),
		"label": _("Actual Revenue (YTD)"),
	}


def _progress_svg(pct: float, metric: str) -> str:
	safe = max(0.0, min(flt(pct), 100.0))
	stroke = "#10b981" if metric == "Profit" else "#3b82f6"
	r = 42
	c = 2 * 3.14159265 * r
	offset = c - (safe / 100.0) * c
	return (
		f'<svg class="{DASH_ROOT}__ring" viewBox="0 0 100 100" aria-hidden="true">'
		f'<circle cx="50" cy="50" r="{r}" class="{DASH_ROOT}__ring-bg"></circle>'
		f'<circle cx="50" cy="50" r="{r}" class="{DASH_ROOT}__ring-fg" stroke="{stroke}"'
		f' stroke-dasharray="{c}" stroke-dashoffset="{offset}"></circle>'
		f'<text x="50" y="50" class="{DASH_ROOT}__ring-text">{safe:g}%</text>'
		f"</svg>"
	)


def _bar_row(label: str, target: float, actual: float, currency: str | None) -> str:
	pct = min((flt(actual) / flt(target)) * 100.0, 100.0) if target else 0.0
	return (
		f'<div class="{DASH_ROOT}__bar-row">'
		f'<div class="{DASH_ROOT}__bar-head">'
		f"<span>{escape_html(label)}</span>"
		f"<span>{_format_money(actual, currency)} / {_format_money(target, currency)}</span>"
		f"</div>"
		f'<div class="{DASH_ROOT}__bar-track">'
		f'<div class="{DASH_ROOT}__bar-fill" style="width:{pct:g}%"></div>'
		f"</div></div>"
	)


def _empty_html(message: str) -> str:
	return (
		f'<style>{DASH_CSS}</style>'
		f'<div class="{DASH_ROOT}"><div class="{DASH_ROOT}__empty">{escape_html(message)}</div></div>'
	)


def render_opportunity_dashboard_html(payload: dict[str, Any], metric: str | None = None) -> str:
	"""Render dashboard cards HTML for the Opportunity form."""
	metric = metric if metric in ("Revenue", "Profit") else (payload.get("default_metric") or "Revenue")
	if not payload.get("has_scopes"):
		return _empty_html(_("Add scopes on the Services tab with annual opportunity values to see attainment."))

	currency = payload.get("currency")
	overall = payload.get("overall") or {}
	mv = _metric_values(overall, metric)
	badge_class = _attainment_class(flt(mv["pct"]))

	subtitle = payload.get("fiscal_label") or ""
	if payload.get("customer"):
		subtitle = f"{subtitle} · {payload['customer']}" if subtitle else payload["customer"]

	service_cards = []
	for svc in payload.get("services") or []:
		sm = _metric_values(svc, metric)
		svc_badge = _attainment_class(flt(sm["pct"]))
		service_cards.append(
			f'<div class="{DASH_ROOT}__card">'
			f'<div class="{DASH_ROOT}__service-title">{escape_html(svc.get("service_type") or "")}</div>'
			f'<div class="{DASH_ROOT}__service-meta">'
			f'{_("{0} scope(s)").format(svc.get("scope_count") or 0)} · '
			f'{_format_money(svc.get("target", 0), currency)} {_(_("annual"))}'
			f"</div>"
			f'<div class="{DASH_ROOT}__kpi-value">{_format_money(sm["actual"], currency)}</div>'
			f'<div class="{DASH_ROOT}__kpi-sub">{escape_html(sm["label"])}</div>'
			f'<div style="margin-top:10px"><span class="{DASH_ROOT}__badge {svc_badge}">'
			f'{sm["pct"]:g}% {_(_("attainment"))}</span></div>'
			f'{_bar_row(_("Progress"), svc.get("target", 0), sm["actual"], currency)}'
			f"</div>"
		)

	scope_rows = []
	for row in payload.get("scopes") or []:
		sm = _metric_values(row, metric)
		row_badge = _attainment_class(flt(sm["pct"]))
		scope_rows.append(
			"<tr>"
			f"<td>{escape_html(row.get('scope_title') or '')}</td>"
			f"<td>{escape_html(row.get('service_type') or '')}</td>"
			f"<td>{escape_html(row.get('origin') or '')}</td>"
			f"<td>{escape_html(row.get('destination') or '')}</td>"
			f"<td>{escape_html(row.get('load_type') or '')}</td>"
			f"<td>{_format_money(row.get('target', 0), currency)}</td>"
			f"<td>{_format_money(sm['actual'], currency)}</td>"
			f'<td><span class="{DASH_ROOT}__badge {row_badge}">{sm["pct"]:g}%</span></td>'
			"</tr>"
		)

	bars = "".join(
		_bar_row(svc.get("service_type") or "", svc.get("target", 0), _metric_values(svc, metric)["actual"], currency)
		for svc in (payload.get("services") or [])
	)

	scopes_table = ""
	if scope_rows:
		scopes_table = (
			f'<div class="{DASH_ROOT}__scopes {DASH_ROOT}__card"><h4>{_("Scope / Services Detail")}</h4>'
			f'<div class="{DASH_ROOT}__table-wrap"><table><thead><tr>'
			f"<th>{_('Scope')}</th><th>{_('Service')}</th><th>{_('Origin')}</th><th>{_('Destination')}</th>"
			f"<th>{_('Load Type')}</th><th>{_('Annual Target')}</th>"
			f"<th>{_('YTD Actual')}</th><th>{_('Attainment')}</th>"
			f"</tr></thead><tbody>{''.join(scope_rows)}</tbody></table></div></div>"
		)

	revenue_active = "is-active" if metric == "Revenue" else ""
	profit_active = "is-active" if metric == "Profit" else ""

	return (
		f"<style>{DASH_CSS}</style>"
		f'<div class="{DASH_ROOT}" data-metric="{escape_html(metric)}">'
		f'<div class="{DASH_ROOT}__header">'
		f"<div>"
		f'<p class="{DASH_ROOT}__title">{_("Opportunity Value Attainment")}</p>'
		f'<p class="{DASH_ROOT}__subtitle">{escape_html(subtitle)}</p>'
		f"</div>"
		f'<div class="{DASH_ROOT}__toggle" role="tablist">'
		f'<button type="button" class="{revenue_active}" data-metric="Revenue">{_("Revenue")}</button>'
		f'<button type="button" class="{profit_active}" data-metric="Profit">{_("Profit")}</button>'
		f"</div></div>"
		f'<div class="{DASH_ROOT}__grid">'
		f'<div class="{DASH_ROOT}__card"><div class="{DASH_ROOT}__hero">'
		f"{_progress_svg(flt(mv['pct']), metric)}"
		f"<div>"
		f'<div class="{DASH_ROOT}__kpi-label">{_("Overall Annual Target")}</div>'
		f'<div class="{DASH_ROOT}__kpi-value">{_format_money(overall.get("target", 0), currency)}</div>'
		f'<div class="{DASH_ROOT}__kpi-sub">{escape_html(mv["label"])}: {_format_money(mv["actual"], currency)}</div>'
		f'<div style="margin-top:8px"><span class="{DASH_ROOT}__badge {badge_class}">'
		f'{mv["pct"]:g}% {_(_("attainment"))}</span></div>'
		f"</div></div></div>"
		f'<div class="{DASH_ROOT}__card"><div class="{DASH_ROOT}__kpi-label">{_("By Service")}</div>'
		f"{bars or _empty_html(_('No service breakdown'))}"
		f"</div></div>"
		f'<div class="{DASH_ROOT}__services">{''.join(service_cards)}</div>'
		f"{scopes_table}"
		f"</div>"
	)
