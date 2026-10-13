# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Company-safe accounting dimensions for invoices created from operational jobs.

A linked service posted in its own company uses that Linked Service's company,
branch, cost center, and profit center. An intercompany Sales Invoice follows
that Linked Service. An intercompany Purchase Invoice is posted in the Main
job's company and follows the Main job's company, branch, cost center, and
profit center. A value that belongs to the other company is not copied across.
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


def _parent_booking_doc(job: Any) -> Any | None:
	"""Parent booking when the operational job does not carry the Linked Service."""
	doctype = _norm(getattr(job, "doctype", None))
	if not job or not doctype:
		return None
	try:
		from logistics.billing.cross_module_billing import INTERNAL_JOB_PARENT_LINKS
	except Exception:
		return None
	parent = INTERNAL_JOB_PARENT_LINKS.get(doctype)
	if not parent:
		return None
	parent_doctype, link_field = parent
	parent_name = _norm(getattr(job, link_field, None))
	if not parent_name:
		return None
	try:
		if not frappe.db.exists(parent_doctype, parent_name):
			return None
		return frappe.get_doc(parent_doctype, parent_name)
	except Exception:
		return None


def _linked_service_name_for_job(job: Any) -> str:
	"""Linked Service name on the job, its parent booking, or a charge row."""
	if not job:
		return ""
	try:
		from logistics.utils.service_role_rules import get_linked_service_name
	except Exception:
		return ""
	for candidate in (job, _parent_booking_doc(job)):
		if not candidate:
			continue
		name = _norm(get_linked_service_name(candidate))
		if name:
			return name
	for row in _child_rows(job, "charges"):
		name = _source_value(row, "linked_service") or _source_value(row, "internal_job")
		if name:
			return name
	return ""


def _linked_service_record_dimensions(linked_service: str) -> dict[str, str]:
	"""Company, branch, cost center, and profit center stored on the Linked Service record.

	The operational job can still hold values copied from Main. Those are not
	used here.
	"""
	linked_service = _norm(linked_service)
	if not linked_service:
		return {}
	try:
		from logistics.utils.linked_service_compat import (
			linked_service_doctype,
			linked_service_record_exists,
		)

		if not linked_service_record_exists(linked_service):
			return {}
		stored = frappe.get_cached_doc(linked_service_doctype(), linked_service)
	except Exception:
		return {}
	found: dict[str, str] = {}
	for fieldname in ("company", "branch", "cost_center", "profit_center"):
		value = _norm(getattr(stored, fieldname, None))
		if value:
			found[fieldname] = value
	return found


def intercompany_sales_invoice_dimensions(job: Any, company: str | None = None) -> dict[str, str]:
	"""Company, branch, cost center, and profit center for the intercompany Sales Invoice.

	The Linked Service record is the only source. Values copied onto the
	operational job from Main are ignored, and a value that belongs to another
	company is omitted.
	"""
	raw = _linked_service_record_dimensions(_linked_service_name_for_job(job))
	invoice_company = _norm(raw.get("company") or company or _source_value(job, "company"))
	chosen = dimensions_belonging_to_company(invoice_company, raw)
	if invoice_company:
		chosen["company"] = invoice_company
	return chosen


def intercompany_purchase_invoice_dimensions(main_job: Any, company: str | None = None) -> dict[str, str]:
	"""Company, branch, cost center, and profit center for the intercompany Purchase Invoice.

	The Main job is the only source. Linked-service values are not a fallback.
	"""
	invoice_company = _norm(_source_value(main_job, "company") or company)
	chosen = dimensions_belonging_to_company(invoice_company, main_job) if main_job else {}
	if invoice_company:
		chosen["company"] = invoice_company
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


def _is_intercompany_invoice(doc: Any) -> bool:
	"""True for the intercompany Sales Invoice or Purchase Invoice leg."""
	flags = getattr(doc, "flags", None)
	if flags and flags.get("is_intercompany_invoice"):
		return True
	try:
		from logistics.intercompany.invoice_guard import INTERCOMPANY_SI_REMARKS_PREFIX
	except Exception:
		INTERCOMPANY_SI_REMARKS_PREFIX = "Intercompany:"
	remarks = _norm(getattr(doc, "remarks", None))
	if remarks.startswith(INTERCOMPANY_SI_REMARKS_PREFIX):
		return True
	name = _norm(getattr(doc, "name", None))
	if not name or name.startswith("new"):
		return False
	fieldname = {
		"Sales Invoice": "intercompany_sales_invoice",
		"Purchase Invoice": "intercompany_purchase_invoice",
	}.get(_norm(getattr(doc, "doctype", None)))
	if not fieldname:
		return False
	try:
		return bool(
			frappe.db.exists(
				"Intercompany Invoice Log",
				{fieldname: name, "status": "Created"},
			)
		)
	except Exception:
		return False


