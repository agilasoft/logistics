# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Service role (Main / Linked / Standalone) for operational documents.

Source of truth: ``service_role``, ``main_service_type``, ``main_service``,
and ``linked_service``. Legacy Internal Job field names are read only as a
fallback for in-memory / pre-migrate data and are never required.
"""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from logistics.utils.sales_quote_ms_ij_rules import (
	apply_sales_quote_ms_ij_rules,
	get_sales_quote_quotation_type,
	has_created_internal_job_children,
)


SERVICE_ROLE_MAIN = "Main"
SERVICE_ROLE_LINKED = "Linked"
SERVICE_ROLE_STANDALONE = "Standalone"

SCOPE_LINKED = "Linked"
SCOPE_MAIN = "Main"
# Backward-compatible alias for Internal Job charge scope
SCOPE_INTERNAL_JOB = SCOPE_LINKED


def _meta_has_field(doc: Any, fieldname: str) -> bool:
	doctype = getattr(doc, "doctype", None)
	if not doctype:
		return hasattr(doc, fieldname)
	try:
		return bool(frappe.get_meta(doctype).has_field(fieldname))
	except Exception:
		return hasattr(doc, fieldname)


def get_main_service_type(doc: Any) -> str:
	"""Main booking DocType for a Linked satellite."""
	return (
		getattr(doc, "main_service_type", None)
		or getattr(doc, "main_job_type", None)
		or ""
	).strip()


def get_main_service_name(doc: Any) -> str:
	"""Main booking name for a Linked satellite."""
	return (
		getattr(doc, "main_service", None) or getattr(doc, "main_job", None) or ""
	).strip()


def get_linked_service_name(doc: Any) -> str:
	"""Canonical Linked Service record name for this operational doc."""
	return (
		getattr(doc, "linked_service", None) or getattr(doc, "internal_job", None) or ""
	).strip()


def set_linked_service_name(doc: Any, name: str | None) -> None:
	val = (name or "").strip() or None
	if _meta_has_field(doc, "linked_service") or hasattr(doc, "linked_service"):
		doc.linked_service = val
	if _meta_has_field(doc, "internal_job") or hasattr(doc, "internal_job"):
		doc.internal_job = val


def get_service_role(doc: Any) -> str:
	role = (getattr(doc, "service_role", None) or "").strip()
	if role in (SERVICE_ROLE_MAIN, SERVICE_ROLE_LINKED, SERVICE_ROLE_STANDALONE):
		return role
	if get_main_service_type(doc) and get_main_service_name(doc):
		return SERVICE_ROLE_LINKED
	# Legacy fallbacks (pre-migrate / tests).
	if cint(getattr(doc, "is_internal_job", 0)):
		return SERVICE_ROLE_LINKED
	if cint(getattr(doc, "is_main_service", 0)):
		return SERVICE_ROLE_MAIN
	return SERVICE_ROLE_STANDALONE


def is_main_service_doc(doc: Any) -> bool:
	return get_service_role(doc) == SERVICE_ROLE_MAIN


def is_linked_service_satellite(doc: Any) -> bool:
	if get_service_role(doc) != SERVICE_ROLE_LINKED:
		return False
	return bool(get_main_service_type(doc) and get_main_service_name(doc))


def apply_linked_service_satellite_flags(
	doc: Any, main_service_type: str, main_service: str
) -> None:
	"""Stamp a satellite operational doc as Linked to *main_service*."""
	mt = (main_service_type or "").strip()
	mn = (main_service or "").strip()
	if _meta_has_field(doc, "service_role") or hasattr(doc, "service_role"):
		doc.service_role = SERVICE_ROLE_LINKED
	if _meta_has_field(doc, "main_service_type") or hasattr(doc, "main_service_type"):
		doc.main_service_type = mt or None
	if _meta_has_field(doc, "main_service") or hasattr(doc, "main_service"):
		doc.main_service = mn or None
	# Legacy mirrors while columns still exist (pre-drop / tests).
	if _meta_has_field(doc, "is_internal_job"):
		doc.is_internal_job = 1
	if _meta_has_field(doc, "is_main_service"):
		doc.is_main_service = 0
	if _meta_has_field(doc, "main_job_type"):
		doc.main_job_type = mt or None
	if _meta_has_field(doc, "main_job"):
		doc.main_job = mn or None


def apply_main_service_flags(doc: Any) -> None:
	"""Stamp an operational doc as Main service."""
	if _meta_has_field(doc, "service_role") or hasattr(doc, "service_role"):
		doc.service_role = SERVICE_ROLE_MAIN
	_clear_main_refs(doc)
	if _meta_has_field(doc, "is_main_service"):
		doc.is_main_service = 1
	if _meta_has_field(doc, "is_internal_job"):
		doc.is_internal_job = 0


def apply_standalone_service_flags(doc: Any) -> None:
	"""Stamp an operational doc as Standalone."""
	if _meta_has_field(doc, "service_role") or hasattr(doc, "service_role"):
		doc.service_role = SERVICE_ROLE_STANDALONE
	_clear_main_refs(doc)
	if _meta_has_field(doc, "is_main_service"):
		doc.is_main_service = 0
	if _meta_has_field(doc, "is_internal_job"):
		doc.is_internal_job = 0


def _clear_main_refs(doc: Any) -> None:
	for fn in ("main_service_type", "main_service", "main_job_type", "main_job"):
		if _meta_has_field(doc, fn) or hasattr(doc, fn):
			try:
				setattr(doc, fn, None)
			except Exception:
				pass


def sync_main_service_refs(doc: Any) -> None:
	"""Normalise main_service_* (and legacy mirrors if present) for Linked docs."""
	role = get_service_role(doc)
	if role != SERVICE_ROLE_LINKED:
		_clear_main_refs(doc)
		return

	mt = get_main_service_type(doc)
	mn = get_main_service_name(doc)
	if _meta_has_field(doc, "main_service_type") or hasattr(doc, "main_service_type"):
		doc.main_service_type = mt or None
	if _meta_has_field(doc, "main_service") or hasattr(doc, "main_service"):
		doc.main_service = mn or None
	if _meta_has_field(doc, "main_job_type"):
		doc.main_job_type = mt or None
	if _meta_has_field(doc, "main_job"):
		doc.main_job = mn or None

	ls = get_linked_service_name(doc)
	if ls:
		set_linked_service_name(doc, ls)


def apply_service_role_rules(doc: Any, method=None) -> None:
	"""Validate hook: enforce service_role and main service linkage."""
	if not (_meta_has_field(doc, "service_role") or hasattr(doc, "service_role")):
		return

	# Derive role when empty (legacy flags or main refs).
	if not (getattr(doc, "service_role", None) or "").strip():
		doc.service_role = get_service_role(doc)

	apply_sales_quote_ms_ij_rules(doc, method)

	# MS/IJ rules may adjust role; re-read and normalise.
	role = get_service_role(doc)
	doc.service_role = role

	if role == SERVICE_ROLE_MAIN:
		apply_main_service_flags(doc)
	elif role == SERVICE_ROLE_LINKED:
		sync_main_service_refs(doc)
		mt = get_main_service_type(doc)
		mn = get_main_service_name(doc)
		if not mt or not mn:
			frappe.throw(
				_("Linked service requires Main Service Type and Main Service."),
				title=_("Linked Service"),
			)
	else:
		apply_standalone_service_flags(doc)

	quotation_type = (get_sales_quote_quotation_type(doc) or "").strip()
	if quotation_type == "Regular" and role == SERVICE_ROLE_MAIN and has_created_internal_job_children(doc):
		doc.service_role = SERVICE_ROLE_MAIN

	from logistics.utils.get_charges_from_quotation import assert_one_off_sales_quote_job_rules

	assert_one_off_sales_quote_job_rules(doc)


def on_validate_service_role(doc, method=None) -> None:
	apply_service_role_rules(doc, method)


# Back-compat aliases used by older imports.
def sync_service_role_from_legacy_flags(doc: Any) -> None:
	if not (_meta_has_field(doc, "service_role") or hasattr(doc, "service_role")):
		return
	if (getattr(doc, "service_role", None) or "").strip():
		return
	doc.service_role = get_service_role(doc)


def sync_legacy_flags_from_service_role(doc: Any) -> None:
	role = get_service_role(doc)
	if role == SERVICE_ROLE_MAIN:
		apply_main_service_flags(doc)
	elif role == SERVICE_ROLE_LINKED:
		sync_main_service_refs(doc)
		if _meta_has_field(doc, "is_internal_job"):
			doc.is_internal_job = 1
		if _meta_has_field(doc, "is_main_service"):
			doc.is_main_service = 0
	else:
		apply_standalone_service_flags(doc)
