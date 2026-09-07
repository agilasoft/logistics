# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Copy MICE Project consolidation charge rows onto operational documents."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import frappe
from frappe import _
from frappe.utils import flt

from logistics.special_projects.special_project_charge_lifecycle import (
	programme_charges_for_service_type,
)
from logistics.utils.charge_service_type import (
	implied_service_type_for_doctype,
	operational_booking_charge_service_type_label,
	sales_quote_charge_service_types_equal,
)
from logistics.utils.internal_job_charge_copy import _scrub_main_row_to_child_dict


SOURCE_MICE_PROJECT_FIELD = "source_mice_project"
SOURCE_CONSOLIDATION_CHARGE_FIELD = "source_consolidation_charge"


def _charges_child_doctype(parent_doctype: str) -> str | None:
	df = frappe.get_meta(parent_doctype).get_field("charges")
	if df and df.fieldtype == "Table" and df.options:
		return (df.options or "").strip() or None
	return None


def _charge_type_label(charge: Any) -> str:
	return (getattr(charge, "charge_type", None) or "").strip()


def _rounded_shares(amount: float, factors: list[float]) -> list[float]:
	"""Split ``amount`` by ``factors`` while keeping the rounded total exact."""
	if not factors:
		return []
	raw = [flt(amount) * flt(factor) for factor in factors]
	rounded = [round(value, 2) for value in raw]
	diff = round(flt(amount) - sum(rounded), 2)
	if diff:
		for idx in range(len(rounded) - 1, -1, -1):
			if rounded[idx] or diff > 0:
				rounded[idx] = round(rounded[idx] + diff, 2)
				break
	return rounded


def _apply_consolidation_amount_adapter(row: dict[str, Any], source: Any) -> None:
	"""Map consolidation ``unit_rate`` / ``total_amount`` onto operational revenue/cost fields.

	Consolidation rows are cost-oriented and usually lack ``estimated_*``. Scrub already
	falls back ``total_amount`` → ``estimated_revenue``; this fills cost fields and
	clears unintended revenue for Cost-type lines.
	"""
	total = flt(getattr(source, "total_amount", 0))
	unit_rate = flt(getattr(source, "unit_rate", 0))
	ctype = _charge_type_label(source)

	if not flt(row.get("estimated_cost")) and total:
		row["estimated_cost"] = total
	if unit_rate and not flt(row.get("unit_cost")):
		row["unit_cost"] = unit_rate

	if ctype == "Cost":
		# Cost consolidation should not land as sell-side revenue from total_amount fallback.
		if total and flt(row.get("estimated_revenue")) == total:
			row["estimated_revenue"] = 0
	elif ctype in ("Revenue", "Margin") and not flt(row.get("estimated_revenue")) and total:
		row["estimated_revenue"] = total


def _apply_consolidation_unit_fields_adapter(row: dict[str, Any], source: Any) -> None:
	"""Map consolidation unit/currency fields onto operational charge cost or revenue side."""
	ctype = _charge_type_label(source)
	calc_method = getattr(source, "revenue_calculation_method", None)
	unit_type = getattr(source, "unit_type", None)
	uom = getattr(source, "unit_of_measure", None)
	currency = getattr(source, "currency", None)
	qty = flt(getattr(source, "quantity", 0)) or 1

	if ctype in ("Revenue", "Margin"):
		if calc_method:
			row["revenue_calculation_method"] = calc_method
		if unit_type:
			row["unit_type"] = unit_type
		if uom:
			row["uom"] = uom
		if currency:
			row["currency"] = currency
		row["quantity"] = qty
	else:
		if calc_method:
			row["cost_calculation_method"] = calc_method
		if unit_type:
			row["cost_unit_type"] = unit_type
		if uom:
			row["cost_uom"] = uom
		if currency:
			row["cost_currency"] = currency
		row["cost_quantity"] = qty


