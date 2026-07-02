# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Special Project Service helpers for Special Project (parameters and operational links)."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _
from frappe.utils import cint

from logistics.special_projects.special_project_service_constants import PLANNING_ORDER_TYPES
from logistics.special_projects.special_project_service_rows import (
	applicable_lifecycle_stages,
	is_execution_special_project_service_row,
	is_planning_special_project_service_row,
	service_rows,
)
from logistics.special_projects.special_project_service_compat import (
	row_special_project_service_link,
)
from logistics.special_projects.special_project_charge_lifecycle import (
	lifecycle_row_order_link_is_cancelled,
)
from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal


def _norm(value: Any) -> str:
	return (value or "").strip()


def _service_row_name(row: Any) -> str:
	return _norm(row_special_project_service_link(row) or getattr(row, "name", None))


def _special_project_services_by_name(doc: Any) -> dict[str, Any]:
	out: dict[str, Any] = {}
	for row in service_rows(doc):
		name = _service_row_name(row)
		if name:
			out[name] = row
	return out


def special_project_service_by_name(sp_doc: Any, row_name: str) -> Any | None:
	return _special_project_services_by_name(sp_doc).get(_norm(row_name))


def execution_services_for_planning(sp_doc: Any, planning_name: str) -> list[Any]:
	planning_name = _norm(planning_name)
	if not planning_name:
		return []
	return [
		row
		for row in service_rows(sp_doc)
		if _norm(getattr(row, "special_project_service_line", None)) == planning_name
	]


def planning_services_for_lifecycle_stage(sp_doc: Any, lifecycle_stage: str) -> list[Any]:
	lifecycle_stage = _norm(lifecycle_stage)
	if not lifecycle_stage:
		return []
	return [
		row
		for row in service_rows(sp_doc)
		if is_planning_special_project_service_row(row)
		and _norm(getattr(row, "lifecycle_stage", None)) == lifecycle_stage
	]


# Legacy alias.
planning_services_for_lifecycle = planning_services_for_lifecycle_stage


def planning_services_for_service_type(sp_doc: Any, service_type: str | None) -> list[Any]:
	st = _norm(service_type)
	return [
		row
		for row in service_rows(sp_doc)
		if is_planning_special_project_service_row(row)
		and (not st or sales_quote_charge_service_types_equal(getattr(row, "service_type", None), st))
	]


def _charge_service_line(charge: Any) -> str:
	return _norm(getattr(charge, "special_project_service_line", None))


def charge_has_service_tag(sp_doc: Any, charge: Any) -> bool:
	return bool(_charge_service_line(charge))


def charge_applies_to_service_row(sp_doc: Any, charge: Any, service_row: Any) -> bool:
	line_name = _norm(getattr(service_row, "name", None))
	if not line_name:
		return False
	return _charge_service_line(charge) == line_name


def planning_service_is_open(sp_doc: Any, row: Any) -> bool:
	name = _norm(getattr(row, "name", None))
	if not name:
		return False
	check = special_project_service_by_name(sp_doc, name) or row
	if not is_planning_special_project_service_row(check):
		return False
	order_cancelled = lifecycle_row_order_link_is_cancelled(check)
	jt = _norm(getattr(check, "job_type", None))
	on = _norm(getattr(check, "order_no", None))
	if jt in PLANNING_ORDER_TYPES and on and not order_cancelled:
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
	return not execution_services_for_planning(sp_doc, name)


def sync_charge_tags_from_service_line(charge: Any, sp_doc: Any) -> None:
	"""When a charge links to a service, inherit lifecycle stage from that service."""
	line_name = _charge_service_line(charge)
	if not line_name:
		return
	service = special_project_service_by_name(sp_doc, line_name)
	if not service:
		return
	stage = _norm(getattr(service, "lifecycle_stage", None))
	if stage and not _norm(getattr(charge, "lifecycle_stage", None)):
		charge.lifecycle_stage = stage


