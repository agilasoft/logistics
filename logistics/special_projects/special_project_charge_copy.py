# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Copy Special Project programme charge rows onto operational booking/order documents."""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import cint

from logistics.utils.charge_service_type import (
	canonical_charge_service_type_for_storage,
	implied_service_type_for_doctype,
	operational_booking_charge_service_type_label,
	sales_quote_charge_service_types_equal,
)
from logistics.utils.internal_job_charge_copy import _scrub_main_row_to_child_dict


def _charges_child_doctype(parent_doctype: str) -> str | None:
	df = frappe.get_meta(parent_doctype).get_field("charges")
	if df and df.fieldtype == "Table" and df.options:
		return (df.options or "").strip() or None
	return None


def _special_project_charge_matches_row(
	charge: Any,
	lifecycle_row: Any | None,
	target_doctype: str,
) -> bool:
	"""True when a programme charge row should copy for this lifecycle line / target document."""
	if lifecycle_row is not None:
		ch_idx = cint(getattr(charge, "lifecycle_job_row", 0) or 0)
		row_idx = cint(getattr(lifecycle_row, "idx", 0) or 0)
		if ch_idx:
			if row_idx and ch_idx != row_idx:
				return False
			row_st = getattr(lifecycle_row, "service_type", None)
			ch_st = getattr(charge, "service_type", None)
			if row_st and ch_st and not sales_quote_charge_service_types_equal(ch_st, row_st):
				return False
			return True

	row_st = (getattr(lifecycle_row, "service_type", None) or "").strip() if lifecycle_row else ""
	ch_st = getattr(charge, "service_type", None)
	if row_st:
		return sales_quote_charge_service_types_equal(ch_st, row_st)
	want = implied_service_type_for_doctype(target_doctype)
	if not want:
		return True
	return sales_quote_charge_service_types_equal(ch_st, want)


def populate_operational_charges_from_special_project(
	sp_doc: Any,
	target_doc: Any,
	lifecycle_row: Any | None = None,
) -> int:
	"""Append charge lines from the Special Project onto *target_doc* (unsaved). Returns row count."""
	child_dt = _charges_child_doctype(target_doc.doctype)
	if not child_dt:
		return 0

	row_st = (getattr(lifecycle_row, "service_type", None) or "").strip() if lifecycle_row else ""
	implied = implied_service_type_for_doctype(target_doc.doctype)
	forced_label = operational_booking_charge_service_type_label(
		row_st or implied,
		default=row_st or "Transport",
	)
	# Operational booking charge child tables (Sea/Air Booking, Transport/Declaration/Inbound Order)
	# only accept Air/Sea/Transport/Customs/Warehousing — never the programme labels. Fall back to
	# the doctype's implied service type when the resolved label would fail Select validation.
	parent_implied_canonical = canonical_charge_service_type_for_storage(implied)
	if (
		canonical_charge_service_type_for_storage(forced_label) in ("special project", "exhibits")
		and parent_implied_canonical not in ("special project", "exhibits")
	):
		forced_label = operational_booking_charge_service_type_label(implied, default="Transport")

	dicts: list[dict[str, Any]] = []
	for ch in getattr(sp_doc, "charges", None) or []:
		if not _special_project_charge_matches_row(ch, lifecycle_row, target_doc.doctype):
			continue
		row = _scrub_main_row_to_child_dict(ch, child_dt, forced_label)
		if row:
			dicts.append(row)

	if not dicts:
		return 0

	target_doc.set("charges", [])
	for row in dicts:
		target_doc.append("charges", row)
	return len(dicts)


def _populate_charges_from_linked_sales_quote(target_doc: Any) -> None:
	"""Fall back to Sales Quote charge population when the programme has no matching rows."""
	sq_name = getattr(target_doc, "sales_quote", None)
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return

	dt = target_doc.doctype
	try:
		if dt == "Air Booking":
			from logistics.utils.internal_job_from_source import (
				_populate_air_booking_charges_from_linked_quote_on_internal_create,
			)

			_populate_air_booking_charges_from_linked_quote_on_internal_create(target_doc)
		elif dt == "Sea Booking":
			from logistics.utils.internal_job_from_source import (
				_populate_sea_booking_charges_from_linked_quote_on_internal_create,
			)

			_populate_sea_booking_charges_from_linked_quote_on_internal_create(target_doc)
		elif dt == "Transport Order" and hasattr(target_doc, "_populate_charges_from_sales_quote"):
			target_doc._populate_charges_from_sales_quote()
		elif dt == "Declaration Order" and hasattr(target_doc, "_populate_charges_from_sales_quote"):
			target_doc._populate_charges_from_sales_quote()
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			f"Special Project — Sales Quote charge population on {dt} create",
		)


def prepare_operational_charges_from_special_project(
	sp_doc: Any,
	target_doc: Any,
	lifecycle_row: Any | None = None,
) -> None:
	"""Copy programme charges when present; otherwise populate from the linked Sales Quote."""
	if populate_operational_charges_from_special_project(sp_doc, target_doc, lifecycle_row):
		return
	_populate_charges_from_linked_sales_quote(target_doc)
