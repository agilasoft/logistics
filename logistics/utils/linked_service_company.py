# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Operating company for a Linked Service (quote-defined, used on designated bookings)."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

_COMPANY_SCOPED_FIELDS: tuple[str, ...] = ("branch", "cost_center", "profit_center")
_SCOPED_FIELD_DOCTYPES: dict[str, str] = {
	"branch": "Branch",
	"cost_center": "Cost Center",
	"profit_center": "Profit Center",
}


def _row_val(row: Any, fieldname: str) -> Any:
	if row is None:
		return None
	if isinstance(row, dict):
		return row.get(fieldname)
	return getattr(row, fieldname, None)


def _norm(value: Any) -> str:
	if value is None:
		return ""
	return str(value).strip()


def _doctype_of(row: Any) -> str:
	dt = _row_val(row, "doctype")
	return _norm(dt)


def linked_service_name_from_row(row: Any) -> str:
	"""Linked Service name from a Linked Service doc, detail row, or charge row."""
	if not row:
		return ""
	dt = _doctype_of(row)
	if dt in ("Linked Service", "Internal Job"):
		return _norm(_row_val(row, "name"))
	from logistics.utils.linked_service_compat import row_linked_service_link

	return _norm(row_linked_service_link(row) or _row_val(row, "name"))


def company_from_linked_service(row_or_doc: Any) -> str:
	"""Company stored on the Linked Service (or copied onto a detail/charge row)."""
	direct = _norm(_row_val(row_or_doc, "company"))
	if direct:
		return direct
	dt = _doctype_of(row_or_doc)
	if dt in ("Linked Service", "Internal Job"):
		return ""
	ls_name = linked_service_name_from_row(row_or_doc)
	if not ls_name:
		return ""
	from logistics.utils.linked_service_compat import linked_service_doctype, linked_service_record_exists

	if not linked_service_record_exists(ls_name):
		return ""
	return _norm(frappe.db.get_value(linked_service_doctype(), ls_name, "company"))


def missing_linked_service_company_message(
	*,
	linked_service: str | None = None,
	service_type: str | None = None,
	sales_quote: str | None = None,
) -> str:
	st = _norm(service_type) or _("this service")
	ls = _norm(linked_service)
	sq = _norm(sales_quote)
	if ls and sq:
		return _(
			"Set Company on Linked Service {0} ({1}) on Sales Quote {2} before creating this booking from the main."
		).format(ls, st, sq)
	if sq:
		return _(
			"Set Company for {0} on Sales Quote {1} before creating this booking from the main."
		).format(st, sq)
	return _("Set Company on the Sales Quote Linked Service for {0} before creating this booking.").format(
		st
	)


def default_company_from_parent(parent_doc: Any) -> str:
	return _norm(_row_val(parent_doc, "company"))


def _company_field_for(doctype: str) -> str | None:
	try:
		meta = frappe.get_meta(doctype)
	except Exception:
		return None
	for fieldname in ("company", "custom_company"):
		if meta.has_field(fieldname):
			return fieldname
	return None


def _link_belongs_to_company(link_doctype: str, name: str, company: str) -> bool:
	"""True when *name* is usable under *company* (same company, or master is not company-scoped)."""
	name = _norm(name)
	company = _norm(company)
	if not name or not company:
		return False
	try:
		if not frappe.db.exists(link_doctype, name):
			return False
	except Exception:
		return False
	company_fn = _company_field_for(link_doctype)
	if not company_fn:
		return True
	actual = _norm(frappe.db.get_value(link_doctype, name, company_fn))
	return not actual or actual == company


def _first_link_for_company(link_doctype: str, company: str, extra: dict[str, Any] | None = None) -> str:
	filters: dict[str, Any] = dict(extra or {})
	company_fn = _company_field_for(link_doctype)
	if company_fn:
		filters[company_fn] = company
	try:
		return _norm(frappe.db.get_value(link_doctype, filters, "name", order_by="creation asc"))
	except Exception:
		return ""


def _default_scoped_value(fieldname: str, link_doctype: str, company: str) -> str:
	if fieldname == "cost_center":
		cc = _norm(frappe.db.get_value("Company", company, "cost_center"))
		if cc and _link_belongs_to_company("Cost Center", cc, company):
			return cc
	extra: dict[str, Any] = {}
	try:
		link_meta = frappe.get_meta(link_doctype)
		if link_meta.has_field("is_group"):
			extra["is_group"] = 0
		if link_meta.has_field("disabled"):
			extra["disabled"] = 0
	except Exception:
		pass
	return _first_link_for_company(link_doctype, company, extra)


