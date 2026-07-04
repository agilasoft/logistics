# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Compatibility helpers for virtual ``special_project_services`` on Special Project."""

from __future__ import annotations

from typing import Any

import frappe

SPECIAL_PROJECT_SERVICE_DOCTYPE = "Special Project Service"
SPECIAL_PROJECT_SERVICE_DETAIL_DOCTYPE = "Special Project Service Detail"
SPECIAL_PROJECT_SERVICES_FIELD = "special_project_services"


def special_project_service_doctype() -> str:
	return SPECIAL_PROJECT_SERVICE_DOCTYPE


def special_project_service_detail_doctype() -> str:
	return SPECIAL_PROJECT_SERVICE_DETAIL_DOCTYPE


def special_project_service_record_exists(name: str | None) -> bool:
	return bool(name and frappe.db.exists(SPECIAL_PROJECT_SERVICE_DOCTYPE, name))


def row_special_project_service_link(row: Any) -> str:
	if row is None:
		return ""
	if isinstance(row, dict):
		return (row.get("special_project_service") or "").strip()
	return (getattr(row, "special_project_service", None) or "").strip()


def set_row_special_project_service_link(row: Any, name: str | None) -> None:
	if isinstance(row, dict):
		row["special_project_service"] = name
		return
	if hasattr(row, "special_project_service"):
		row.special_project_service = name


def special_project_service_grid_rows(parent_doc: Any) -> list[Any]:
	"""Return Services grid rows, honouring unsaved desk/API grid edits when present."""
	if not parent_doc or getattr(parent_doc, "doctype", None) != "Special Project":
		return []
	if getattr(getattr(parent_doc, "flags", None), "_special_project_services_from_form", False):
		return list(parent_doc.__dict__.get(SPECIAL_PROJECT_SERVICES_FIELD) or [])
	build_view = getattr(parent_doc, "_build_special_project_services_view", None)
	if callable(build_view):
		return build_view()
	return list(getattr(parent_doc, SPECIAL_PROJECT_SERVICES_FIELD, None) or [])
