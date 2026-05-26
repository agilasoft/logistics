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


def apply_sales_quote_ms_ij_rules(doc: Any, method=None) -> None:
	"""Validate hook: enforce MS/IJ flags from quote type, satellite role, and scenario 1."""
	if not hasattr(doc, "is_internal_job") or not hasattr(doc, "is_main_service"):
		return

	_enforce_mutual_exclusivity(doc)

	if is_internal_job_satellite(doc):
		doc.is_internal_job = 1
		doc.is_main_service = 0
		return

	quotation_type = (get_sales_quote_quotation_type(doc) or "").strip()

	if quotation_type == "One-off":
		if cint(getattr(doc, "is_internal_job", 0)):
			doc.is_main_service = 0
			return
		doc.is_main_service = 1
		doc.is_internal_job = 0
		return

	if quotation_type == "Project":
		doc.is_main_service = 0
		doc.is_internal_job = 0
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
		return

	# Regular: allow user toggles; mutual exclusivity already applied


def on_validate_main_service_internal_job(doc, method=None) -> None:
	"""Doc event entry point (hooks)."""
	apply_sales_quote_ms_ij_rules(doc, method)
