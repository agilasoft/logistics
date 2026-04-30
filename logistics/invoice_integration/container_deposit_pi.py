# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""
Purchase Invoice: route container-deposit item lines to Deposits Pending for Refund Request (Sea Freight Settings).

Submitted PI posts Dr Deposits Pending for Refund Request / Cr Payables for those lines (standard ERPNext PI GL).
"""

from __future__ import unicode_literals

import frappe

JOB_DOCTYPES_CONTAINER_DEPOSIT = ("Sea Shipment", "Declaration")


def _pending_refund_account(company=None):
	if not company:
		company = frappe.defaults.get_user_default("Company")
	try:
		from logistics.sea_freight.doctype.sea_freight_settings.sea_freight_settings import SeaFreightSettings

		sf = SeaFreightSettings.get_settings(company)
	except Exception:
		return None
	return sf.get("container_deposit_pending_refund_account") if sf else None


def get_container_deposit_pending_refund_account(company=None):
	"""Sea Freight Settings: Deposits Pending for Refund Request account (for PI expense and charge hints)."""
	return _pending_refund_account(company)


def item_is_container_deposit(item_code):
	if not item_code:
		return False
	if not frappe.db.has_column("Item", "custom_container_deposit_charge"):
		return False
	return frappe.utils.cint(
		frappe.db.get_value("Item", item_code, "custom_container_deposit_charge") or 0
	)


def item_is_container_charge(item_code):
	"""Operational container charge item — rolls into Container charges from GL (Item dimension); not deducted from deposit."""
	if not item_code:
		return False
	if not frappe.db.has_column("Item", "custom_container_charge"):
		return False
	return frappe.utils.cint(frappe.db.get_value("Item", item_code, "custom_container_charge") or 0)


def apply_container_deposit_expense_account(doc, method=None):
	"""Set expense_account on PI item rows for container-deposit items linked to Sea Shipment / Declaration."""
	if doc.doctype != "Purchase Invoice":
		return
	if doc.docstatus != 0:
		return
	pending = _pending_refund_account(doc.company)
	if not pending:
		return
	header_ref_dt = doc.get("reference_doctype") or ""
	header_ref_name = doc.get("reference_name") or ""

	for row in doc.get("items") or []:
		if not row.get("item_code"):
			continue
		if not item_is_container_deposit(row.item_code):
			continue
		job_dt = row.get("reference_doctype") or header_ref_dt
		job_nm = row.get("reference_name") or header_ref_name
		if job_dt not in JOB_DOCTYPES_CONTAINER_DEPOSIT or not job_nm:
			continue
		if not frappe.db.exists(job_dt, job_nm):
			continue
		row.expense_account = pending
