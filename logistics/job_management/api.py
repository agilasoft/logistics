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


def get_job_profitability_from_gl(job_costing_number, company, to_date=None, from_date=None):
	"""
	Get revenue, cost, profit, WIP, and accrual for a job from the General Ledger.

	Uses job_costing_number as the accounting dimension on GL Entry.

	:param job_costing_number: Job Costing Number name (Link)
	:param company: Company
	:param to_date: Optional; limit GL entries on or before this date
	:param from_date: Optional; limit GL entries on or after this date
	:return: dict with revenue, cost, gross_profit, profit_margin_pct, wip_amount, accrual_amount, currency
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

	# Revenue: sum(credit - debit) for Income accounts
	revenue_row = frappe.db.sql("""
		SELECT COALESCE(SUM(gle.credit - gle.debit), 0) as amount
		FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE {where}
		AND acc.root_type = 'Income'
	""".format(where=where), values, as_dict=True)
	revenue = flt(revenue_row[0].amount, 2) if revenue_row else 0

	# Cost: sum(debit - credit) for Expense accounts
	cost_row = frappe.db.sql("""
		SELECT COALESCE(SUM(gle.debit - gle.credit), 0) as amount
		FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE {where}
		AND acc.root_type = 'Expense'
	""".format(where=where), values, as_dict=True)
	cost = flt(cost_row[0].amount, 2) if cost_row else 0

	gross_profit = revenue - cost
	profit_margin_pct = (gross_profit / revenue * 100) if revenue else 0

	# WIP and accrual: get accounts from recognition policy for this job
	wip_amount = 0
	accrual_amount = 0
	try:
		from logistics.job_management.recognition_engine import get_recognition_policy_for_job
		policy = get_recognition_policy_for_job(job_costing_number)
		if policy:
			if policy.get("wip_account"):
				wip_row = frappe.db.sql("""
					SELECT COALESCE(SUM(gle.debit - gle.credit), 0) as balance
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
			if policy.get("accrued_cost_liability_account"):
				# Liability: credit - debit
				acc_row = frappe.db.sql("""
					SELECT COALESCE(SUM(gle.credit - gle.debit), 0) as balance
					FROM `tabGL Entry` gle
					WHERE gle.job_costing_number = %(job_costing_number)s
					AND gle.company = %(company)s
					AND gle.account = %(accrued_account)s
					AND gle.docstatus = 1
				""" + (" AND gle.posting_date <= %(to_date)s" if to_date else ""), {
					"job_costing_number": job_costing_number,
					"company": company,
					"accrued_account": policy.accrued_cost_liability_account,
					**({"to_date": to_date} if to_date else {})
				}, as_dict=True)
				accrual_amount = flt(acc_row[0].balance, 2) if acc_row else 0
	except Exception:
		pass

	currency = frappe.get_cached_value("Company", company, "default_currency") or "USD"

	return {
		"revenue": revenue,
		"cost": cost,
		"gross_profit": gross_profit,
		"profit_margin_pct": round(profit_margin_pct, 2),
		"wip_amount": wip_amount,
		"accrual_amount": accrual_amount,
		"currency": currency,
	}


