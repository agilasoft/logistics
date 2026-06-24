# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Compatibility helpers for Internal Job → Linked Service rename."""

from __future__ import annotations

from typing import Any

import frappe

LINKED_SERVICE_DOCTYPE = "Linked Service"
LINKED_SERVICE_DETAIL_DOCTYPE = "Linked Service Detail"
LEGACY_INTERNAL_JOB_DOCTYPE = "Internal Job"
LEGACY_INTERNAL_JOB_DETAIL_DOCTYPE = "Internal Job Detail"

CHARGE_SCOPE_MAIN = "Main"
CHARGE_SCOPE_LINKED = "Linked"
LEGACY_CHARGE_SCOPE_INTERNAL_JOB = "Internal Job"


def linked_service_doctype() -> str:
	if frappe.db.exists("DocType", LINKED_SERVICE_DOCTYPE):
		return LINKED_SERVICE_DOCTYPE
	return LEGACY_INTERNAL_JOB_DOCTYPE


def linked_service_detail_doctype() -> str:
	if frappe.db.exists("DocType", LINKED_SERVICE_DETAIL_DOCTYPE):
		return LINKED_SERVICE_DETAIL_DOCTYPE
	return LEGACY_INTERNAL_JOB_DETAIL_DOCTYPE


def linked_service_doctype_exists() -> bool:
	return bool(
		frappe.db.exists("DocType", LINKED_SERVICE_DOCTYPE)
		or frappe.db.exists("DocType", LEGACY_INTERNAL_JOB_DOCTYPE)
	)


def linked_service_record_exists(name: str | None) -> bool:
	"""True when *name* resolves in either Linked Service or legacy Internal Job storage."""
	if not name:
		return False
	for dt in (LINKED_SERVICE_DOCTYPE, LEGACY_INTERNAL_JOB_DOCTYPE):
		if frappe.db.exists("DocType", dt) and frappe.db.exists(dt, name):
			return True
	return False


def filter_invalid_links_with_linked_service_compat(
	invalid_links: list[tuple],
) -> list[tuple]:
	"""Drop false link errors for ``internal_job`` / ``linked_service`` backed by either DocType."""
	out: list[tuple] = []
	for fieldname, docname, msg in invalid_links:
		if fieldname in ("internal_job", "linked_service") and linked_service_record_exists(
			docname
		):
			continue
		out.append((fieldname, docname, msg))
	return out


def linked_services_fieldname(parent_doctype: str) -> str | None:
	"""Child-table field on *parent_doctype* holding Linked Service Detail rows."""
	if parent_doctype == "Sales Quote":
		try:
			meta = frappe.get_meta("Sales Quote")
			if meta.has_field("linked_services"):
				return "linked_services"
		except Exception:
			pass
		return "internal_job_details"
	if parent_doctype in ("MICE Project", "Docket", "Exhibit"):
		return "internal_jobs"
	return "internal_job_details"


def row_linked_service_link(row: Any) -> str:
	if row is None:
		return ""
	if isinstance(row, dict):
		return (row.get("linked_service") or row.get("internal_job") or "").strip()
	return (getattr(row, "linked_service", None) or getattr(row, "internal_job", None) or "").strip()


def set_row_linked_service_link(row: Any, name: str | None) -> None:
	if isinstance(row, dict):
		row["internal_job"] = name
		row["linked_service"] = name
		return
	if hasattr(row, "internal_job"):
		row.internal_job = name
	if hasattr(row, "linked_service"):
		row.linked_service = name


def is_linked_charge_scope(scope: str | None) -> bool:
	s = (scope or "").strip()
	return s in (LEGACY_CHARGE_SCOPE_INTERNAL_JOB, CHARGE_SCOPE_LINKED)


def normalize_charge_scope(scope: str | None) -> str:
	s = (scope or CHARGE_SCOPE_MAIN).strip() or CHARGE_SCOPE_MAIN
	if is_linked_charge_scope(s):
		return CHARGE_SCOPE_LINKED
	return CHARGE_SCOPE_MAIN


def charge_row_linked_service_link(row: Any) -> str:
	if row is None:
		return ""
	if isinstance(row, dict):
		return (row.get("linked_service") or row.get("internal_job") or "").strip()
	return (getattr(row, "linked_service", None) or getattr(row, "internal_job", None) or "").strip()


def set_charge_row_linked_service_link(row: Any, name: str | None) -> None:
	set_row_linked_service_link(row, name)


def linked_service_rows(parent_doc: Any) -> list[Any]:
	"""Return linked-service child rows, honouring unsaved desk/API grid edits when present."""
	fieldname = linked_services_fieldname(getattr(parent_doc, "doctype", None) or "")
	if not fieldname:
		return []
	doctype = getattr(parent_doc, "doctype", None) or ""
	if doctype == "Sales Quote":
		if getattr(getattr(parent_doc, "flags", None), "_linked_services_from_form", False):
			return list(parent_doc.__dict__.get(fieldname) or [])
		if hasattr(parent_doc, "_build_linked_services_view"):
			return parent_doc._build_linked_services_view()
	if doctype in ("Docket", "Exhibit"):
		if getattr(getattr(parent_doc, "flags", None), "_internal_jobs_from_form", False):
			return list(parent_doc.__dict__.get(fieldname) or [])
		if hasattr(parent_doc, "_build_internal_jobs_view"):
			return parent_doc._build_internal_jobs_view()
	return list(getattr(parent_doc, fieldname, None) or [])
