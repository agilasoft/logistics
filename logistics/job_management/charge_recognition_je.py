# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Persist WIP / accrual adjustment Journal Entry links on job charge rows (not parent job)."""

from __future__ import unicode_literals

import frappe

JOB_TYPE_TO_CHARGES_CHILD = {
	"Air Shipment": ("charges", "Air Shipment Charges"),
	"Sea Shipment": ("charges", "Sea Shipment Charges"),
	"Transport Job": ("charges", "Transport Job Charges"),
	"Warehouse Job": ("charges", "Warehouse Job Charges"),
	"Declaration": ("charges", "Declaration Charges"),
}


def _row_item_code(row):
	return (row.get("item_code") or row.get("charge_item") or "").strip()


def set_wip_adjustment_je_on_charges(job_doctype, job_name, je_name, item_codes=None):
	"""
	Update wip_adjustment_journal_entry on charge child rows.

	:param item_codes: If set, only rows with WIP recognition whose item is in this set.
	                   None = all rows that have wip_recognition_journal_entry set.
	"""
	if not je_name:
		return
	mapping = JOB_TYPE_TO_CHARGES_CHILD.get(job_doctype)
	if not mapping:
		return
	_, child_dt = mapping
	if not frappe.db.table_exists(child_dt):
		return
	meta = frappe.get_meta(child_dt)
	if not meta.has_field("wip_adjustment_journal_entry"):
		return

	rows = frappe.get_all(
		child_dt,
		filters={"parent": job_name, "parenttype": job_doctype},
		fields=["name", "item_code", "charge_item", "wip_recognition_journal_entry"],
	)
	for r in rows:
		if not r.get("wip_recognition_journal_entry"):
			continue
		if item_codes is not None and _row_item_code(r) not in item_codes:
			continue
		frappe.db.set_value(
			child_dt,
			r.name,
			"wip_adjustment_journal_entry",
			je_name,
			update_modified=False,
		)


def set_accrual_adjustment_je_on_charges(job_doctype, job_name, je_name, item_codes=None):
	"""
	Update accrual_adjustment_journal_entry on charge child rows.

	:param item_codes: If set, only rows with accrual recognition whose item is in this set.
	                   None = all rows that have accrual_recognition_journal_entry set.
	"""
	if not je_name:
		return
	mapping = JOB_TYPE_TO_CHARGES_CHILD.get(job_doctype)
	if not mapping:
		return
	_, child_dt = mapping
	if not frappe.db.table_exists(child_dt):
		return
	meta = frappe.get_meta(child_dt)
	if not meta.has_field("accrual_adjustment_journal_entry"):
		return

	rows = frappe.get_all(
		child_dt,
		filters={"parent": job_name, "parenttype": job_doctype},
		fields=["name", "item_code", "charge_item", "accrual_recognition_journal_entry"],
	)
	for r in rows:
		if not r.get("accrual_recognition_journal_entry"):
			continue
		if item_codes is not None and _row_item_code(r) not in item_codes:
			continue
		frappe.db.set_value(
			child_dt,
			r.name,
			"accrual_adjustment_journal_entry",
			je_name,
			update_modified=False,
		)
