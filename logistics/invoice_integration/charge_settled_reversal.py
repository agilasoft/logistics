# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Shared helpers for WIP / accrual reversal when invoices settle linked charge rows."""

from __future__ import unicode_literals

import frappe
from frappe.utils import flt

from logistics.utils.freight_95_5 import _rate_precision

CHARGES_FIELD_BY_JOB = {
	"Transport Job": "charges",
	"Air Shipment": "charges",
	"Sea Shipment": "charges",
	"Warehouse Job": "charges",
	"Declaration": "charges",
	"General Job": "charges",
	"Project Job": "charges",
	"Special Project": "charges",
	"Docket": "charges",
}


def _charge_item_code(charge):
	return getattr(charge, "item_code", None) or getattr(charge, "charge_item", None)


def get_charge_items_settled_by_sales_invoice(job, si_name):
	"""Item codes on job charge rows linked to this submitted Sales Invoice."""
	return _charge_items_settled_by_voucher(job, "sales_invoice", si_name)


def get_charge_items_settled_by_purchase_invoice(job, pi_name):
	"""Item codes on job charge rows linked to this submitted Purchase Invoice."""
	return _charge_items_settled_by_voucher(job, "purchase_invoice", pi_name)


def _charge_items_settled_by_voucher(job, voucher_field, voucher_name):
	items = set()
	if not job or not voucher_name:
		return items
	charges_field = CHARGES_FIELD_BY_JOB.get(job.doctype)
	if not charges_field:
		return items
	meta = frappe.get_meta(job.doctype)
	if not meta.get_field(charges_field):
		return items
	child_meta = frappe.get_meta(meta.get_field(charges_field).options)
	if not child_meta.get_field(voucher_field):
		return items
	for row in job.get(charges_field) or []:
		if getattr(row, voucher_field, None) != voucher_name:
			continue
		item_code = _charge_item_code(row)
		if item_code:
			items.add(item_code)
	return items


def recognition_reversal_tolerance(company, open_item):
	"""Allow small invoice vs recognition variance (currency precision + relative cap)."""
	prec = _rate_precision(company)
	base = 10 ** (-prec) if prec > 0 else 0.01
	return max(flt(base), flt(open_item) * 0.001)


def compute_item_reversal_amount(amt, open_item, remaining, item_code, settled_items, company):
	"""
	Amount to reverse for one item line.

	When the invoice settles a linked charge row, reverse full open GL balance for that item
	(avoid WIP residue from rounding). Otherwise cap at invoice line amount (partial invoice).
	"""
	if remaining <= 0:
		return 0
	amt = flt(amt)
	open_item = flt(open_item)
	remaining = flt(remaining)
	if open_item <= 0:
		return min(amt, remaining) if amt > 0 else 0
	if item_code and item_code in settled_items:
		return min(open_item, remaining)
	tol = recognition_reversal_tolerance(company, open_item)
	if amt >= open_item - tol:
		return min(open_item, remaining)
	return min(amt, open_item, remaining)
