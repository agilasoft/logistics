# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Charge-to-lifecycle tagging and cost helpers for Special Project."""

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


def _norm(value: Any) -> str:
	return (value or "").strip()


def _lifecycle_job_lines_by_name(doc: Any) -> dict[str, Any]:
	out: dict[str, Any] = {}
	for row in doc.get("lifecycle_jobs") or []:
		name = _norm(getattr(row, "name", None))
		if name:
			out[name] = row
	return out


def _charge_lifecycle_line(charge: Any) -> str:
	return _norm(getattr(charge, "lifecycle_job_line", None))


def charge_has_lifecycle_tag(sp_doc: Any, charge: Any) -> bool:
	return bool(_charge_lifecycle_line(charge))


charge_has_lifecycle_allocations = charge_has_lifecycle_tag
charge_has_lifecycle_tags = charge_has_lifecycle_tag


def available_charges(sp_doc: Any, service_type: str | None = None) -> list[Any]:
	out: list[Any] = []
	st = _norm(service_type)
	for charge in sp_doc.get("charges") or []:
		if _charge_lifecycle_line(charge):
			continue
		if st and not sales_quote_charge_service_types_equal(
			getattr(charge, "service_type", None), st
		):
			continue
		out.append(charge)
	return out


def programme_charges_for_service_type(
	sp_doc: Any, service_type: str | None = None
) -> list[Any]:
	"""Programme charge rows matching a lifecycle service type (budget lines, not tagged)."""
	out: list[Any] = []
	st = _norm(service_type)
	for charge in sp_doc.get("charges") or []:
		if _is_disbursement_charge(charge):
			continue
		if st and not sales_quote_charge_service_types_equal(
			getattr(charge, "service_type", None), st
		):
			continue
		out.append(charge)
	return out


def _lifecycle_job_row_by_name(sp_doc: Any, row_name: str) -> Any | None:
	row_name = _norm(row_name)
	if not row_name:
		return None
	for row in sp_doc.get("lifecycle_jobs") or []:
		if _norm(getattr(row, "name", None)) == row_name:
			return row
	return None


def execution_rows_for_planning(sp_doc: Any, planning_name: str) -> list[Any]:
	planning_name = _norm(planning_name)
	if not planning_name:
		return []
	return [
		row
		for row in sp_doc.get("lifecycle_jobs") or []
		if _norm(getattr(row, "lifecycle_job_line", None)) == planning_name
	]


_PLANNING_ORDER_TYPES = frozenset(
	{
		"Air Booking",
		"Sea Booking",
		"Transport Order",
		"Declaration Order",
		"Inbound Order",
		"Project Order",
	}
)

_LIFECYCLE_EXECUTION_JOB_TYPES = frozenset(
	{
		"Air Shipment",
		"Sea Shipment",
		"Transport Job",
		"Declaration",
		"Warehouse Job",
		"Project Job",
	}
)

LIFECYCLE_JOB_TYPE_OPTIONS = _PLANNING_ORDER_TYPES


def sync_lifecycle_job_execution_no(row: Any) -> None:
	"""Ensure ``job_no`` stores the shipment/job name, not the booking/order number."""
	if is_execution_lifecycle_row(row):
		return
	jt = _norm(getattr(row, "job_type", None))
	on = _norm(getattr(row, "order_no", None))
	if not jt or jt not in _PLANNING_ORDER_TYPES or not on:
		return
	from logistics.utils.special_project_internal_jobs import (
		_resolve_execution_name_to_operational_ref,
		_resolve_order_ref_to_operational_ref,
	)

	jn = _norm(getattr(row, "job_no", None))
	if jn:
		exec_ref = _resolve_execution_name_to_operational_ref(jn)
		if exec_ref and jn != on:
			return
		if jn == on or (jn and frappe.db.exists(jt, jn)):
			row.job_no = None
			jn = ""
	ref = _resolve_order_ref_to_operational_ref(jt, on)
	if ref:
		row.job_no = ref[1]
	elif not jn:
		row.job_no = None


def sync_lifecycle_job_execution_refs(doc: Any) -> None:
	for row in doc.get("lifecycle_jobs") or []:
		sync_lifecycle_job_execution_no(row)


