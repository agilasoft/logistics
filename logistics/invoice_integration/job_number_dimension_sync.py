# -*- coding: utf-8 -*-
"""
Backfill Job Number accounting dimension on invoice item rows.

Why: Some flows set job_number on the Purchase Invoice header, but GL tagging relies
on the Accounting Dimension field being set on the item row (Purchase Invoice Item).

Special Project PIs must tag each line with the lifecycle leg job JCN (Project Job,
Sea Shipment, etc.), not the programme Special Project job_number.

Credit / debit notes (is_return) also miss Job Number because ERPNext creates the
Accounting Dimension field with no_copy=1, so make_sales_return / make_purchase_return
do not copy it from the original invoice.
"""

from __future__ import unicode_literals

import frappe
from frappe.utils import flt

from logistics.job_management.gl_reference_dimension import reference_dimension_row_dict
from logistics.invoice_integration.purchase_invoice_api import _sea_shipment_row_cost
from logistics.special_projects.special_project_si_job_number import (
	resolve_job_number_for_special_project_charge,
)

RETURN_ITEM_LINK_FIELDS = {
	"Sales Invoice": "sales_invoice_item",
	"Purchase Invoice": "purchase_invoice_item",
}


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


def _apply_job_number_dimension_on_item(
	row,
	child_doctype: str,
	job_number: str,
	*,
	programme_jcn: str | None = None,
	overwrite_programme: bool = False,
) -> None:
	if not job_number:
		return
	dim_map = reference_dimension_row_dict(child_doctype, "Job Number", job_number)
	if not dim_map:
		dim_map = {"job_number": job_number}
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


def _apply_job_number_dimension_on_pi_item(
	row,
	job_number: str,
	*,
	programme_jcn: str | None = None,
	overwrite_programme: bool = False,
) -> None:
	_apply_job_number_dimension_on_item(
		row,
		"Purchase Invoice Item",
		job_number,
		programme_jcn=programme_jcn,
		overwrite_programme=overwrite_programme,
	)


def _strip(value) -> str:
	return (value or "").strip()