def sync_company_scoped_fields_on_operational_doc(doc: Any, company: str) -> None:
	"""Keep or refill branch / cost center / profit center for *company*.

	Values that already belong to the operating company are kept. Values that belong
	to another company (or are empty) are replaced from that company's masters so
	mandatory fields on Transport Order, Declaration Order, and similar bookings
	are populated when Linked Service company differs from the main shipment.
	"""
	company = _norm(company)
	if not doc or not company:
		return
	meta = frappe.get_meta(doc.doctype)
	missing_labels: list[str] = []
	for fn, link_dt in _SCOPED_FIELD_DOCTYPES.items():
		df = meta.get_field(fn)
		if not df:
			continue
		current = _norm(_row_val(doc, fn))
		if current and _link_belongs_to_company(link_dt, current, company):
			continue
		default = _default_scoped_value(fn, link_dt, company)
		doc.set(fn, default or None)
		if getattr(df, "reqd", False) and not _norm(_row_val(doc, fn)):
			missing_labels.append(_(getattr(df, "label", None) or fn.replace("_", " ").title()))
	if missing_labels:
		frappe.throw(
			_(
				"Cannot create {0} for company {1}: missing {2}. "
				"Set Branch, Cost Center, and Profit Center on the Linked Service, "
				"or add them for that company, then try again."
			).format(doc.doctype, company, ", ".join(missing_labels)),
			title=_("Company defaults required"),
		)


def _scoped_values_from_linked_service(row: Any) -> dict[str, str]:
	"""Branch / cost center / profit center stored on the row or its Linked Service."""
	values = {fn: _norm(_row_val(row, fn)) for fn in _COMPANY_SCOPED_FIELDS}
	if all(values.values()) or _doctype_of(row) in ("Linked Service", "Internal Job"):
		return values
	ls_name = linked_service_name_from_row(row)
	if not ls_name:
		return values
	from logistics.utils.linked_service_compat import linked_service_doctype, linked_service_record_exists

	if not linked_service_record_exists(ls_name):
		return values
	try:
		stored = (
			frappe.db.get_value(
				linked_service_doctype(),
				ls_name,
				list(_COMPANY_SCOPED_FIELDS),
				as_dict=True,
			)
			or {}
		)
	except Exception:
		return values
	for fn in _COMPANY_SCOPED_FIELDS:
		if not values[fn]:
			values[fn] = _norm(stored.get(fn) if isinstance(stored, dict) else None)
	return values


def _apply_scoped_values_from_linked_service(doc: Any, row: Any, company: str) -> None:
	"""Copy Linked Service branch / cost center / profit center when they belong to *company*."""
	meta = frappe.get_meta(doc.doctype)
	for fn, value in _scoped_values_from_linked_service(row).items():
		if not value or not meta.get_field(fn):
			continue
		if _link_belongs_to_company(_SCOPED_FIELD_DOCTYPES[fn], value, company):
			doc.set(fn, value)


def apply_linked_service_company_to_operational_doc(
	doc: Any,
	row: Any,
	*,
	overwrite: bool = False,
	require: bool = False,
	sales_quote: str | None = None,
) -> str:
	"""Stamp Linked Service company onto a designated booking/order.

	When *require* is True and the row points at a Linked Service with no company,
	raises so users set it on the Sales Quote before creating from the main.

	When the Linked Service company differs from the source booking, company-scoped
	fields (branch, cost center, profit center) are refilled for the new company
	instead of being left blank.
	"""
	if not doc or not row:
		return ""
	company = company_from_linked_service(row)
	ls_name = linked_service_name_from_row(row)
	if not company:
		if require and ls_name:
			frappe.throw(
				missing_linked_service_company_message(
					linked_service=ls_name,
					service_type=_row_val(row, "service_type"),
					sales_quote=sales_quote or _row_val(doc, "sales_quote"),
				),
				title=_("Company required"),
			)
		return ""
	meta = frappe.get_meta(doc.doctype)
	if not meta.get_field("company"):
		return company
	current = _norm(_row_val(doc, "company"))
	if current and current != company and not overwrite:
		return current
	if current != company:
		doc.set("company", company)
	elif not current:
		doc.set("company", company)
	_apply_scoped_values_from_linked_service(doc, row, company)
	sync_company_scoped_fields_on_operational_doc(doc, company)
	return company
