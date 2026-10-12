# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Company-safe accounting dimensions for invoices created from operational jobs.

A linked service is posted in the operating company. Its Purchase Invoice and
Sales Invoice must use that company's branch, cost center, and profit center.
Copying the main job's profit center (or leaving a line blank so a session
default from the main company is applied) fails ERPNext company validation.
"""

from __future__ import annotations

from typing import Any

import frappe

DIMENSION_FIELDS: tuple[str, ...] = ("branch", "cost_center", "profit_center", "project")
DIMENSION_DOCTYPES: dict[str, str] = {
	"branch": "Branch",
	"cost_center": "Cost Center",
	"profit_center": "Profit Center",
	"project": "Project",
}
CHILD_TABLES: tuple[str, ...] = ("items", "taxes")
OPERATIONAL_DOCTYPES = {
	"Transport Job",
	"Air Shipment",
	"Sea Shipment",
	"Warehouse Job",
	"Declaration",
	"Declaration Order",
	"Special Project",
	"Docket",
	"MICE Project",
	"Air Consolidation",
	"Sea Consolidation",
}


def _norm(value: Any) -> str:
	if value is None:
		return ""
	return str(value).strip()


def _child_rows(doc: Any, table: str) -> list:
	"""Child rows for a Document or a dict.

	``dict.items`` is a method, so attribute access cannot be used to read a
	child table stored under the key ``items``.
	"""
	if isinstance(doc, dict):
		rows = doc.get(table)
	else:
		rows = getattr(doc, table, None)
	if not rows:
		return []
	try:
		return list(rows)
	except TypeError:
		return []


def _source_value(source: Any, fieldname: str) -> str:
	if not source:
		return ""
	if isinstance(source, dict):
		return _norm(source.get(fieldname))
	return _norm(getattr(source, fieldname, None))


def _assign(target: Any, fieldname: str, value: Any) -> None:
	setter = getattr(target, "set", None)
	module = getattr(target.__class__, "__module__", "") or ""
	if callable(setter) and module.startswith("frappe"):
		setter(fieldname, value)
		return
	setattr(target, fieldname, value)


def dimension_belongs(fieldname: str, value: Any, company: str) -> bool:
	"""True when *value* may be posted on a document for *company*."""
	value = _norm(value)
	company = _norm(company)
	link_doctype = DIMENSION_DOCTYPES.get(fieldname)
	if not value or not company or not link_doctype:
		return False
	from logistics.utils.linked_service_company import _link_belongs_to_company

	try:
		return bool(_link_belongs_to_company(link_doctype, value, company))
	except Exception:
		return False


def linked_service_dimension_source(job: Any) -> dict[str, str]:
	"""Branch / cost center / profit center stored on the job's Linked Service."""
	if not job:
		return {}
	try:
		from logistics.utils.linked_service_compat import linked_service_doctype
		from logistics.utils.linked_service_company import accounting_dimensions_from_linked_service
		from logistics.utils.service_role_rules import (
			get_linked_service_name,
			is_linked_service_satellite,
		)

		if not is_linked_service_satellite(job):
			return {}
		ls_name = get_linked_service_name(job)
		if not ls_name:
			return {}
		stored = accounting_dimensions_from_linked_service(
			frappe._dict(doctype=linked_service_doctype(), name=ls_name)
		)
	except Exception:
		return {}
	return {fieldname: _norm(stored.get(fieldname)) for fieldname in DIMENSION_FIELDS if _norm(stored.get(fieldname))}


def dimensions_belonging_to_company(company: str, *sources: Any) -> dict[str, str]:
	"""First value of each dimension, walking *sources* in order, that belongs to *company*."""
	company = _norm(company)
	chosen: dict[str, str] = {}
	if not company:
		return chosen
	for fieldname in DIMENSION_FIELDS:
		for source in sources:
			value = _source_value(source, fieldname)
			if value and dimension_belongs(fieldname, value, company):
				chosen[fieldname] = value
				break
	return chosen


