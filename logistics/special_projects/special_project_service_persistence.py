# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Persistence for virtual ``special_project_services`` on Special Project.

The Services grid is a live view of top-level ``Special Project Service`` documents
parented via ``parent_booking_type`` / ``parent_booking_name``. ``before_save`` keeps
those documents in sync with desk grid rows; ``on_trash`` deletes owned services.
"""

from __future__ import annotations

from typing import Any

import frappe

from logistics.special_projects.special_project_service_compat import (
	is_local_special_project_service_detail_name,
	row_special_project_service_link,
	set_row_special_project_service_link,
	special_project_service_doctype,
	special_project_service_grid_rows,
	special_project_service_record_exists,
)
from logistics.utils.charge_service_type import default_job_type_for_internal_job_service_type
from logistics.utils.sales_quote_charge_parameters import SALES_QUOTE_CHARGE_PARAMETER_FIELDS

_PARAM_FIELDS: tuple[str, ...] = (
	"lifecycle_stage",
	"activity_code",
	"activity_name",
	"lifecycle_row_label",
	"lifecycle_activity_status",
	"special_project_service_line",
	"service_type",
	"job_type",
	"job_no",
	"order_no",
	"job_description",
) + tuple(
	fn
	for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS
	if fn != "charge_group"
)
# planned/actual cost/revenue are rolled up by sync_lifecycle_job_financials — never copy from the desk grid.


def _norm(val: Any) -> str:
	if val is None:
		return ""
	return str(val).strip()


def _row_value(row: Any, fieldname: str) -> Any:
	if row is None:
		return None
	if isinstance(row, dict):
		return row.get(fieldname)
	return getattr(row, fieldname, None)


def get_special_project_services_for_special_project(special_project_name: str) -> list[Any]:
	"""All Special Project Service documents owned by a Special Project, ordered by creation."""
	if not special_project_name:
		return []
	names = frappe.get_all(
		special_project_service_doctype(),
		filters={
			"parent_booking_type": "Special Project",
			"parent_booking_name": special_project_name,
		},
		pluck="name",
		order_by="creation asc",
	)
	return [frappe.get_doc(special_project_service_doctype(), n) for n in names]


def _special_project_service_names_from_db(parent_name: str) -> set[str]:
	if not parent_name:
		return set()
	return set(
		frappe.get_all(
			special_project_service_doctype(),
			filters={
				"parent_booking_type": "Special Project",
				"parent_booking_name": parent_name,
			},
			pluck="name",
		)
		or []
	)


def _copy_row_params_to_service_doc(row: Any, service_doc: Any) -> bool:
	meta = frappe.get_meta(special_project_service_doctype())
	changed = False
	for fn in _PARAM_FIELDS:
		if not meta.has_field(fn):
			continue
		new_val = _row_value(row, fn)
		if new_val is None:
			continue
		cur_val = getattr(service_doc, fn, None)
		if _norm(cur_val) != _norm(new_val):
			setattr(service_doc, fn, new_val)
			changed = True
	return changed


def _ensure_job_type_from_service(service_doc: Any) -> None:
	st = (getattr(service_doc, "service_type", None) or "").strip()
	if not st:
		return
	expected = default_job_type_for_internal_job_service_type(st)
	if not expected:
		return
	jt = (getattr(service_doc, "job_type", None) or "").strip()
	if st == "Warehousing":
		if jt in ("Inbound Order", "Release Order", "Transfer Order"):
			return
		service_doc.job_type = "Inbound Order"
		return
	service_doc.job_type = expected


def _create_service_doc_from_row(parent_doc: Any, row: Any, *, preferred_name: str | None = None) -> str:
	service_doc = frappe.new_doc(special_project_service_doctype())
	service_doc.parent_booking_type = parent_doc.doctype
	service_doc.parent_booking_name = parent_doc.name or ""
	_copy_row_params_to_service_doc(row, service_doc)
	_ensure_job_type_from_service(service_doc)
	service_doc.flags.ignore_permissions = True
	preferred = _norm(preferred_name)
	if preferred and not special_project_service_record_exists(preferred):
		service_doc.insert(ignore_permissions=True, set_name=preferred)
	else:
		service_doc.insert(ignore_permissions=True)
	return service_doc.name


def _update_service_doc_from_row(row: Any, service_name: str) -> None:
	if not service_name or not special_project_service_record_exists(service_name):
		return
	service_doc = frappe.get_doc(special_project_service_doctype(), service_name)
	changed = _copy_row_params_to_service_doc(row, service_doc)
	_ensure_job_type_from_service(service_doc)
	if not changed and (
		service_doc.job_type == _row_value(row, "job_type") or not _row_value(row, "job_type")
	):
		return
	service_doc.flags.ignore_permissions = True
	service_doc.flags.skip_special_project_service_detail_sync = True
	service_doc.save(ignore_permissions=True)


def _backfill_service_parent_link(service_doc: Any, parent_doc: Any) -> bool:
	parent_name = _norm(getattr(parent_doc, "name", None))
	if not parent_name:
		return False
	changed = False
	parent_dt = getattr(parent_doc, "doctype", None) or ""
	if parent_dt and _norm(getattr(service_doc, "parent_booking_type", None)) != parent_dt:
		service_doc.parent_booking_type = parent_dt
		changed = True
	if _norm(getattr(service_doc, "parent_booking_name", None)) != parent_name:
		service_doc.parent_booking_name = parent_name
		changed = True
	return changed


def _ensure_service_docs_for_grid_rows(parent_doc: Any) -> None:
	if not parent_doc or parent_doc.doctype != "Special Project":
		return
	if not frappe.db.exists("DocType", special_project_service_doctype()):
		return

	for row in special_project_service_grid_rows(parent_doc):
		if _row_value(row, "__quote_linked_service_readonly__"):
			continue
		service_name = row_special_project_service_link(row)
		if service_name and special_project_service_record_exists(service_name):
			_update_service_doc_from_row(row, service_name)
			if _norm(getattr(parent_doc, "name", None)):
				service_doc = frappe.get_doc(special_project_service_doctype(), service_name)
				if _backfill_service_parent_link(service_doc, parent_doc):
					service_doc.flags.ignore_permissions = True
					service_doc.flags.skip_special_project_service_detail_sync = True
					service_doc.save(ignore_permissions=True)
			continue
		stale_name = service_name or None
		new_name = _create_service_doc_from_row(parent_doc, row, preferred_name=stale_name)
		set_row_special_project_service_link(row, new_name)


def _currently_linked_service_names(parent_doc: Any) -> set[str]:
	return {
		row_special_project_service_link(r)
		for r in special_project_service_grid_rows(parent_doc)
		if row_special_project_service_link(r)
	}


def _delete_orphan_service_docs(prev: set[str], cur: set[str]) -> None:
	for service_name in prev - cur:
		if not service_name or not special_project_service_record_exists(service_name):
			continue
		try:
			frappe.delete_doc(
				special_project_service_doctype(),
				service_name,
				ignore_permissions=True,
				force=True,
			)
		except Exception:
			frappe.log_error(
				title="Special Project Service orphan cleanup failed",
				message=frappe.get_traceback(),
			)


def _service_row_temp_to_persisted_remap(parent_doc: Any) -> dict[str, str]:
	"""Map unsaved virtual grid row names to persisted Special Project Service names."""
	remap: dict[str, str] = {}
	for row in special_project_service_grid_rows(parent_doc):
		temp = _norm(_row_value(row, "name"))
		persisted = row_special_project_service_link(row)
		if temp and persisted and temp != persisted:
			remap[temp] = persisted
	return remap


def _heal_special_project_service_line_links(parent_doc: Any, remap: dict[str, str]) -> None:
	"""Replace stale virtual grid names on charge / service Link fields."""
	for charge in parent_doc.get("charges") or []:
		line = _norm(getattr(charge, "special_project_service_line", None))
		if not line:
			continue
		if line in remap:
			charge.special_project_service_line = remap[line]
			continue
		if is_local_special_project_service_detail_name(line):
			charge.special_project_service_line = None
			continue
		if not special_project_service_record_exists(line):
			charge.special_project_service_line = None

	for row in special_project_service_grid_rows(parent_doc):
		line = _norm(_row_value(row, "special_project_service_line"))
		if not line:
			continue
		if line in remap:
			new_line = remap[line]
			if isinstance(row, dict):
				row["special_project_service_line"] = new_line
			elif hasattr(row, "special_project_service_line"):
				row.special_project_service_line = new_line
			continue
		if is_local_special_project_service_detail_name(line):
			if isinstance(row, dict):
				row["special_project_service_line"] = None
			elif hasattr(row, "special_project_service_line"):
				row.special_project_service_line = None


def prepare_special_project_services_before_link_validation(doc: Any) -> None:
	"""Materialise service documents and heal charge links before Frappe link validation.

	Frappe validates Link fields after ``validate()`` but before ``before_save`` hooks.
	The virtual Services grid uses temporary row names until ``Special Project Service``
	documents are synced; charge auto-tagging can reference those names during
	``validate()``. Pre-flight sync keeps desk saves from raising ``LinkValidationError``.
	"""
	if not doc or doc.doctype != "Special Project":
		return
	if getattr(doc.flags, "ignore_links", False):
		return
	if not special_project_service_grid_rows(doc):
		return
	if not doc.name:
		return
	honour_form_rows = getattr(doc, "_honour_special_project_services_form_rows", None)
	if callable(honour_form_rows):
		honour_form_rows()
	sync_special_project_services_to_documents(doc)
	_heal_special_project_service_line_links(doc, _service_row_temp_to_persisted_remap(doc))


def sync_special_project_services_to_documents(doc: Any, *_method) -> None:
	"""``before_save`` hook: sync desk grid rows to Special Project Service documents."""
	if not doc or doc.doctype != "Special Project":
		return
	prev_orphans: set[str] | None = None
	if doc.name:
		prev_orphans = _special_project_service_names_from_db(doc.name)
	_ensure_service_docs_for_grid_rows(doc)
	if prev_orphans is not None:
		cur = _currently_linked_service_names(doc)
		_delete_orphan_service_docs(prev_orphans, cur)


def delete_special_project_services_for_project(doc: Any, *_method) -> None:
	"""``on_trash`` hook: delete every Special Project Service owned by this project."""
	if not doc or doc.doctype != "Special Project":
		return
	for name in _special_project_service_names_from_db(doc.name or ""):
		try:
			frappe.delete_doc(
				special_project_service_doctype(),
				name,
				ignore_permissions=True,
				force=True,
			)
		except Exception:
			frappe.log_error(
				title="Special Project Service parent-trash cleanup failed",
				message=frappe.get_traceback(),
			)
