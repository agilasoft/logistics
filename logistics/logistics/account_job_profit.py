# -*- coding: utf-8 -*-
# Copyright (c) 2025, www.agilasoft.com and contributors

import frappe
from frappe import _

PL_ACCOUNT_TYPES = ("Income Account", "Expense Account")
JOB_PROFIT_ALL = ("Profit", "WIP", "Accrual", "Disbursements")


def validate_account_job_profit(doc, method=None):
	"""Enforce Job Profit Account Type vs Account Type (matches client options)."""
	meta = frappe.get_meta("Account")
	if not meta.get_field("job_profit_account_type"):
		return
	if doc.is_group:
		doc.job_profit_account_type = None
		return
	val = (doc.get("job_profit_account_type") or "").strip()
	if not val:
		return
	at = (doc.get("account_type") or "").strip()
	if at in PL_ACCOUNT_TYPES:
		if val not in JOB_PROFIT_ALL:
			frappe.throw(
				_("Job Profit Account Type must be one of: {0}").format(", ".join(JOB_PROFIT_ALL)),
				title=_("Invalid Job Profit Account Type"),
			)
	else:
		if val != "Disbursements":
			frappe.throw(
				_(
					"Job Profit Account Type may only be **Disbursements** unless Account Type is "
					"**Income Account** or **Expense Account** (then Profit, WIP, Accrual, or Disbursements)."
				),
				title=_("Invalid Job Profit Account Type"),
			)