def validate_charge_service_tags(doc: Any) -> None:
	services_by_name = _special_project_services_by_name(doc)
	allowed_stages = set(applicable_lifecycle_stages(doc))

	for charge in doc.get("charges") or []:
		line_name = _charge_service_line(charge)
		if not line_name:
			continue
		ch_idx = cint(getattr(charge, "idx", 0) or 0) or "?"
		if line_name not in services_by_name:
			frappe.throw(
				_("Charge row {0}: Service line {1} is not on this document.").format(
					ch_idx, line_name
				),
				title=_("Charge service tag"),
			)
		service = services_by_name[line_name]
		ch_st = getattr(charge, "service_type", None)
		svc_st = getattr(service, "service_type", None)
		if ch_st and svc_st and not sales_quote_charge_service_types_equal(ch_st, svc_st):
			frappe.throw(
				_("Charge row {0}: Service Type {1} does not match Service line ({2}).").format(
					ch_idx, _norm(ch_st), _norm(svc_st)
				),
				title=_("Service Type mismatch"),
			)
		charge_stage = _norm(getattr(charge, "lifecycle_stage", None))
		svc_stage = _norm(getattr(service, "lifecycle_stage", None))
		if charge_stage and svc_stage and charge_stage != svc_stage:
			frappe.throw(
				_(
					"Charge row {0}: Lifecycle stage does not match the selected Service line."
				).format(ch_idx),
				title=_("Lifecycle / Service mismatch"),
			)
		if svc_stage and allowed_stages and svc_stage not in allowed_stages:
			frappe.throw(
				_("Charge row {0}: Service line references Lifecycle Stage {1} not on this project.").format(
					ch_idx, svc_stage
				),
				title=_("Charge service tag"),
			)


def validate_special_project_service_line_not_referenced(doc: Any, removed_line_names: set[str]) -> None:
	if not removed_line_names:
		return
	for charge in doc.get("charges") or []:
		line_name = _charge_service_line(charge)
		if line_name in removed_line_names:
			frappe.throw(
				_("Cannot remove Service line {0}: charge row {1} still references it.").format(
					line_name, cint(getattr(charge, "idx", 0) or 0) or "?"
				),
				title=_("Charge service tag"),
			)
	for row in service_rows(doc):
		source = _norm(getattr(row, "special_project_service_line", None))
		if source in removed_line_names:
			frappe.throw(
				_("Cannot remove Service line {0}: execution rows still reference it.").format(
					source
				),
				title=_("Charge service tag"),
			)


def validate_lifecycle_job_line_not_referenced_by_services(
	doc: Any, removed_line_names: set[str]
) -> None:
	"""Legacy hook — lifecycle job rows removed; no-op."""
	return


def validate_special_project_service_lifecycle_stages(doc: Any) -> None:
	"""Ensure header and service rows use lifecycle stages selected on the project."""
	allowed = set(applicable_lifecycle_stages(doc))
	if not allowed:
		return
	stage = _norm(getattr(doc, "lifecycle_stage", None))
	if stage and stage not in allowed:
		frappe.throw(
			_("Lifecycle Stage {0} is not in Applicable Lifecycle Stages.").format(stage),
			title=_("Lifecycle stage"),
		)
	for row in service_rows(doc):
		stage = _norm(getattr(row, "lifecycle_stage", None))
		if not stage:
			continue
		if stage not in allowed:
			frappe.throw(
				_(
					"Service row {0}: Lifecycle Stage {1} is not in Applicable Lifecycle Stages."
				).format(cint(getattr(row, "idx", 0) or 0) or "?", stage),
				title=_("Lifecycle stage"),
			)


def normalize_special_project_service_order_job_fields(doc: Any) -> None:
	"""Normalize programme service link fields before Select validation."""
	from logistics.special_projects.special_project_service_constants import (
		LIFECYCLE_EXECUTION_JOB_TYPES,
		LIFECYCLE_JOB_TYPE_OPTIONS,
	)
	from logistics.special_projects.special_project_charge_lifecycle import (
		sync_lifecycle_job_execution_no,
	)

	for row in service_rows(doc):
		if is_execution_special_project_service_row(row):
			jt = _norm(getattr(row, "job_type", None))
			if jt in LIFECYCLE_EXECUTION_JOB_TYPES:
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
		if jt in LIFECYCLE_EXECUTION_JOB_TYPES:
			if jn:
				row.job_no = jn
			row.job_type = None
		elif jt in PLANNING_ORDER_TYPES and jn and not on:
			row.order_no = jn
			row.job_no = None
		elif jt and jt not in LIFECYCLE_JOB_TYPE_OPTIONS:
			row.job_type = None
		sync_lifecycle_job_execution_no(row)