def normalize_lifecycle_job_order_job_fields(doc: Any) -> None:
	"""Normalize lifecycle job link fields before Select validation.

	``job_type`` / ``order_no`` hold the booking or order. ``job_no`` holds the
	submitted shipment or job name. Legacy rows may still use ``order_type`` or
	store execution doctype labels on ``job_type``.
	"""
	for row in doc.get("lifecycle_jobs") or []:
		if is_execution_lifecycle_row(row):
			jt = _norm(getattr(row, "job_type", None))
			if jt in _LIFECYCLE_EXECUTION_JOB_TYPES:
				row.job_type = None
			row.job_no = None
			continue
		ot = _norm(getattr(row, "order_type", None))
		on = _norm(getattr(row, "order_no", None))
		jt = _norm(getattr(row, "job_type", None))
		jn = _norm(getattr(row, "job_no", None))
		if ot and on and not jt:
			row.job_type = ot
		if hasattr(row, "order_type"):
			row.order_type = None
		if jt in _LIFECYCLE_EXECUTION_JOB_TYPES:
			if jn:
				row.job_no = jn
			row.job_type = None
		elif jt in _PLANNING_ORDER_TYPES and jn and not on:
			row.order_no = jn
			row.job_no = None
		elif jt and jt not in LIFECYCLE_JOB_TYPE_OPTIONS:
			row.job_type = None
		sync_lifecycle_job_execution_no(row)


def lifecycle_row_order_link_is_cancelled(row: Any) -> bool:
	"""True when the lifecycle row's planning order_no points at a cancelled document."""
	jt = _norm(getattr(row, "job_type", None))
	on = _norm(getattr(row, "order_no", None))
	if not jt or not on:
		return False
	from logistics.utils.internal_job_from_source import linked_internal_job_target_is_cancelled

	if linked_internal_job_target_is_cancelled(jt, on):
		return True
	if jt == "Project Order" and frappe.db.exists("Project Order", on):
		return (frappe.db.get_value("Project Order", on, "docstatus") or 0) == 2
	return False


def planning_row_is_open(sp_doc: Any, row: Any) -> bool:
	name = _norm(getattr(row, "name", None))
	if not name:
		return False
	# Prefer saved row: desk payload may omit job_no after Create > Booking/Order.
	check = _lifecycle_job_row_by_name(sp_doc, name) or row
	if _norm(getattr(check, "lifecycle_job_line", None)):
		return False
	order_cancelled = lifecycle_row_order_link_is_cancelled(check)
	jt = _norm(getattr(check, "job_type", None))
	on = _norm(getattr(check, "order_no", None))
	if jt in _PLANNING_ORDER_TYPES and on and not order_cancelled:
		return False
	if not order_cancelled:
		jn = _norm(getattr(check, "job_no", None))
		if jn and jn != on:
			from logistics.utils.special_project_internal_jobs import (
				_resolve_execution_name_to_operational_ref,
			)

			if _resolve_execution_name_to_operational_ref(jn):
				return False
		from logistics.utils.special_project_internal_jobs import (
			resolve_lifecycle_job_row_to_operational_ref,
		)

		if resolve_lifecycle_job_row_to_operational_ref(check):
			return False
	return not execution_rows_for_planning(sp_doc, name)


@frappe.whitelist()
def get_cancelled_lifecycle_order_links(lifecycle_jobs: Any = None) -> dict[str, str]:
	"""Map lifecycle row name -> order_no for rows whose planning order link is cancelled."""
	rows = (
		frappe.parse_json(lifecycle_jobs)
		if isinstance(lifecycle_jobs, str)
		else (lifecycle_jobs or [])
	)
	out: dict[str, str] = {}
	for row in rows:
		name = _norm(row.get("name") if isinstance(row, dict) else getattr(row, "name", None))
		if not name:
			continue
		check = row if isinstance(row, dict) else row
		if lifecycle_row_order_link_is_cancelled(check):
			out[name] = _norm(
				row.get("order_no") if isinstance(row, dict) else getattr(row, "order_no", None)
			)
	return out


