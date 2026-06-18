# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Service role (Main / Linked / Standalone) rules for operational documents."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from logistics.utils.sales_quote_ms_ij_rules import (
	apply_sales_quote_ms_ij_rules,
	get_sales_quote_quotation_type,
	has_created_internal_job_children,
	is_internal_job_satellite,
)


SERVICE_ROLE_MAIN = "Main"
SERVICE_ROLE_LINKED = "Linked"
SERVICE_ROLE_STANDALONE = "Standalone"

SCOPE_LINKED = "Linked"
SCOPE_MAIN = "Main"
# Backward-compatible alias for Internal Job charge scope
SCOPE_INTERNAL_JOB = SCOPE_LINKED


def get_service_role(doc: Any) -> str:
	role = (getattr(doc, "service_role", None) or "").strip()
	if role in (SERVICE_ROLE_MAIN, SERVICE_ROLE_LINKED, SERVICE_ROLE_STANDALONE):
		return role
	if cint(getattr(doc, "is_internal_job", 0)) and is_internal_job_satellite(doc):
		return SERVICE_ROLE_LINKED
	if cint(getattr(doc, "is_main_service", 0)):
		return SERVICE_ROLE_MAIN
	return SERVICE_ROLE_STANDALONE


def sync_service_role_from_legacy_flags(doc: Any) -> None:
	if not hasattr(doc, "service_role"):
		return
	if (getattr(doc, "service_role", None) or "").strip():
		return
	doc.service_role = get_service_role(doc)


def sync_legacy_flags_from_service_role(doc: Any) -> None:
	if not hasattr(doc, "service_role"):
		return
	role = (getattr(doc, "service_role", None) or "").strip()
	if not role:
		sync_service_role_from_legacy_flags(doc)
		role = (getattr(doc, "service_role", None) or "").strip()
	if not role:
		return
	if hasattr(doc, "is_main_service"):
		doc.is_main_service = 1 if role == SERVICE_ROLE_MAIN else 0
	if hasattr(doc, "is_internal_job"):
		doc.is_internal_job = 1 if role == SERVICE_ROLE_LINKED else 0
	if role != SERVICE_ROLE_LINKED and hasattr(doc, "main_job"):
		if hasattr(doc, "main_job_type"):
			doc.main_job_type = None
		doc.main_job = None


def is_linked_service_satellite(doc: Any) -> bool:
	return get_service_role(doc) == SERVICE_ROLE_LINKED or is_internal_job_satellite(doc)


def apply_service_role_rules(doc: Any, method=None) -> None:
	"""Validate hook: service_role + legacy MS/IJ flags."""
	sync_service_role_from_legacy_flags(doc)
	apply_sales_quote_ms_ij_rules(doc, method)
	sync_legacy_flags_from_service_role(doc)

	role = get_service_role(doc)
	if hasattr(doc, "service_role"):
		doc.service_role = role

	if role == SERVICE_ROLE_LINKED:
		mt = (getattr(doc, "main_service_type", None) or getattr(doc, "main_job_type", None) or "").strip()
		mn = (getattr(doc, "main_service", None) or getattr(doc, "main_job", None) or "").strip()
		if not mt or not mn:
			frappe.throw(
				_("Linked service requires Main Service Type and Main Service."),
				title=_("Linked Service"),
			)
		if hasattr(doc, "main_service_type") and not doc.main_service_type:
			doc.main_service_type = mt
		if hasattr(doc, "main_service") and not getattr(doc, "main_service", None):
			doc.main_service = mn

	sq = (getattr(doc, "sales_quote", None) or "").strip()
	if sq and hasattr(doc, "service_scope") and not (getattr(doc, "service_scope", None) or "").strip():
		doc.service_scope = sq

	quotation_type = (get_sales_quote_quotation_type(doc) or "").strip()
	if quotation_type == "Regular" and role == SERVICE_ROLE_MAIN and has_created_internal_job_children(doc):
		if hasattr(doc, "service_role"):
			doc.service_role = SERVICE_ROLE_MAIN


def on_validate_service_role(doc, method=None) -> None:
	apply_service_role_rules(doc, method)
