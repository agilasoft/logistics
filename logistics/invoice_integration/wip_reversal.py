# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
When a Sales Invoice is posted against a job, reverse open WIP recognition (Dr WIP, Cr revenue liability)
up to each line amount, capped by the job's wip_amount / open GL balances.

Intercompany Sales Invoices use the same DocType and hooks — no separate path.

Line → Job Number: header ``job_number`` if set; otherwise ``reference_doctype`` /
``reference_name`` on the line when they point to a logistics job with a JCN.
"""

from __future__ import unicode_literals

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt

from logistics.job_management.charge_recognition_je import set_wip_adjustment_je_on_charges
from logistics.job_management.gl_item_dimension import get_item_dimension_fieldname_on_gl_entry, item_row_dict
from logistics.job_management.recognition_engine import (
	apply_journal_entry_posting_header_from_job,
	resolve_policy_row_for_job,
)
from logistics.invoice_integration.lifecycle import get_jobs_linked_to_sales_invoice
from logistics.invoice_integration.recognition_voucher_reversal import (
	append_logistics_reversal_marker,
	reversal_journal_entry_exists_for_voucher,
)

# Jobs that may appear on Sales Invoice Item reference
LINE_REFERENCE_JOB_TYPES = (
	"Transport Job",
	"Air Shipment",
	"Sea Shipment",
	"Warehouse Job",
	"Declaration",
	"Declaration Order",
	"General Job",
)


def _paired_wip_open_for_item(jcn, company, wip_acc, liab_acc, item_fn, item_code):
	"""Min of (credit − debit) on WIP account and (debit − credit) on revenue liability for this item."""
	wip_side = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(credit - debit), 0)
		FROM `tabGL Entry`
		WHERE docstatus = 1 AND company = %(company)s
		  AND job_number = %(jcn)s AND account = %(acc)s
		  AND `{item_fn}` = %(item)s
		""".format(item_fn=item_fn),
		{"company": company, "jcn": jcn, "acc": wip_acc, "item": item_code or ""},
	)[0][0]
	liab_side = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(debit - credit), 0)
		FROM `tabGL Entry`
		WHERE docstatus = 1 AND company = %(company)s
		  AND job_number = %(jcn)s AND account = %(acc)s
		  AND `{item_fn}` = %(item)s
		""".format(item_fn=item_fn),
		{"company": company, "jcn": jcn, "acc": liab_acc, "item": item_code or ""},
	)[0][0]
	return min(flt(wip_side), flt(liab_side))


def _resolve_jcn_for_si_line(si_doc, row, header_jcn):
	if header_jcn:
		return header_jcn
	line_jcn = row.get("job_number")
	if line_jcn:
		return line_jcn
	rdt = row.get("reference_doctype")
	rn = row.get("reference_name")
	if rdt and rn and rdt in LINE_REFERENCE_JOB_TYPES and frappe.db.exists(rdt, rn):
		return frappe.db.get_value(rdt, rn, "job_number")
	return None


def _si_item_amount_for_wip_reversal(row):
	"""Company-currency line amount to cap WIP reversal (ERPNext / custom field variance)."""
	for key in ("base_net_amount", "base_amount", "amount", "net_amount"):
		v = flt(row.get(key))
		if v:
			return v
	qty = flt(row.get("qty") or row.get("stock_qty") or 0)
	rate = flt(row.get("rate") or row.get("price_list_rate") or 0)
	if qty and rate:
		return qty * rate
	return 0


def _fallback_jcn_from_linked_sales_invoice(si_name):
	"""When SI lines have no JCN, use the job's JCN if exactly one logistics job links to this SI."""
	jcns = []
	seen = set()
	for dt, nm in get_jobs_linked_to_sales_invoice(si_name):
		jcn = frappe.db.get_value(dt, nm, "job_number")
		if jcn and jcn not in seen:
			seen.add(jcn)
			jcns.append(jcn)
	if len(jcns) == 1:
		return jcns[0]
	return None


def post_wip_reversal_journal(
	job,
	je_pairs,
	posting_date,
	company,
	user_remark,
):
	"""
	Post Dr WIP / Cr Revenue Liability for each (amount, item_code). Update job wip fields.
	"""
	return post_wip_reversal_journal_multi(
		[(job, je_pairs)],
		posting_date,
		company,
		user_remark,
	)