def is_planning_lifecycle_row(row: Any) -> bool:
	return not _norm(getattr(row, "lifecycle_job_line", None))


def is_execution_lifecycle_row(row: Any) -> bool:
	return bool(_norm(getattr(row, "lifecycle_job_line", None)))


def append_charge_lifecycle_tag_for_test(
	sp_doc: Any,
	charge_row: int,
	lifecycle_job_line: str,
	**fields: Any,
) -> Any:
	"""Set lifecycle_job_line on a charge row (tests and scripts)."""
	if not sp_doc.name:
		sp_doc.insert(ignore_permissions=True)
	charge = None
	for ch in sp_doc.get("charges") or []:
		if cint(getattr(ch, "idx", 0) or 0) == cint(charge_row):
			charge = ch
			break
	if not charge:
		frappe.throw(_("Charge row {0} not found.").format(charge_row))
	charge.lifecycle_job_line = lifecycle_job_line
	for key, value in fields.items():
		setattr(charge, key, value)
	return charge


append_charge_lifecycle_allocation_for_test = append_charge_lifecycle_tag_for_test


def charge_applies_to_lifecycle_row(sp_doc: Any, charge: Any, lifecycle_row: Any) -> bool:
	if _is_disbursement_charge(charge):
		return False
	line_name = _norm(getattr(lifecycle_row, "name", None))
	if not line_name:
		return False
	return _charge_lifecycle_line(charge) == line_name


def _charge_tagged_to_other_lifecycle_row(charge: Any, lifecycle_row: Any) -> bool:
	line_name = _norm(getattr(lifecycle_row, "name", None))
	tag = _charge_lifecycle_line(charge)
	return bool(tag and tag != line_name)


def programme_charges_for_lifecycle_row(sp_doc: Any, lifecycle_row: Any) -> list[Any]:
	"""Programme charges whose planned amounts roll up onto one lifecycle row.

	Precedence:
	1. Explicit ``lifecycle_job_line`` tag on the charge matching this row.
	2. Parameter match between row and charge (same rules as Create booking/order).
	3. Single planning row for the service type with no row parameters (implicit).
	"""
	st = _norm(getattr(lifecycle_row, "service_type", None))
	if not st:
		return []

	line_name = _norm(getattr(lifecycle_row, "name", None))
	matched: list[Any] = []
	seen_idxs: set[int] = set()

	for charge in sp_doc.get("charges") or []:
		if _is_disbursement_charge(charge):
			continue
		if not charge_applies_to_lifecycle_row(sp_doc, charge, lifecycle_row):
			continue
		idx = cint(getattr(charge, "idx", 0) or 0)
		if idx and idx in seen_idxs:
			continue
		matched.append(charge)
		if idx:
			seen_idxs.add(idx)

	if is_execution_lifecycle_row(lifecycle_row):
		return matched

	from logistics.utils.sales_quote_charge_parameters import (
		_effective_programme_charge_row,
		extract_service_scoped_quote_parameters,
		programme_charge_matches_creation_parameters,
	)

	row_params = extract_service_scoped_quote_parameters(lifecycle_row, st)

	if row_params:
		for charge in programme_charges_for_service_type(sp_doc, st):
			if _charge_tagged_to_other_lifecycle_row(charge, lifecycle_row):
				continue
			idx = cint(getattr(charge, "idx", 0) or 0)
			if idx and idx in seen_idxs:
				continue
			if programme_charge_matches_creation_parameters(
				_effective_programme_charge_row(charge, st), row_params
			):
				matched.append(charge)
				if idx:
					seen_idxs.add(idx)
		return matched

	planning_rows = _planning_lifecycle_rows_for_service(sp_doc, st)
	if (
		is_planning_lifecycle_row(lifecycle_row)
		and len(planning_rows) == 1
		and _norm(getattr(planning_rows[0], "name", None)) == line_name
	):
		for charge in programme_charges_for_service_type(sp_doc, st):
			if _charge_lifecycle_line(charge):
				continue
			idx = cint(getattr(charge, "idx", 0) or 0)
			if idx and idx in seen_idxs:
				continue
			matched.append(charge)
			if idx:
				seen_idxs.add(idx)

	return matched