def get_job_gl_entries(job_costing_number, company, to_date=None, from_date=None, limit=100):
	"""
	Get GL entries linked to the job (by job_costing_number) for the profitability "related entries" table.
	Includes party (supplier/customer), date, references, other header details, and Revenue/Cost/WIP/Accrual amounts per row.
	"""
	if not job_costing_number or not company:
		return []

	wip_account = None
	accrual_account = None
	try:
		from logistics.job_management.recognition_engine import get_recognition_policy_for_job
		policy = get_recognition_policy_for_job(job_costing_number)
		if policy:
			wip_account = policy.get("wip_account")
			accrual_account = policy.get("accrued_cost_liability_account")
	except Exception:
		pass

	conditions = [
		"gle.job_costing_number = %(job_costing_number)s",
		"gle.company = %(company)s",
		"gle.docstatus = 1",
	]
	values = {"job_costing_number": job_costing_number, "company": company, "limit": limit}
	if to_date:
		conditions.append("gle.posting_date <= %(to_date)s")
		values["to_date"] = to_date
	if from_date:
		conditions.append("gle.posting_date >= %(from_date)s")
		values["from_date"] = from_date
	where = " AND ".join(conditions)

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
			acc.root_type AS account_root_type
		FROM `tabGL Entry` gle
		LEFT JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE {where}
		ORDER BY gle.posting_date DESC, gle.creation DESC
		LIMIT %(limit)s
	""".format(where=where), values, as_dict=True)

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
		if root_type == "Income":
			revenue_amt = credit - debit
		elif root_type == "Expense":
			if wip_account and acc == wip_account:
				wip_amt = debit - credit
			elif accrual_account and acc == accrual_account:
				accrual_amt = credit - debit
			else:
				cost_amt = debit - credit
		else:
			if wip_account and acc == wip_account:
				wip_amt = debit - credit
			elif accrual_account and acc == accrual_account:
				accrual_amt = credit - debit

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
			"voucher_type": r.voucher_type or "",
			"voucher_no": r.voucher_no or "",
			"view_url": view_url,
		})
	return entries


def _empty_profitability(company):
	currency = frappe.get_cached_value("Company", company, "default_currency") or "USD" if company else "USD"
	return {
		"revenue": 0,
		"cost": 0,
		"gross_profit": 0,
		"profit_margin_pct": 0,
		"wip_amount": 0,
		"accrual_amount": 0,
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
		data["entries"] = get_job_gl_entries(
			job_costing_number=job_costing_number,
			company=company,
			to_date=to_date,
			from_date=from_date,
		)
		html = _build_profitability_html(data)
		return html if isinstance(html, str) else str(html)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Job Profitability HTML")
		return "<p class='text-danger'>" + _("Error loading profitability: ") + str(e) + "</p>"


def _build_profitability_html(data):
	"""Build summary table and related GL entries table with View buttons."""
	c = data.get("currency") or ""
	rev = flt(data.get("revenue"), 2)
	cost = flt(data.get("cost"), 2)
	profit = flt(data.get("gross_profit"), 2)
	margin = flt(data.get("profit_margin_pct"), 2)
	wip = flt(data.get("wip_amount"), 2)
	accrual = flt(data.get("accrual_amount"), 2)
	entries = data.get("entries") or []

	def fmt(v):
		return "{:,.2f}".format(v) if v is not None else "0.00"

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
		chart_title=_("Revenue vs Cost"),
		rev_pct=rev_pct,
		cost_pct=cost_pct,
		source_note=_("Figures from General Ledger by Job Costing Number."),
	)

	# Related GL entries table: Date, Supplier/Customer, Account, References, Other, Revenue, Cost, WIP, Accrual, View
	entries_html = ""
	if entries:
		rows = []
		for e in entries:
			posting_date = escape_html(str(e.get("posting_date") or ""))
			party = escape_html(e.get("party_display") or "-")
			account = escape_html(e.get("account") or "")
			references = escape_html(e.get("references") or "-")
			other = escape_html(e.get("other") or "-")
			rev_amt = flt(e.get("revenue_amount"), 2)
			cost_amt = flt(e.get("cost_amount"), 2)
			wip_amt = flt(e.get("wip_amount"), 2)
			accrual_amt = flt(e.get("accrual_amount"), 2)
			rev_str = fmt(rev_amt) if rev_amt else ""
			cost_str = fmt(cost_amt) if cost_amt else ""
			wip_str = fmt(wip_amt) if wip_amt else ""
			accrual_str = fmt(accrual_amt) if accrual_amt else ""
			view_url = e.get("view_url") or "#"
			view_label = _("View")
			view_btn = (
				'<a href="{url}" class="btn btn-xs btn-default" target="_blank" rel="noopener">{label}</a>'
				.format(url=view_url, label=view_label)
			) if view_url != "#" else ""
			rows.append(
				"<tr><td>{date}</td><td>{party}</td><td>{account}</td><td>{references}</td><td>{other}</td>"
				'<td style="text-align: right;">{revenue}</td><td style="text-align: right;">{cost}</td>'
				'<td style="text-align: right;">{wip}</td><td style="text-align: right;">{accrual}</td><td>{view}</td></tr>'.format(
					date=posting_date,
					party=party,
					account=account,
					references=references,
					other=other,
					revenue=rev_str,
					cost=cost_str,
					wip=wip_str,
					accrual=accrual_str,
					view=view_btn,
				)
			)
		entries_rows = "\n".join(rows)
		entries_html = """
		<div style="margin-top: 16px;">
			<h6 style="margin-bottom: 8px;">{title}</h6>
			<div style="max-height: 360px; overflow: auto;">
				<table class="table table-bordered table-condensed table-striped" style="font-size: 11px;">
					<thead>
						<tr style="background-color: #f5f5f5;">
							<th>{col_date}</th>
							<th>{col_party}</th>
							<th>{col_account}</th>
							<th>{col_references}</th>
							<th>{col_other}</th>
							<th style="text-align: right;">{col_revenue}</th>
							<th style="text-align: right;">{col_cost}</th>
							<th style="text-align: right;">{col_wip}</th>
							<th style="text-align: right;">{col_accrual}</th>
							<th>{col_view}</th>
						</tr>
					</thead>
					<tbody>
						{rows}
					</tbody>
				</table>
			</div>
			<p class="text-muted small" style="margin-top: 4px;">{limit_note}</p>
		</div>
		""".format(
			title=_("Related GL Entries"),
			col_date=_("Date"),
			col_party=_("Supplier/Customer"),
			col_account=_("Account"),
			col_references=_("References"),
			col_other=_("Other"),
			col_revenue=_("Revenue"),
			col_cost=_("Cost"),
			col_wip=_("WIP"),
			col_accrual=_("Accrual"),
			col_view=_("View"),
			rows=entries_rows,
			limit_note=_("Showing up to 100 most recent entries. Amounts by type (Revenue/Cost/WIP/Accrual) per line."),
		)
	else:
		entries_html = """
		<div style="margin-top: 16px;">
			<h6 style="margin-bottom: 8px;">{title}</h6>
			<p class="text-muted small">{no_entries}</p>
		</div>
		""".format(
			title=_("Related GL Entries"),
			no_entries=_("No GL entries found for this Job Costing Number yet."),
		)

	return (summary_html + entries_html).strip()
