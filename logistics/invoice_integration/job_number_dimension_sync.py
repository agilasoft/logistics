# -*- coding: utf-8 -*-
"""
Backfill Job Number accounting dimension on Purchase Invoice Item rows.

Why: Some flows set job_number on the Purchase Invoice header, but GL tagging relies
on the Accounting Dimension field being set on the item row (Purchase Invoice Item).

Special Project PIs must tag each line with the lifecycle leg job JCN (Project Job,
Sea Shipment, etc.), not the programme Special Project job_number.
"""

from __future__ import unicode_literals

import frappe
from frappe.utils import flt

from logistics.job_management.gl_reference_dimension import reference_dimension_row_dict
from logistics.invoice_integration.purchase_invoice_api import _sea_shipment_row_cost
from logistics.special_projects.special_project_si_job_number import (
	resolve_job_number_for_special_project_charge,
)


def _resolve_job_number_for_pi(doc) -> str | None:
	"""Return a job number for the PI from header or its reference doc."""
	job_number = (getattr(doc, "job_number", None) or "").strip()
	if job_number:
		return job_number

	ref_dt = (getattr(doc, "reference_doctype", None) or "").strip()
	ref_nm = (getattr(doc, "reference_name", None) or "").strip()
	if not ref_dt or not ref_nm:
		return None
	if not frappe.db.exists(ref_dt, ref_nm):
		return None
	return frappe.db.get_value(ref_dt, ref_nm, "job_number")


def _apply_job_number_dimension_on_pi_item(
	row,
	job_number: str,
	*,
	programme_jcn: str | None = None,
	overwrite_programme: bool = False,
) -> None:
	if not job_number:
		return
	dim_map = reference_dimension_row_dict("Purchase Invoice Item", "Job Number", job_number)
	if not dim_map:
		return
	for k, v in dim_map.items():
		current = getattr(row, k, None)
		if not current:
			setattr(row, k, v)
		elif (
			overwrite_programme
			and programme_jcn
			and current == programme_jcn
			and v != programme_jcn
		):
			setattr(row, k, v)


def _charge_matches_pi_item(charge, item) -> bool:
	item_code = getattr(charge, "item_code", None)
	if not item_code or item_code != getattr(item, "item_code", None):
		return False
	return flt(_sea_shipment_row_cost(charge), 2) == flt(getattr(item, "rate", 0), 2)


def _charges_linked_to_pi(sp_doc, pi_name: str) -> list:
	return [
		ch
		for ch in sp_doc.get("charges") or []
		if (getattr(ch, "purchase_invoice", None) or "") == pi_name
	]


def _match_pi_items_to_charges(items, charges) -> list[tuple]:
	"""Return [(pi_item_row, charge), ...] in PI item order."""
	used_charge_names: set[str] = set()
	pairs = []
	for item in items or []:
		matched = None
		for ch in charges:
			ch_name = getattr(ch, "name", None)
			if ch_name and ch_name in used_charge_names:
				continue
			if _charge_matches_pi_item(ch, item):
				matched = ch
				break
		if matched:
			ch_name = getattr(matched, "name", None)
			if ch_name:
				used_charge_names.add(ch_name)
			pairs.append((item, matched))
	return pairs


def _sync_special_project_pi_item_job_numbers(doc) -> bool:
	"""Per-line Job Number from linked SP charges; returns True when handled."""
	ref_dt = (getattr(doc, "reference_doctype", None) or "").strip()
	ref_nm = (getattr(doc, "reference_name", None) or "").strip()
	if ref_dt != "Special Project" or not ref_nm:
		return False
	if not frappe.db.exists("Special Project", ref_nm):
		return False

	sp = frappe.get_doc("Special Project", ref_nm)
	programme_jcn = (getattr(sp, "job_number", None) or getattr(sp, "job_costing_number", None) or "").strip() or None
	linked_charges = _charges_linked_to_pi(sp, doc.name)
	if not linked_charges:
		return False

	pairs = _match_pi_items_to_charges(doc.get("items") or [], linked_charges)
	if not pairs:
		return False

	for item, charge in pairs:
		line_jcn = resolve_job_number_for_special_project_charge(sp, charge)
		if not line_jcn:
			continue
		_apply_job_number_dimension_on_pi_item(
			item,
			line_jcn,
			programme_jcn=programme_jcn,
			overwrite_programme=True,
		)
	return True


def sync_job_number_dimension_on_purchase_invoice_items(doc, method=None):
	"""Hook: validate/before_submit on Purchase Invoice (draft only).

	Sets the Job Number Accounting Dimension on each PI item row when missing.
	Special Project PIs resolve per charge (leg job JCN); other PIs use header/reference.
	"""
	if getattr(doc, "doctype", None) != "Purchase Invoice":
		return
	if getattr(doc, "docstatus", None) != 0:
		return

	if _sync_special_project_pi_item_job_numbers(doc):
		return

	job_number = _resolve_job_number_for_pi(doc)
	if not job_number:
		return

	for row in doc.get("items") or []:
		_apply_job_number_dimension_on_pi_item(row, job_number)