def _planning_lifecycle_rows_for_service(sp_doc: Any, service_type: str | None) -> list[Any]:
	st = _norm(service_type)
	if not st:
		return []
	rows = [
		row
		for row in sp_doc.get("lifecycle_jobs") or []
		if is_planning_lifecycle_row(row)
		and sales_quote_charge_service_types_equal(getattr(row, "service_type", None), st)
	]
	return sorted(rows, key=lambda row: cint(getattr(row, "idx", 0) or 0))


def _untagged_programme_charges_for_item(
	sp_doc: Any, service_type: str | None, item_code: str
) -> list[Any]:
	st = _norm(service_type)
	item_code = _norm(item_code)
	if not st or not item_code:
		return []
	rows = [
		ch
		for ch in sp_doc.get("charges") or []
		if not _is_disbursement_charge(ch)
		and not _charge_lifecycle_line(ch)
		and sales_quote_charge_service_types_equal(getattr(ch, "service_type", None), st)
		and _norm(getattr(ch, "item_code", None)) == item_code
	]
	return sorted(rows, key=lambda ch: cint(getattr(ch, "idx", 0) or 0))


def programme_charge_applies_to_planning_lifecycle(
	sp_doc: Any, charge: Any, lifecycle_row: Any
) -> bool:
	"""Whether a programme charge should post when this planning lifecycle leg executes."""
	if _is_disbursement_charge(charge):
		return False
	if charge_applies_to_lifecycle_row(sp_doc, charge, lifecycle_row):
		return True
	if _charge_lifecycle_line(charge):
		return False
	if not is_planning_lifecycle_row(lifecycle_row):
		return False

	st = _norm(getattr(lifecycle_row, "service_type", None))
	if st and not sales_quote_charge_service_types_equal(
		getattr(charge, "service_type", None), st
	):
		return False

	item_code = _norm(getattr(charge, "item_code", None))
	if not item_code:
		return False

	same_item = _untagged_programme_charges_for_item(sp_doc, st, item_code)
	if not same_item:
		return False

	planning_rows = _planning_lifecycle_rows_for_service(sp_doc, st)
	lifecycle_name = _norm(getattr(lifecycle_row, "name", None))
	leg_pos = next(
		(
			idx
			for idx, row in enumerate(planning_rows)
			if _norm(getattr(row, "name", None)) == lifecycle_name
		),
		None,
	)
	if leg_pos is None:
		return False

	if len(same_item) == 1:
		return cint(getattr(charge, "idx", 0) or 0) == cint(
			getattr(same_item[0], "idx", 0) or 0
		)

	if leg_pos >= len(same_item):
		return False

	return cint(getattr(charge, "idx", 0) or 0) == cint(
		getattr(same_item[leg_pos], "idx", 0) or 0
	)


def charge_applies_to_lifecycle_idx(
	sp_doc: Any,
	charge: Any,
	lifecycle_jobs_idx: int,
) -> tuple[bool, float]:
	for row in sp_doc.get("lifecycle_jobs") or []:
		if cint(getattr(row, "idx", 0) or 0) != cint(lifecycle_jobs_idx):
			continue
		if charge_applies_to_lifecycle_row(sp_doc, charge, row):
			return True, 100.0
	return False, 0.0


def charge_planned_cost_for_lifecycle(
	sp_doc: Any,
	charge: Any,
	lifecycle_jobs_idx: int,
) -> float:
	for row in sp_doc.get("lifecycle_jobs") or []:
		if cint(getattr(row, "idx", 0) or 0) != cint(lifecycle_jobs_idx):
			continue
		if charge_applies_to_lifecycle_row(sp_doc, charge, row):
			return flt(_charge_planned_cost(charge))
	return 0.0


def charge_planned_revenue_for_lifecycle(
	sp_doc: Any,
	charge: Any,
	lifecycle_jobs_idx: int,
) -> float:
	for row in sp_doc.get("lifecycle_jobs") or []:
		if cint(getattr(row, "idx", 0) or 0) != cint(lifecycle_jobs_idx):
			continue
		if charge_applies_to_lifecycle_row(sp_doc, charge, row):
			return flt(_charge_planned_revenue(charge))
	return 0.0


