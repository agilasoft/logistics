# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Main / Linked service rules from Sales Quote quotation_type and conversion state."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint


def get_sales_quote_quotation_type(doc: Any) -> str | None:
	sq = (getattr(doc, "sales_quote", None) or "").strip()
	if not sq or sq.startswith("new-"):
		return None
	if not frappe.db.exists("Sales Quote", sq):
		return None
	return frappe.db.get_value("Sales Quote", sq, "quotation_type")


def is_internal_job_satellite(doc: Any) -> bool:
	"""True when this doc is a Linked satellite of a main operational job."""
	from logistics.utils.service_role_rules import is_linked_service_satellite

	return is_linked_service_satellite(doc)


def has_created_internal_job_children(doc: Any) -> bool:
	"""True when Linked Services has at least one row with a job_no."""
	if not getattr(doc, "doctype", None):
		return False

	def _rows_have_job_no(rows) -> bool:
		for row in rows or []:
			jn = row.get("job_no") if isinstance(row, dict) else getattr(row, "job_no", None)
			if (jn or "").strip():
				return True
		return False

	for fieldname in ("linked_services", "internal_job_details", "internal_jobs"):
		rows = doc.get(fieldname) if hasattr(doc, "get") else getattr(doc, fieldname, None)
		if _rows_have_job_no(rows):
			return True
	try:
		from logistics.utils.linked_service_compat import linked_service_rows

		if _rows_have_job_no(linked_service_rows(doc)):
			return True
	except Exception:
		pass
	return False


def main_service_has_created_internal_jobs(doc: Any) -> bool:
	from logistics.utils.service_role_rules import is_main_service_doc

	if not is_main_service_doc(doc):
		return False
	return has_created_internal_job_children(doc)


def _resolve_and_set_linked_service_link(doc: Any) -> None:
	"""Stamp ``linked_service`` / legacy ``internal_job`` from the parent planning row."""
	from logistics.utils.service_role_rules import (
		get_linked_service_name,
		get_service_role,
		SERVICE_ROLE_LINKED,
		set_linked_service_name,
	)

	role = get_service_role(doc)
	if role != SERVICE_ROLE_LINKED:
		if get_linked_service_name(doc):
			set_linked_service_name(doc, None)
		return
	if get_linked_service_name(doc):
		return
	if not (getattr(doc, "name", None) or "").strip():
		return
	try:
		from logistics.utils.internal_job_persistence import (
			resolve_internal_job_for_internal_job_booking,
		)
	except Exception:
		return
	try:
		resolved = resolve_internal_job_for_internal_job_booking(doc)
	except Exception:
		resolved = None
	if resolved:
		set_linked_service_name(doc, resolved)


def apply_sales_quote_ms_ij_rules(doc: Any, method=None) -> None:
	"""Validate hook: enforce service_role from quote type, satellite role, and children."""
	from logistics.utils.service_role_rules import (
		SERVICE_ROLE_LINKED,
		SERVICE_ROLE_MAIN,
		SERVICE_ROLE_STANDALONE,
		apply_linked_service_satellite_flags,
		apply_main_service_flags,
		apply_standalone_service_flags,
		get_main_service_name,
		get_main_service_type,
		get_service_role,
		is_linked_service_satellite,
	)

	if not (hasattr(doc, "service_role") or getattr(doc, "doctype", None)):
		return

	if is_linked_service_satellite(doc):
		apply_linked_service_satellite_flags(
			doc, get_main_service_type(doc), get_main_service_name(doc)
		)
		_resolve_and_set_linked_service_link(doc)
		return

	quotation_type = (get_sales_quote_quotation_type(doc) or "").strip()

	if quotation_type == "One-off":
		if get_service_role(doc) == SERVICE_ROLE_LINKED or cint(
			getattr(doc, "is_internal_job", 0)
		):
			# Keep linked satellites on one-off quotes.
			if get_main_service_type(doc) and get_main_service_name(doc):
				apply_linked_service_satellite_flags(
					doc, get_main_service_type(doc), get_main_service_name(doc)
				)
			_resolve_and_set_linked_service_link(doc)
			return
		apply_main_service_flags(doc)
		_resolve_and_set_linked_service_link(doc)
		return

	if quotation_type == "Project":
		apply_standalone_service_flags(doc)
		_resolve_and_set_linked_service_link(doc)
		return

	# Regular (and quotes without sales_quote / unknown type)
	if has_created_internal_job_children(doc):
		role = get_service_role(doc)
		if role != SERVICE_ROLE_MAIN and not cint(getattr(doc, "is_main_service", 0)):
			frappe.throw(
				_(
					"Main Service cannot be cleared while Linked Services are linked on this document. "
					"Remove or cancel linked services first."
				),
				title=_("Main Service Locked"),
			)
		apply_main_service_flags(doc)
		_resolve_and_set_linked_service_link(doc)
		return

	_resolve_and_set_linked_service_link(doc)


def on_validate_main_service_internal_job(doc, method=None) -> None:
	"""Doc event entry point (hooks)."""
	from logistics.utils.service_role_rules import apply_service_role_rules

	apply_service_role_rules(doc, method)
