# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Roll up planned cost/revenue from programme charges onto Lifecycle Job rows by lifecycle_job_row idx."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt

from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal
from logistics.utils.internal_job_main_rollup import (
	_charge_planned_cost,
	_charge_planned_revenue,
	_is_disbursement_charge,
)


def _lifecycle_rows(doc: Any) -> list[Any]:
	return list(doc.get("lifecycle_jobs") or [])


def _charges(doc: Any) -> list[Any]:
	return list(doc.get("charges") or [])


def _rows_for_service_type(lifecycle_rows: list[Any], service_type: str | None) -> list[Any]:
	st = (service_type or "").strip()
	if not st:
		return []
	return [
		r
		for r in lifecycle_rows
		if sales_quote_charge_service_types_equal(getattr(r, "service_type", None), st)
	]


def _planning_lifecycle_rows(candidates: list[Any]) -> list[Any]:
	"""Lifecycle rows with the same service type that still have no linked operational job."""
	return [
		row
		for row in candidates
		if not (getattr(row, "job_no", None) or "").strip()
	]


def _auto_assign_charge_lifecycle_rows(doc: Any) -> None:
	"""Set lifecycle_job_row when the charge maps to one lifecycle line for its service type.

	When multiple lines share the service type but only one is still in programme planning
	(no ``job_no``), attribute unassigned charges to that row.
	"""
	lifecycle_rows = _lifecycle_rows(doc)
	for charge in _charges(doc):
		if cint(getattr(charge, "lifecycle_job_row", 0) or 0):
			continue
		st = getattr(charge, "service_type", None)
		candidates = _rows_for_service_type(lifecycle_rows, st)
		if len(candidates) == 1:
			charge.lifecycle_job_row = cint(candidates[0].idx or 0)
			continue
		planning = _planning_lifecycle_rows(candidates)
		if len(planning) == 1:
			charge.lifecycle_job_row = cint(planning[0].idx or 0)


def _lifecycle_rows_need_programme_charge_attribution(candidates: list[Any]) -> bool:
	"""True when any matching lifecycle row has no operational job yet (programme charges still plan the leg)."""
	for row in candidates:
		if not (getattr(row, "job_no", None) or "").strip():
			return True
	return False


def _validate_charge_lifecycle_links(doc: Any) -> None:
	lifecycle_rows = _lifecycle_rows(doc)
	if not lifecycle_rows:
		return

	for charge in _charges(doc):
		if _is_disbursement_charge(charge):
			continue
		st = getattr(charge, "service_type", None)
		ch_idx = cint(getattr(charge, "lifecycle_job_row", 0) or 0)
		if ch_idx:
			matching = [r for r in lifecycle_rows if cint(r.idx or 0) == ch_idx]
			if not matching:
				frappe.throw(
					_("Charge row {0}: Lifecycle Job row {1} does not exist on this document.").format(
						cint(getattr(charge, "idx", 0) or 0) or "?",
						ch_idx,
					),
					title=_("Invalid Lifecycle Job on charge"),
				)
			lifecycle_row = matching[0]
			if st and not sales_quote_charge_service_types_equal(
				st, getattr(lifecycle_row, "service_type", None)
			):
				frappe.throw(
					_(
						"Charge row {0}: Service Type {1} does not match Lifecycle Job row {2} ({3})."
					).format(
						cint(getattr(charge, "idx", 0) or 0) or "?",
						(st or "").strip(),
						ch_idx,
						(getattr(lifecycle_row, "service_type", None) or "").strip(),
					),
					title=_("Service Type mismatch"),
				)


def _charge_belongs_to_lifecycle_row(
	charge: Any,
	lifecycle_row: Any,
	lifecycle_rows: list[Any],
) -> bool:
	if _is_disbursement_charge(charge):
		return False

	row_idx = cint(getattr(lifecycle_row, "idx", 0) or 0)
	ch_idx = cint(getattr(charge, "lifecycle_job_row", 0) or 0)
	row_st = getattr(lifecycle_row, "service_type", None)
	ch_st = getattr(charge, "service_type", None)

	if ch_idx:
		if ch_idx != row_idx:
			return False
		if row_st and ch_st and not sales_quote_charge_service_types_equal(ch_st, row_st):
			return False
		return True

	# Legacy: no lifecycle_job_row — attribute to sole lifecycle row for this service type.
	if not row_st or not sales_quote_charge_service_types_equal(ch_st, row_st):
		return False
	candidates = _rows_for_service_type(lifecycle_rows, row_st)
	return len(candidates) == 1 and cint(candidates[0].idx or 0) == row_idx


def _planned_totals_for_lifecycle_row(
	lifecycle_row: Any,
	lifecycle_rows: list[Any],
	charges: list[Any],
) -> tuple[float, float]:
	planned_cost = 0.0
	planned_revenue = 0.0
	for charge in charges:
		if not _charge_belongs_to_lifecycle_row(charge, lifecycle_row, lifecycle_rows):
			continue
		planned_cost += _charge_planned_cost(charge)
		planned_revenue += _charge_planned_revenue(charge)
	return planned_cost, planned_revenue


def sync_lifecycle_job_planned_from_charges(doc: Any) -> None:
	"""Backward-compatible entry: sync lifecycle planned/actual (jobs when linked, else programme charges)."""
	from logistics.special_projects.lifecycle_job_financial_rollup import (
		sync_lifecycle_job_financials,
	)

	sync_lifecycle_job_financials(doc)
