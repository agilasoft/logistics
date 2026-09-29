# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
When a Journal Entry is submitted with a Job Number, reverse open WIP and cost accrual
the same way Sales Invoice and Purchase Invoice do.

- Income credit (not the policy WIP account) reverses WIP: Dr WIP, Cr Revenue Liability.
- Expense debit (not the policy Cost Accrual account) reverses accrual: Dr Accrued Cost Liability, Cr Cost Accrual.

Recognition journals, reversal journals, and internal-billing journals are skipped.
Each reversal is capped by the job's open wip_amount or accrual_amount.
"""

from __future__ import unicode_literals

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt

from logistics.invoice_integration.accrual_reversal import (
	_paired_accrual_open_for_item,
	post_cost_accrual_reversal_journal_multi,
)
from logistics.invoice_integration.charge_settled_reversal import compute_item_reversal_amount
from logistics.invoice_integration.recognition_voucher_reversal import (
	append_logistics_reversal_marker,
	reversal_journal_entry_exists_for_voucher,
)
from logistics.invoice_integration.wip_reversal import (
	_paired_wip_open_for_item,
	post_wip_reversal_journal_multi,
)
from logistics.job_management.api import is_stock_received_not_billed_cost_account
from logistics.job_management.gl_item_dimension import (
	get_item_dimension_fieldname_on_gl_entry,
	get_item_link_fieldname,
)
from logistics.job_management.recognition_engine import (
	get_recognition_policy_for_job,
	resolve_policy_row_for_job,
)

_REVERSAL_MARKER_PREFIX = "CargoNext|RecognitionReversal|"
_INTERNAL_BILLING_REMARK = "Internal Billing"

# Separate idempotency keys so WIP and accrual reversals can both exist for one source JE.
_WIP_VOUCHER_TYPE = "Journal Entry WIP"
_ACCRUAL_VOUCHER_TYPE = "Journal Entry Accrual"

_SKIP_JOB_PROFIT_TYPES = frozenset(("Disbursements", "WIP", "Accrual"))


def on_journal_entry_submit(doc, method=None):
	"""Reverse open WIP and accrual for job-tagged revenue and cost on this Journal Entry."""
	if not doc or getattr(doc, "docstatus", None) != 1:
		return
	try:
		reverse_wip_and_accrual_for_journal_entry(doc)
	except Exception as e:
		frappe.log_error(
			title="WIP / accrual reversal on Journal Entry submit",
			message=frappe.get_traceback(),
		)
		frappe.msgprint(
			_("WIP / accrual reversal could not be posted: {0}").format(str(e)),
			indicator="orange",
		)


def reverse_wip_and_accrual_for_journal_entry(je_doc):
	"""
	Post WIP and accrual reversal journals for a submitted Journal Entry.

	Returns a dict with optional ``wip_journal_entry`` and ``accrual_journal_entry``, or None when skipped.
	"""
	if not je_doc or getattr(je_doc, "docstatus", None) != 1:
		return None
	if _should_skip_journal_entry(je_doc):
		return None

	lines_by_jcn = collect_journal_entry_recognition_lines(je_doc)
	if not lines_by_jcn:
		return None

	company = je_doc.company
	posting_date = je_doc.posting_date
	out = {}

	if not reversal_journal_entry_exists_for_voucher(_ACCRUAL_VOUCHER_TYPE, je_doc.name):
		accrual_segments = _accrual_segments(lines_by_jcn, company)
		if accrual_segments:
			remark = append_logistics_reversal_marker(
				_("Accrual reversal for Journal Entry {0}").format(je_doc.name),
				_ACCRUAL_VOUCHER_TYPE,
				je_doc.name,
			)
			out["accrual_journal_entry"] = post_cost_accrual_reversal_journal_multi(
				accrual_segments,
				posting_date,
				company,
				remark,
			)

	if not reversal_journal_entry_exists_for_voucher(_WIP_VOUCHER_TYPE, je_doc.name):
		wip_segments = _wip_segments(lines_by_jcn, company)
		if wip_segments:
			remark = append_logistics_reversal_marker(
				_("WIP reversal for Journal Entry {0}").format(je_doc.name),
				_WIP_VOUCHER_TYPE,
				je_doc.name,
			)
			out["wip_journal_entry"] = post_wip_reversal_journal_multi(
				wip_segments,
				posting_date,
				company,
				remark,
			)

	return out or None


def _should_skip_journal_entry(je_doc):
	"""Recognition, reversal, and internal-billing journals already handle their own balances."""
	flags = getattr(je_doc, "flags", None)
	if flags is not None and getattr(flags, "skip_logistics_recognition_reversal", False):
		return True
	remark = je_doc.get("user_remark") or ""
	if _REVERSAL_MARKER_PREFIX in remark:
		return True
	if _INTERNAL_BILLING_REMARK in remark:
		return True
	return False


def collect_journal_entry_recognition_lines(je_doc):
	"""
	Group actual revenue and cost on a Journal Entry by Job Number.

	:return: {job_number: {"wip": [(amount, item_code), ...], "accrual": [(amount, item_code), ...]}}
	"""
	header_jcn = (je_doc.get("job_number") or "").strip()
	account_cache = {}
	policy_accounts = {}
	buckets = defaultdict(lambda: {"wip": [], "accrual": []})

	for row in je_doc.get("accounts") or []:
		jcn = (row.get("job_number") or "").strip() or header_jcn
		if not jcn:
			continue
		account = (row.get("account") or "").strip()
		if not account:
			continue
		if account in _policy_accounts_for(jcn, policy_accounts):
			continue

		info = _account_info(account, account_cache)
		jp = (info.get("job_profit_account_type") or "").strip()
		if jp in _SKIP_JOB_PROFIT_TYPES:
			continue

		item_code = _je_row_item_code(row)
		root_type = (info.get("root_type") or "").strip()
		account_type = (info.get("account_type") or "").strip()
		debit = _row_debit(row)
		credit = _row_credit(row)

		if debit > 0 and (
			root_type == "Expense" or is_stock_received_not_billed_cost_account(root_type, account_type)
		):
			buckets[jcn]["accrual"].append((debit, item_code))
		if credit > 0 and root_type == "Income":
			buckets[jcn]["wip"].append((credit, item_code))

	return {jcn: sides for jcn, sides in buckets.items() if sides["wip"] or sides["accrual"]}


def _policy_accounts_for(jcn, cache):
	if jcn not in cache:
		accounts = set()
		try:
			policy = get_recognition_policy_for_job(jcn) or {}
		except Exception:
			policy = {}
		for key in (
			"wip_account",
			"revenue_liability_account",
			"cost_accrual_account",
			"accrued_cost_liability_account",
		):
			name = (policy.get(key) or "").strip() if isinstance(policy, dict) else (policy.get(key) or "")
			if name:
				accounts.add(name)
		cache[jcn] = accounts
	return cache[jcn]


def _account_info(account, cache):
	if account not in cache:
		fields = ["root_type", "account_type"]
		if _account_has_job_profit_type():
			fields.append("job_profit_account_type")
		cache[account] = frappe.db.get_value("Account", account, fields, as_dict=True) or {}
	return cache[account]


def _account_has_job_profit_type():
	try:
		return bool(frappe.db.has_column("Account", "job_profit_account_type"))
	except Exception:
		return False


def _je_row_item_code(row):
	fn = get_item_link_fieldname("Journal Entry Account")
	if fn:
		code = row.get(fn)
		if code:
			return code
	return row.get("item") or row.get("item_code")


def _row_debit(row):
	debit = flt(row.get("debit"))
	if debit:
		return debit
	return flt(row.get("debit_in_account_currency"))


def _row_credit(row):
	credit = flt(row.get("credit"))
	if credit:
		return credit
	return flt(row.get("credit_in_account_currency"))


def _job_from_jcn(jcn):
	if not jcn or not frappe.db.exists("Job Number", jcn):
		return None
	jcn_doc = frappe.get_doc("Job Number", jcn)
	job_dt = jcn_doc.job_type
	job_no = jcn_doc.job_no
	if not job_dt or not job_no or not frappe.db.exists(job_dt, job_no):
		return None
	return frappe.get_doc(job_dt, job_no)


def _accrual_segments(lines_by_jcn, company):
	segments = []
	item_fn_gl = get_item_dimension_fieldname_on_gl_entry()
	for jcn, sides in lines_by_jcn.items():
		debit_lines = sides.get("accrual") or []
		if not debit_lines:
			continue
		policy = get_recognition_policy_for_job(jcn)
		if not policy:
			continue
		cost_acc = policy.get("cost_accrual_account")
		liab_acc = policy.get("accrued_cost_liability_account")
		if not cost_acc or not liab_acc:
			continue
		job = _job_from_jcn(jcn)
		if not job or not frappe.get_meta(job.doctype).has_field("accrual_amount"):
			continue
		remaining = flt(job.get("accrual_amount"))
		if remaining <= 0:
			continue
		pairs = _pairs_for_lines(
			debit_lines,
			remaining,
			company,
			item_fn_gl,
			lambda item_code: _paired_accrual_open_for_item(
				jcn, company, cost_acc, liab_acc, item_fn_gl, item_code
			),
		)
		if pairs:
			segments.append((job, pairs))
	return segments


def _wip_segments(lines_by_jcn, company):
	segments = []
	item_fn_gl = get_item_dimension_fieldname_on_gl_entry()
	for jcn, sides in lines_by_jcn.items():
		credit_lines = sides.get("wip") or []
		if not credit_lines:
			continue
		job = _job_from_jcn(jcn)
		if not job or not frappe.get_meta(job.doctype).has_field("wip_amount"):
			continue
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
		pairs = _pairs_for_lines(
			credit_lines,
			remaining,
			company,
			item_fn_gl,
			lambda item_code: _paired_wip_open_for_item(
				jcn, company, wip_acc, liab_acc, item_fn_gl, item_code
			),
		)
		if pairs:
			segments.append((job, pairs))
	return segments


def _pairs_for_lines(lines, remaining, company, item_fn_gl, open_for_item):
	"""Same cap as Purchase Invoice / Sales Invoice: item open balance, else min(line, remaining)."""
	remaining = flt(remaining)
	pairs = []
	for amt, item_code in lines:
		amt = flt(amt)
		if amt <= 0 or remaining <= 0:
			continue
		rev = 0
		if item_fn_gl and item_code:
			open_item = flt(open_for_item(item_code))
			if open_item > 0:
				rev = compute_item_reversal_amount(
					amt, open_item, remaining, item_code, set(), company
				)
		if rev <= 0:
			rev = min(amt, remaining)
		if rev <= 0:
			continue
		pairs.append((rev, item_code))
		remaining -= rev
	return pairs
