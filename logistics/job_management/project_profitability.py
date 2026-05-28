# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Project-level (and Exhibit-level) profitability from General Ledger.

This is the parent-of-many-jobs analogue of ``logistics.job_management.api`` which
reports profitability for a single Job Number. A Special Project / Exhibit is
backed by an ERPNext Project, and every booking / shipment / job created under
the lifecycle inherits that project as their ``project`` accounting dimension.
Sales / Purchase Invoices created from those jobs propagate the value to GL
Entry, and the recognition journal entries created by the policy engine carry
it too. Filtering GL Entry by ``gle.project`` therefore aggregates every WIP,
accrual, revenue, cost, and disbursement line that belongs to the project.
"""

from __future__ import unicode_literals

from collections import OrderedDict

import frappe
from frappe import _
from frappe.utils import escape_html, flt, get_url_to_form

from logistics.job_management.api import (
	_account_has_job_profit_type,
	_jp_exclude_fragment,
	_profitability_gl_tabs_markup,
	_signed_accrual_by_job_profit,
	_signed_disbursement_amount,
	_signed_wip_by_job_profit,
	aggregate_gl_entries_by_item,
)
from logistics.job_management.gl_item_dimension import (
	get_item_accounting_dimension_label,
	get_item_dimension_fieldname_on_gl_entry,
)


def _job_doctypes_with_project_link():
	"""Logistics job DocTypes that carry their own ``project`` field.

	Used to walk back from a GL Entry's ``job_number`` to the operational doc that
	originated it when the GL line was tagged with a job number but no project.
	"""
	return (
		"Air Shipment",
		"Sea Shipment",
		"Transport Job",
		"Warehouse Job",
		"Declaration",
		"Special Project",
		"Docket",
		"Project Job",
		"General Job",
	)


def _job_number_to_project_map(job_numbers):
	"""Resolve {job_number: project} for any Job Number whose operational doc has a project.

	GL rows posted before the project dimension started flowing through (e.g. legacy
	WIP / accrual journals) carry job_number but no project. The profitability roll-up
	uses this map to attribute those legacy lines to the right project.
	"""
	if not job_numbers:
		return {}
	job_numbers = list({jn for jn in job_numbers if jn})
	if not job_numbers:
		return {}
	rows = frappe.get_all(
		"Job Number",
		filters={"name": ["in", job_numbers]},
		fields=["name", "job_type", "job_no"],
	)
	mapping = {}
	by_type = {}
	for row in rows:
		jt = (row.get("job_type") or "").strip()
		jn = (row.get("job_no") or "").strip()
		if not jt or not jn:
			continue
		by_type.setdefault(jt, []).append((row.name, jn))
	for jt, items in by_type.items():
		if jt not in _job_doctypes_with_project_link():
			continue
		try:
			if not frappe.get_meta(jt).get_field("project"):
				continue
		except Exception:
			continue
		names = [jn for _, jn in items]
		if not names:
			continue
		project_by_name = {
			r.get("name"): (r.get("project") or "").strip()
			for r in frappe.get_all(
				jt,
				filters={"name": ["in", names]},
				fields=["name", "project"],
			)
		}
		for jcn_name, op_name in items:
			project = project_by_name.get(op_name)
			if project:
				mapping[jcn_name] = project
	return mapping


def get_project_profitability_from_gl(project, company=None, to_date=None, from_date=None):
	"""
	Aggregate revenue / cost / profit / WIP / accrual / disbursements for every GL
	Entry tagged with the given ERPNext Project. ``Job Number`` policy exclusions
	mirror :func:`logistics.job_management.api.get_job_profitability_from_gl` so
	the project total is the sum of the per-job totals.
	"""
	if not project:
		return _empty_project_profitability(company)

	# Build the base WHERE; legacy GL rows for the project's jobs may have no project
	# value, so we also collect job_numbers that resolve back to this project and OR them in.
	job_numbers = _project_job_numbers(project)
	conditions = ["gle.docstatus = 1"]
	values = {"project": project}
	project_clause = "gle.project = %(project)s"
	if job_numbers:
		placeholders = []
		for i, jn in enumerate(job_numbers):
			key = f"jn_{i}"
			placeholders.append(f"%({key})s")
			values[key] = jn
		project_clause = (
			"("
			f"gle.project = %(project)s"
			f" OR (IFNULL(gle.project, '') = '' AND gle.job_number IN ({', '.join(placeholders)}))"
			")"
		)
	conditions.append(project_clause)
	if company:
		conditions.append("gle.company = %(company)s")
		values["company"] = company
	if to_date:
		conditions.append("gle.posting_date <= %(to_date)s")
		values["to_date"] = to_date
	if from_date:
		conditions.append("gle.posting_date >= %(from_date)s")
		values["from_date"] = from_date
	where = " AND ".join(conditions)

	jp_ex = _jp_exclude_fragment()

	# Revenue: Income root_type, excluding lines flagged Disbursements / WIP / Accrual.
	revenue_row = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(gle.credit - gle.debit), 0) AS amount
		FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE {where}
		AND acc.root_type = 'Income'
		{jp_ex}
		""".format(where=where, jp_ex=jp_ex),
		values,
		as_dict=True,
	)
	revenue = flt(revenue_row[0].amount, 2) if revenue_row else 0

	# Cost: Expense root_type, excluding lines flagged Disbursements / WIP / Accrual.
	cost_row = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(gle.debit - gle.credit), 0) AS amount
		FROM `tabGL Entry` gle
		INNER JOIN `tabAccount` acc ON acc.name = gle.account
		WHERE {where}
		AND acc.root_type = 'Expense'
		{jp_ex}
		""".format(where=where, jp_ex=jp_ex),
		values,
		as_dict=True,
	)
	cost = flt(cost_row[0].amount, 2) if cost_row else 0

	gross_profit = revenue - cost
	profit_margin_pct = (gross_profit / revenue * 100) if revenue else 0

	disbursements_amount = 0
	wip_amount = 0
	accrual_amount = 0

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

		wip_row = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(
				CASE acc.root_type
					WHEN 'Income' THEN gle.credit - gle.debit
					WHEN 'Asset' THEN gle.debit - gle.credit
					WHEN 'Liability' THEN gle.credit - gle.debit
					WHEN 'Expense' THEN gle.debit - gle.credit
					ELSE gle.credit - gle.debit
				END
			), 0) AS amount
			FROM `tabGL Entry` gle
			INNER JOIN `tabAccount` acc ON acc.name = gle.account
			WHERE {where}
			AND IFNULL(acc.job_profit_account_type, '') = 'WIP'
			""".format(where=where),
			values,
			as_dict=True,
		)
		wip_amount = flt(wip_row[0].amount, 2) if wip_row else 0

		accr_row = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(
				CASE acc.root_type
					WHEN 'Liability' THEN gle.credit - gle.debit
					WHEN 'Expense' THEN gle.debit - gle.credit
					WHEN 'Income' THEN gle.credit - gle.debit
					WHEN 'Asset' THEN gle.debit - gle.credit
					ELSE gle.credit - gle.debit
				END
			), 0) AS amount
			FROM `tabGL Entry` gle
			INNER JOIN `tabAccount` acc ON acc.name = gle.account
			WHERE {where}
			AND IFNULL(acc.job_profit_account_type, '') = 'Accrual'
			""".format(where=where),
			values,
			as_dict=True,
		)
		accrual_amount = flt(accr_row[0].amount, 2) if accr_row else 0

	currency = (
		frappe.get_cached_value("Company", company, "default_currency") if company else None
	) or _company_currency_for_project(project) or "USD"

	return {
		"project": project,
		"revenue": revenue,
		"cost": cost,
		"gross_profit": gross_profit,
		"profit_margin_pct": round(profit_margin_pct, 2),
		"wip_amount": wip_amount,
		"accrual_amount": accrual_amount,
		"disbursements_amount": disbursements_amount,
		"currency": currency,
		"job_count": len(job_numbers),
	}


def _project_job_numbers(project):
	"""Every Job Number whose operational doc points at this Project."""
	if not project:
		return []
	job_numbers = set()
	for jt in _job_doctypes_with_project_link():
		try:
			if not frappe.get_meta(jt).get_field("project"):
				continue
		except Exception:
			continue
		try:
			rows = frappe.get_all(
				jt,
				filters={"project": project},
				fields=["job_number"],
			)
		except Exception:
			rows = []
		for r in rows:
			jn = (r.get("job_number") or "").strip()
			if jn:
				job_numbers.add(jn)
	return sorted(job_numbers)


def _company_currency_for_project(project):
	try:
		company = frappe.db.get_value("Project", project, "company")
	except Exception:
		company = None
	if not company:
		return None
	return frappe.get_cached_value("Company", company, "default_currency")


def _get_project_gl_entries_classified(
	project,
	company=None,
	to_date=None,
	from_date=None,
	max_fetch=5000,
):
	"""Classified GL rows for the project (same shape as :func:`_get_job_gl_entries_classified`)."""
	if not project:
		return []

	item_link_fn = get_item_dimension_fieldname_on_gl_entry()
	item_select = "NULL AS dimension_item"
	if item_link_fn:
		item_select = "gle.`{0}` AS dimension_item".format(item_link_fn)

	job_numbers = _project_job_numbers(project)
	jcn_to_project = _job_number_to_project_map(job_numbers)
	matching_job_numbers = [jn for jn, p in jcn_to_project.items() if p == project] or job_numbers

	conditions = ["gle.docstatus = 1"]
	fetch_cap = max_fetch if max_fetch is not None else 5000
	values = {"project": project, "limit": int(fetch_cap)}

	project_clause = "gle.project = %(project)s"
	if matching_job_numbers:
		placeholders = []
		for i, jn in enumerate(matching_job_numbers):
			key = f"jn_{i}"
			placeholders.append(f"%({key})s")
			values[key] = jn
		project_clause = (
			"("
			f"gle.project = %(project)s"
			f" OR (IFNULL(gle.project, '') = '' AND gle.job_number IN ({', '.join(placeholders)}))"
			")"
		)
	conditions.append(project_clause)

	if company:
		conditions.append("gle.company = %(company)s")
		values["company"] = company
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

	rows = frappe.db.sql(
		"""
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
			gle.job_number,
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
		""".format(where=where, dim_item=item_select, jp_col=jp_col),
		values,
		as_dict=True,
	)

	entries = []
	for r in rows:
		view_url = ""
		if r.get("voucher_type") and r.get("voucher_no"):
			view_url = get_url_to_form(r.voucher_type, r.voucher_no)

		debit = flt(r.debit, 2)
		credit = flt(r.credit, 2)
		root_type = (r.get("account_root_type") or "").strip()
		jp = ((r.get("job_profit_account_type") or "") if _account_has_job_profit_type() else "").strip()

		revenue_amt = 0
		cost_amt = 0
		wip_amt = 0
		accrual_amt = 0
		disbursement_amt = 0

		# Project-level uses Job Profit Account Type tags rather than per-job recognition policy
		# accounts, because the same project can span jobs that use different policies.
		if jp == "Disbursements":
			disbursement_amt = _signed_disbursement_amount(root_type, debit, credit)
		elif jp == "WIP":
			wip_amt = _signed_wip_by_job_profit(root_type, debit, credit)
		elif jp == "Accrual":
			accrual_amt = _signed_accrual_by_job_profit(root_type, debit, credit)
		elif root_type == "Income":
			revenue_amt = credit - debit
		elif root_type == "Expense":
			cost_amt = debit - credit

		party_display = ""
		if r.get("party_type") and r.get("party"):
			party_display = "{}: {}".format(r.party_type or "", r.party or "").strip(": ")
		if not party_display and r.get("against"):
			party_display = (r.against or "")[:80]

		refs = []
		if r.get("voucher_type") and r.get("voucher_no"):
			refs.append("{} {}".format(r.voucher_type, r.voucher_no).strip())
		if r.get("against_voucher_type") and r.get("against_voucher"):
			refs.append("Against: {} {}".format(r.against_voucher_type, r.against_voucher).strip())
		references_display = " | ".join(refs) if refs else "-"

		other_parts = []
		if r.get("remarks"):
			other_parts.append(str(r.remarks)[:60])
		if r.get("cost_center"):
			other_parts.append("CC: {}".format(r.cost_center))
		if r.get("job_number"):
			other_parts.append("Job: {}".format(r.job_number))
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
			"job_number": r.get("job_number") or "",
			"voucher_type": r.voucher_type or "",
			"voucher_no": r.voucher_no or "",
			"view_url": view_url,
		})

	filtered = [
		e for e in entries
		if any(
			flt(e.get(k)) != 0
			for k in (
				"revenue_amount",
				"cost_amount",
				"wip_amount",
				"accrual_amount",
				"disbursement_amount",
			)
		)
	]
	return filtered


def aggregate_gl_entries_by_job_number(entries):
	"""Roll classified GL rows up by Job Number for the project summary table."""
	buckets = OrderedDict()
	for e in entries or []:
		raw = (e.get("job_number") or "").strip()
		key = raw if raw else "__no_job__"
		if key not in buckets:
			buckets[key] = {
				"job_number": raw,
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
	rows = list(buckets.values())
	rows.sort(key=lambda x: (x["job_number"] or "").lower())
	return rows


def _empty_project_profitability(company):
	currency = (
		frappe.get_cached_value("Company", company, "default_currency") if company else None
	) or "USD"
	return {
		"project": None,
		"revenue": 0,
		"cost": 0,
		"gross_profit": 0,
		"profit_margin_pct": 0,
		"wip_amount": 0,
		"accrual_amount": 0,
		"disbursements_amount": 0,
		"currency": currency,
		"job_count": 0,
	}


def _resolve_project_for_parent(parent_doctype, parent_name):
	"""Return (project, company) for a Special Project or Exhibit (or any parent with ``project``)."""
	if not parent_doctype or not parent_name:
		return None, None
	try:
		row = frappe.db.get_value(
			parent_doctype, parent_name, ["project", "company"], as_dict=True
		)
	except Exception:
		return None, None
	if not row:
		return None, None
	return (row.get("project") or "").strip() or None, (row.get("company") or "").strip() or None


@frappe.whitelist()
def get_project_profitability_html(
	parent_doctype=None,
	parent_name=None,
	project=None,
	company=None,
	to_date=None,
	from_date=None,
):
	"""HTML snippet for the Profitability tab on Special Project / Exhibit.

	Accepts either an explicit ``project`` (and ``company``) or a parent reference
	(``parent_doctype`` + ``parent_name``, e.g. ``Special Project``) — the project /
	company are looked up from the parent so callers in the form don't need to know
	what fields live where.
	"""
	try:
		if not project and parent_doctype and parent_name:
			project, parent_company = _resolve_project_for_parent(parent_doctype, parent_name)
			if not company:
				company = parent_company
		if not project:
			return (
				"<p class=\"text-muted\">"
				+ _("Set the linked Project on this {0} to view its profitability from GL.").format(
					_(parent_doctype) if parent_doctype else _("project")
				)
				+ "</p>"
			)

		data = get_project_profitability_from_gl(
			project=project,
			company=company,
			to_date=to_date,
			from_date=from_date,
		)
		all_classified = _get_project_gl_entries_classified(
			project=project,
			company=company,
			to_date=to_date,
			from_date=from_date,
			max_fetch=5000,
		)
		data["entries"] = all_classified[:150]
		data["summary_by_item"] = aggregate_gl_entries_by_item(all_classified)
		data["summary_by_job"] = aggregate_gl_entries_by_job_number(all_classified)
		data["parent_doctype"] = parent_doctype
		data["parent_name"] = parent_name
		return _build_project_profitability_html(data)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Project Profitability HTML")
		return "<p class=\"text-danger\">" + _("Error loading project profitability: ") + str(e) + "</p>"


def _build_project_profitability_html(data):
	"""KPI cards + Revenue vs Cost bar + tabbed tables (Per Job / Per Item / Per Line)."""
	c = data.get("currency") or ""
	rev = flt(data.get("revenue"), 2)
	cost = flt(data.get("cost"), 2)
	profit = flt(data.get("gross_profit"), 2)
	margin = flt(data.get("profit_margin_pct"), 2)
	wip = flt(data.get("wip_amount"), 2)
	accrual = flt(data.get("accrual_amount"), 2)
	disb = flt(data.get("disbursements_amount"), 2)
	project = data.get("project") or ""
	job_count = int(data.get("job_count") or 0)
	entries = data.get("entries") or []
	summary_items = data.get("summary_by_item") or []
	summary_jobs = data.get("summary_by_job") or []

	def fmt(v):
		return "{:,.2f}".format(v) if v is not None else "0.00"

	def fmt_cell(v):
		x = flt(v, 2)
		return fmt(x) if x else ""

	total_abs = max(abs(rev), abs(cost), 1)
	rev_pct = min(100, max(0, (rev / total_abs) * 100)) if total_abs else 0
	cost_pct = min(100, max(0, (cost / total_abs) * 100)) if total_abs else 0
	profit_color = "green" if profit >= 0 else "red"
	margin_color = "green" if margin >= 0 else "orange" if margin == 0 else "red"

	project_link = ""
	if project:
		try:
			project_link = (
				f' &middot; <a href="{get_url_to_form("Project", project)}" target="_blank" '
				f'rel="noopener">{escape_html(project)}</a>'
			)
		except Exception:
			project_link = f' &middot; {escape_html(project)}'

	header_html = """
	<div class="job-profitability-dashboard" style="padding: 12px 0; font-family: inherit;">
		<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
			<h5 style="margin: 0; font-size: 15px; font-weight: 600;">{label}{project_link} <span class="text-muted" style="font-weight: 400; font-size: 12px;">({job_count} {jobs_word})</span></h5>
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
		label=_("Project Profitability (from GL)"),
		project_link=project_link,
		job_count=job_count,
		jobs_word=_("jobs") if job_count != 1 else _("job"),
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
		source_note=_(
			"Figures aggregated from General Ledger by Project (and by Job Number for "
			"legacy GL rows without a project tag)."
		),
	)

	_item_dim_label = get_item_accounting_dimension_label() or _("Item")
	_item_dim_html = escape_html(_item_dim_label)

	if not (entries or summary_items or summary_jobs):
		empty_html = """
		<div class="logistics-profitability-wrapper" style="margin-top: 16px;">
			<h6 style="margin-bottom: 8px;">{title}</h6>
			<p class="text-muted small">{no_entries}</p>
		</div>
		""".format(
			title=_("Project GL (classified)"),
			no_entries=_(
				"No GL entries in Revenue, Cost, WIP, Accrual, or Disbursements for this Project."
			),
		)
		return (header_html + empty_html).strip()

	# Per-job summary rows
	job_lines = []
	for s in summary_jobs:
		jn = (s.get("job_number") or "").strip()
		jn_display = escape_html(jn) if jn else _("(No Job Number)")
		jn_link = jn_display
		if jn:
			try:
				jn_link = (
					f'<a href="{get_url_to_form("Job Number", jn)}" target="_blank" rel="noopener">'
					f"{jn_display}</a>"
				)
			except Exception:
				pass
		job_lines.append(
			"<tr><td>{jn}</td>"
			'<td style="text-align: right;">{r}</td><td style="text-align: right;">{c}</td>'
			'<td style="text-align: right;">{w}</td><td style="text-align: right;">{a}</td>'
			'<td style="text-align: right;">{d}</td></tr>'.format(
				jn=jn_link,
				r=fmt_cell(s.get("revenue_amount")),
				c=fmt_cell(s.get("cost_amount")),
				w=fmt_cell(s.get("wip_amount")),
				a=fmt_cell(s.get("accrual_amount")),
				d=fmt_cell(s.get("disbursement_amount")),
			)
		)
	job_tbody = "\n".join(job_lines) if job_lines else (
		'<tr><td colspan="6" class="text-muted">{empty}</td></tr>'.format(empty=_("No data."))
	)

	# Per-item summary rows
	item_lines = []
	for s in summary_items:
		dlabel = (s.get("dimension_item") or "").strip()
		if not dlabel:
			dlabel = _("(No Item)")
		item_lines.append(
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
	item_tbody = "\n".join(item_lines) if item_lines else (
		'<tr><td colspan="6" class="text-muted">{empty}</td></tr>'.format(empty=_("No data."))
	)

	# Per-line detail rows (up to 150 most recent)
	detail_rows = []
	for e in entries:
		posting_date = escape_html(str(e.get("posting_date") or ""))
		party = escape_html(e.get("party_display") or "-")
		account = escape_html(e.get("account") or "")
		dim_item = escape_html(e.get("dimension_item") or "-")
		references = escape_html(e.get("references") or "-")
		other = escape_html(e.get("other") or "-")
		jn = escape_html(e.get("job_number") or "-")
		view_url = e.get("view_url") or "#"
		view_btn = (
			'<a href="{url}" class="btn btn-xs btn-default" target="_blank" rel="noopener">{label}</a>'.format(
				url=view_url, label=_("View")
			)
			if view_url != "#"
			else ""
		)
		detail_rows.append(
			"<tr><td>{date}</td><td>{jn}</td><td>{party}</td><td>{account}</td>"
			"<td>{dim_item}</td><td>{references}</td><td>{other}</td>"
			'<td style="text-align: right;">{revenue}</td><td style="text-align: right;">{cost}</td>'
			'<td style="text-align: right;">{wip}</td><td style="text-align: right;">{accrual}</td>'
			'<td style="text-align: right;">{disb}</td><td>{view}</td></tr>'.format(
				date=posting_date,
				jn=jn,
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
		'<tr><td colspan="13" class="text-muted">{empty}</td></tr>'.format(
			empty=_("No classified GL lines in the latest fetch.")
		)
	)

	rid = frappe.generate_hash(length=10)
	tables_html = _project_profitability_gl_tabs_markup(rid) + """
		<div class="lgprv-{rid}-panel-details">
			<h6 style="margin-bottom: 8px;">{detail_title}</h6>
			<div style="max-height: 360px; overflow: auto;">
				<table class="table table-bordered table-condensed table-striped" style="font-size: 11px;">
					<thead>
						<tr style="background-color: #f5f5f5;">
							<th>{col_date}</th>
							<th>{col_job}</th>
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
			<h6 style="margin-bottom: 8px;">{summary_jobs_title}</h6>
			<div style="max-height: 240px; overflow: auto; margin-bottom: 14px;">
				<table class="table table-bordered table-condensed table-striped" style="font-size: 11px;">
					<thead>
						<tr style="background-color: #f5f5f5;">
							<th>{col_job}</th>
							<th style="text-align: right;">{col_revenue}</th>
							<th style="text-align: right;">{col_cost}</th>
							<th style="text-align: right;">{col_wip}</th>
							<th style="text-align: right;">{col_accrual}</th>
							<th style="text-align: right;">{col_disb}</th>
						</tr>
					</thead>
					<tbody>{summary_jobs_body}</tbody>
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
		summary_jobs_title=_("Summary by Job Number"),
		summary_items_title=_("Summary by {0}").format(_item_dim_html),
		col_date=_("Date"),
		col_job=_("Job Number"),
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
		summary_jobs_body=job_tbody,
		summary_items_body=item_tbody,
		detail_note=_(
			"Up to 150 most recent classified GL rows tagged with this Project "
			"(Revenue, Cost, WIP, Accrual, Disbursements)."
		),
		summary_note=_(
			"Totals by Job Number and by {0} over up to 5000 classified GL rows."
		).format(_item_dim_html),
	)

	return (header_html + tables_html).strip()


def _project_profitability_gl_tabs_markup(rid):
	"""Pure-CSS tabbed panel (Summary | Details) — defaults to the Summary panel."""
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
