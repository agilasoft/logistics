# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Main Service / Internal Job rules from Sales Quote quotation_type and conversion state."""

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
	if not cint(getattr(doc, "is_internal_job", 0)):
		return False
	mt = (getattr(doc, "main_job_type", None) or "").strip()
	mn = (getattr(doc, "main_job", None) or "").strip()
	return bool(mt and mn)


def has_created_internal_job_children(doc: Any) -> bool:
	"""True when Internal Job Details has at least one row with a linked job_no."""
	if not getattr(doc, "doctype", None):
		return False
	meta = frappe.get_meta(doc.doctype)
	if not meta.get_field("internal_job_details"):
		return False
	for row in doc.get("internal_job_details") or []:
		if (getattr(row, "job_no", None) or "").strip():
			return True
	return False


def main_service_has_created_internal_jobs(doc: Any) -> bool:
	if not cint(getattr(doc, "is_main_service", 0)):
		return False
	return has_created_internal_job_children(doc)


def _enforce_mutual_exclusivity(doc: Any) -> None:
	if not hasattr(doc, "is_internal_job") or not hasattr(doc, "is_main_service"):
		return
	if cint(getattr(doc, "is_internal_job", 0)):
		doc.is_main_service = 0


def _resolve_and_set_internal_job_link(doc: Any) -> None:
	"""Defensive fallback: stamp ``doc.internal_job`` from the parent's Internal Job Detail row.

	The create flows (e.g. ``create_transport_order_from_*``) already populate ``internal_job``
	directly from the Internal Job Detail row via ``apply_internal_job_detail_row_to_operational_doc``.
	This hook handles the remaining cases:

	* legacy documents created before the field existed,
	* docs created through paths that bypass the IJ-row helper (e.g. context inheritance from a
	  Transport Job source),
	* re-saves where ``internal_job`` may have been cleared manually.

	The lookup uses ``logistics.utils.internal_job_persistence.resolve_internal_job_for_internal_job_booking``
	which walks ``main_job_type`` + ``main_job`` → ``Internal Job Detail`` (matching this doc's
	``doctype`` + ``name``) → ``internal_job`` link.
	"""
	try:
		meta = frappe.get_meta(getattr(doc, "doctype", None))
	except Exception:
		return
	if not meta or not meta.get_field("internal_job"):
		return
	if not cint(getattr(doc, "is_internal_job", 0)):
		# Not (any longer) an IJ → clear stale link rather than leave a dangling pointer.
		if (getattr(doc, "internal_job", None) or "").strip():
			doc.internal_job = None
		return
	if (getattr(doc, "internal_job", None) or "").strip():
		return
	if not (getattr(doc, "name", None) or "").strip():
		# Pre-insert without a name yet; nothing reliable to look up. The IJ-row creation path
		# stamps the link directly, so we wait for the first re-save before backfilling.
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
		doc.internal_job = resolved


def apply_sales_quote_ms_ij_rules(doc: Any, method=None) -> None:
	"""Validate hook: enforce MS/IJ flags from quote type, satellite role, and scenario 1."""
	if not hasattr(doc, "is_internal_job") or not hasattr(doc, "is_main_service"):
		return

	_enforce_mutual_exclusivity(doc)

	if is_internal_job_satellite(doc):
		doc.is_internal_job = 1
		doc.is_main_service = 0
		_resolve_and_set_internal_job_link(doc)
		return

	quotation_type = (get_sales_quote_quotation_type(doc) or "").strip()

	if quotation_type == "One-off":
		if cint(getattr(doc, "is_internal_job", 0)):
			doc.is_main_service = 0
			_resolve_and_set_internal_job_link(doc)
			return
		doc.is_main_service = 1
		doc.is_internal_job = 0
		_resolve_and_set_internal_job_link(doc)
		return

	if quotation_type == "Project":
		doc.is_main_service = 0
		doc.is_internal_job = 0
		_resolve_and_set_internal_job_link(doc)
		return

	# Regular (and quotes without sales_quote / unknown type)
	if has_created_internal_job_children(doc):
		if not cint(getattr(doc, "is_main_service", 0)):
			frappe.throw(
				_(
					"Main Service cannot be cleared while Internal Jobs are linked on this document. "
					"Remove or cancel linked internal jobs first."
				),
				title=_("Main Service Locked"),
			)
		doc.is_main_service = 1
		_resolve_and_set_internal_job_link(doc)
		return

	# Regular: allow user toggles; mutual exclusivity already applied
	_resolve_and_set_internal_job_link(doc)


def on_validate_main_service_internal_job(doc, method=None) -> None:
	"""Doc event entry point (hooks)."""
	apply_sales_quote_ms_ij_rules(doc, method)
