# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Copy Internal Job Detail child rows between operational documents (e.g. booking → shipment)."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

DECLARATION_ORDER_JOB_TYPE = "Declaration Order"

_DEFAULT_SERVICE_TYPE_FOR_JOB_TYPE: dict[str, str] = {
	"Declaration Order": "Customs",
	"Transport Order": "Transport",
	"Air Booking": "Air",
	"Sea Booking": "Sea",
}

_SKIP_KEYS = frozenset(
	{
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"idx",
		"parent",
		"parentfield",
		"parenttype",
		"doctype",
	}
)


def internal_job_detail_row_as_dict(row: Any) -> dict:
	"""Serialize a child row for append() on another parent."""
	d = row.as_dict()
	for k in _SKIP_KEYS:
		d.pop(k, None)
	return d


def copy_internal_job_details_to_doc(source_doc: Any, dest_doc: Any) -> None:
	"""Append copies of source_doc.internal_job_details onto dest_doc."""
	rows = getattr(source_doc, "internal_job_details", None) or []
	if not rows:
		return
	for row in rows:
		dest_doc.append("internal_job_details", internal_job_detail_row_as_dict(row))


def get_declaration_order_job_no_from_shipment_doc(shipment_doc: Any) -> str | None:
	"""Return linked Declaration Order name from internal_job_details (job_type = Declaration Order)."""
	for row in getattr(shipment_doc, "internal_job_details", None) or []:
		if (getattr(row, "job_type", None) or "").strip() != DECLARATION_ORDER_JOB_TYPE:
			continue
		jn = (getattr(row, "job_no", None) or "").strip()
		if jn and frappe.db.exists("Declaration Order", jn):
			return jn
	return None


def _save_parent_internal_job_details(parent: Any) -> None:
	"""Persist internal_job_details (including after submit)."""
	parent.flags.ignore_validate_update_after_submit = True
	parent.flags.ignore_links = True
	parent.save(ignore_permissions=True)


def _save_shipment_internal_jobs(shipment: Any) -> None:
	_save_parent_internal_job_details(shipment)


def _coerce_positive_detail_idx(value: Any) -> int | None:
	if value is None or value == "":
		return None
	try:
		i = int(value)
		return i if i > 0 else None
	except (TypeError, ValueError):
		return None


def persist_internal_job_detail_job_link(
	parent_doctype: str,
	parent_name: str,
	job_type: str,
	job_no: str,
	*,
	detail_idx: int | None = None,
) -> None:
	"""Set job_type + job_no on the matching Internal Job Detail row (by idx, first open line, or append)."""
	jn = (job_no or "").strip()
	if not jn or not frappe.db.exists(parent_doctype, parent_name):
		return
	meta = frappe.get_meta(parent_doctype)
	if not meta.get_field("internal_job_details"):
		return

	parent = frappe.get_doc(parent_doctype, parent_name)
	jt = (job_type or "").strip()
	st_default = _DEFAULT_SERVICE_TYPE_FOR_JOB_TYPE.get(jt)
	rows = list(getattr(parent, "internal_job_details", None) or [])

	di = _coerce_positive_detail_idx(detail_idx)
	if di is not None:
		if di < 1 or di > len(rows):
			frappe.throw(_("Invalid Internal Job Detail row index for persist."))
		row = rows[di - 1]
		existing_jt = (getattr(row, "job_type", None) or "").strip()
		if existing_jt and existing_jt != jt:
			frappe.throw(_("Internal Job Detail row {0} is for {1}, not {2}.").format(di, existing_jt, jt))
		row.job_type = jt
		row.job_no = jn
		if st_default and hasattr(row, "service_type") and not (getattr(row, "service_type", None) or "").strip():
			row.service_type = st_default
		_save_parent_internal_job_details(parent)
		return

	for row in rows:
		if (getattr(row, "job_type", None) or "").strip() != jt:
			continue
		if (getattr(row, "job_no", None) or "").strip():
			continue
		row.job_no = jn
		if st_default and hasattr(row, "service_type") and not (getattr(row, "service_type", None) or "").strip():
			row.service_type = st_default
		_save_parent_internal_job_details(parent)
		return

	new_row: dict[str, Any] = {"job_type": jt, "job_no": jn}
	if st_default:
		new_row["service_type"] = st_default
	parent.append("internal_job_details", new_row)
	_save_parent_internal_job_details(parent)


def link_declaration_order_on_shipment(
	shipment_doctype: str, shipment_name: str, declaration_order_name: str
) -> None:
	"""Set or append an Internal Job Detail row linking this shipment to a Declaration Order."""
	if not declaration_order_name or not frappe.db.exists("Declaration Order", declaration_order_name):
		return
	meta = frappe.get_meta(shipment_doctype)
	if not meta.get_field("internal_job_details"):
		return
	shipment = frappe.get_doc(shipment_doctype, shipment_name)
	for row in shipment.internal_job_details or []:
		if (getattr(row, "job_type", None) or "").strip() != DECLARATION_ORDER_JOB_TYPE:
			continue
		row.job_type = DECLARATION_ORDER_JOB_TYPE
		row.job_no = declaration_order_name
		if hasattr(row, "service_type") and not (getattr(row, "service_type", None) or "").strip():
			row.service_type = "Customs"
		_save_shipment_internal_jobs(shipment)
		return
	shipment.append(
		"internal_job_details",
		{
			"job_type": DECLARATION_ORDER_JOB_TYPE,
			"job_no": declaration_order_name,
			"service_type": "Customs",
		},
	)
	_save_shipment_internal_jobs(shipment)


def unlink_declaration_order_from_shipment(
	shipment_doctype: str,
	shipment_name: str,
	declaration_order_name: str,
) -> None:
	"""Remove the Internal Job Detail row that points to this Declaration Order."""
	if not (declaration_order_name or "").strip():
		return
	meta = frappe.get_meta(shipment_doctype)
	if not meta.get_field("internal_job_details"):
		return
	try:
		shipment = frappe.get_doc(shipment_doctype, shipment_name)
	except frappe.DoesNotExistError:
		return
	to_remove = []
	for row in list(shipment.internal_job_details or []):
		if (getattr(row, "job_type", None) or "").strip() != DECLARATION_ORDER_JOB_TYPE:
			continue
		jn = (getattr(row, "job_no", None) or "").strip()
		if jn != declaration_order_name.strip():
			continue
		to_remove.append(row)
	for row in to_remove:
		shipment.remove(row)
	if to_remove:
		_save_shipment_internal_jobs(shipment)