def dimensions_for_operational_job(job: Any, company: str | None = None) -> dict[str, str]:
	"""Dimensions for an invoice posted in the operational job's company.

	Linked satellites prefer the Linked Service record. A value that belongs to
	another company is omitted so it cannot be copied onto the invoice.
	"""
	if not job:
		return {}
	company = _norm(company or getattr(job, "company", None))
	if not company:
		return {}
	sources: list[Any] = []
	linked = linked_service_dimension_source(job)
	if linked:
		sources.append(linked)
	sources.append(job)
	return dimensions_belonging_to_company(company, *sources)


def _row_has_field(row: Any, fieldname: str) -> bool:
	doctype = _norm(getattr(row, "doctype", None))
	if not doctype:
		return True
	try:
		return bool(frappe.get_meta(doctype).get_field(fieldname))
	except Exception:
		return False


def stamp_dimensions(
	doc: Any,
	dims: dict[str, str] | None,
	*,
	include_children: bool = True,
	child_fields: tuple[str, ...] | None = None,
) -> None:
	"""Copy *dims* onto the invoice header and, when requested, item and tax rows."""
	clean = {fieldname: _norm(value) for fieldname, value in (dims or {}).items() if _norm(value)}
	if not doc or not clean:
		return
	try:
		meta = frappe.get_meta(doc.doctype)
	except Exception:
		meta = None
	for fieldname, value in clean.items():
		if meta is not None and not meta.get_field(fieldname):
			continue
		_assign(doc, fieldname, value)
	if not include_children:
		return
	allowed = child_fields or tuple(clean.keys())
	for table in CHILD_TABLES:
		for row in _child_rows(doc, table):
			for fieldname in allowed:
				value = clean.get(fieldname)
				if not value or not _row_has_field(row, fieldname):
					continue
				_assign(row, fieldname, value)


def _reference_job(doc: Any) -> Any | None:
	pairs = [(getattr(doc, "reference_doctype", None), getattr(doc, "reference_name", None))]
	for row in _child_rows(doc, "items"):
		pairs.append((getattr(row, "reference_doctype", None), getattr(row, "reference_name", None)))
	for doctype, name in pairs:
		doctype = _norm(doctype)
		name = _norm(name)
		if doctype not in OPERATIONAL_DOCTYPES or not name:
			continue
		try:
			if not frappe.db.exists(doctype, name):
				continue
			return frappe.get_doc(doctype, name)
		except Exception:
			continue
	return None


def align_invoice_dimensions_to_company(doc: Any, method: str | None = None) -> None:
	"""Drop accounting dimensions that do not belong to the invoice company.

	Runs on before_validate, after insert defaults have filled empty lines from
	the user session. A line that already belongs to the company is left as-is.
	An invalid value is replaced from the header or the referenced operational
	job (Linked Service first). Blank lines stay blank.
	"""
	company = _norm(getattr(doc, "company", None))
	if not doc or not company or not getattr(doc, "doctype", None):
		return
	try:
		meta = frappe.get_meta(doc.doctype)
	except Exception:
		return

	job_dims: dict[str, str] | None = None

	def _job_dims() -> dict[str, str]:
		nonlocal job_dims
		if job_dims is None:
			job = _reference_job(doc)
			job_dims = dimensions_for_operational_job(job, company) if job else {}
		return job_dims

	header_ok: dict[str, str] = {}
	for fieldname in DIMENSION_FIELDS:
		if not meta.get_field(fieldname):
			continue
		current = _norm(getattr(doc, fieldname, None))
		if current and dimension_belongs(fieldname, current, company):
			header_ok[fieldname] = current
			continue
		if not current:
			continue
		replacement = _job_dims().get(fieldname) or ""
		if replacement:
			_assign(doc, fieldname, replacement)
			header_ok[fieldname] = replacement
		else:
			_assign(doc, fieldname, None)

	for table in CHILD_TABLES:
		for row in _child_rows(doc, table):
			for fieldname in DIMENSION_FIELDS:
				if not _row_has_field(row, fieldname):
					continue
				current = _norm(getattr(row, fieldname, None))
				if not current or dimension_belongs(fieldname, current, company):
					continue
				replacement = header_ok.get(fieldname) or _job_dims().get(fieldname) or None
				_assign(row, fieldname, replacement)
