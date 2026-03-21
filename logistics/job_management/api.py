# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Job profitability from General Ledger (GL).

All figures are computed from GL Entry using job_costing_number (accounting dimension).
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt, get_url_to_form, escape_html

from logistics.job_management.gl_item_dimension import (
	get_item_accounting_dimension_label,
	get_item_dimension_fieldname_on_gl_entry,
)


def _profitability_gl_tabs_markup(rid):
	"""
	Bootstrap-style tabs (Summary | Details) without JS: hidden radios + label[for] as tab links.
	Default tab: Summary. `rid` must be safe for HTML id (hex from frappe.generate_hash).
	"""
	r = rid
	rs = (
		"position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;"
		"clip:rect(0,0,0,0);white-space:nowrap;border:0;opacity:0;"
	)
	style = (
		'<style type="text/css">'
		".lgprv-{r} .lgprv-{r}-panel-summary {{ display: none !important; }}"
		".lgprv-{r} .lgprv-{r}-panel-details {{ display: block; }}"
		".lgprv-{r} #lgprv-{r}-summary:checked ~ .lgprv-{r}-panel-details {{ display: none !important; }}"
		".lgprv-{r} #lgprv-{r}-summary:checked ~ .lgprv-{r}-panel-summary {{ display: block !important; }}"
		".lgprv-{r} ul.logistics-gl-nav-tabs {{ display: flex; flex-wrap: wrap; padding-left: 0; margin-bottom: 0; list-style: none; border-bottom: 1px solid #d1d8dd; }}"
		".lgprv-{r} ul.logistics-gl-nav-tabs li {{ margin-bottom: -1px; }}"
		".lgprv-{r} ul.logistics-gl-nav-tabs label.nav-link {{ display: block; padding: 0.5rem 0.85rem; margin: 0; cursor: pointer; "
		"border: 1px solid transparent; border-top-left-radius: 0.25rem; border-top-right-radius: 0.25rem; color: #6c757d; font-size: 12px; font-weight: 500; }}"
		".lgprv-{r} #lgprv-{r}-summary:checked ~ ul.logistics-gl-nav-tabs label[for=\"lgprv-{r}-summary\"] {{"
		" color: #495057; background-color: #fff; border-color: #d1d8dd #d1d8dd #fff; }}"
		".lgprv-{r} #lgprv-{r}-details:checked ~ ul.logistics-gl-nav-tabs label[for=\"lgprv-{r}-details\"] {{"
		" color: #495057; background-color: #fff; border-color: #d1d8dd #d1d8dd #fff; }}"
		"</style>"
	)
	# Single .format: if we format `style` first, literal `{ display: ... }` breaks a second .format (KeyError ' display').
	return (
		style
		+ '<div class="logistics-profitability-wrapper lgprv-root lgprv-{r}" style="margin-top: 16px;">'
		'<input type="radio" name="lgprv-{r}" id="lgprv-{r}-summary" checked="checked" autocomplete="off" style="{rs}">'
		'<input type="radio" name="lgprv-{r}" id="lgprv-{r}-details" autocomplete="off" style="{rs}">'
		'<ul class="nav nav-tabs logistics-gl-nav-tabs" role="tablist" style="border-bottom:1px solid #d1d8dd;">'
		'<li class="nav-item" role="presentation">'
		'<label class="nav-link" for="lgprv-{r}-summary" role="tab">{lbl_sum}</label>'
		"</li>"
		'<li class="nav-item" role="presentation">'
		'<label class="nav-link" for="lgprv-{r}-details" role="tab">{lbl_det}</label>'
		"</li>"
		"</ul>"
	).format(r=r, rs=rs, lbl_sum=_("Summary"), lbl_det=_("Details"))


def _account_has_job_profit_type():
	return frappe.db.has_column("Account", "job_profit_account_type")


def _jp_exclude_fragment():
	"""Exclude Job Profit–tagged lines from generic Revenue/Cost GL totals."""
	if not _account_has_job_profit_type():
		return ""
	return (
		" AND IFNULL(acc.job_profit_account_type, '') NOT IN "
		"('Disbursements', 'WIP', 'Accrual')"
	)