def _consolidation_charge_matches_row(
	charge: Any,
	lifecycle_row: Any | None,
	target_doctype: str,
) -> bool:
	row_st = (getattr(lifecycle_row, "service_type", None) or "").strip() if lifecycle_row else ""
	ch_st = getattr(charge, "service_type", None)
	if row_st:
		# Blank charge service_type is a wildcard (already in programme_charges_for_service_type).
		ch_norm = (ch_st or "").strip()
		if not ch_norm:
			return True
		return sales_quote_charge_service_types_equal(ch_st, row_st)
	want = implied_service_type_for_doctype(target_doctype)
	if not want:
		return True
	ch_norm = (ch_st or "").strip()
	if not ch_norm:
		return True
	return sales_quote_charge_service_types_equal(ch_st, want)


def _docket_allocation_rows(ep_doc: Any) -> list[Any]:
	return [
		row
		for row in (ep_doc.get("cost_allocations") or [])
		if (getattr(row, "target_type", None) or "").strip() == "Docket"
		and (getattr(row, "target", None) or "").strip()
	]


def ensure_mice_docket_cost_allocation(ep_doc: Any) -> list[Any]:
	"""Refresh and apply Docket allocations so PI charge copying uses current splits."""
	if not getattr(ep_doc, "name", None) or getattr(ep_doc, "__islocal", False):
		frappe.throw(_("Save the MICE Project before creating a Purchase Invoice."))
	ep_doc._refresh_cost_allocation_targets("Docket")
	ep_doc._validate_allocation_prerequisites()
	ep_doc._apply_allocation_to_targets()
	ep_doc._recalculate_consolidation_charge_totals()
	ep_doc._recalculate_cost_allocation_totals()
	rows = _docket_allocation_rows(ep_doc)
	if not rows:
		frappe.throw(
			_("No Dockets linked to this MICE Project. Create one first, then try again."),
			title=_("No Allocation Targets"),
		)
	ep_doc.save(ignore_permissions=True)
	return rows


def push_consolidation_charges_to_dockets(
	ep_doc: Any,
	*,
	selected_charges: list[Any] | None = None,
	purchase_invoice: str | None = None,
) -> int:
	"""Push selected consolidation charges onto Dockets using the current allocation split."""
	allocation_rows = ensure_mice_docket_cost_allocation(ep_doc)
	selected = list(selected_charges or [])
	if not selected:
		return 0

	child_dt = _charges_child_doctype("Docket")
	if not child_dt:
		return 0
	forced_label = operational_booking_charge_service_type_label(
		implied_service_type_for_doctype("Docket"),
		default="MICE",
	)
	selected_names = {
		(getattr(charge, "name", None) or "").strip()
		for charge in selected
		if (getattr(charge, "name", None) or "").strip()
	}
	rows_by_docket: dict[str, list[dict[str, Any]]] = defaultdict(list)

	for charge in selected:
		if _charge_type_label(charge) == "Disbursement":
			continue
		base_row = _scrub_main_row_to_child_dict(charge, child_dt, forced_label)
		if not base_row:
			continue
		_apply_consolidation_amount_adapter(base_row, charge)
		_apply_consolidation_unit_fields_adapter(base_row, charge)
		factors = ep_doc._per_target_allocation_factor(charge, allocation_rows, len(allocation_rows))
		if not factors:
			continue

		# Split consolidation Total Amount (not Unit Rate) across Dockets.
		total_amount = flt(getattr(charge, "total_amount", 0)) or flt(base_row.get("estimated_cost"))
		if total_amount <= 0:
			continue
		allocated_totals = _rounded_shares(total_amount, factors)
		ctype = _charge_type_label(charge)

		for idx, alloc_row in enumerate(allocation_rows):
			if idx >= len(allocated_totals):
				continue
			share = flt(allocated_totals[idx])
			if share <= 0:
				continue
			row = dict(base_row)
			row["charge_scope"] = "Main"
			# cost_quantity 1 + unit_cost = allocated total so Docket recalc keeps the share.
			row["cost_quantity"] = 1
			if ctype in ("Revenue", "Margin"):
				row["quantity"] = 1
			row["unit_rate"] = share
			row["unit_cost"] = share
			row["estimated_cost"] = share
			if ctype == "Cost":
				row["estimated_revenue"] = 0
			elif ctype in ("Revenue", "Margin"):
				row["estimated_revenue"] = share
			else:
				row["estimated_revenue"] = flt(base_row.get("estimated_revenue")) and share or 0
			row[SOURCE_MICE_PROJECT_FIELD] = ep_doc.name
			row[SOURCE_CONSOLIDATION_CHARGE_FIELD] = getattr(charge, "name", None)
			if purchase_invoice:
				row["purchase_invoice"] = purchase_invoice
				row["purchase_invoice_status"] = "Requested"
			rows_by_docket[(getattr(alloc_row, "target", None) or "").strip()].append(row)

	if not rows_by_docket:
		return 0

	for docket_name, new_rows in rows_by_docket.items():
		docket = frappe.get_doc("Docket", docket_name)
		kept_rows = []
		for row in docket.get("charges") or []:
			source_project = (getattr(row, SOURCE_MICE_PROJECT_FIELD, None) or "").strip()
			source_charge = (getattr(row, SOURCE_CONSOLIDATION_CHARGE_FIELD, None) or "").strip()
			if source_project == ep_doc.name and source_charge in selected_names:
				continue
			as_dict = getattr(row, "as_dict", None)
			kept_rows.append(as_dict() if callable(as_dict) else dict(row))
		docket.set("charges", kept_rows)
		for row in new_rows:
			docket.append("charges", row)
		docket.save(ignore_permissions=True)

	return sum(len(rows) for rows in rows_by_docket.values())


