# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""GL profitability summary cards and Revenue vs Cost chart.

Visual language matches the Sales Quote estimated profitability card:
one green-bordered panel, uppercase labels, bold figures, and light rules
between metrics.
"""

from __future__ import unicode_literals

_GREEN = "#198754"
_INK = "#212529"
_RED = "#dc3545"
_LABEL = "#6c757d"
_CAPTION = "#adb5bd"
_RULE = "#e9ecef"

_RESPONSIVE_CSS = """
<style>
@media (max-width: 768px) {
	.lg-profit-metrics-4 { grid-template-columns: 1fr 1fr !important; row-gap: 14px; }
	.lg-profit-metrics-3 { grid-template-columns: 1fr !important; row-gap: 14px; }
	.lg-profit-metrics-4 > div,
	.lg-profit-metrics-3 > div {
		border-right: none !important;
		padding-left: 0 !important;
		padding-right: 8px !important;
	}
}
@media (max-width: 480px) {
	.lg-profit-metrics-4 { grid-template-columns: 1fr !important; }
}
</style>
"""


def _t(text):
	try:
		from frappe import _

		return _(text)
	except Exception:
		return text


def _esc(text):
	raw = "" if text is None else str(text)
	try:
		from frappe.utils.html_utils import escape_html

		return escape_html(raw)
	except Exception:
		from html import escape

		return escape(raw)


def format_profitability_amount(amount, currency=None):
	"""Format a money figure, preferring the company currency symbol."""
	try:
		value = float(amount or 0)
	except (TypeError, ValueError):
		value = 0.0
	formatted = None
	try:
		from frappe.utils import fmt_money

		formatted = fmt_money(value, currency=currency or None)
	except Exception:
		formatted = None
	if not formatted:
		prefix = "{0} ".format(currency) if currency else ""
		formatted = "{0}{1:,.2f}".format(prefix, value)
	return _esc(formatted)


def _tone(amount):
	try:
		value = float(amount or 0)
	except (TypeError, ValueError):
		value = 0.0
	return _GREEN if value >= 0 else _RED


def _bar_pct(value, scale):
	try:
		amount = float(value or 0)
		span = float(scale or 0)
	except (TypeError, ValueError):
		return 0.0
	if span <= 0:
		return 0.0
	return round(min(100.0, max(0.0, (amount / span) * 100.0)), 2)


def _metric_cell(label, value, caption, color, edge):
	if edge == "first":
		padding = "4px 14px 4px 0"
		border = "border-right:1px solid {0};".format(_RULE)
	elif edge == "last":
		padding = "4px 0 4px 14px"
		border = ""
	else:
		padding = "4px 14px"
		border = "border-right:1px solid {0};".format(_RULE)
	return (
		'<div style="padding:{padding};{border}">'
		'<div style="font-size:11px;color:{label_color};text-transform:uppercase;'
		'letter-spacing:0.04em;margin-bottom:6px;">{label}</div>'
		'<div style="font-size:20px;font-weight:700;color:{color};line-height:1.2;">{value}</div>'
		'<div style="font-size:11px;color:{caption_color};margin-top:4px;">{caption}</div>'
		"</div>"
	).format(
		padding=padding,
		border=border,
		label_color=_LABEL,
		caption_color=_CAPTION,
		label=_esc(label),
		value=value,
		caption=_esc(caption),
		color=color,
	)


def _metrics_row(metrics, columns):
	cells = []
	last = len(metrics) - 1
	for index, metric in enumerate(metrics):
		if index == 0:
			edge = "first"
		elif index == last:
			edge = "last"
		else:
			edge = "middle"
		cells.append(
			_metric_cell(
				metric.get("label"),
				metric.get("value") or "",
				metric.get("caption"),
				metric.get("color") or _INK,
				edge,
			)
		)
	return (
		'<div class="lg-profit-metrics lg-profit-metrics-{columns}" '
		'style="display:grid;grid-template-columns:repeat({columns},minmax(0,1fr));gap:0;">'
		"{cells}</div>"
	).format(columns=int(columns), cells="".join(cells))


def _card(title, icon, body_html, info_title="", header_extra_html=""):
	info = ""
	if info_title:
		info = (
			'<span title="{title}" style="color:{muted};cursor:help;font-size:12px;line-height:1;">'
			'<i class="fa fa-info-circle" aria-hidden="true"></i></span>'
		).format(title=_esc(info_title), muted=_LABEL)
	extra = header_extra_html or ""
	return (
		'<div class="lg-profit-card" style="border:1px solid {green};border-radius:10px;'
		'padding:16px 18px;margin:0 0 12px 0;background:#fff;">'
		'<div style="display:flex;align-items:center;gap:8px;margin-bottom:14px;flex-wrap:wrap;">'
		'<span style="color:{green};font-size:15px;line-height:1;">'
		'<i class="fa {icon}" aria-hidden="true"></i></span>'
		'<span style="font-size:12px;font-weight:700;letter-spacing:0.06em;'
		'text-transform:uppercase;color:{ink};">{title}</span>'
		"{extra}{info}</div>{body}</div>"
	).format(
		green=_GREEN,
		icon=icon,
		ink=_INK,
		title=_esc(title),
		extra=extra,
		info=info,
		body=body_html,
	)


def _chart_rows(rows):
	parts = []
	for row in rows:
		parts.append(
			(
				'<div style="margin-bottom:12px;">'
				'<div style="display:flex;justify-content:space-between;align-items:baseline;'
				'gap:12px;margin-bottom:6px;">'
				'<span style="font-size:11px;color:{label};text-transform:uppercase;'
				'letter-spacing:0.04em;">{name}</span>'
				'<span style="font-size:16px;font-weight:700;color:{color};">{value}</span>'
				"</div>"
				'<div style="height:8px;background:{track};border-radius:4px;overflow:hidden;">'
				'<div style="height:100%;width:{pct}%;background:{color};border-radius:4px;"></div>'
				"</div></div>"
			).format(
				label=_LABEL,
				track=_RULE,
				name=_esc(row.get("label")),
				value=row.get("value") or "",
				color=row.get("color") or _INK,
				pct=row.get("pct") if row.get("pct") is not None else 0,
			)
		)
	return "".join(parts)


def render_gl_profitability_dashboard(
	data,
	title,
	info_title,
	source_note,
	header_extra_html="",
	empty_banner_html="",
):
	"""Build the profitability number card and Revenue vs Cost chart."""
	data = data or {}
	currency = data.get("currency") or ""
	revenue = data.get("revenue") or 0
	cost = data.get("cost") or 0
	profit = data.get("gross_profit") or 0
	margin = data.get("profit_margin_pct") or 0
	wip = data.get("wip_amount") or 0
	accrual = data.get("accrual_amount") or 0
	disbursements = data.get("disbursements_amount") or 0

	try:
		margin_text = "{:.2f}%".format(float(margin or 0))
	except (TypeError, ValueError):
		margin_text = "0.00%"

	excl_tax = _t("(Excl. Tax)")
	headline = [
		{
			"label": _t("Total Revenue"),
			"value": format_profitability_amount(revenue, currency),
			"caption": excl_tax,
			"color": _GREEN,
		},
		{
			"label": _t("Total Cost"),
			"value": format_profitability_amount(cost, currency),
			"caption": excl_tax,
			"color": _INK,
		},
		{
			"label": _t("Gross Profit"),
			"value": format_profitability_amount(profit, currency),
			"caption": excl_tax,
			"color": _tone(profit),
		},
		{
			"label": _t("Margin %"),
			"value": _esc(margin_text),
			"caption": _t("(Profit ÷ Revenue)"),
			"color": _tone(margin),
		},
	]
	supporting = [
		{
			"label": _t("WIP Amount"),
			"value": format_profitability_amount(wip, currency),
			"caption": _t("(Open WIP)"),
			"color": _INK,
		},
		{
			"label": _t("Accrual Amount"),
			"value": format_profitability_amount(accrual, currency),
			"caption": _t("(Open accrual)"),
			"color": _INK,
		},
		{
			"label": _t("Disbursements"),
			"value": format_profitability_amount(disbursements, currency),
			"caption": _t("(Recoverable)"),
			"color": _INK,
		},
	]
	def _as_float(amount):
		try:
			return float(amount or 0)
		except (TypeError, ValueError):
			return 0.0

	scale = max(abs(_as_float(revenue)), abs(_as_float(cost)), 1)
	chart = [
		{
			"label": _t("Total Revenue"),
			"value": format_profitability_amount(revenue, currency),
			"color": _GREEN,
			"pct": _bar_pct(revenue, scale),
		},
		{
			"label": _t("Total Cost"),
			"value": format_profitability_amount(cost, currency),
			"color": _INK,
			"pct": _bar_pct(cost, scale),
		},
	]
	numbers_body = _metrics_row(headline, 4) + (
		'<div class="lg-profit-supporting" style="margin-top:14px;padding-top:14px;'
		'border-top:1px solid {rule};">{row}</div>'
	).format(rule=_RULE, row=_metrics_row(supporting, 3))
	numbers = _card(
		title,
		"fa-calculator",
		numbers_body,
		info_title=info_title,
		header_extra_html=header_extra_html,
	)
	chart_card = _card(
		_t("Revenue vs Cost"),
		"fa-bar-chart",
		_chart_rows(chart),
		info_title=info_title,
	)
	note = ""
	if source_note:
		note = (
			'<p class="text-muted small" style="margin:0;font-size:11px;">{note}</p>'
		).format(note=_esc(source_note))
	return (
		'<div class="job-profitability-dashboard" style="padding:12px 0;font-family:inherit;">'
		"{banner}{numbers}{chart}{note}</div>{css}"
	).format(
		banner=empty_banner_html or "",
		numbers=numbers,
		chart=chart_card,
		note=note,
		css=_RESPONSIVE_CSS,
	)