def _signed_disbursement_amount(root_type, debit, credit):
	"""Signed P&L-style amount for accounts tagged Disbursements."""
	rt = (root_type or "").strip()
	dr = flt(debit)
	cr = flt(credit)
	if rt == "Income":
		return cr - dr
	if rt == "Expense":
		return dr - cr
	if rt == "Liability":
		return cr - dr
	if rt in ("Asset", "Equity"):
		return dr - cr
	return 0


def _signed_wip_by_job_profit(root_type, debit, credit):
	"""WIP bucket for accounts tagged WIP (non-policy)."""
	rt = (root_type or "").strip()
	dr = flt(debit)
	cr = flt(credit)
	if rt == "Income":
		return cr - dr
	if rt == "Asset":
		return dr - cr
	if rt == "Liability":
		return cr - dr
	if rt == "Expense":
		return dr - cr
	return cr - dr


def _signed_accrual_by_job_profit(root_type, debit, credit):
	"""Accrual bucket for accounts tagged Accrual (non-policy)."""
	rt = (root_type or "").strip()
	dr = flt(debit)
	cr = flt(credit)
	if rt == "Liability":
		return cr - dr
	if rt == "Expense":
		return dr - cr
	if rt == "Income":
		return cr - dr
	if rt == "Asset":
		return dr - cr
	return cr - dr


def aggregate_gl_entries_by_item(entries):
	"""Roll up classified GL rows by dimension item (for Summary view)."""
	from collections import OrderedDict

	buckets = OrderedDict()
	for e in entries or []:
		raw = (e.get("dimension_item") or "").strip()
		key = raw if raw else "__no_item__"
		if key not in buckets:
			buckets[key] = {
				"dimension_item": raw,
				"revenue_amount": 0,
				"cost_amount": 0,
				"wip_amount": 0,
				"accrual_amount": 0,
				"disbursement_amount": 0,
			}
		b = buckets[key]
		b["revenue_amount"] += flt(e.get("revenue_amount"))
		b["cost_amount"] += flt(e.get("cost_amount"))
		b["wip_amount"] += flt(e.get("wip_amount"))
		b["accrual_amount"] += flt(e.get("accrual_amount"))
		b["disbursement_amount"] += flt(e.get("disbursement_amount"))

	out = list(buckets.values())
	out.sort(key=lambda x: (x["dimension_item"] or "").lower())
	return out