def build_operational_charge_dicts_from_mice_consolidation(
	ep_doc: Any,
	target_doctype: str,
	lifecycle_row: Any | None = None,
) -> list[dict[str, Any]]:
	"""Map matching consolidation charges into operational child-table row dicts."""
	child_dt = _charges_child_doctype(target_doctype)
	if not child_dt:
		return []

	row_st = (getattr(lifecycle_row, "service_type", None) or "").strip() if lifecycle_row else ""
	implied = implied_service_type_for_doctype(target_doctype)
	forced_label = operational_booking_charge_service_type_label(
		row_st or implied,
		default=row_st or implied or "Sea",
	)

	service_for_pool = row_st or implied
	source_charges = programme_charges_for_service_type(ep_doc, service_for_pool)

	dicts: list[dict[str, Any]] = []
	for ch in source_charges:
		if not _consolidation_charge_matches_row(ch, lifecycle_row, target_doctype):
			continue
		row = _scrub_main_row_to_child_dict(ch, child_dt, forced_label)
		if not row:
			continue
		_apply_consolidation_amount_adapter(row, ch)
		_apply_consolidation_unit_fields_adapter(row, ch)
		dicts.append(row)
	return dicts


def populate_operational_charges_from_mice_consolidation(
	ep_doc: Any,
	target_doc: Any,
	lifecycle_row: Any | None = None,
) -> int:
	"""Copy consolidation charges onto *target_doc*. Returns number of rows appended."""
	dicts = build_operational_charge_dicts_from_mice_consolidation(
		ep_doc, target_doc.doctype, lifecycle_row
	)
	if not dicts:
		return 0
	target_doc.set("charges", [])
	for row in dicts:
		target_doc.append("charges", row)
	return len(dicts)


def consolidation_charges_preview_rows(
	ep_doc: Any,
	job_type: str,
	lifecycle_row: Any | None = None,
	params: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
	"""Preview rows for the booking dialog (consolidation source)."""
	dicts = build_operational_charge_dicts_from_mice_consolidation(
		ep_doc, job_type, lifecycle_row
	)
	out: list[dict[str, Any]] = []
	for d in dicts:
		out.append(
			{
				"service_type": d.get("service_type"),
				"item_code": d.get("item_code"),
				"item_name": d.get("item_name"),
				"unit_rate": flt(d.get("unit_rate")) or None,
				"currency": d.get("currency"),
				"estimated_revenue": flt(d.get("estimated_revenue")) or None,
				"estimated_cost": flt(d.get("estimated_cost")) or None,
				"parameters": params or {},
			}
		)
	return out
