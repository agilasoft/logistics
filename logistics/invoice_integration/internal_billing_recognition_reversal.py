# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
After internal billing Journal Entry is submitted, recognize and reverse WIP / accrual
on each main and linked job using that job's Recognition Policy and job-level flags.

- Linked job (credit / income on IB JV): WIP reversal up to credited amounts.
- Main job (debit / expense on IB JV): accrual reversal up to debited amounts.
- Linked job cost accrual: reversed from charge cost when the job has no debit on the JV.
"""

from __future__ import unicode_literals

from collections import defaultdict

import frappe
from frappe.utils import flt

from logistics.billing.cross_module_billing import iter_internal_job_charge_splits
from logistics.invoice_integration.accrual_reversal import (
	_paired_accrual_open_for_item,
	post_cost_accrual_reversal_journal_multi,
)
from logistics.invoice_integration.charge_settled_reversal import compute_item_reversal_amount
from logistics.invoice_integration.recognition_voucher_reversal import (
	reversal_journal_entry_exists_by_remark_locate,
)
from logistics.invoice_integration.wip_reversal import (
	_paired_wip_open_for_item,
	post_wip_reversal_journal_multi,
)
from logistics.job_management.gl_item_dimension import get_item_dimension_fieldname_on_gl_entry
from logistics.job_management.recognition_engine import (
	RecognitionEngine,
	get_recognition_settings,
	resolve_policy_row_for_job,
)


def _resolve_job_doc_from_jcn(jcn):
	if not jcn or not frappe.db.exists("Job Number", jcn):
		return None
	jcn_doc = frappe.get_doc("Job Number", jcn)
	job_dt = jcn_doc.job_type
	job_no = jcn_doc.job_no
	if not job_dt or not job_no or not frappe.db.exists(job_dt, job_no):
		return None
	return frappe.get_doc(job_dt, job_no)


def _ib_je_line_buckets(je_doc):
	"""Group IB JV row amounts by job_number: credit (revenue) and debit (cost) per item."""
	buckets = defaultdict(lambda: {"credit": [], "debit": []})
	for row in je_doc.get("accounts") or []:
		jcn = row.get("job_number")
		if not jcn:
			continue
		item_code = row.get("item") or row.get("item_code")
		cr = flt(row.get("credit_in_account_currency"))
		dr = flt(row.get("debit_in_account_currency"))
		if cr > 0:
			buckets[jcn]["credit"].append((cr, item_code))
		if dr > 0:
			buckets[jcn]["debit"].append((dr, item_code))
	return buckets


def _collect_jobs_from_ib_je(je_doc, billing_main_job=None):
	"""Unique job documents referenced on the IB JV (main + linked)."""
	seen = {}
	for jcn in _ib_je_line_buckets(je_doc):
		job = _resolve_job_doc_from_jcn(jcn)
		if job:
			seen[(job.doctype, job.name)] = job
	if billing_main_job and getattr(billing_main_job, "name", None):
		key = (billing_main_job.doctype, billing_main_job.name)
		seen[key] = billing_main_job
	return list(seen.values())


def _ensure_job_recognition(job, posting_date):
	"""
	Post WIP and accrual recognition on a job when enabled on the job / policy.

	Uses RecognitionEngine recognition dates (job booking, ATA, user-specified, etc.).
	"""
	settings = get_recognition_settings(job)
	out = {}
	if not settings.get("enable_wip_recognition") and not settings.get("enable_accrual_recognition"):
		return out

	engine = RecognitionEngine(job)
	if settings.get("enable_wip_recognition") and flt(job.get("wip_amount")) <= 0:
		try:
			wip_date = engine.get_wip_recognition_date() or posting_date
			wip_je = engine.recognize_wip(wip_date)
			if wip_je:
				out["wip_recognition_journal_entry"] = wip_je
		except Exception:
			frappe.log_error(
				title="WIP recognition before internal billing reversal",
				message=frappe.get_traceback(),
			)

	job.reload()
	engine = RecognitionEngine(job)
	if settings.get("enable_accrual_recognition") and flt(job.get("accrual_amount")) <= 0:
		try:
			acc_date = engine.get_accrual_recognition_date() or posting_date
			acc_je = engine.recognize_accruals(acc_date)
			if acc_je:
				out["accrual_recognition_journal_entry"] = acc_je
		except Exception:
			frappe.log_error(
				title="Accrual recognition before internal billing reversal",
				message=frappe.get_traceback(),
			)
	return out


def _wip_reversal_segments_for_job(job, credit_lines, company):
	"""Build WIP reversal (amount, item) pairs for one job from IB JV credit rows."""
	meta = frappe.get_meta(job.doctype)
	if not meta.has_field("wip_amount"):
		return []
	settings = get_recognition_settings(job)
	if not settings.get("enable_wip_recognition"):
		return []

	jcn = job.get("job_number")
	_policy, param_row = resolve_policy_row_for_job(job)
	if not param_row:
		return []
	wip_acc = param_row.get("wip_account")
	liab_acc = param_row.get("revenue_liability_account")
	if not wip_acc or not liab_acc:
		return []

	remaining = flt(job.get("wip_amount"))
	if remaining <= 0:
		return []

	item_fn_gl = get_item_dimension_fieldname_on_gl_entry()
	je_pairs = []
	for amt, item_code in credit_lines:
		rev = 0
		if item_fn_gl and item_code:
			open_item = _paired_wip_open_for_item(jcn, company, wip_acc, liab_acc, item_fn_gl, item_code)
			if open_item > 0:
				rev = compute_item_reversal_amount(amt, open_item, remaining, item_code, set(), company)
		if rev <= 0:
			rev = min(amt, remaining)
		if rev <= 0:
			continue
		je_pairs.append((rev, item_code))
		remaining -= rev
	return je_pairs


def _accrual_reversal_segments_for_job(job, debit_lines, company, end_customer):
	"""Build accrual reversal pairs for one job from IB JV debit rows or charge costs."""
	meta = frappe.get_meta(job.doctype)
	if not meta.has_field("accrual_amount"):
		return []
	settings = get_recognition_settings(job)
	if not settings.get("enable_accrual_recognition"):
		return []

	if not debit_lines:
		for split in iter_internal_job_charge_splits(
			job.doctype, job.name, customer=end_customer, prefer_actual=True
		):
			cost = flt(split.get("cost"))
			if cost <= 0:
				continue
			debit_lines.append((cost, split.get("item_code")))

	if not debit_lines:
		return []

	jcn = job.get("job_number")
	settings = get_recognition_settings(job)
	cost_acc = settings.get("cost_accrual_account")
	liab_acc = settings.get("accrued_cost_liability_account")
	if not cost_acc or not liab_acc:
		_policy, param_row = resolve_policy_row_for_job(job)
		if param_row:
			cost_acc = param_row.get("cost_accrual_account")
			liab_acc = param_row.get("accrued_cost_liability_account")
	if not cost_acc or not liab_acc:
		return []

	remaining = flt(job.get("accrual_amount"))
	if remaining <= 0:
		return []

	item_fn_gl = get_item_dimension_fieldname_on_gl_entry()
	je_pairs = []
	for amt, item_code in debit_lines:
		rev = 0
		if item_fn_gl and item_code:
			open_item = _paired_accrual_open_for_item(jcn, company, cost_acc, liab_acc, item_fn_gl, item_code)
			if open_item > 0:
				rev = compute_item_reversal_amount(amt, open_item, remaining, item_code, set(), company)
		if rev <= 0:
			rev = min(amt, remaining)
		if rev <= 0:
			continue
		je_pairs.append((rev, item_code))
		remaining -= rev
	return je_pairs


def reverse_recognition_for_internal_billing_je(je_doc, end_customer, billing_main_job=None):
	"""
	Recognize and reverse WIP / accrual for main and linked jobs on an internal billing JE.

	:param je_doc: submitted Journal Entry (internal billing)
	:param end_customer: Sales Quote customer
	:param billing_main_job: operational main job document (billing Dr side)
	:return: dict with optional recognition and reversal journal entry names
	"""
	if not je_doc or getattr(je_doc, "docstatus", None) != 1:
		return {}

	buckets = _ib_je_line_buckets(je_doc)
	jobs = _collect_jobs_from_ib_je(je_doc, billing_main_job=billing_main_job)
	if not jobs and not buckets:
		return {}

	out = {}
	posting_date = je_doc.posting_date
	company = je_doc.company
	wip_segments = []
	accrual_segments = []

	for job in jobs:
		recognition = _ensure_job_recognition(job, posting_date)
		if recognition.get("wip_recognition_journal_entry"):
			out["wip_recognition_journal_entry"] = recognition["wip_recognition_journal_entry"]
		if recognition.get("accrual_recognition_journal_entry"):
			out["accrual_recognition_journal_entry"] = recognition["accrual_recognition_journal_entry"]

		job.reload()
		jcn = job.get("job_number")
		sides = buckets.get(jcn) or {"credit": [], "debit": []}

		credit_lines = list(sides.get("credit") or [])
		wip_pairs = _wip_reversal_segments_for_job(job, credit_lines, company)
		# Main job: linked-scope revenue WIP may settle on the expense (debit) side of the IB JV.
		if not wip_pairs and (sides.get("debit") or []):
			wip_pairs = _wip_reversal_segments_for_job(job, list(sides.get("debit") or []), company)
		if wip_pairs:
			wip_segments.append((job, wip_pairs))

		acc_pairs = _accrual_reversal_segments_for_job(
			job, list(sides.get("debit") or []), company, end_customer
		)
		if acc_pairs:
			accrual_segments.append((job, acc_pairs))

	wip_marker = "WIP recognition reversal (Internal Billing JV {0})".format(je_doc.name)
	if wip_segments and not reversal_journal_entry_exists_by_remark_locate(wip_marker):
		out["wip_journal_entry"] = post_wip_reversal_journal_multi(
			wip_segments,
			posting_date,
			company,
			wip_marker,
		)

	accrual_marker = "Accrual recognition reversal (Internal Billing JV {0})".format(je_doc.name)
	if accrual_segments and not reversal_journal_entry_exists_by_remark_locate(accrual_marker):
		out["accrual_journal_entry"] = post_cost_accrual_reversal_journal_multi(
			accrual_segments,
			posting_date,
			company,
			accrual_marker,
		)

	return out
