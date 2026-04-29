# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
When a Purchase Invoice is posted against a job, reverse open cost accrual (Dr liability, Cr cost accrual)
up to each line amount, capped by the job's open accrual balance.

Uses Item accounting dimension on JE rows when configured, and matches open accrual by item when GL rows are tagged.
"""

from __future__ import unicode_literals

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt

from logistics.job_management.gl_reference_dimension import get_accounting_dimension_fieldname
from logistics.job_management.charge_recognition_je import set_accrual_adjustment_je_on_charges
from logistics.job_management.gl_item_dimension import get_item_dimension_fieldname_on_gl_entry, item_row_dict
from logistics.job_management.recognition_engine import (
	apply_journal_entry_posting_header_from_job,
	get_recognition_policy_for_job,
)
from logistics.invoice_integration.recognition_voucher_reversal import (
	append_logistics_reversal_marker,
	reversal_journal_entry_exists_for_voucher,
)


def _paired_accrual_open_for_item(jcn, company, cost_acc, liab_acc, item_fn, item_code):
	"""Min of (debit − credit) on cost accrual and (credit − debit) on liability for this item."""
	exp = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(debit - credit), 0)
		FROM `tabGL Entry`
		WHERE docstatus = 1 AND company = %(company)s
		  AND job_number = %(jcn)s AND account = %(acc)s
		  AND `{item_fn}` = %(item)s
		""".format(item_fn=item_fn),
		{"company": company, "jcn": jcn, "acc": cost_acc, "item": item_code or ""},
	)[0][0]
	liab = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(credit - debit), 0)
		FROM `tabGL Entry`
		WHERE docstatus = 1 AND company = %(company)s
		  AND job_number = %(jcn)s AND account = %(acc)s
		  AND `{item_fn}` = %(item)s
		""".format(item_fn=item_fn),
		{"company": company, "jcn": jcn, "acc": liab_acc, "item": item_code or ""},
	)[0][0]
	return min(flt(exp), flt(liab))


def post_cost_accrual_reversal_journal(
	job,
	je_pairs,
	posting_date,
	company,
	user_remark,
):
	"""
	Post Dr Accrued Cost Liability / Cr Cost Accrual for each (amount, item_code) in je_pairs.
	Update job accrual_amount, recognized_costs; link JE on charge rows where configured.

	:param job: job document (must have job_number, cost_center, etc. as available)
	:param je_pairs: list of (rev_amt, item_code)
	:return: JE name or None if je_pairs empty
	"""
	if not je_pairs:
		return None
	return post_cost_accrual_reversal_journal_multi(
		[(job, je_pairs)],
		posting_date,
		company,
		user_remark,
	)


def post_cost_accrual_reversal_journal_multi(
	segments,
	posting_date,
	company,
	user_remark,
):
	"""
	Post one Journal Entry with Dr Liability / Cr Cost Accrual for multiple jobs.

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
		policy = get_recognition_policy_for_job(jcn)
		if not policy:
			continue
		if header_job is None:
			header_job = job
		cost_acc = policy.get("cost_accrual_account")
		liab_acc = policy.get("accrued_cost_liability_account")
		if not cost_acc or not liab_acc:
			continue

		jcn_val = jcn
		seg_total = 0.0
		for rev_amt, item_code in je_pairs:
			seg_total += flt(rev_amt)
			item_extra = item_row_dict("Journal Entry Account", item_code)
			# Do not set reference_type to Purchase Invoice on rows — ERPNext validate_reference_doc
			# requires account = PI credit_to and party = supplier; use user_remark marker for idempotency.
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
					"account": liab_acc,
					"debit_in_account_currency": rev_amt,
					"credit_in_account_currency": 0,
				},
			)
			je.append(
				"accounts",
				{
					**base_row,
					"account": cost_acc,
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
				"accrual_amount": max(0, flt(job.accrual_amount) - seg_total),
				"recognized_costs": flt(job.get("recognized_costs")) + seg_total,
			},
			update_modified=False,
		)

	jobs_posted = {job.name for job, _ in totals_per_job}
	for job, je_pairs in segments:
		if not je_pairs or job.name not in jobs_posted:
			continue
		item_codes = {ic for _, ic in je_pairs if ic}
		restrict = item_codes if item_codes else None
		set_accrual_adjustment_je_on_charges(job.doctype, job.name, je.name, restrict)

	return je.name