def copy_job_number_from_return_against(doc, method=None):
	"""Copy Job Number from the original invoice onto a credit/debit note.

	Accounting Dimension fields are created with no_copy=1, so ERPNext's return
	mapper omits them. Header and item rows are filled when missing.
	"""
	if not getattr(doc, "is_return", None):
		return
	doctype = getattr(doc, "doctype", None)
	link_field = RETURN_ITEM_LINK_FIELDS.get(doctype)
	if not link_field:
		return
	return_against = _strip(getattr(doc, "return_against", None))
	if not return_against:
		return
	try:
		if not frappe.get_meta(doctype).get_field("job_number"):
			return
	except Exception:
		return
	if not frappe.db.exists(doctype, return_against):
		return

	source_header_jn = _strip(frappe.db.get_value(doctype, return_against, "job_number")) or None
	child_dt = "{0} Item".format(doctype)
	source_items = {
		r.name: _strip(r.job_number) or None
		for r in frappe.get_all(
			child_dt,
			filters={"parent": return_against},
			fields=["name", "job_number"],
		)
	}
	if not source_header_jn:
		unique = {v for v in source_items.values() if v}
		if len(unique) == 1:
			source_header_jn = unique.pop()

	if source_header_jn and not _strip(getattr(doc, "job_number", None)):
		doc.job_number = source_header_jn

	for row in doc.get("items") or []:
		if _strip(getattr(row, "job_number", None)):
			continue
		src_name = _strip(getattr(row, link_field, None))
		line_jn = source_items.get(src_name) if src_name else None
		job_number = line_jn or source_header_jn
		if job_number:
			_apply_job_number_dimension_on_item(row, child_dt, job_number)


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
	Returns copy Job Number from the original invoice when this PI is a debit note.
	"""
	if getattr(doc, "doctype", None) != "Purchase Invoice":
		return
	if getattr(doc, "docstatus", None) != 0:
		return

	copy_job_number_from_return_against(doc)

	if _sync_special_project_pi_item_job_numbers(doc):
		return

	job_number = _resolve_job_number_for_pi(doc)
	if not job_number:
		return

	for row in doc.get("items") or []:
		_apply_job_number_dimension_on_pi_item(row, job_number)


def sync_job_number_dimension_on_sales_invoice_items(doc, method=None):
	"""Hook: validate/before_submit on Sales Invoice (draft only).

	Credit notes inherit Job Number from return_against. Header Job Number is
	also copied onto item rows when the dimension is missing.
	"""
	if getattr(doc, "doctype", None) != "Sales Invoice":
		return
	if getattr(doc, "docstatus", None) != 0:
		return

	copy_job_number_from_return_against(doc)

	job_number = _strip(getattr(doc, "job_number", None))
	if not job_number:
		return
	for row in doc.get("items") or []:
		_apply_job_number_dimension_on_item(row, "Sales Invoice Item", job_number)


def _set_job_number_on_ledgers(doctype: str, name: str, job_number: str) -> None:
	if not job_number:
		return
	for ledger_dt in ("GL Entry", "Payment Ledger Entry"):
		if not frappe.db.has_column(ledger_dt, "job_number"):
			continue
		frappe.db.sql(
			"""
			UPDATE `tab{0}`
			SET job_number = %s
			WHERE voucher_type = %s AND voucher_no = %s
			  AND IFNULL(job_number, '') = ''
			""".format(ledger_dt),
			(job_number, doctype, name),
		)


def _return_invoices_needing_job_number(doctype: str) -> list[str]:
	child = "{0} Item".format(doctype)
	return [
		r.name
		for r in frappe.db.sql(
			"""
			SELECT ret.name
			FROM `tab{doctype}` ret
			WHERE ret.is_return = 1
			  AND IFNULL(ret.return_against, '') != ''
			  AND (
				IFNULL(ret.job_number, '') = ''
				OR EXISTS (
					SELECT 1 FROM `tab{child}` sii
					WHERE sii.parent = ret.name AND IFNULL(sii.job_number, '') = ''
				)
			  )
			""".format(doctype=doctype, child=child),
			as_dict=True,
		)
	]


def backfill_one_return_invoice_job_number(doctype: str, name: str) -> str | None:
	"""Copy Job Number from the original invoice onto a saved return (incl. submitted)."""
	link_field = RETURN_ITEM_LINK_FIELDS.get(doctype)
	if not link_field or not name:
		return None
	if not frappe.db.has_column(doctype, "job_number"):
		return None

	return_against = _strip(frappe.db.get_value(doctype, name, "return_against"))
	if not return_against or not frappe.db.exists(doctype, return_against):
		return None

	child_dt = "{0} Item".format(doctype)
	source_header_jn = _strip(frappe.db.get_value(doctype, return_against, "job_number")) or None
	source_items = {
		r.name: _strip(r.job_number) or None
		for r in frappe.get_all(
			child_dt,
			filters={"parent": return_against},
			fields=["name", "job_number"],
		)
	}
	if not source_header_jn:
		unique = {v for v in source_items.values() if v}
		if len(unique) == 1:
			source_header_jn = unique.pop()

	current_header = _strip(frappe.db.get_value(doctype, name, "job_number")) or None
	header_jn = current_header or source_header_jn
	if source_header_jn and not current_header:
		frappe.db.set_value(doctype, name, "job_number", source_header_jn, update_modified=False)
		header_jn = source_header_jn

	if frappe.db.has_column(child_dt, "job_number"):
		fields = ["name", "job_number", link_field]
		for item in frappe.get_all(child_dt, filters={"parent": name}, fields=fields):
			if _strip(item.get("job_number")):
				continue
			src_name = _strip(item.get(link_field))
			line_jn = (source_items.get(src_name) if src_name else None) or header_jn
			if line_jn:
				frappe.db.set_value(child_dt, item.name, "job_number", line_jn, update_modified=False)

	_set_job_number_on_ledgers(doctype, name, header_jn)
	return header_jn


def backfill_job_number_on_existing_return_invoices() -> int:
	"""Patch helper: fill Job Number on existing credit/debit notes and their ledgers."""
	updated = 0
	for doctype in ("Sales Invoice", "Purchase Invoice"):
		if not frappe.db.has_column(doctype, "job_number"):
			continue
		for name in _return_invoices_needing_job_number(doctype):
			if backfill_one_return_invoice_job_number(doctype, name):
				updated += 1
	return updated
