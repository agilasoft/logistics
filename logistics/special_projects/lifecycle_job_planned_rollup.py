# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Roll up planned cost/revenue from programme charges onto Lifecycle Job rows."""

from __future__ import annotations

from typing import Any

from logistics.special_projects.special_project_charge_lifecycle import (
	is_planning_lifecycle_row,
	programme_charges_for_lifecycle_row,
)
from logistics.utils.internal_job_main_rollup import (
	_charge_planned_cost,
	_charge_planned_revenue,
)


def _lifecycle_rows(doc: Any) -> list[Any]:
	return list(doc.get("lifecycle_jobs") or [])


def _charges(doc: Any) -> list[Any]:
	return list(doc.get("charges") or [])


def _planning_lifecycle_rows(candidates: list[Any]) -> list[Any]:
	return [row for row in candidates if is_planning_lifecycle_row(row)]


def _lifecycle_rows_need_programme_charge_attribution(lifecycle_rows: list[Any]) -> bool:
	return any(is_planning_lifecycle_row(row) for row in lifecycle_rows)


def _auto_assign_charge_lifecycle_rows(doc: Any) -> None:
	return


def _validate_charge_lifecycle_links(doc: Any) -> None:
	from logistics.special_projects.special_project_charge_lifecycle import (
		validate_charge_lifecycle_tags,
	)

	validate_charge_lifecycle_tags(doc)


def _planned_totals_for_lifecycle_row(
	doc: Any,
	lifecycle_row: Any,
	lifecycle_rows: list[Any],
	charges: list[Any],
) -> tuple[float, float]:
	planned_cost = 0.0
	planned_revenue = 0.0
	for charge in programme_charges_for_lifecycle_row(doc, lifecycle_row):
		planned_cost += _charge_planned_cost(charge)
		planned_revenue += _charge_planned_revenue(charge)
	return planned_cost, planned_revenue


def sync_lifecycle_job_planned_from_charges(doc: Any) -> None:
	from logistics.special_projects.lifecycle_job_financial_rollup import (
		sync_lifecycle_job_financials,
	)

	sync_lifecycle_job_financials(doc)