def post_wip_reversal_journal_multi(
	segments,
	posting_date,
	company,
	user_remark,
):
	"""
	Post one balanced Journal Entry for one or more jobs.

	:param segments: list of (job_doc, [(rev_amt, item_code), ...])
	"""
	if not segments:
		return None

	je = frappe.new_doc("Journal Entry")
	je.posting_date = posting_date
	je.company = company
	je.voucher_type = "Journal Entry"
	je.user_remark = user_remark

	totals_per_job = []
	header_job = None

	for job, je_pairs in segments:
		if not je_pairs:
			continue
		jcn = job.get("job_number")
		_policy, param_row = resolve_policy_row_for_job(job)
		if not param_row:
			continue
		if header_job is None:
			header_job = job
		wip_acc = param_row.get("wip_account")
		liab_acc = param_row.get("revenue_liability_account")
		if not wip_acc or not liab_acc:
			continue

		jcn_val = jcn
		seg_total = 0.0
		for rev_amt, item_code in je_pairs:
			seg_total += flt(rev_amt)
			item_extra = item_row_dict("Journal Entry Account", item_code)
			# Do not set reference_type to Sales Invoice / PI on rows: ERPNext requires
			# account + party to match invoice receivable/payable; WIP/liability rows would fail validate_reference_doc.
			base_row = {
				"cost_center": job.get("cost_center"),
				"profit_center": job.get("profit_center"),
				"reference_type": "",
				"reference_name": "",
				**item_extra,
			}
			if jcn_val:
				base_row["job_number"] = jcn_val

			je.append(
				"accounts",
				{
					**base_row,
					"account": wip_acc,
					"debit_in_account_currency": rev_amt,
					"credit_in_account_currency": 0,
				},
			)
			je.append(
				"accounts",
				{
					**base_row,
					"account": liab_acc,
					"debit_in_account_currency": 0,
					"credit_in_account_currency": rev_amt,
				},
			)
		if seg_total > 0:
			totals_per_job.append((job, seg_total))

	if not len(getattr(je, "accounts", []) or []):
		return None

	if header_job:
		apply_journal_entry_posting_header_from_job(je, header_job)

	je.insert()
	je.submit()

	for job, seg_total in totals_per_job:
		frappe.db.set_value(
			job.doctype,
			job.name,
			{
				"wip_amount": max(0, flt(job.wip_amount) - seg_total),
				"recognized_revenue": flt(job.get("recognized_revenue")) + seg_total,
			},
			update_modified=False,
		)

	jobs_posted = {job.name for job, _ in totals_per_job}
	for job, je_pairs in segments:
		if not je_pairs or job.name not in jobs_posted:
			continue
		item_codes = {ic for _, ic in je_pairs if ic}
		restrict = item_codes if item_codes else None
		set_wip_adjustment_je_on_charges(job.doctype, job.name, je.name, restrict)

	return je.name


def reverse_wip_for_sales_invoice(si_doc):
	"""
	Reverse WIP for each distinct Job Number represented on the invoice.

	Idempotent: skips if a submitted JE already references this Sales Invoice.
	"""
	if not si_doc or getattr(si_doc, "docstatus", None) != 1:
		return None

	existing_je = reversal_journal_entry_exists_for_voucher("Sales Invoice", si_doc.name)
	if existing_je:
		return existing_je

	meta_si = frappe.get_meta("Sales Invoice")
	header_jcn = getattr(si_doc, "job_number", None)
	if not header_jcn and meta_si.get_field("job_number"):
		header_jcn = frappe.db.get_value("Sales Invoice", si_doc.name, "job_number")

	buckets = defaultdict(list)
	for row in si_doc.get("items") or []:
		amt = _si_item_amount_for_wip_reversal(row)
		if amt <= 0:
			continue
		jcn = _resolve_jcn_for_si_line(si_doc, row, header_jcn)
		if not jcn:
			continue
		buckets[jcn].append((amt, row.get("item_code")))

	# Lines often lack job_number / reference; job may still point to this SI (logistics flow).
	if not buckets:
		fb_jcn = _fallback_jcn_from_linked_sales_invoice(si_doc.name)
		if fb_jcn:
			for row in si_doc.get("items") or []:
				amt = _si_item_amount_for_wip_reversal(row)
				if amt <= 0:
					continue
				buckets[fb_jcn].append((amt, row.get("item_code")))

	if not buckets:
		return None

	company = si_doc.company
	item_fn_gl = get_item_dimension_fieldname_on_gl_entry()
	segments = []

	for jcn, line_amts in buckets.items():
		if not frappe.db.exists("Job Number", jcn):
			continue
		jcn_doc = frappe.get_doc("Job Number", jcn)
		job_dt = jcn_doc.job_type
		job_no = jcn_doc.job_no
		if not job_dt or not job_no or not frappe.db.exists(job_dt, job_no):
			continue

		meta_job = frappe.get_meta(job_dt)
		if not meta_job.has_field("wip_amount"):
			continue

		job = frappe.get_doc(job_dt, job_no)
		_policy, param_row = resolve_policy_row_for_job(job)
		if not param_row:
			continue
		wip_acc = param_row.get("wip_account")
		liab_acc = param_row.get("revenue_liability_account")
		if not wip_acc or not liab_acc:
			continue

		remaining = flt(job.get("wip_amount"))
		if remaining <= 0:
			continue

		je_pairs = []
		for amt, item_code in line_amts:
			rev = 0
			if item_fn_gl and item_code:
				open_item = _paired_wip_open_for_item(jcn, company, wip_acc, liab_acc, item_fn_gl, item_code)
				if open_item > 0:
					rev = min(amt, open_item, remaining)
			if rev <= 0:
				rev = min(amt, remaining)
			if rev <= 0:
				continue
			je_pairs.append((rev, item_code))
			remaining -= rev

		if je_pairs:
			segments.append((job, je_pairs))

	if not segments:
		return None

	user_remark = append_logistics_reversal_marker(
		_("WIP reversal for Sales Invoice {0}").format(si_doc.name),
		"Sales Invoice",
		si_doc.name,
	)
	return post_wip_reversal_journal_multi(
		segments,
		si_doc.posting_date,
		company,
		user_remark,
	)