def _main_job_for_intercompany_invoice(doc: Any) -> Any | None:
	"""Main job linked from the operational job referenced on an intercompany invoice."""
	job = _reference_job(doc)
	if not job:
		return None
	try:
		from logistics.billing.cross_module_billing import resolve_internal_job_main_job

		main_type, main_name = resolve_internal_job_main_job(
			_norm(getattr(job, "doctype", None)),
			_norm(getattr(job, "name", None)),
		)
	except Exception:
		return None
	if not main_type or not main_name:
		return None
	try:
		if not frappe.db.exists(main_type, main_name):
			return None
		return frappe.get_doc(main_type, main_name)
	except Exception:
		return None


def _forced_intercompany_dimensions(doc: Any, company: str) -> dict[str, str] | None:
	"""Dimensions this intercompany invoice must follow, or None when it is not one.

	Sales Invoice follows the Linked Service. Purchase Invoice follows Main.
	An empty dict means the invoice is intercompany and the other party must
	not be used as a fallback.
	"""
	if not _is_intercompany_invoice(doc):
		return None
	doctype = _norm(getattr(doc, "doctype", None))
	if doctype == "Sales Invoice":
		source = intercompany_sales_invoice_dimensions(_reference_job(doc), company)
	elif doctype == "Purchase Invoice":
		source = intercompany_purchase_invoice_dimensions(
			_main_job_for_intercompany_invoice(doc),
			company,
		)
	else:
		return None
	return dimensions_belonging_to_company(company, source)


def _apply_forced_dimensions(doc: Any, meta: Any, company: str, forced: dict[str, str]) -> None:
	"""Write *forced* dimensions onto the header and lines when they belong to *company*."""
	header_values: dict[str, str] = {}
	for fieldname in DIMENSION_FIELDS:
		if meta is not None and not meta.get_field(fieldname):
			continue
		forced_value = _norm(forced.get(fieldname))
		current = _norm(getattr(doc, fieldname, None))
		if forced_value and dimension_belongs(fieldname, forced_value, company):
			_assign(doc, fieldname, forced_value)
			header_values[fieldname] = forced_value
			continue
		if current and dimension_belongs(fieldname, current, company):
			header_values[fieldname] = current
			continue
		if current:
			_assign(doc, fieldname, None)

	for table in CHILD_TABLES:
		for row in _child_rows(doc, table):
			for fieldname in DIMENSION_FIELDS:
				if not _row_has_field(row, fieldname):
					continue
				forced_value = _norm(forced.get(fieldname))
				if forced_value and dimension_belongs(fieldname, forced_value, company):
					_assign(row, fieldname, forced_value)
					continue
				current = _norm(getattr(row, fieldname, None))
				if not current or dimension_belongs(fieldname, current, company):
					continue
				_assign(row, fieldname, header_values.get(fieldname) or None)


def align_invoice_dimensions_to_company(doc: Any, method: str | None = None) -> None:
	"""Drop accounting dimensions that do not belong to the invoice company.

	Runs on before_validate, after insert defaults have filled empty lines from
	the user session. A line that already belongs to the company is left as-is.
	An invalid value is replaced from the header or the referenced operational
	job (Linked Service first). Blank lines stay blank.

	Intercompany invoices are stricter. The Sales Invoice follows the Linked
	Service, and the Purchase Invoice follows Main, even when the other party's
	value also passes the company check.
	"""
	company = _norm(getattr(doc, "company", None))
	if not doc or not company or not getattr(doc, "doctype", None):
		return
	try:
		meta = frappe.get_meta(doc.doctype)
	except Exception:
		return

	forced = _forced_intercompany_dimensions(doc, company)
	if forced is not None:
		_apply_forced_dimensions(doc, meta, company, forced)
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