def get_job_profitability_from_gl(job_costing_number, company, to_date=None, from_date=None):
	"""
	Get revenue, cost, profit, WIP, and accrual for a job from the General Ledger.

	Uses job_costing_number as the accounting dimension on GL Entry.

	:param job_costing_number: Job Costing Number name (Link)
	:param company: Company
	:param to_date: Optional; limit GL entries on or before this date
	:param from_date: Optional; limit GL entries on or after this date
	:return: dict with revenue, cost, gross_profit, profit_margin_pct, wip_amount, accrual_amount (always 0; Accrued Cost Liability excluded), currency
	"""
	if not job_costing_number or not company:
		return _empty_profitability(company)

	conditions = [
		"gle.job_costing_number = %(job_costing_number)s",
		"gle.company = %(company)s",
		"gle.docstatus = 1",
	]
	values = {"job_costing_number": job_costing_number, "company": company}
	if to_date:
		conditions.append("gle.posting_date <= %(to_date)s")
		values["to_date"] = to_date
	if from_date:
		conditions.append("gle.posting_date >= %(from_date)s")
		values["from_date"] = from_date
	where = " AND ".join(conditions)

	policy = None
	try:
		from logistics.job_management.recognition_engine import get_recognition_policy_for_job
		policy = get_recognition_policy_for_job(job_costing_number)
	except Exception:
		pass

	# Revenue: sum(credit - debit) for Income accounts (exclude policy WIP Income — it is reported under WIP)
	revenue_values = dict(values)
	revenue_exclude = ""
	if policy and policy.get("wip_account"):
		revenue_exclude = " AND gle.account != %(wip_account_exclude)s"
		revenue_values["wip_account_exclude"] = policy["wip_account"]
	jp_ex = _jp_exclude_fragment()
	revenue_row = frappe.db.sql("""
		SELECT COALESCE(SUM(gle.credit - gle.debit), 0) as amount
		FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE {where}
		AND acc.root_type = 'Income'
		{revenue_exclude}
		{jp_ex}
	""".format(where=where, revenue_exclude=revenue_exclude, jp_ex=jp_ex), revenue_values, as_dict=True)
	revenue = flt(revenue_row[0].amount, 2) if revenue_row else 0

	# Cost: sum(debit - credit) for Expense accounts (exclude policy Cost Accrual — shown under Accrual, not Cost)
	cost_exclude = ""
	cost_values = dict(values)
	if policy and policy.get("cost_accrual_account"):
		cost_exclude = " AND gle.account != %(cost_accrual_exclude)s"
		cost_values["cost_accrual_exclude"] = policy["cost_accrual_account"]
	cost_row = frappe.db.sql("""
		SELECT COALESCE(SUM(gle.debit - gle.credit), 0) as amount
		FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE {where}
		AND acc.root_type = 'Expense'
		{cost_exclude}
		{jp_ex}
	""".format(where=where, cost_exclude=cost_exclude, jp_ex=jp_ex), cost_values, as_dict=True)
	cost = flt(cost_row[0].amount, 2) if cost_row else 0

	gross_profit = revenue - cost
	profit_margin_pct = (gross_profit / revenue * 100) if revenue else 0

	# Disbursements: Job Profit Account Type = Disbursements
	disbursements_amount = 0
	if _account_has_job_profit_type():
		disb_row = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(
				CASE acc.root_type
					WHEN 'Income' THEN gle.credit - gle.debit
					WHEN 'Expense' THEN gle.debit - gle.credit
					WHEN 'Liability' THEN gle.credit - gle.debit
					WHEN 'Asset' THEN gle.debit - gle.credit
					WHEN 'Equity' THEN gle.debit - gle.credit
					ELSE 0
				END
			), 0) AS amount
			FROM `tabGL Entry` gle
			INNER JOIN `tabAccount` acc ON acc.name = gle.account
			WHERE {where}
			AND IFNULL(acc.job_profit_account_type, '') = 'Disbursements'
			""".format(where=where),
			values,
			as_dict=True,
		)
		disbursements_amount = flt(disb_row[0].amount, 2) if disb_row else 0

	# WIP from policy; accrual KPI excludes Accrued Cost Liability (balance-sheet) by design
	wip_amount = 0
	accrual_amount = 0
	if policy:
		if policy.get("wip_account"):
			# WIP recognition JEs credit the WIP (Income) account; show positive open WIP as (credit - debit)
			wip_row = frappe.db.sql("""
				SELECT COALESCE(SUM(gle.credit - gle.debit), 0) as balance
				FROM `tabGL Entry` gle
				WHERE gle.job_costing_number = %(job_costing_number)s
				AND gle.company = %(company)s
				AND gle.account = %(wip_account)s
				AND gle.docstatus = 1
			""" + (" AND gle.posting_date <= %(to_date)s" if to_date else ""), {
				"job_costing_number": job_costing_number,
				"company": company,
				"wip_account": policy.wip_account,
				**({"to_date": to_date} if to_date else {})
			}, as_dict=True)
			wip_amount = flt(wip_row[0].balance, 2) if wip_row else 0
		# Accrued Cost Liability Account is excluded from profitability (not in KPI or classified GL tables).

	currency = frappe.get_cached_value("Company", company, "default_currency") or "USD"

	return {
		"revenue": revenue,
		"cost": cost,
		"gross_profit": gross_profit,
		"profit_margin_pct": round(profit_margin_pct, 2),
		"wip_amount": wip_amount,
		"accrual_amount": accrual_amount,
		"disbursements_amount": disbursements_amount,
		"currency": currency,
	}


def _get_job_gl_entries_classified(
	job_costing_number,
	company,
	to_date=None,
	from_date=None,
	max_fetch=5000,
):
	"""
	Fetch GL rows for the job, classify into Revenue/Cost/WIP/Accrual/Disbursements, drop unclassified lines.
	Returns all matching rows up to max_fetch (posting date desc).
	"""
	if not job_costing_number or not company:
		return []

	wip_account = None
	cost_accrual_account = None
	try:
		from logistics.job_management.recognition_engine import get_recognition_policy_for_job
		policy = get_recognition_policy_for_job(job_costing_number)
		if policy:
			wip_account = policy.get("wip_account")
			cost_accrual_account = policy.get("cost_accrual_account")
	except Exception:
		pass

	item_link_fn = get_item_dimension_fieldname_on_gl_entry()
	item_select = "NULL AS dimension_item"
	if item_link_fn:
		item_select = "gle.`{0}` AS dimension_item".format(item_link_fn)

	conditions = [
		"gle.job_costing_number = %(job_costing_number)s",
		"gle.company = %(company)s",
		"gle.docstatus = 1",
	]
	fetch_cap = max_fetch if max_fetch is not None else 5000
	values = {"job_costing_number": job_costing_number, "company": company, "limit": int(fetch_cap)}
	if to_date:
		conditions.append("gle.posting_date <= %(to_date)s")
		values["to_date"] = to_date
	if from_date:
		conditions.append("gle.posting_date >= %(from_date)s")
		values["from_date"] = from_date
	where = " AND ".join(conditions)

	jp_col = "NULL AS job_profit_account_type"
	if _account_has_job_profit_type():
		jp_col = "acc.job_profit_account_type AS job_profit_account_type"

	rows = frappe.db.sql("""
		SELECT
			gle.posting_date,
			gle.transaction_date,
			gle.account,
			gle.party_type,
			gle.party,
			gle.against,
			gle.remarks,
			gle.cost_center,
			gle.project,
			gle.debit,
			gle.credit,
			gle.voucher_type,
			gle.voucher_no,
			gle.against_voucher_type,
			gle.against_voucher,
			acc.root_type AS account_root_type,
			{jp_col},
			{dim_item}
		FROM `tabGL Entry` gle
		LEFT JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE {where}
		ORDER BY gle.posting_date DESC, gle.creation DESC
		LIMIT %(limit)s
	""".format(where=where, dim_item=item_select, jp_col=jp_col), values, as_dict=True)

	entries = []
	for r in rows:
		view_url = ""
		if r.get("voucher_type") and r.get("voucher_no"):
			view_url = get_url_to_form(r.voucher_type, r.voucher_no)

		debit = flt(r.debit, 2)
		credit = flt(r.credit, 2)
		root_type = (r.get("account_root_type") or "").strip()
		acc = (r.get("account") or "").strip()

		revenue_amt = 0
		cost_amt = 0
		wip_amt = 0
		accrual_amt = 0
		disbursement_amt = 0
		jp = ((r.get("job_profit_account_type") or "") if _account_has_job_profit_type() else "").strip()

		# 1) Recognition policy accounts (exact match). Accrued Cost Liability is excluded from profitability.
		if wip_account and acc == wip_account:
			wip_amt = credit - debit
		elif cost_accrual_account and acc == cost_accrual_account:
			accrual_amt = debit - credit
		elif jp == "Disbursements":
			disbursement_amt = _signed_disbursement_amount(root_type, debit, credit)
		elif jp == "WIP":
			wip_amt = _signed_wip_by_job_profit(root_type, debit, credit)
		elif jp == "Accrual":
			accrual_amt = _signed_accrual_by_job_profit(root_type, debit, credit)
		elif root_type == "Income":
			revenue_amt = credit - debit
		elif root_type == "Expense":
			cost_amt = debit - credit
		else:
			# Other root types: only show if tagged Disbursements/WIP/Accrual (handled above)
			pass

		# Supplier/Customer: party_type + party, or against text
		party_display = ""
		if r.get("party_type") and r.get("party"):
			party_display = "{}: {}".format(r.party_type or "", r.party or "").strip(": ")
		if not party_display and r.get("against"):
			party_display = (r.against or "")[:80]

		# References: voucher and against voucher
		refs = []
		if r.get("voucher_type") and r.get("voucher_no"):
			refs.append("{} {}".format(r.voucher_type, r.voucher_no).strip())
		if r.get("against_voucher_type") and r.get("against_voucher"):
			refs.append("Against: {} {}".format(r.against_voucher_type, r.against_voucher).strip())
		references_display = " | ".join(refs) if refs else "-"

		# Other: remarks, cost center, project
		other_parts = []
		if r.get("remarks"):
			other_parts.append(str(r.remarks)[:60])
		if r.get("cost_center"):
			other_parts.append("CC: {}".format(r.cost_center))
		if r.get("project"):
			other_parts.append("Proj: {}".format(r.project))
		other_display = " | ".join(other_parts) if other_parts else "-"

		entries.append({
			"posting_date": r.posting_date,
			"transaction_date": r.transaction_date,
			"account": r.account or "",
			"party_display": party_display or "-",
			"references": references_display,
			"other": other_display,
			"debit": debit,
			"credit": credit,
			"revenue_amount": revenue_amt,
			"cost_amount": cost_amt,
			"wip_amount": wip_amt,
			"accrual_amount": accrual_amt,
			"disbursement_amount": disbursement_amt,
			"dimension_item": (r.get("dimension_item") or "") if item_link_fn else "",
			"voucher_type": r.voucher_type or "",
			"voucher_no": r.voucher_no or "",
			"view_url": view_url,
		})

	# Drop lines that do not fall into any profitability classification
	filtered = []
	for e in entries:
		if any(
			flt(e.get(k)) != 0
			for k in (
				"revenue_amount",
				"cost_amount",
				"wip_amount",
				"accrual_amount",
				"disbursement_amount",
			)
		):
			filtered.append(e)

	return filtered


def get_job_gl_entries(
	job_costing_number,
	company,
	to_date=None,
	from_date=None,
	limit=100,
	max_fetch=5000,
):
	"""
	Public API: classified GL lines for the job, capped for list display (default 100).
	"""
	all_rows = _get_job_gl_entries_classified(
		job_costing_number,
		company,
		to_date=to_date,
		from_date=from_date,
		max_fetch=max_fetch,
	)
	if limit is None:
		return all_rows
	return all_rows[: max(0, int(limit))]


def _empty_profitability(company):
	currency = frappe.get_cached_value("Company", company, "default_currency") or "USD" if company else "USD"
	return {
		"revenue": 0,
		"cost": 0,
		"gross_profit": 0,
		"profit_margin_pct": 0,
		"wip_amount": 0,
		"accrual_amount": 0,
		"disbursements_amount": 0,
		"currency": currency,
	}


@frappe.whitelist()
def get_job_profitability_html(job_costing_number, company, to_date=None, from_date=None):
	"""
	Return HTML snippet for the Profitability section on job/shipment forms.
	Includes summary (revenue, cost, profit, WIP, accrual) and a table of related GL entries with View buttons.

	:param job_costing_number: Job Costing Number name
	:param company: Company
	:param to_date: Optional
	:param from_date: Optional
	:return: HTML string
	"""
	try:
		data = get_job_profitability_from_gl(
			job_costing_number=job_costing_number,
			company=company,
			to_date=to_date,
			from_date=from_date,
		)
		all_classified = _get_job_gl_entries_classified(
			job_costing_number=job_costing_number,
			company=company,
			to_date=to_date,
			from_date=from_date,
			max_fetch=5000,
		)
		data["entries"] = all_classified[:100]
		data["summary_by_item"] = aggregate_gl_entries_by_item(all_classified)
		html = _build_profitability_html(data)
		return html if isinstance(html, str) else str(html)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Job Profitability HTML")
		return "<p class=\"text-danger\">" + _("Error loading profitability: ") + str(e) + "</p>"


def _build_profitability_html(data):
	"""Build KPI cards, Revenue vs Cost chart, and GL tables (Details per line or Summary per item)."""
	c = data.get("currency") or ""
	rev = flt(data.get("revenue"), 2)
	cost = flt(data.get("cost"), 2)
	profit = flt(data.get("gross_profit"), 2)
	margin = flt(data.get("profit_margin_pct"), 2)
	wip = flt(data.get("wip_amount"), 2)
	accrual = flt(data.get("accrual_amount"), 2)
	disb = flt(data.get("disbursements_amount"), 2)
	entries = data.get("entries") or []
	summary_rows = data.get("summary_by_item") or []

	def fmt(v):
		return "{:,.2f}".format(v) if v is not None else "0.00"

	def fmt_cell(v):
		x = flt(v, 2)
		return fmt(x) if x else ""

	# Chart scale: max of revenue, cost for bar widths (avoid div by zero)
	total_abs = max(abs(rev), abs(cost), 1)
	rev_pct = min(100, max(0, (rev / total_abs) * 100)) if total_abs else 0
	cost_pct = min(100, max(0, (cost / total_abs) * 100)) if total_abs else 0
	profit_color = "green" if profit >= 0 else "red"
	margin_color = "green" if margin >= 0 else "orange" if margin == 0 else "red"

	summary_html = """
	<div class="job-profitability-dashboard" style="padding: 12px 0; font-family: inherit;">
		<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
			<h5 style="margin: 0; font-size: 15px; font-weight: 600;">{label}</h5>
			<span style="background: #e9ecef; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{currency}</span>
		</div>
		<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 16px;">
			<div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; border-left: 4px solid #28a745;">
				<div style="font-size: 11px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.3px;">{revenue_label}</div>
				<div style="font-size: 18px; font-weight: 600; color: #212529;">{revenue}</div>
			</div>
			<div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; border-left: 4px solid #dc3545;">
				<div style="font-size: 11px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.3px;">{cost_label}</div>
				<div style="font-size: 18px; font-weight: 600; color: #212529;">{cost}</div>
			</div>
			<div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; border-left: 4px solid #007bff;">
				<div style="font-size: 11px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.3px;">{profit_label}</div>
				<div style="font-size: 18px; font-weight: 600; color: {profit_color_val};">{profit}</div>
			</div>
			<div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; border-left: 4px solid #6f42c1;">
				<div style="font-size: 11px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.3px;">{margin_label}</div>
				<div style="font-size: 18px; font-weight: 600; color: {margin_color_val};">{margin}%</div>
			</div>
			<div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; border-left: 4px solid #fd7e14;">
				<div style="font-size: 11px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.3px;">{wip_label}</div>
				<div style="font-size: 18px; font-weight: 600; color: #212529;">{wip}</div>
			</div>
			<div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; border-left: 4px solid #20c997;">
				<div style="font-size: 11px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.3px;">{accrual_label}</div>
				<div style="font-size: 18px; font-weight: 600; color: #212529;">{accrual}</div>
			</div>
			<div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; border-left: 4px solid #17a2b8;">
				<div style="font-size: 11px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.3px;">{disb_label}</div>
				<div style="font-size: 18px; font-weight: 600; color: #212529;">{disb}</div>
			</div>
		</div>
		<div style="background: #f8f9fa; border: 1px solid #dee2e6; border-radius: 8px; padding: 12px; margin-bottom: 12px;">
			<div style="font-size: 12px; font-weight: 600; margin-bottom: 8px; color: #495057;">{chart_title}</div>
			<div style="display: flex; flex-direction: column; gap: 8px;">
				<div>
					<div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 2px;">
						<span>{revenue_label}</span>
						<span>{revenue}</span>
					</div>
					<div style="height: 8px; background: #e9ecef; border-radius: 4px; overflow: hidden;">
						<div style="height: 100%; width: {rev_pct}%; background: #28a745; border-radius: 4px;"></div>
					</div>
				</div>
				<div>
					<div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 2px;">
						<span>{cost_label}</span>
						<span>{cost}</span>
					</div>
					<div style="height: 8px; background: #e9ecef; border-radius: 4px; overflow: hidden;">
						<div style="height: 100%; width: {cost_pct}%; background: #dc3545; border-radius: 4px;"></div>
					</div>
				</div>
			</div>
		</div>
		<p class="text-muted small" style="margin: 0; font-size: 11px;">{source_note}</p>
	</div>
	""".format(
		label=_("Profitability (from GL)"),
		currency=c,
		revenue_label=_("Revenue"),
		revenue=fmt(rev),
		cost_label=_("Cost"),
		cost=fmt(cost),
		profit_label=_("Gross Profit"),
		profit=fmt(profit),
		profit_color_val=profit_color,
		margin_label=_("Profit Margin"),
		margin=fmt(margin),
		margin_color_val=margin_color,
		wip_label=_("WIP Amount"),
		wip=fmt(wip),
		accrual_label=_("Accrual Amount"),
		accrual=fmt(accrual),
		disb_label=_("Disbursements"),
		disb=fmt(disb),
		chart_title=_("Revenue vs Cost"),
		rev_pct=rev_pct,
		cost_pct=cost_pct,
		source_note=_("Figures from General Ledger by Job Costing Number."),
	)

	# Column header = Accounting Dimension label (matches GL Entry form), else "Item"
	_item_dim_label = get_item_accounting_dimension_label() or _("Item")
	_item_dim_html = escape_html(_item_dim_label)

	# Classified GL only: Details (per GL row) vs Summary (per Item accounting dimension on GL)
	tables_html = ""
	if entries or summary_rows:
		detail_rows = []
		for e in entries:
			posting_date = escape_html(str(e.get("posting_date") or ""))
			party = escape_html(e.get("party_display") or "-")
			account = escape_html(e.get("account") or "")
			dim_item = escape_html(e.get("dimension_item") or "-")
			references = escape_html(e.get("references") or "-")
			other = escape_html(e.get("other") or "-")
			view_url = e.get("view_url") or "#"
			view_lbl = _("View")
			view_btn = (
				'<a href="{url}" class="btn btn-xs btn-default" target="_blank" rel="noopener">{label}</a>'
				.format(url=view_url, label=view_lbl)
			) if view_url != "#" else ""
			detail_rows.append(
				"<tr><td>{date}</td><td>{party}</td><td>{account}</td><td>{dim_item}</td><td>{references}</td><td>{other}</td>"
				'<td style="text-align: right;">{revenue}</td><td style="text-align: right;">{cost}</td>'
				'<td style="text-align: right;">{wip}</td><td style="text-align: right;">{accrual}</td>'
				'<td style="text-align: right;">{disb}</td><td>{view}</td></tr>'.format(
					date=posting_date,
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
		detail_tbody = "\n".join(detail_rows) if detail_rows else (
			'<tr><td colspan="11" class="text-muted">{empty}</td></tr>'.format(
				empty=_("No classified GL lines in the latest fetch.")
			)
		)

		summary_lines = []
		for s in summary_rows:
			dlabel = (s.get("dimension_item") or "").strip()
			if not dlabel:
				dlabel = _("(No Item)")
			dim_esc = escape_html(dlabel)
			summary_lines.append(
				"<tr><td>{dim}</td>"
				'<td style="text-align: right;">{r}</td><td style="text-align: right;">{c}</td>'
				'<td style="text-align: right;">{w}</td><td style="text-align: right;">{a}</td>'
				'<td style="text-align: right;">{d}</td></tr>'.format(
					dim=dim_esc,
					r=fmt_cell(s.get("revenue_amount")),
					c=fmt_cell(s.get("cost_amount")),
					w=fmt_cell(s.get("wip_amount")),
					a=fmt_cell(s.get("accrual_amount")),
					d=fmt_cell(s.get("disbursement_amount")),
				)
			)
		summary_tbody = "\n".join(summary_lines) if summary_lines else (
			'<tr><td colspan="6" class="text-muted">{empty}</td></tr>'.format(empty=_("No data."))
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
				<h6 style="margin-bottom: 8px;">{summary_title}</h6>
				<div style="max-height: 360px; overflow: auto;">
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
						<tbody>{summary_body}</tbody>
					</table>
				</div>
				<p class="text-muted small" style="margin-top: 4px;">{summary_note}</p>
			</div>
		</div>
		""".format(
			rid=rid,
			detail_title=_("GL entries (classified)"),
			summary_title=_("Summary by {0}").format(_item_dim_html),
			col_date=_("Date"),
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
			summary_body=summary_tbody,
			detail_note=_(
				"Up to 100 most recent classified GL rows (Revenue, Cost, WIP, Accrual, Disbursements). "
				'"{0}" is the value stored on each GL Entry line for the Item accounting dimension.'
			).format(_item_dim_html),
			summary_note=_(
				"Totals by {0} as on GL Entry (Item accounting dimension), over up to 5000 classified GL rows."
			).format(_item_dim_html),
		)
	else:
		tables_html = """
		<div class="logistics-profitability-wrapper" style="margin-top: 16px;">
			<h6 style="margin-bottom: 8px;">{title}</h6>
			<p class="text-muted small">{no_entries}</p>
		</div>
		""".format(
			title=_("Job GL (classified)"),
			no_entries=_("No GL entries in Revenue, Cost, WIP, Accrual, or Disbursements for this Job Costing Number."),
		)

	return (summary_html + tables_html).strip()
