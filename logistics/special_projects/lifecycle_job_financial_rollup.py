# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Roll up lifecycle job planned/actual financials from linked operational jobs or programme charges."""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import cint, flt

from logistics.special_projects.lifecycle_job_planned_rollup import (
	_auto_assign_charge_lifecycle_rows,
	_charges,
	_lifecycle_rows,
	_planned_totals_for_lifecycle_row,
	_validate_charge_lifecycle_links,
)
from logistics.utils.charge_service_type import effective_internal_job_detail_job_type
from logistics.utils.internal_job_main_rollup import (
	_charge_planned_cost,
	_charge_planned_revenue,
	_is_disbursement_charge,
	calculate_internal_job_rollup_totals,
	charge_child_tracks_actual_amounts,
)
from logistics.utils.special_project_internal_jobs import (
	resolve_lifecycle_job_row_to_operational_ref,
)

# Doctypes that may be flagged ``is_internal_job`` and linked to a main via main_job / main_job_type.
_INTERNAL_JOB_CAPABLE_DOCTYPES: tuple[str, ...] = (
	"Air Booking",
	"Sea Booking",
	"Air Shipment",
	"Sea Shipment",
	"Transport Order",
	"Transport Job",
	"Declaration",
	"Declaration Order",
	"Warehouse Job",
	"Inbound Order",
	"Release Order",
	"Project Job",
	"Project Order",
)


def _doctype_has_charges_table(doctype: str) -> bool:
	meta = frappe.get_meta(doctype)
	df = meta.get_field("charges")
	return bool(df and df.fieldtype == "Table" and df.options)


def _lifecycle_row_job_type(lifecycle_row: Any) -> str:
	return effective_internal_job_detail_job_type(lifecycle_row)


def _active_job_doc(job_type: str, job_no: str) -> Any | None:
	jt = (job_type or "").strip()
	jn = (job_no or "").strip()
	if not jt or not jn or not frappe.db.exists(jt, jn):
		return None
	if not _doctype_has_charges_table(jt):
		return None
	if cint(frappe.db.get_value(jt, jn, "docstatus") or 0) == 2:
		return None
	try:
		return frappe.get_doc(jt, jn)
	except Exception:
		return None


def _doc_has_charge_lines(doc: Any) -> bool:
	return bool(getattr(doc, "charges", None))


def _primary_charge_doc_for_lifecycle_link(
	link_job_type: str,
	link_job_no: str,
	lifecycle_row: Any | None = None,
) -> Any | None:
	"""Pick the document whose ``charges`` drive lifecycle financials for this lifecycle link.

	When an execution child exists (e.g. Transport Job for Transport Order), prefer it so
	``actual_cost`` on charge rows is used. Fall back to the lifecycle ``job_no`` document when
	the child has no charge lines yet.
	"""
	link_doc = _active_job_doc(link_job_type, link_job_no)
	row = lifecycle_row if lifecycle_row is not None else frappe._dict(
		job_type=link_job_type,
		job_no=link_job_no,
	)
	execution_ref = resolve_lifecycle_job_row_to_operational_ref(row)
	if execution_ref:
		exec_doc = _active_job_doc(execution_ref[0], execution_ref[1])
		if exec_doc and _doc_has_charge_lines(exec_doc):
			return exec_doc
	return link_doc


def calculate_lifecycle_job_charge_totals(doc: Any) -> tuple[float, float, float, float]:
	"""Sum charge totals for lifecycle roll-up.

	Uses ``calculate_internal_job_rollup_totals`` when the charge child table tracks actual
	amounts. Otherwise treats estimated/planned charge amounts as actual (same basis as client
	charge calculation before separate actual inputs exist), so order-level docs without
	``actual_cost`` still contribute.
	"""
	if charge_child_tracks_actual_amounts(doc.doctype):
		return calculate_internal_job_rollup_totals(doc)

	planned_cost = 0.0
	planned_revenue = 0.0
	actual_cost = 0.0
	actual_revenue = 0.0
	for row in getattr(doc, "charges", None) or []:
		if _is_disbursement_charge(row):
			continue
		pc = _charge_planned_cost(row)
		pr = _charge_planned_revenue(row)
		planned_cost += pc
		planned_revenue += pr
		actual_cost += pc
		actual_revenue += pr
	return planned_cost, planned_revenue, actual_cost, actual_revenue


def _iter_internal_satellite_docs(main_job_type: str, main_job_no: str) -> list[Any]:
	docs: list[Any] = []
	main_job_type = (main_job_type or "").strip()
	main_job_no = (main_job_no or "").strip()
	if not main_job_type or not main_job_no:
		return docs

	for dt in _INTERNAL_JOB_CAPABLE_DOCTYPES:
		if dt == main_job_type:
			continue
		meta = frappe.get_meta(dt)
		if not meta.get_field("is_internal_job") or not meta.get_field("main_job"):
			continue
		if not _doctype_has_charges_table(dt):
			continue
		for name in frappe.get_all(
			dt,
			filters={
				"is_internal_job": 1,
				"main_job_type": main_job_type,
				"main_job": main_job_no,
				"docstatus": ("!=", 2),
			},
			pluck="name",
		):
			doc = _active_job_doc(dt, name)
			if doc:
				docs.append(doc)
	return docs