def primary_lifecycle_idx_for_charge(sp_doc: Any, charge: Any) -> int | None:
	line_name = _charge_lifecycle_line(charge)
	if not line_name:
		return None
	for row in sp_doc.get("lifecycle_jobs") or []:
		if _norm(getattr(row, "name", None)) == line_name:
			return cint(getattr(row, "idx", 0) or 0) or None
	return None


def find_lifecycle_row_for_charge(sp_doc: Any, charge: Any) -> Any | None:
	line_name = _charge_lifecycle_line(charge)
	if not line_name:
		return None
	return _lifecycle_job_lines_by_name(sp_doc).get(line_name)


def charge_allocation_factor_for_lifecycle_row(
	sp_doc: Any,
	charge: Any,
	lifecycle_row: Any,
) -> float:
	if charge_applies_to_lifecycle_row(sp_doc, charge, lifecycle_row):
		return 1.0
	if charge_has_lifecycle_tag(sp_doc, charge):
		return 0.0
	return 0.0


def recompute_all_charge_tag_allocations(doc: Any) -> None:
	"""No-op: 1:1 charge tags do not require allocation recompute."""
	return


def validate_charge_lifecycle_tags(doc: Any) -> None:
	lines_by_name = _lifecycle_job_lines_by_name(doc)
	planning_rows = [
		row
		for row in doc.get("lifecycle_jobs") or []
		if is_planning_lifecycle_row(row)
	]

	for charge in doc.get("charges") or []:
		if _is_disbursement_charge(charge):
			continue
		line_name = _charge_lifecycle_line(charge)
		if not line_name:
			continue
		ch_idx = cint(getattr(charge, "idx", 0) or 0) or "?"
		if line_name not in lines_by_name:
			frappe.throw(
				_("Charge row {0}: Lifecycle Job line {1} is not on this document.").format(
					ch_idx, line_name
				),
				title=_("Charge lifecycle tag"),
			)
		lj = lines_by_name[line_name]
		ch_st = getattr(charge, "service_type", None)
		lj_st = getattr(lj, "service_type", None)
		if ch_st and lj_st and not sales_quote_charge_service_types_equal(ch_st, lj_st):
			frappe.throw(
				_(
					"Charge row {0}: Service Type {1} does not match Lifecycle Job line ({2})."
				).format(ch_idx, _norm(ch_st), _norm(lj_st)),
				title=_("Service Type mismatch"),
			)

	# Programme charges are budget lines by service type; execution logs attribute usage.


validate_charge_lifecycle_allocations = validate_charge_lifecycle_tags


def validate_lifecycle_job_line_not_referenced(doc: Any, removed_line_names: set[str]) -> None:
	if not removed_line_names:
		return
	for charge in doc.get("charges") or []:
		line_name = _charge_lifecycle_line(charge)
		if line_name in removed_line_names:
			frappe.throw(
				_(
					"Cannot remove Lifecycle Job line {0}: charge row {1} still references it."
				).format(line_name, cint(getattr(charge, "idx", 0) or 0) or "?"),
				title=_("Charge lifecycle tag"),
			)
	for row in doc.get("lifecycle_jobs") or []:
		source = _norm(getattr(row, "lifecycle_job_line", None))
		if source in removed_line_names:
			frappe.throw(
				_(
					"Cannot remove Lifecycle Job line {0}: execution rows still reference it."
				).format(source),
				title=_("Charge lifecycle tag"),
			)


def tag_available_charges_for_execution(
	sp_doc: Any,
	execution_row: Any,
	service_type: str | None = None,
) -> list[Any]:
	"""Tag untagged charges matching service type to an execution lifecycle row."""
	exec_name = _norm(getattr(execution_row, "name", None))
	if not exec_name:
		return []
	st = _norm(service_type) or _norm(getattr(execution_row, "service_type", None))
	tagged: list[Any] = []
	for charge in available_charges(sp_doc, st):
		charge.lifecycle_job_line = exec_name
		tagged.append(charge)
	return tagged
