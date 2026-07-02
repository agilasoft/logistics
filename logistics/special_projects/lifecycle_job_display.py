# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Human-readable labels for Special Project Service child rows (link display)."""

from __future__ import annotations

from typing import Any

from frappe import _
from frappe.utils import cint

from logistics.special_projects.special_project_service_rows import (
	service_row_field,
	service_rows,
	set_service_row_field,
)


def _norm_text(value: Any) -> str:
	return (value or "").strip()


def lifecycle_job_line_display_label(row: Any) -> str:
	"""Build a user-facing label for a service row."""
	if row is None:
		return ""
	existing = _norm_text(service_row_field(row, "lifecycle_row_label"))
	if existing:
		return existing

	parts: list[str] = []
	stage = _norm_text(service_row_field(row, "lifecycle_stage"))
	if stage:
		parts.append(stage)
	activity = _norm_text(service_row_field(row, "activity_name"))
	if activity:
		parts.append(activity)
	else:
		activity_code = service_row_field(row, "activity_code")
		if activity_code:
			parts.append(str(activity_code))
	if parts:
		return " — ".join(parts)

	description = _norm_text(service_row_field(row, "job_description"))
	if description:
		return description[:140]

	idx = cint(service_row_field(row, "idx") or 0)
	if idx:
		return _("Service row {0}").format(idx)
	return ""


def sync_lifecycle_row_labels(doc: Any) -> None:
	"""Persist ``lifecycle_row_label`` on special_project_services rows for link display."""
	import frappe

	for row in service_rows(doc):
		existing = service_row_field(row, "lifecycle_row_label")
		label = lifecycle_job_line_display_label(row) or existing
		if not label or label == existing:
			continue
		set_service_row_field(row, "lifecycle_row_label", label)
		if not isinstance(row, dict):
			continue
		service_name = _norm_text(
			service_row_field(row, "special_project_service")
		) or _norm_text(service_row_field(row, "name"))
		if service_name and frappe.db.exists("Special Project Service", service_name):
			frappe.db.set_value(
				"Special Project Service",
				service_name,
				"lifecycle_row_label",
				label,
				update_modified=False,
			)