def calculate_linked_job_stack_totals(
	job_type: str,
	job_no: str,
	lifecycle_row: Any | None = None,
) -> tuple[float, float, float, float]:
	"""Sum planned/actual from the lifecycle link and internal jobs linked to it."""
	link_job_type = (job_type or "").strip()
	link_job_no = (job_no or "").strip()
	main_doc = _primary_charge_doc_for_lifecycle_link(link_job_type, link_job_no, lifecycle_row)
	if not main_doc:
		return 0.0, 0.0, 0.0, 0.0

	planned_cost = 0.0
	planned_revenue = 0.0
	actual_cost = 0.0
	actual_revenue = 0.0

	for doc in [main_doc, *_iter_internal_satellite_docs(link_job_type, link_job_no)]:
		pc, pr, ac, ar = calculate_lifecycle_job_charge_totals(doc)
		planned_cost += pc
		planned_revenue += pr
		actual_cost += ac
		actual_revenue += ar

	return planned_cost, planned_revenue, actual_cost, actual_revenue


def sync_lifecycle_job_financials(doc: Any) -> None:
	"""Update lifecycle_jobs planned/actual from linked jobs or programme charges."""
	if not doc.get("lifecycle_jobs"):
		return

	_auto_assign_charge_lifecycle_rows(doc)
	_validate_charge_lifecycle_links(doc)

	lifecycle_rows = _lifecycle_rows(doc)
	charges = _charges(doc)

	for row in lifecycle_rows:
		job_type = _lifecycle_row_job_type(row)
		job_no = (getattr(row, "job_no", None) or "").strip()
		if job_type and job_no and _active_job_doc(job_type, job_no):
			pc, pr, ac, ar = calculate_linked_job_stack_totals(job_type, job_no, lifecycle_row=row)
			row.planned_cost = flt(pc)
			row.planned_revenue = flt(pr)
			row.actual_cost = flt(ac)
			row.actual_revenue = flt(ar)
		else:
			planned_cost, planned_revenue = _planned_totals_for_lifecycle_row(
				row, lifecycle_rows, charges
			)
			row.planned_cost = flt(planned_cost)
			row.planned_revenue = flt(planned_revenue)
			row.actual_cost = 0.0
			row.actual_revenue = 0.0


def _lifecycle_link_keys_for_operational_doc(doc: Any) -> list[tuple[str, str]]:
	"""Return ``(job_type, job_no)`` pairs that may appear on a Special Project lifecycle row."""
	keys: list[tuple[str, str]] = []
	dt = (getattr(doc, "doctype", None) or "").strip()
	name = (getattr(doc, "name", None) or "").strip()
	if not dt or not name:
		return keys
	keys.append((dt, name))
	if dt == "Transport Job":
		to = (getattr(doc, "transport_order", None) or "").strip()
		if to:
			keys.append(("Transport Order", to))
	elif dt == "Air Shipment":
		ab = (getattr(doc, "air_booking", None) or "").strip()
		if ab:
			keys.append(("Air Booking", ab))
	elif dt == "Sea Shipment":
		sb = (getattr(doc, "sea_booking", None) or "").strip()
		if sb:
			keys.append(("Sea Booking", sb))
	elif dt == "Declaration":
		do = (getattr(doc, "declaration_order", None) or "").strip()
		if do:
			keys.append(("Declaration Order", do))
	elif dt == "Warehouse Job":
		ref_type = (getattr(doc, "reference_order_type", None) or "").strip()
		ref = (getattr(doc, "reference_order", None) or "").strip()
		if ref_type and ref:
			keys.append((ref_type, ref))
	return keys


def refresh_special_project_lifecycle_financials_for_job_doc(doc: Any) -> int:
	"""Re-sync lifecycle planned/actual on Special Projects referencing this operational job.

	Returns the number of Special Project documents updated.
	"""
	updated = 0
	seen_parents: set[str] = set()
	for job_type, job_no in _lifecycle_link_keys_for_operational_doc(doc):
		for parent in frappe.get_all(
			"Lifecycle Job",
			filters={
				"parenttype": "Special Project",
				"parentfield": "lifecycle_jobs",
				"job_type": job_type,
				"job_no": job_no,
			},
			pluck="parent",
		):
			if not parent or parent in seen_parents:
				continue
			seen_parents.add(parent)
			try:
				sp = frappe.get_doc("Special Project", parent)
			except Exception:
				continue
			sync_lifecycle_job_financials(sp)
			for row in sp.get("lifecycle_jobs") or []:
				if not row.name:
					continue
				frappe.db.set_value(
					"Lifecycle Job",
					row.name,
					{
						"planned_cost": row.planned_cost,
						"planned_revenue": row.planned_revenue,
						"actual_cost": row.actual_cost,
						"actual_revenue": row.actual_revenue,
					},
					update_modified=False,
				)
			updated += 1
	return updated


def on_operational_job_update_refresh_special_project_lifecycle(doc: Any, method: str | None = None) -> None:
	"""Doc event: keep lifecycle financial columns current when job charges change."""
	if int(getattr(doc, "docstatus", 0) or 0) == 2:
		return
	if not _doctype_has_charges_table(doc.doctype):
		return
	try:
		refresh_special_project_lifecycle_financials_for_job_doc(doc)
	except Exception:
		frappe.log_error(title="Lifecycle financial refresh failed", message=frappe.get_traceback())
