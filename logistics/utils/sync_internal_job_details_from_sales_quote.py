# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Copy Transport / Customs parameter fields from Sales Quote Charge into Internal Job Detail rows."""

from __future__ import annotations

from typing import Any

import frappe

from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal
from logistics.utils.internal_job_detail_copy import internal_job_detail_row_as_dict
from logistics.utils.sales_quote_charge_parameters import extract_sales_quote_charge_parameters

# (Sales Quote Charge.service_type value, default Internal Job Detail.job_type when empty)
_SERVICE_SPECS: tuple[tuple[str, str], ...] = (
	("Transport", "Transport Order"),
	("Customs", "Declaration Order"),
)


def _first_charge_for_service(sales_quote_doc: Any, service_label: str):
	for row in getattr(sales_quote_doc, "charges", None) or []:
		if sales_quote_charge_service_types_equal(getattr(row, "service_type", None), service_label):
			return row
	return None


def _find_open_detail_row(parent_doc: Any, service_label: str):
	for row in getattr(parent_doc, "internal_job_details", None) or []:
		if (getattr(row, "service_type", None) or "").strip() != service_label:
			continue
		if (getattr(row, "job_no", None) or "").strip():
			continue
		return row
	return None


def _find_any_detail_row(parent_doc: Any, service_label: str):
	for row in getattr(parent_doc, "internal_job_details", None) or []:
		if (getattr(row, "service_type", None) or "").strip() == service_label:
			return row
	return None


def _apply_params_to_row(row: Any, params: dict[str, Any], default_job_type: str, service_label: str) -> None:
	if not (getattr(row, "job_type", None) or "").strip():
		row.job_type = default_job_type
	row.service_type = service_label
	for k, v in params.items():
		if hasattr(row, k):
			setattr(row, k, v)


def sync_internal_job_details_from_sales_quote(parent_doc: Any, sales_quote_doc: Any) -> None:
	"""Merge Transport and Customs charge parameters from the quote into internal_job_details.

	Updates an existing **open** row (same service_type, no job_no) or appends a new row when none
	exists. Skips when a linked job_no is already set for that service (user-created link).
	"""
	if not parent_doc or not sales_quote_doc:
		return
	meta = frappe.get_meta(getattr(parent_doc, "doctype", None) or "")
	if not meta.get_field("internal_job_details"):
		return

	for service_label, default_job_type in _SERVICE_SPECS:
		charge = _first_charge_for_service(sales_quote_doc, service_label)
		if not charge:
			continue
		params = extract_sales_quote_charge_parameters(charge)
		open_row = _find_open_detail_row(parent_doc, service_label)
		if open_row:
			_apply_params_to_row(open_row, params, default_job_type, service_label)
			continue
		if _find_any_detail_row(parent_doc, service_label):
			continue
		new_row: dict[str, Any] = {
			"service_type": service_label,
			"job_type": default_job_type,
		}
		new_row.update(params)
		parent_doc.append("internal_job_details", new_row)


def build_internal_job_details_payload_for_quote_response(parent_doctype: str, doc: Any, sales_quote_doc: Any) -> list[dict]:
	"""Merge existing internal_job_details on doc with quote charge parameters; return rows for the desk API."""
	work = frappe.new_doc(parent_doctype)
	if doc:
		for r in getattr(doc, "internal_job_details", None) or []:
			work.append("internal_job_details", internal_job_detail_row_as_dict(r))
	sync_internal_job_details_from_sales_quote(work, sales_quote_doc)
	return [internal_job_detail_row_as_dict(r) for r in work.internal_job_details]
