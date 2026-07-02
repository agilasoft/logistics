# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Link search for Lifecycle Job rows on a Special Project (shows stage/activity names)."""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe.utils import cint

from logistics.special_projects.lifecycle_job_display import lifecycle_job_line_display_label


def _parse_filters(filters: Any) -> dict:
	if filters is None:
		return {}
	if isinstance(filters, str):
		try:
			return json.loads(filters)
		except Exception:
			return {}
	if isinstance(filters, dict):
		return dict(filters)
	return {}


def _parse_client_rows(value: Any) -> list[dict]:
	if value is None or value == "":
		return []
	if isinstance(value, str):
		try:
			value = json.loads(value)
		except Exception:
			return []
	if not isinstance(value, list):
		return []
	return [r for r in value if isinstance(r, dict)]


def _row_map_for_parent(parent: str, client_rows: list[dict]) -> dict[str, Any]:
	rows_by_name: dict[str, Any] = {}
	if parent:
		for row in frappe.get_all(
			"Lifecycle Job",
			filters={
				"parent": parent,
				"parenttype": "Special Project",
				"parentfield": "lifecycle_jobs",
			},
			fields=[
				"name",
				"idx",
				"lifecycle_stage",
				"activity_code",
				"activity_name",
				"job_description",
				"lifecycle_row_label",
			],
			order_by="idx asc",
		):
			rows_by_name[row.name] = frappe._dict(row)

	for row in client_rows:
		name = (row.get("name") or "").strip()
		if name:
			rows_by_name[name] = frappe._dict(row)

	return rows_by_name


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def lifecycle_job_line_search(
	doctype, txt, searchfield, start, page_len, filters, as_dict=False, **kwargs
):
	_ = (doctype, searchfield, as_dict, kwargs)
	f = _parse_filters(filters)
	parent = (f.get("parent") or "").strip()
	client_rows = _parse_client_rows(f.get("lifecycle_jobs"))
	start = cint(start)
	page_len = cint(page_len) or 20
	txt_norm = (txt or "").strip().lower()

	rows_by_name = _row_map_for_parent(parent, client_rows)
	candidates: list[tuple[int, str, str]] = []
	for name, row in rows_by_name.items():
		label = lifecycle_job_line_display_label(row) or name
		if txt_norm and txt_norm not in label.lower() and txt_norm not in name.lower():
			continue
		candidates.append((cint(getattr(row, "idx", 0) or 0), name, label))

	candidates.sort(key=lambda item: (item[0], item[1]))
	page = candidates[start : start + page_len]
	return [[name, label] for _, name, label in page]
