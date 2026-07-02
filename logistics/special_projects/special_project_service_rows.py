# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Unified access to Special Project service rows (Special Project Service child table)."""

from __future__ import annotations

from typing import Any

def _norm(value: Any) -> str:
	return (value or "").strip()


def is_planning_special_project_service_row(row: Any) -> bool:
	return not _norm(service_row_field(row, "special_project_service_line"))


def is_execution_special_project_service_row(row: Any) -> bool:
	return bool(_norm(service_row_field(row, "special_project_service_line")))


def applicable_lifecycle_stages(doc: Any) -> list[str]:
	"""Lifecycle Stage names selected on the Special Project."""
	stages: list[str] = []
	seen: set[str] = set()
	for row in doc.get("applicable_lifecycle_stages") or []:
		stage = _norm(getattr(row, "lifecycle_stage", None))
		if stage and stage not in seen:
			stages.append(stage)
			seen.add(stage)
	if not stages:
		parent = _norm(getattr(doc, "name", None))
		if parent:
			import frappe

			for row in frappe.get_all(
				"Special Project Lifecycle Stage",
				filters={"parent": parent, "parentfield": "applicable_lifecycle_stages"},
				fields=["lifecycle_stage"],
				order_by="idx asc",
			):
				stage = _norm(row.get("lifecycle_stage"))
				if stage and stage not in seen:
					stages.append(stage)
					seen.add(stage)
	return stages


def order_lifecycle_stage_names(stage_names: list[str]) -> list[str]:
	"""Order lifecycle stage names by Lifecycle Stage master sort_order."""
	names = [_norm(name) for name in (stage_names or []) if _norm(name)]
	if not names:
		return []

	import frappe

	seen: set[str] = set()
	ordered: list[str] = []
	if frappe.db.exists("DocType", "Lifecycle Stage"):
		for row in frappe.get_all(
			"Lifecycle Stage",
			filters={"name": ["in", names]},
			fields=["name"],
			order_by="sort_order asc, name asc",
		):
			stage = _norm(row.get("name"))
			if stage and stage not in seen:
				ordered.append(stage)
				seen.add(stage)
	for stage in names:
		if stage not in seen:
			ordered.append(stage)
			seen.add(stage)
	return ordered


def applicable_lifecycle_stages_ordered(doc: Any) -> list[str]:
	"""Applicable lifecycle stages in master sort order (for dashboard / summaries)."""
	from logistics.utils.lifecycle_stage import FOR_SPECIAL_PROJECT, get_lifecycle_stages

	selected = applicable_lifecycle_stages(doc)
	if not selected:
		return get_lifecycle_stages(FOR_SPECIAL_PROJECT)
	return order_lifecycle_stage_names(selected)


def dashboard_lifecycle_stage_names(
	doc: Any,
	client_stages: list[str] | None = None,
) -> list[str]:
	"""Lifecycle stage groups for the Special Project dashboard Route tab."""
	from logistics.utils.lifecycle_stage import FOR_SPECIAL_PROJECT, get_lifecycle_stages

	client = [_norm(stage) for stage in (client_stages or []) if _norm(stage)]
	saved = applicable_lifecycle_stages(doc)
	selected = client if client else saved
	if not selected:
		return get_lifecycle_stages(FOR_SPECIAL_PROJECT)
	return order_lifecycle_stage_names(selected)


def has_configured_applicable_lifecycle_stages(
	doc: Any,
	client_stages: list[str] | None = None,
) -> bool:
	client = [_norm(stage) for stage in (client_stages or []) if _norm(stage)]
	return bool(client or applicable_lifecycle_stages(doc))


def service_row_field(row: Any, field: str) -> Any:
	"""Read a field from a service grid row (dict view or document child)."""
	if isinstance(row, dict):
		return row.get(field)
	return getattr(row, field, None)


def set_service_row_field(row: Any, field: str, value: Any) -> None:
	"""Write a field on a service grid row (dict view or document child)."""
	if isinstance(row, dict):
		row[field] = value
		return
	setattr(row, field, value)


def service_row_currency_total(rows: list[Any], field: str) -> float:
	from frappe.utils import flt

	return sum(flt(service_row_field(row, field) or 0) for row in rows)


def service_rows(doc: Any) -> list[Any]:
	"""All Special Project Service rows (virtual grid backed by Special Project Service docs)."""
	from logistics.special_projects.special_project_service_compat import (
		special_project_service_grid_rows,
	)

	return list(special_project_service_grid_rows(doc))


def planning_service_rows(doc: Any) -> list[Any]:
	return [row for row in service_rows(doc) if is_planning_special_project_service_row(row)]


def execution_service_rows(doc: Any) -> list[Any]:
	return [row for row in service_rows(doc) if is_execution_special_project_service_row(row)]


def service_row_by_name(doc: Any, row_name: str) -> Any | None:
	row_name = _norm(row_name)
	if not row_name:
		return None
	for row in service_rows(doc):
		if _norm(service_row_field(row, "name")) == row_name:
			return row
	return None


def execution_rows_for_planning(doc: Any, planning_name: str) -> list[Any]:
	planning_name = _norm(planning_name)
	if not planning_name:
		return []
	return [
		row
		for row in service_rows(doc)
		if _norm(getattr(row, "special_project_service_line", None)) == planning_name
	]
