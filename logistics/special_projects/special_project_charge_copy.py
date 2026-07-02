# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Copy Special Project programme charge rows onto operational booking/order documents."""

from __future__ import annotations

from typing import Any

import frappe

from logistics.special_projects.special_project_charge_lifecycle import (
	programme_charges_for_service_type,
)
from logistics.utils.charge_service_type import (
	canonical_charge_service_type_for_storage,
	implied_service_type_for_doctype,
	operational_booking_charge_service_type_label,
	sales_quote_charge_service_types_equal,
)
from logistics.utils.internal_job_charge_copy import _scrub_main_row_to_child_dict
from logistics.utils.linked_service_compat import is_linked_charge_scope, normalize_charge_scope
from logistics.utils.sales_quote_charge_parameters import (
	programme_charge_matches_creation_parameters,
)


def _programme_charge_scope(charge: Any) -> str:
	if isinstance(charge, dict):
		return normalize_charge_scope(charge.get("charge_scope"))
	return normalize_charge_scope(getattr(charge, "charge_scope", None))


def linked_scope_programme_charges(charges: list[Any]) -> list[Any]:
	"""Programme charge rows whose scope is Linked (or legacy Internal Job)."""
	return [ch for ch in charges if is_linked_charge_scope(_programme_charge_scope(ch))]


def booking_copy_uses_linked_scope_only(target_doctype: str) -> bool:
	"""Operational freight/customs bookings copy Linked-scope programme charges only."""
	return (target_doctype or "").strip() != "Project Order"


def service_type_uses_linked_scope_copy(service_type_label: str | None) -> bool:
	"""Whether programme charge copy / preview for this service type is Linked-scope only."""
	if sales_quote_charge_service_types_equal(service_type_label, "Special Project"):
		return False
	stored = canonical_charge_service_type_for_storage(service_type_label)
	return stored not in ("special project", "exhibits")


def programme_charges_for_booking_copy(
	sp_doc: Any,
	service_type: str | None,
	*,
	job_type: str | None = None,
) -> list[Any]:
	"""Programme charges eligible to copy or preview for a booking/order create."""
	pool = programme_charges_for_service_type(sp_doc, service_type)
	if (job_type or "").strip() == "Project Order":
		return pool
	if service_type_uses_linked_scope_copy(service_type):
		return linked_scope_programme_charges(pool)
	return pool

_NUMERIC_SCALE_FIELDS = (
	"estimated_cost",
	"actual_cost",
	"estimated_revenue",
	"actual_revenue",
	"quantity",
	"cost_quantity",
	"unit_rate",
	"unit_cost",
	"base_amount",
	"cost_base_amount",
	"minimum_charge",
	"maximum_charge",
	"cost_minimum_charge",
	"cost_maximum_charge",
)


def _charges_child_doctype(parent_doctype: str) -> str | None:
	df = frappe.get_meta(parent_doctype).get_field("charges")
	if df and df.fieldtype == "Table" and df.options:
		return (df.options or "").strip() or None
	return None


def _special_project_charge_matches_row(
	sp_doc: Any,
	charge: Any,
	lifecycle_row: Any | None,
	target_doctype: str,
	*,
	ignore_pin: bool = False,
) -> bool:
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
	*,
	ignore_pin: bool = False,
	creation_parameters: dict | None = None,
) -> int:
	child_dt = _charges_child_doctype(target_doc.doctype)
	if not child_dt:
		return 0

	row_st = (getattr(lifecycle_row, "service_type", None) or "").strip() if lifecycle_row else ""
	implied = implied_service_type_for_doctype(target_doc.doctype)
	forced_label = operational_booking_charge_service_type_label(
		row_st or implied,
		default=row_st or "Transport",
	)
	parent_implied_canonical = canonical_charge_service_type_for_storage(implied)
	if (
		canonical_charge_service_type_for_storage(forced_label) in ("special project", "exhibits")
		and parent_implied_canonical not in ("special project", "exhibits")
	):
		forced_label = operational_booking_charge_service_type_label(implied, default="Transport")

	source_charges = programme_charges_for_booking_copy(
		sp_doc,
		getattr(lifecycle_row, "service_type", None) if lifecycle_row else None,
		job_type=target_doc.doctype,
	)
	if creation_parameters:
		source_charges = [
			ch
			for ch in source_charges
			if programme_charge_matches_creation_parameters(ch, creation_parameters)
		]

	dicts: list[dict[str, Any]] = []
	for ch in source_charges:
		if not _special_project_charge_matches_row(
			sp_doc, ch, lifecycle_row, target_doc.doctype, ignore_pin=ignore_pin
		):
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


def _restrict_charges_to_linked_scope(target_doc: Any) -> None:
	"""Keep only Linked-scope charge rows on an operational booking/order."""
	rows = list(getattr(target_doc, "charges", None) or [])
	if not rows:
		return
	kept = [
		ch
		for ch in rows
		if is_linked_charge_scope(
			normalize_charge_scope(getattr(ch, "charge_scope", None))
		)
	]
	if len(kept) == len(rows):
		return
	target_doc.set("charges", kept)


def _restrict_charges_to_target_service_type(
	target_doc: Any, lifecycle_row: Any | None = None
) -> None:
	row_st = (getattr(lifecycle_row, "service_type", None) or "").strip() if lifecycle_row else ""
	implied = implied_service_type_for_doctype(target_doc.doctype)
	want = row_st or implied
	if not want:
		return
	rows = list(getattr(target_doc, "charges", None) or [])
	if not rows:
		return
	kept: list[Any] = []
	for ch in rows:
		ch_st = (getattr(ch, "service_type", None) or "").strip()
		if not ch_st:
			kept.append(ch)
			continue
		if sales_quote_charge_service_types_equal(ch_st, want):
			kept.append(ch)
	if len(kept) == len(rows):
		return
	target_doc.set("charges", kept)


def prepare_operational_charges_from_special_project(
	sp_doc: Any,
	target_doc: Any,
	lifecycle_row: Any | None = None,
	creation_parameters: dict | None = None,
) -> None:
	populated = populate_operational_charges_from_special_project(
		sp_doc, target_doc, lifecycle_row, creation_parameters=creation_parameters
	)
	if not populated:
		populated = populate_operational_charges_from_special_project(
			sp_doc,
			target_doc,
			lifecycle_row,
			ignore_pin=True,
			creation_parameters=creation_parameters,
		)
	if not populated:
		_populate_charges_from_linked_sales_quote(target_doc)
		_restrict_charges_to_target_service_type(target_doc, lifecycle_row)
	if booking_copy_uses_linked_scope_only(target_doc.doctype):
		_restrict_charges_to_linked_scope(target_doc)
