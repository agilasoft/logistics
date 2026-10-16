# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Exhibit-level profitability from General Ledger.

Mirrors :mod:`logistics.job_management.api` (per-Docket / per-Job profitability)
but aggregates every Docket connected to the Exhibit so the Exhibit form shows
the same KPI cards / chart / classified tables as a single Docket — just summed
across all of its exhibitors' dockets.

Why this exists instead of using ``project_profitability``:
``project_profitability`` aggregates **every** operational doc tagged with the
Exhibit's Project (lifecycle jobs, exhibit orders, etc.), which over-counts when
the user only wants the exhibitor-facing Dockets. Each Docket also carries its
own Recognition Policy (per-job WIP / Accrual accounts), so the per-Docket
classifier has to run once per Docket — we then sum the resulting buckets and
concatenate the classified GL rows for the table.
"""

from __future__ import unicode_literals

from collections import OrderedDict

import frappe
from frappe import _
from frappe.utils import escape_html, flt, get_url_to_form

from logistics.job_management.profitability_dashboard import render_gl_profitability_dashboard
from logistics.job_management.api import (
	_get_job_gl_entries_classified,
	_profitability_gl_tabs_markup,
	aggregate_gl_entries_by_item,
	get_job_profitability_from_gl,
)
from logistics.job_management.gl_item_dimension import (
	get_item_accounting_dimension_label,
)


def _exhibit_dockets(exhibit):
	"""Dockets connected to the Exhibit that can contribute to profitability.

	Cancelled dockets are excluded; rows without a Job Number or Company can't
	be matched to GL Entry and are silently skipped.
	"""
	if not exhibit:
		return []
	rows = frappe.get_all(
		"Docket",
		filters={"exhibit": exhibit, "docstatus": ["<", 2]},
		fields=[
			"name",
			"job_number",
			"company",
			"exhibitor",
			"exhibitor_name",
			"booth_no",
			"status",
		],
		order_by="creation asc",
	)
	return [r for r in rows if r.get("job_number") and r.get("company")]


def _exhibit_default_currency(exhibit):
	"""Best-effort currency for the empty / no-docket case."""
	company = None
	try:
		project = frappe.db.get_value("Exhibit", exhibit, "project") if exhibit else None
		if project:
			company = frappe.db.get_value("Project", project, "company")
	except Exception:
		company = None
	if not company:
		try:
			company = frappe.defaults.get_defaults().get("company")
		except Exception:
			company = None
	if company:
		try:
			return frappe.get_cached_value("Company", company, "default_currency") or "USD"
		except Exception:
			return "USD"
	return "USD"


def _empty_exhibit_profitability(exhibit):
	return {
		"exhibit": exhibit,
		"revenue": 0,
		"cost": 0,
		"gross_profit": 0,
		"profit_margin_pct": 0,
		"wip_amount": 0,
		"accrual_amount": 0,
		"disbursements_amount": 0,
		"currency": _exhibit_default_currency(exhibit),
		"docket_count": 0,
	}


def get_exhibit_profitability_from_dockets(exhibit, to_date=None, from_date=None):
	"""Aggregate per-Docket profitability into a single Exhibit-level dict.

	Returns ``(data, entries, by_docket)``:
	- ``data``: aggregated KPI dict with the same shape used by Docket profitability.
	- ``entries``: classified GL rows from every Docket, each annotated with its
	  source ``docket`` so the detail table can show which exhibitor a line belongs to.
	- ``by_docket``: per-Docket summary rows (totals come from the per-Docket
	  ``get_job_profitability_from_gl`` to respect each Docket's Recognition Policy
	  for WIP / Accrual splits).
	"""
	dockets = _exhibit_dockets(exhibit)
	if not dockets:
		return _empty_exhibit_profitability(exhibit), [], []

	sums = {
		"revenue": 0.0,
		"cost": 0.0,
		"wip_amount": 0.0,
		"accrual_amount": 0.0,
		"disbursements_amount": 0.0,
	}
	currency = None
	all_entries = []
	by_docket = []

	for d in dockets:
		per = get_job_profitability_from_gl(
			job_number=d["job_number"],
			company=d["company"],
			to_date=to_date,
			from_date=from_date,
		)
		for k in sums:
			sums[k] += flt(per.get(k))
		if not currency:
			currency = per.get("currency")

		rows = _get_job_gl_entries_classified(
			job_number=d["job_number"],
			company=d["company"],
			to_date=to_date,
			from_date=from_date,
			max_fetch=5000,
		)
		for r in rows:
			r["docket"] = d["name"]
			r["exhibitor_name"] = d.get("exhibitor_name") or ""
			r["booth_no"] = d.get("booth_no") or ""
		all_entries.extend(rows)

		by_docket.append(
			{
				"docket": d["name"],
				"exhibitor": d.get("exhibitor") or "",
				"exhibitor_name": d.get("exhibitor_name") or "",
				"booth_no": d.get("booth_no") or "",
				"status": d.get("status") or "",
				"job_number": d["job_number"],
				"revenue_amount": flt(per.get("revenue")),
				"cost_amount": flt(per.get("cost")),
				"wip_amount": flt(per.get("wip_amount")),
				"accrual_amount": flt(per.get("accrual_amount")),
				"disbursement_amount": flt(per.get("disbursements_amount")),
			}
		)

	revenue = flt(sums["revenue"], 2)
	cost = flt(sums["cost"], 2)
	gross_profit = revenue - cost
	margin = (gross_profit / revenue * 100) if revenue else 0

	data = {
		"exhibit": exhibit,
		"revenue": revenue,
		"cost": cost,
		"gross_profit": gross_profit,
		"profit_margin_pct": round(margin, 2),
		"wip_amount": flt(sums["wip_amount"], 2),
		"accrual_amount": flt(sums["accrual_amount"], 2),
		"disbursements_amount": flt(sums["disbursements_amount"], 2),
		"currency": currency or _exhibit_default_currency(exhibit),
		"docket_count": len(dockets),
	}
	return data, all_entries, by_docket


@frappe.whitelist()
def get_exhibit_profitability_html(exhibit, to_date=None, from_date=None):
	"""HTML snippet for the Profitability tab on Exhibit.

	Renders the same KPI cards / Revenue vs Cost chart used by the Docket
	Profitability section, with classified GL tables tabbed as
	Summary (per Docket and per Item) / Details.
	"""
	try:
		if not exhibit:
			return (
				"<p class=\"text-muted\">"
				+ _("Save this Exhibit to view profitability from General Ledger.")
				+ "</p>"
			)
		dockets_full = _exhibit_dockets(exhibit)
		if not dockets_full:
			return (
				"<p class=\"text-muted\">"
				+ _(
					"No active Dockets with a Job Number and Company are connected to this Exhibit yet. "
					"Profitability will appear here once the exhibitor Dockets are created and posted to GL."
				)
				+ "</p>"
			)

		data, all_entries, by_docket = get_exhibit_profitability_from_dockets(
			exhibit, to_date=to_date, from_date=from_date
		)
		data["entries"] = all_entries[:150]
		data["summary_by_item"] = aggregate_gl_entries_by_item(all_entries)
		data["summary_by_docket"] = by_docket
		return _build_exhibit_profitability_html(data)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Exhibit Profitability HTML")
		return (
			"<p class=\"text-danger\">"
			+ _("Error loading exhibit profitability: ")
			+ str(e)
			+ "</p>"
		)


def _build_exhibit_profitability_html(data):
	"""KPI cards + Revenue vs Cost bar + tabbed tables (Summary by Docket + Item / Details)."""
	docket_count = int(data.get("docket_count") or 0)
	entries = data.get("entries") or []
	summary_items = data.get("summary_by_item") or []
	summary_dockets = data.get("summary_by_docket") or []

	def fmt(v):
		return "{:,.2f}".format(v) if v is not None else "0.00"

	def fmt_cell(v):
		x = flt(v, 2)
		return fmt(x) if x else ""

	dockets_word = _("dockets") if docket_count != 1 else _("docket")
	source_note = _(
		"Aggregated from General Ledger by Job Number across every Docket connected "
		"to this Exhibit (same buckets and Recognition Policy split as the Docket Profitability section)."
	)
	header_extra_html = (
		'<span style="font-size:12px;font-weight:500;color:#6c757d;'
		'letter-spacing:0;text-transform:none;">({docket_count} {dockets_word})</span>'
	).format(docket_count=docket_count, dockets_word=escape_html(dockets_word))
	header_html = render_gl_profitability_dashboard(
		data,
		title=_("Exhibit Profitability (from GL)"),
		info_title=source_note,
		source_note=source_note,
		header_extra_html=header_extra_html,
	)

	_item_dim_label = get_item_accounting_dimension_label() or _("Item")
	_item_dim_html = escape_html(_item_dim_label)

	if not (entries or summary_items or summary_dockets):
		empty_html = """
		<div class="logistics-profitability-wrapper" style="margin-top: 16px;">
			<h6 style="margin-bottom: 8px;">{title}</h6>
			<p class="text-muted small">{no_entries}</p>
		</div>
		""".format(
			title=_("Exhibit GL (classified)"),
			no_entries=_(
				"No GL entries in Revenue, Cost, WIP, Accrual, or Disbursements for any "
				"Docket connected to this Exhibit."
			),
		)
		return (header_html + empty_html).strip()

	docket_rows_html = []
	for s in summary_dockets:
		docket_name = (s.get("docket") or "").strip()
		docket_label = escape_html(docket_name) if docket_name else _("(No Docket)")
		docket_link = docket_label
		if docket_name:
			try:
				docket_link = (
					f'<a href="{get_url_to_form("Docket", docket_name)}" target="_blank" rel="noopener">'
					f"{docket_label}</a>"
				)
			except Exception:
				pass

		exhibitor = escape_html((s.get("exhibitor_name") or s.get("exhibitor") or "").strip() or "-")
		booth = escape_html((s.get("booth_no") or "").strip() or "-")

		docket_rows_html.append(
			"<tr><td>{docket}</td><td>{exhibitor}</td><td>{booth}</td>"
			'<td style="text-align: right;">{r}</td><td style="text-align: right;">{c}</td>'
			'<td style="text-align: right;">{w}</td><td style="text-align: right;">{a}</td>'
			'<td style="text-align: right;">{d}</td></tr>'.format(
				docket=docket_link,
				exhibitor=exhibitor,
				booth=booth,
				r=fmt_cell(s.get("revenue_amount")),
				c=fmt_cell(s.get("cost_amount")),
				w=fmt_cell(s.get("wip_amount")),
				a=fmt_cell(s.get("accrual_amount")),
				d=fmt_cell(s.get("disbursement_amount")),
			)
		)
	docket_tbody = "\n".join(docket_rows_html) if docket_rows_html else (
		'<tr><td colspan="8" class="text-muted">{empty}</td></tr>'.format(empty=_("No data."))
	)

	item_rows_html = []
	for s in summary_items:
		dlabel = (s.get("dimension_item") or "").strip()
		if not dlabel:
			dlabel = _("(No Item)")
		item_rows_html.append(
			"<tr><td>{dim}</td>"
			'<td style="text-align: right;">{r}</td><td style="text-align: right;">{c}</td>'
			'<td style="text-align: right;">{w}</td><td style="text-align: right;">{a}</td>'
			'<td style="text-align: right;">{d}</td></tr>'.format(
				dim=escape_html(dlabel),
				r=fmt_cell(s.get("revenue_amount")),
				c=fmt_cell(s.get("cost_amount")),
				w=fmt_cell(s.get("wip_amount")),
				a=fmt_cell(s.get("accrual_amount")),
				d=fmt_cell(s.get("disbursement_amount")),
			)
		)
	item_tbody = "\n".join(item_rows_html) if item_rows_html else (
		'<tr><td colspan="6" class="text-muted">{empty}</td></tr>'.format(empty=_("No data."))
	)

	detail_rows_html = []
	for e in entries:
		posting_date = escape_html(str(e.get("posting_date") or ""))
		docket_raw = (e.get("docket") or "").strip()
		if docket_raw:
			try:
				docket_cell = (
					f'<a href="{get_url_to_form("Docket", docket_raw)}" target="_blank" rel="noopener">'
					f"{escape_html(docket_raw)}</a>"
				)
			except Exception:
				docket_cell = escape_html(docket_raw)
		else:
			docket_cell = "-"
		party = escape_html(e.get("party_display") or "-")
		account = escape_html(e.get("account") or "")
		dim_item = escape_html(e.get("dimension_item") or "-")
		references = escape_html(e.get("references") or "-")
		other = escape_html(e.get("other") or "-")
		view_url = e.get("view_url") or "#"
		view_btn = (
			'<a href="{url}" class="btn btn-xs btn-default" target="_blank" rel="noopener">{label}</a>'.format(
				url=view_url, label=_("View")
			)
			if view_url != "#"
			else ""
		)
		detail_rows_html.append(
			"<tr><td>{date}</td><td>{docket}</td><td>{party}</td><td>{account}</td>"
			"<td>{dim_item}</td><td>{references}</td><td>{other}</td>"
			'<td style="text-align: right;">{revenue}</td><td style="text-align: right;">{cost}</td>'
			'<td style="text-align: right;">{wip}</td><td style="text-align: right;">{accrual}</td>'
			'<td style="text-align: right;">{disb}</td><td>{view}</td></tr>'.format(
				date=posting_date,
				docket=docket_cell,
				party=party,
				account=account,
				dim_item=dim_item,
				references=references,
				other=other,
				revenue=fmt_cell(e.get("revenue_amount")),
				cost=fmt_cell(e.get("cost_amount")),
				wip=fmt_cell(e.get("wip_amount")),
				accrual=fmt_cell(e.get("accrual_amount")),
				disb=fmt_cell(e.get("disbursement_amount")),
				view=view_btn,
			)
		)
	detail_tbody = "\n".join(detail_rows_html) if detail_rows_html else (
		'<tr><td colspan="13" class="text-muted">{empty}</td></tr>'.format(
			empty=_("No classified GL lines in the latest fetch.")
		)
	)

	rid = frappe.generate_hash(length=10)
	tables_html = _profitability_gl_tabs_markup(rid) + """
		<div class="lgprv-{rid}-panel-details">
			<h6 style="margin-bottom: 8px;">{detail_title}</h6>
			<div style="max-height: 360px; overflow: auto;">
				<table class="table table-bordered table-condensed table-striped" style="font-size: 11px;">
					<thead>
						<tr style="background-color: #f5f5f5;">
							<th>{col_date}</th>
							<th>{col_docket}</th>
							<th>{col_party}</th>
							<th>{col_account}</th>
							<th>{col_dim_item}</th>
							<th>{col_references}</th>
							<th>{col_other}</th>
							<th style="text-align: right;">{col_revenue}</th>
							<th style="text-align: right;">{col_cost}</th>
							<th style="text-align: right;">{col_wip}</th>
							<th style="text-align: right;">{col_accrual}</th>
							<th style="text-align: right;">{col_disb}</th>
							<th>{col_view}</th>
						</tr>
					</thead>
					<tbody>{detail_body}</tbody>
				</table>
			</div>
			<p class="text-muted small" style="margin-top: 4px;">{detail_note}</p>
		</div>
		<div class="lgprv-{rid}-panel-summary">
			<h6 style="margin-bottom: 8px;">{summary_dockets_title}</h6>
			<div style="max-height: 240px; overflow: auto; margin-bottom: 14px;">
				<table class="table table-bordered table-condensed table-striped" style="font-size: 11px;">
					<thead>
						<tr style="background-color: #f5f5f5;">
							<th>{col_docket}</th>
							<th>{col_exhibitor}</th>
							<th>{col_booth}</th>
							<th style="text-align: right;">{col_revenue}</th>
							<th style="text-align: right;">{col_cost}</th>
							<th style="text-align: right;">{col_wip}</th>
							<th style="text-align: right;">{col_accrual}</th>
							<th style="text-align: right;">{col_disb}</th>
						</tr>
					</thead>
					<tbody>{summary_dockets_body}</tbody>
				</table>
			</div>
			<h6 style="margin-bottom: 8px;">{summary_items_title}</h6>
			<div style="max-height: 240px; overflow: auto;">
				<table class="table table-bordered table-condensed table-striped" style="font-size: 11px;">
					<thead>
						<tr style="background-color: #f5f5f5;">
							<th>{col_dim_item}</th>
							<th style="text-align: right;">{col_revenue}</th>
							<th style="text-align: right;">{col_cost}</th>
							<th style="text-align: right;">{col_wip}</th>
							<th style="text-align: right;">{col_accrual}</th>
							<th style="text-align: right;">{col_disb}</th>
						</tr>
					</thead>
					<tbody>{summary_items_body}</tbody>
				</table>
			</div>
			<p class="text-muted small" style="margin-top: 4px;">{summary_note}</p>
		</div>
	</div>
	""".format(
		rid=rid,
		detail_title=_("GL entries (classified)"),
		summary_dockets_title=_("Summary by Docket"),
		summary_items_title=_("Summary by {0}").format(_item_dim_html),
		col_date=_("Date"),
		col_docket=_("Docket"),
		col_exhibitor=_("Exhibitor"),
		col_booth=_("Booth"),
		col_party=_("Supplier/Customer"),
		col_account=_("Account"),
		col_dim_item=_item_dim_html,
		col_references=_("References"),
		col_other=_("Other"),
		col_revenue=_("Revenue"),
		col_cost=_("Cost"),
		col_wip=_("WIP"),
		col_accrual=_("Accrual"),
		col_disb=_("Disbursements"),
		col_view=_("View"),
		detail_body=detail_tbody,
		summary_dockets_body=docket_tbody,
		summary_items_body=item_tbody,
		detail_note=_(
			"Up to 150 most recent classified GL rows tagged with the Job Numbers of "
			"this Exhibit's Dockets (Revenue, Cost, WIP, Accrual, Disbursements)."
		),
		summary_note=_(
			"Per-Docket totals respect each Docket's Recognition Policy; per-{0} totals "
			"are summed across every Docket on this Exhibit."
		).format(_item_dim_html),
	)

	return (header_html + tables_html).strip()