def _reverse_cost_accrual_for_purchase_invoice_single(pi_doc, jcn):
	"""Single header Job Number: original behavior (all PI items apply to that job)."""
	policy = get_recognition_policy_for_job(jcn)
	if not policy:
		return None
	cost_acc = policy.get("cost_accrual_account")
	liab_acc = policy.get("accrued_cost_liability_account")
	if not cost_acc or not liab_acc:
		return None

	if not frappe.db.exists("Job Number", jcn):
		return None
	jcn_doc = frappe.get_doc("Job Number", jcn)
	job_dt = jcn_doc.job_type
	job_no = jcn_doc.job_no
	if not job_dt or not job_no or not frappe.db.exists(job_dt, job_no):
		return None

	job = frappe.get_doc(job_dt, job_no)
	if not frappe.get_meta(job_dt).has_field("accrual_amount"):
		return None

	remaining = flt(job.get("accrual_amount"))
	if remaining <= 0:
		return None

	company = pi_doc.company
	item_fn_gl = get_item_dimension_fieldname_on_gl_entry()

	je_pairs = []
	for row in pi_doc.get("items") or []:
		amt = flt(row.get("base_net_amount")) or flt(row.get("amount")) or 0
		if amt <= 0:
			continue
		item_code = row.get("item_code")
		rev = 0
		if item_fn_gl and item_code:
			open_item = _paired_accrual_open_for_item(jcn, company, cost_acc, liab_acc, item_fn_gl, item_code)
			if open_item > 0:
				rev = min(amt, open_item, remaining)
		if rev <= 0:
			rev = min(amt, remaining)
		if rev <= 0:
			continue
		je_pairs.append((rev, item_code))
		remaining -= rev

	if not je_pairs:
		return None

	user_remark = append_logistics_reversal_marker(
		_("Accrual reversal for Purchase Invoice {0}").format(pi_doc.name),
		"Purchase Invoice",
		pi_doc.name,
	)
	return post_cost_accrual_reversal_journal(
		job,
		je_pairs,
		pi_doc.posting_date,
		company,
		user_remark,
	)


def reverse_cost_accrual_for_purchase_invoice(pi_doc):
	"""
	Post accrual reversal Journal Entry(ies) for a submitted Purchase Invoice.

	Uses header Job Number when set; otherwise splits by Job Number on each PI Item (multi-job consolidation invoices).
	"""
	if not pi_doc or getattr(pi_doc, "docstatus", None) != 1:
		return None

	existing_je = reversal_journal_entry_exists_for_voucher("Purchase Invoice", pi_doc.name)
	if existing_je:
		return existing_je

	meta_pi = frappe.get_meta("Purchase Invoice")
	jcn_header = getattr(pi_doc, "job_number", None)
	if not jcn_header and meta_pi.get_field("job_number"):
		jcn_header = frappe.db.get_value("Purchase Invoice", pi_doc.name, "job_number")

	if jcn_header:
		return _reverse_cost_accrual_for_purchase_invoice_single(pi_doc, jcn_header)

	fn_item = get_accounting_dimension_fieldname("Job Number")
	meta_item = frappe.get_meta("Purchase Invoice Item")
	if not fn_item or not meta_item.get_field(fn_item):
		return None

	rows_by_jcn = defaultdict(list)
	for row in pi_doc.get("items") or []:
		jcn = getattr(row, fn_item, None)
		if jcn:
			rows_by_jcn[jcn].append(row)

	if not rows_by_jcn:
		return None

	company = pi_doc.company
	item_fn_gl = get_item_dimension_fieldname_on_gl_entry()
	segments = []

	for jcn_val, rows in rows_by_jcn.items():
		policy = get_recognition_policy_for_job(jcn_val)
		if not policy:
			continue
		cost_acc = policy.get("cost_accrual_account")
		liab_acc = policy.get("accrued_cost_liability_account")
		if not cost_acc or not liab_acc:
			continue
		if not frappe.db.exists("Job Number", jcn_val):
			continue
		jcn_doc = frappe.get_doc("Job Number", jcn_val)
		job_dt = jcn_doc.job_type
		job_no = jcn_doc.job_no
		if not job_dt or not job_no or not frappe.db.exists(job_dt, job_no):
			continue
		job = frappe.get_doc(job_dt, job_no)
		if not frappe.get_meta(job_dt).has_field("accrual_amount"):
			continue

		remaining = flt(job.get("accrual_amount"))
		if remaining <= 0:
			continue

		je_pairs = []
		for row in rows:
			amt = flt(row.get("base_net_amount")) or flt(row.get("amount")) or 0
			if amt <= 0:
				continue
			item_code = row.get("item_code")
			rev = 0
			if item_fn_gl and item_code:
				open_item = _paired_accrual_open_for_item(jcn_val, company, cost_acc, liab_acc, item_fn_gl, item_code)
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
		_("Accrual reversal for Purchase Invoice {0}").format(pi_doc.name),
		"Purchase Invoice",
		pi_doc.name,
	)
	return post_cost_accrual_reversal_journal_multi(
		segments,
		pi_doc.posting_date,
		company,
		user_remark,
	)
