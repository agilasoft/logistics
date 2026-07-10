# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
After internal billing Journal Entry is submitted, reverse WIP and cost accrual on referenced
Internal Jobs (same amounts basis as internal billing: get_internal_job_revenue_and_cost).
"""

from __future__ import unicode_literals

import frappe
from frappe.utils import flt

from logistics.billing.cross_module_billing import get_internal_job_revenue_and_cost
from logistics.billing.internal_billing import INTERNAL_BILLING_JOB_TYPES
from logistics.invoice_integration.accrual_reversal import post_cost_accrual_reversal_journal_multi
from logistics.invoice_integration.recognition_voucher_reversal import (
	reversal_journal_entry_exists_by_remark_locate,
)
from logistics.invoice_integration.wip_reversal import post_wip_reversal_journal_multi


def _linked_jobs_on_internal_billing_je(je_doc):
	"""Resolve linked jobs from JE credit rows (job_number) or legacy reference fields."""
	seen = set()
	for row in je_doc.get("accounts") or []:
		rt = row.get("reference_type")
		rn = row.get("reference_name")
		if rt in INTERNAL_BILLING_JOB_TYPES and rn and frappe.db.exists(rt, rn):
			seen.add((rt, rn))
			continue
		if flt(row.get("credit_in_account_currency")) <= 0:
			continue
		jcn = row.get("job_number")
		if not jcn:
			continue
		for jt in INTERNAL_BILLING_JOB_TYPES:
			jn = frappe.db.get_value(jt, {"job_number": jcn}, "name")
			if jn:
				seen.add((jt, jn))
				break
	return seen


def reverse_recognition_for_internal_billing_je(je_doc, end_customer):
	"""
	Reverse WIP and accrual for each job referenced on the internal billing JE.

	:param je_doc: submitted Journal Entry (internal billing)
	:param end_customer: Sales Quote customer (same as internal billing build)
	:return: dict with optional wip_journal_entry, accrual_journal_entry
	"""
	if not je_doc or getattr(je_doc, "docstatus", None) != 1:
		return {}

	seen = _linked_jobs_on_internal_billing_je(je_doc)

	if not seen:
		return {}

	wip_segments = []
	accrual_segments = []

	for job_type, job_no in seen:
		job = frappe.get_doc(job_type, job_no)
		rev, cost = get_internal_job_revenue_and_cost(job_type, job_no, customer=end_customer)
		meta = frappe.get_meta(job_type)

		if meta.has_field("wip_amount") and flt(job.get("wip_amount")) > 0 and flt(rev) > 0:
			wip_amt = min(flt(rev), flt(job.get("wip_amount")))
			wip_segments.append((job, [(wip_amt, None)]))

		if meta.has_field("accrual_amount") and flt(job.get("accrual_amount")) > 0 and flt(cost) > 0:
			acc_amt = min(flt(cost), flt(job.get("accrual_amount")))
			accrual_segments.append((job, [(acc_amt, None)]))

	out = {}
	posting_date = je_doc.posting_date
	company = je_doc.company

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
