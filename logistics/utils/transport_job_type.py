# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Transport job type selection (load-type compatibility, internal-job container context)."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _


def determine_transport_job_type(
	current_job_type: str | None,
	load_type: str | None,
	container_type: str | None,
) -> str:
	"""Determine transport_job_type from load_type compatibility and container_type (Sales Quote rules)."""
	if not load_type:
		return current_job_type or "Non-Container"

	load_type_doc = frappe.db.get_value(
		"Load Type",
		load_type,
		["container", "non_container", "special", "oversized", "multimodal", "heavy_haul"],
		as_dict=True,
	)

	if not load_type_doc:
		return current_job_type or "Non-Container"

	field_map = {
		"Container": "container",
		"Non-Container": "non_container",
		"Special": "special",
		"Oversized": "oversized",
		"Multimodal": "multimodal",
		"Heavy Haul": "heavy_haul",
	}

	def find_best_job_type() -> str:
		if load_type_doc.get("container"):
			if container_type:
				return "Container"
			if load_type_doc.get("non_container"):
				return "Non-Container"
			frappe.throw(
				_(
					"Load Type '{0}' requires Container job type, but Container Type is missing. "
					"Please set Container Type in Sales Quote."
				).format(load_type),
				title=_("Missing Container Type"),
			)
		if load_type_doc.get("non_container"):
			return "Non-Container"
		if load_type_doc.get("special"):
			return "Special"
		if load_type_doc.get("oversized"):
			return "Oversized"
		if load_type_doc.get("multimodal"):
			return "Multimodal"
		if load_type_doc.get("heavy_haul"):
			return "Heavy Haul"
		return "Non-Container"

	if current_job_type:
		allowed_field = field_map.get(current_job_type)
		if allowed_field and load_type_doc.get(allowed_field):
			if current_job_type == "Container" and not container_type:
				if load_type_doc.get("non_container"):
					return "Non-Container"
				frappe.throw(
					_("Container job type requires Container Type, but it is missing. Please set Container Type in Sales Quote."),
					title=_("Missing Container Type"),
				)
			return current_job_type
		return find_best_job_type()

	return find_best_job_type()


def _row_val(row: Any, fieldname: str) -> Any:
	if row is None:
		return None
	if isinstance(row, dict):
		return row.get(fieldname)
	return getattr(row, fieldname, None)


def internal_job_detail_indicates_container(row: Any) -> bool:
	"""True when Internal Job Detail (or order) has both container type and container number."""
	if not row:
		return False
	ctype = _row_val(row, "container_type")
	cno = _row_val(row, "container_no")
	return bool(ctype and cno and str(cno).strip())


def _copy_ij_container_fields_to_order(order: Any, ij_row: Any) -> None:
	if not ij_row or not order:
		return
	meta = frappe.get_meta(order.doctype)
	for fn in ("container_type", "container_no"):
		if not meta.get_field(fn):
			continue
		val = _row_val(ij_row, fn)
		if val is None or val == "":
			continue
		cur = getattr(order, fn, None)
		if cur is None or cur == "":
			order.set(fn, val)


def apply_container_transport_context_to_order(order: Any, ij_row: Any = None) -> bool:
	"""Upgrade Transport Order to Container when IJ row / order has container_type + container_no.

	Returns True when transport_job_type is Container after this call.
	"""
	if not order or getattr(order, "doctype", None) != "Transport Order":
		return getattr(order, "transport_job_type", None) == "Container"

	_copy_ij_container_fields_to_order(order, ij_row)

	if not internal_job_detail_indicates_container(ij_row) and not internal_job_detail_indicates_container(order):
		return getattr(order, "transport_job_type", None) == "Container"

	was_container = getattr(order, "transport_job_type", None) == "Container"
	order.transport_job_type = determine_transport_job_type(
		current_job_type="Container",
		load_type=getattr(order, "load_type", None),
		container_type=getattr(order, "container_type", None),
	)
	return order.transport_job_type == "Container" or was_container


def set_internal_transport_order_draft_insert_flags(order: Any) -> None:
	"""Relax container field validation on draft insert (internal job create paths)."""
	order.flags.skip_container_no_validation = True
	order.flags.skip_container_type_validation = True
