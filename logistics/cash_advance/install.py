# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors

from __future__ import unicode_literals

import frappe


def after_migrate():
	if frappe.flags.in_install:
		return
	_ensure_cash_advance_settings()
	_backfill_account_require_job_number_for_revolving_fund()


def _ensure_cash_advance_settings():
	if not frappe.db.exists("DocType", "Cash Advance Settings"):
		return
	if frappe.db.exists("Cash Advance Settings", "Cash Advance Settings"):
		return
	doc = frappe.new_doc("Cash Advance Settings")
	doc.insert(ignore_permissions=True)


def _backfill_account_require_job_number_for_revolving_fund():
	if not frappe.db.has_column("Account", "require_job_number"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabAccount`
		SET require_job_number = 1
		WHERE fund_type = 'Revolving Fund'
		  AND IFNULL(require_job_number, 0) = 0
		"""
	)
