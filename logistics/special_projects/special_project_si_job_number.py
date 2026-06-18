# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Resolve Job Number for Sales Invoice lines created from Special Project programme charges."""

from __future__ import annotations

from typing import Any, Optional

import frappe
from frappe.utils import cint

from logistics.special_projects.special_project_charge_lifecycle import (
	find_lifecycle_row_for_charge,
)
from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal
from logistics.utils.special_project_internal_jobs import resolve_lifecycle_job_row_to_operational_ref


def _lifecycle_rows(sp_doc: Any) -> list[Any]:
	return list(sp_doc.get("lifecycle_jobs") or [])


def _find_lifecycle_row_for_charge(sp_doc: Any, charge: Any) -> Optional[Any]:
	return find_lifecycle_row_for_charge(sp_doc, charge)


def _job_number_on_doctype(doctype: str, name: str) -> Optional[str]:
	if not doctype or not name or not frappe.db.exists(doctype, name):
		return None
	meta = frappe.get_meta(doctype)
	if not meta.get_field("job_number"):
		return None
	return frappe.db.get_value(doctype, name, "job_number")


def _job_number_for_project_order(order_name: str) -> Optional[str]:
	order_jcn = _job_number_on_doctype("Project Order", order_name)
	if order_jcn:
		return order_jcn

	pjs = frappe.get_all(
		"Project Job",
		filters={"special_project_order": order_name, "job_number": ["is", "set"]},
		fields=["job_number"],
		order_by="creation asc",
		limit=1,
	)
	if pjs:
		row = pjs[0]
		jcn = row.get("job_number") if isinstance(row, dict) else getattr(row, "job_number", None)
		if jcn:
			return jcn
	return None


def _job_number_for_special_project_lifecycle_row(lifecycle_row: Any) -> Optional[str]:
	jt = (getattr(lifecycle_row, "job_type", None) or "").strip()
	jn = (getattr(lifecycle_row, "job_no", None) or "").strip()
	if not jn:
		return None

	if jt == "Project Job":
		return _job_number_on_doctype("Project Job", jn)
	if jt == "Project Order":
		return _job_number_for_project_order(jn)
	return None


def _job_number_for_operational_lifecycle_row(lifecycle_row: Any) -> Optional[str]:
	exec_ref = resolve_lifecycle_job_row_to_operational_ref(lifecycle_row)
	if exec_ref:
		jcn = _job_number_on_doctype(exec_ref[0], exec_ref[1])
		if jcn:
			return jcn

	jt = (getattr(lifecycle_row, "job_type", None) or "").strip()
	jn = (getattr(lifecycle_row, "job_no", None) or "").strip()
	if jt and jn:
		return _job_number_on_doctype(jt, jn)
	return None


def resolve_job_number_for_special_project_charge(sp_doc: Any, charge: Any) -> Optional[str]:
	"""
	Return the Job Number name for a Special Project programme charge row.

	Routes by charge ``service_type``:
	- Special Project → linked Project Job (via lifecycle → Project Order / Project Job)
	- Air, Sea, Transport, etc. → linked operational job (shipment, transport job, …)
	- Fallback → programme Special Project ``job_number``
	"""
	lifecycle_row = _find_lifecycle_row_for_charge(sp_doc, charge)
	service_type = getattr(charge, "service_type", None)

	if lifecycle_row:
		if sales_quote_charge_service_types_equal(service_type, "Special Project"):
			jcn = _job_number_for_special_project_lifecycle_row(lifecycle_row)
			if jcn:
				return jcn
		else:
			jcn = _job_number_for_operational_lifecycle_row(lifecycle_row)
			if jcn:
				return jcn

	programme_jcn = getattr(sp_doc, "job_number", None) or getattr(sp_doc, "job_costing_number", None)
	return programme_jcn or None
