# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Copy Internal Job Detail child rows between operational documents (e.g. booking → shipment)."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from logistics.utils.charge_service_type import effective_internal_job_detail_job_type

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


def sync_internal_job_details_from_declaration_to_declaration_order(declaration: Any) -> None:
	"""Copy Declaration.internal_job_details onto the linked Declaration Order so row counts stay aligned.

	Called when the Declaration is saved so downstream flows (e.g. persist_internal_job_detail_job_link on
	the Order) see the same Internal Jobs lines as on the Declaration. Preserves ``job_no`` / ``job_type``
	from the Order row when the Declaration row is still open (link was written only on the Order).
	"""
	do_name = (getattr(declaration, "declaration_order", None) or "").strip()
	if not do_name or not frappe.db.exists("Declaration Order", do_name):
		return
	dec_rows = list(getattr(declaration, "internal_job_details", None) or [])

	try:
		order = frappe.get_doc("Declaration Order", do_name)
	except frappe.DoesNotExistError:
		return

	old_rows = list(getattr(order, "internal_job_details", None) or [])
	if not dec_rows:
		if not old_rows:
			return
		order.set("internal_job_details", [])
		order.flags.ignore_validate_update_after_submit = True
		order.flags.ignore_links = True
		order.save(ignore_permissions=True)
		return

	merged: list[dict[str, Any]] = []
	for i, row in enumerate(dec_rows):
		d = internal_job_detail_row_as_dict(row)
		if i < len(old_rows):
			old_jn = (getattr(old_rows[i], "job_no", None) or "").strip()
			new_jn = (d.get("job_no") or "").strip()
			old_jt = (getattr(old_rows[i], "job_type", None) or "").strip()
			if old_jn and not new_jn:
				d["job_no"] = old_jn
				if old_jt:
					d["job_type"] = old_jt
		merged.append(d)

	def _row_matches(doc_row: Any, want: dict[str, Any]) -> bool:
		for k, v in want.items():
			if getattr(doc_row, k, None) != v:
				return False
		return True

	if len(merged) == len(old_rows) and all(
		_row_matches(old_rows[i], merged[i]) for i in range(len(merged))
	):
		return

	order.set("internal_job_details", [])
	for d in merged:
		order.append("internal_job_details", d)
	order.flags.ignore_validate_update_after_submit = True
	order.flags.ignore_links = True
	order.save(ignore_permissions=True)


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
		if effective_internal_job_detail_job_type(row) != DECLARATION_ORDER_JOB_TYPE:
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
	"""Set job_type + job_no on the matching Internal Job Detail row (by idx, first open line, or append).

	When the desk passes ``internal_job_details`` JSON, resolution uses that list but we must write
	``job_no`` onto the parent document's real child rows so ``save`` persists the back-reference.
	"""
	jn = (job_no or "").strip()
	if not jn or not frappe.db.exists(parent_doctype, parent_name):
		return
	meta = frappe.get_meta(parent_doctype)
	if not meta.get_field("internal_job_details"):
		return

	from logistics.utils.internal_job_from_source import _ij_rows_list

	parent = frappe.get_doc(parent_doctype, parent_name)
	jt = (job_type or "").strip()
	st_default = _DEFAULT_SERVICE_TYPE_FOR_JOB_TYPE.get(jt)
	# Rows as seen during create (grid JSON when provided, else DB child rows on parent).
	form_rows = _ij_rows_list(parent)
	canonical = list(getattr(parent, "internal_job_details", None) or [])

	def _apply_to_canonical_row(target: Any, di: int) -> None:
		src = form_rows[di - 1] if 0 < di <= len(form_rows) else target
		existing_eff = effective_internal_job_detail_job_type(src)
		if existing_eff and existing_eff != jt:
			frappe.throw(
				_("Internal Job Detail row {0} is for {1}, not {2}.").format(di, existing_eff, jt)
			)
		target.job_type = jt
		target.job_no = jn
		if st_default and hasattr(target, "service_type") and not (getattr(target, "service_type", None) or "").strip():
			target.service_type = st_default

	di = _coerce_positive_detail_idx(detail_idx)
	if di is not None:
		if di < 1 or di > len(form_rows):
			frappe.throw(_("Invalid Internal Job Detail row index for persist."))
		if di > len(canonical):
			frappe.throw(
				_(
					"Save {0} before creating this internal job so the Internal Jobs line exists in the database."
				).format(parent_name),
				title=_("Save required"),
			)
		_apply_to_canonical_row(canonical[di - 1], di)
		_save_parent_internal_job_details(parent)
		return

	for i, src in enumerate(form_rows):
		if effective_internal_job_detail_job_type(src) != jt:
			continue
		if (getattr(src, "job_no", None) or "").strip():
			continue
		di_open = i + 1
		if di_open > len(canonical):
			frappe.throw(
				_(
					"Save {0} before creating this internal job so the Internal Jobs line exists in the database."
				).format(parent_name),
				title=_("Save required"),
			)
		_apply_to_canonical_row(canonical[di_open - 1], di_open)
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
		if effective_internal_job_detail_job_type(row) != DECLARATION_ORDER_JOB_TYPE:
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
