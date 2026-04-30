# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Internal Job Detail rows on operational documents: service_type scoping + parameters for integrations."""

from __future__ import annotations

from typing import Any, Optional

import frappe

from logistics.utils.charge_service_type import (
	IMPLIED_SERVICE_TYPE_BY_DOCTYPE,
	ROUTING_LEG_JOB_TYPES,
	canonical_charge_service_type_for_storage,
	effective_internal_job_detail_job_type,
)
from logistics.utils.sales_quote_charge_parameters import extract_sales_quote_charge_parameters


def _job_detail_rows(parent_doc: Any) -> list:
	if not parent_doc:
		return []
	return list(getattr(parent_doc, "internal_job_details", None) or [])


def job_detail_parameters_dict(row: Any) -> dict[str, Any]:
	if not row:
		return {}
	return extract_sales_quote_charge_parameters(row)


def _row_links_parent_doc(row: Any, parent_doc: Any) -> bool:
	"""True when this row's Job No points at parent and operational type matches parent's service leg."""
	my_name = getattr(parent_doc, "name", None)
	my_dt = getattr(parent_doc, "doctype", None)
	if getattr(row, "job_no", None) != my_name:
		return False
	row_jt = effective_internal_job_detail_job_type(row)
	if row_jt == my_dt:
		return True
	parent_svc = IMPLIED_SERVICE_TYPE_BY_DOCTYPE.get(my_dt)
	row_svc = IMPLIED_SERVICE_TYPE_BY_DOCTYPE.get(row_jt)
	return bool(parent_svc and row_svc and parent_svc == row_svc)


def get_internal_job_detail_for_parent(parent_doc: Any):
	"""Match an Internal Job Detail row to this document (job_no + job_type, else first applicable row)."""
	rows = _job_detail_rows(parent_doc)
	my_name = getattr(parent_doc, "name", None)
	my_dt = getattr(parent_doc, "doctype", None)
	acceptable = ROUTING_LEG_JOB_TYPES.get(my_dt) or ()

	for row in rows:
		if _row_links_parent_doc(row, parent_doc):
			return row

	for row in rows:
		if effective_internal_job_detail_job_type(row) not in acceptable:
			continue
		jn = getattr(row, "job_no", None)
		if jn and my_name and jn != my_name:
			continue
		return row
	return None


def job_detail_service_type_for_parent(parent_doc: Any, sales_quote_doc: Any = None) -> Optional[str]:
	"""If a matched Internal Job Detail row sets service_type, filter Sales Quote Charge rows when populating."""
	row = get_internal_job_detail_for_parent(parent_doc)
	if not row:
		return None
	st = (getattr(row, "service_type", None) or "").strip()
	return st or None


def _service_type_match(row: Any, want: str) -> bool:
	row_c = canonical_charge_service_type_for_storage(getattr(row, "service_type", None))
	want_c = canonical_charge_service_type_for_storage(want)
	return bool(row_c and want_c and row_c == want_c)


def get_internal_job_detail_by_service_type(parent_doc: Any, service_type: str, *, rows: list | None = None):
	"""Prefer row linked to parent with matching service_type, then applicable job_type, then any match.

	If ``rows`` is passed (e.g. form grid not yet saved), use it instead of ``parent_doc.internal_job_details``.
	"""
	rows = list(rows) if rows is not None else _job_detail_rows(parent_doc)
	want = (service_type or "").strip().lower()
	if not want:
		return None
	my_name = getattr(parent_doc, "name", None)
	my_dt = getattr(parent_doc, "doctype", None)
	acceptable = ROUTING_LEG_JOB_TYPES.get(my_dt) or ()

	for row in rows:
		if not _service_type_match(row, want):
			continue
		if _row_links_parent_doc(row, parent_doc):
			return row

	for row in rows:
		if not _service_type_match(row, want):
			continue
		if effective_internal_job_detail_job_type(row) not in acceptable:
			continue
		jn = getattr(row, "job_no", None)
		if jn and my_name and jn != my_name:
			continue
		return row

	for row in rows:
		if _service_type_match(row, want):
			return row
	return None


def get_first_internal_job_detail_by_service_type(parent_doc: Any, service_type: str):
	"""First row on parent_doc whose service_type matches."""
	want = (service_type or "").strip().lower()
	if not want:
		return None
	for row in _job_detail_rows(parent_doc):
		if _service_type_match(row, want):
			return row
	return None


def get_routing_parameters_for_service(parent_doc: Any, sales_quote: Any, service_type: str) -> dict[str, Any]:
	"""Parameters from Internal Job Detail on parent_doc (sales_quote arg ignored; kept for API compatibility)."""
	row = get_internal_job_detail_by_service_type(parent_doc, service_type)
	if row:
		return job_detail_parameters_dict(row)
	return {}


# Backward-compatible names
routing_leg_parameters_dict = job_detail_parameters_dict
get_sales_quote_job_detail_for_parent = get_internal_job_detail_for_parent
get_sales_quote_routing_leg_for_parent = get_internal_job_detail_for_parent
routing_leg_service_type_for_parent = job_detail_service_type_for_parent


def get_sales_quote_job_detail_by_service_type(parent_doc: Any, sales_quote_doc: Any, service_type: str):
	return get_internal_job_detail_by_service_type(parent_doc, service_type)


def get_sales_quote_routing_leg_by_service_type(parent_doc: Any, sales_quote_doc: Any, service_type: str):
	return get_internal_job_detail_by_service_type(parent_doc, service_type)


def get_first_sales_quote_job_detail_by_service_type(sales_quote_doc: Any, service_type: str):
	"""Deprecated: no job details on Sales Quote. Returns None."""
	return None


def get_first_sales_quote_routing_leg_by_service_type(sales_quote_doc: Any, service_type: str):
	return None
