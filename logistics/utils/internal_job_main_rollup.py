# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Roll up planned / actual cost & revenue from an internal job into the Main Service's Internal Job Detail row.

When an operational document acts as an *internal job* (``is_internal_job=1`` with
``main_job_type`` + ``main_job`` set), its charge totals belong on the Internal Jobs table of the
Main Service. This module computes those totals from the internal job's ``charges`` child table
and writes them back to the matching ``Internal Job Detail`` row (matched by ``job_no = doc.name``).

Coverage (all current internal-job-capable doctypes):

* ``Air Booking`` / ``Sea Booking``
* ``Transport Order`` / ``Declaration Order``
* ``Transport Job`` / ``Declaration``
* ``Warehouse Job`` / ``Inbound Order`` / ``Release Order``
* ``Project Task Job``

The Main Service may be submitted; child writes use ``frappe.db.set_value`` with
``update_modified=False`` so the parent's submission state and modified timestamp are unaffected.
"""

from __future__ import annotations

from typing import Any, Iterable, Tuple

import frappe
from frappe.utils import cint, flt


_DISBURSEMENT_LOWER = "disbursement"


def _is_disbursement_charge(row: Any) -> bool:
	return (getattr(row, "charge_type", "") or "").strip().lower() == _DISBURSEMENT_LOWER


def _charge_planned_revenue(row: Any) -> float:
	"""Planned (estimated) selling-side amount for a charge row.

	Prefer ``estimated_revenue``; fall back to common selling totals when an internal job's
	charge child schema does not expose ``estimated_revenue`` (e.g. ``Inbound Order Charges``
	exposes ``total`` only).
	"""
	for attr in ("estimated_revenue", "base_amount", "selling_amount", "total_amount", "total", "amount"):
		if hasattr(row, attr):
			v = flt(getattr(row, attr, 0) or 0)
			if v:
				return v
	return 0


def _charge_planned_cost(row: Any) -> float:
	"""Planned (estimated) cost-side amount for a charge row."""
	for attr in ("estimated_cost", "cost_base_amount", "cost_amount", "cost"):
		if hasattr(row, attr):
			v = flt(getattr(row, attr, 0) or 0)
			if v:
				return v
	return 0


def _charge_actual_revenue(row: Any) -> float:
	"""Actual selling-side amount when tracked on the charge row; ``0`` otherwise."""
	if hasattr(row, "actual_revenue"):
		return flt(getattr(row, "actual_revenue", 0) or 0)
	return 0


def _charge_actual_cost(row: Any) -> float:
	"""Actual cost-side amount when tracked on the charge row; ``0`` otherwise."""
	if hasattr(row, "actual_cost"):
		return flt(getattr(row, "actual_cost", 0) or 0)
	return 0


def calculate_internal_job_rollup_totals(doc: Any) -> Tuple[float, float, float, float]:
	"""Return ``(planned_cost, planned_revenue, actual_cost, actual_revenue)`` summed from ``doc.charges``.

	Disbursement rows are excluded (they pass through and do not contribute to job P&L).
	"""
	planned_cost = 0.0
	planned_revenue = 0.0
	actual_cost = 0.0
	actual_revenue = 0.0
	for row in getattr(doc, "charges", None) or []:
		if _is_disbursement_charge(row):
			continue
		planned_revenue += _charge_planned_revenue(row)
		planned_cost += _charge_planned_cost(row)
		actual_revenue += _charge_actual_revenue(row)
		actual_cost += _charge_actual_cost(row)
	return planned_cost, planned_revenue, actual_cost, actual_revenue


def _doc_is_internal_job(doc: Any) -> bool:
	"""Internal job iff ``is_internal_job=1`` AND a non-empty ``main_job_type`` + ``main_job`` pair."""
	if not cint(getattr(doc, "is_internal_job", 0)):
		return False
	mt = (getattr(doc, "main_job_type", None) or "").strip()
	mn = (getattr(doc, "main_job", None) or "").strip()
	return bool(mt and mn)


def _iter_internal_job_detail_rows_for_job(job_type: str, job_no: str) -> Iterable[dict]:
	"""Yield ``Internal Job Detail`` row metadata across all parents linked to this internal job.

	Filters by ``job_type + job_no`` so a single internal-job document only touches its matching rows.
	"""
	rows = frappe.get_all(
		"Internal Job Detail",
		filters={"job_type": job_type, "job_no": job_no},
		fields=["name", "parent", "parenttype", "parentfield"],
	)
	return rows


def _update_internal_job_detail_row(
	row_name: str,
	planned_cost: float,
	planned_revenue: float,
	actual_cost: float,
	actual_revenue: float,
) -> bool:
	"""Update one ``Internal Job Detail`` row's planned / actual totals; returns True if any value changed."""
	cur = frappe.db.get_value(
		"Internal Job Detail",
		row_name,
		("planned_cost", "planned_revenue", "actual_cost", "actual_revenue"),
		as_dict=True,
	) or {}
	desired = {
		"planned_cost": flt(planned_cost),
		"planned_revenue": flt(planned_revenue),
		"actual_cost": flt(actual_cost),
		"actual_revenue": flt(actual_revenue),
	}
	changes = {k: v for k, v in desired.items() if abs(flt(cur.get(k)) - flt(v)) > 0.0001}
	if not changes:
		return False
	frappe.db.set_value("Internal Job Detail", row_name, changes, update_modified=False)
	return True


def sync_internal_job_rollup_to_main(doc: Any, *, cancelled: bool = False) -> bool:
	"""Push planned / actual totals from this internal job onto its Main Service's Internal Job Detail row.

	When ``cancelled`` is True the rollup zeros the values (the internal job is no longer active so the
	main service should not show stale numbers from a cancelled document).

	Returns True when any row was updated; False otherwise.
	"""
	if not _doc_is_internal_job(doc):
		return False
	job_type = doc.doctype
	job_no = doc.name or ""
	if not job_no:
		return False
	if cancelled:
		planned_cost = planned_revenue = actual_cost = actual_revenue = 0.0
	else:
		planned_cost, planned_revenue, actual_cost, actual_revenue = (
			calculate_internal_job_rollup_totals(doc)
		)
	changed = False
	for row in _iter_internal_job_detail_rows_for_job(job_type, job_no):
		row_name = row.get("name") if isinstance(row, dict) else row.name
		if not row_name:
			continue
		try:
			if _update_internal_job_detail_row(
				row_name,
				planned_cost,
				planned_revenue,
				actual_cost,
				actual_revenue,
			):
				changed = True
		except Exception:
			frappe.log_error(
				title="Internal job rollup failed",
				message=frappe.get_traceback(),
			)
	return changed


def refresh_internal_job_details_for_main_service(main_doctype: str, main_name: str) -> int:
	"""Recompute planned / actual totals for every Internal Job Detail row on this Main Service.

	Useful as a one-shot reconcile (e.g. patch, manual fix) so existing main documents whose
	internal jobs were submitted before this rollup existed are brought up to date.

	Returns the number of rows that changed.
	"""
	if not main_doctype or not main_name or not frappe.db.exists(main_doctype, main_name):
		return 0
	meta = frappe.get_meta(main_doctype)
	if not meta.get_field("internal_job_details"):
		return 0
	rows = frappe.get_all(
		"Internal Job Detail",
		filters={"parent": main_name, "parenttype": main_doctype},
		fields=["name", "job_type", "job_no"],
	)
	changed = 0
	for r in rows:
		jt = (r.get("job_type") or "").strip()
		jn = (r.get("job_no") or "").strip()
		if not jt or not jn or not frappe.db.exists(jt, jn):
			continue
		try:
			job = frappe.get_doc(jt, jn)
		except Exception:
			continue
		if int(getattr(job, "docstatus", 0) or 0) == 2:
			planned_cost = planned_revenue = actual_cost = actual_revenue = 0.0
		else:
			planned_cost, planned_revenue, actual_cost, actual_revenue = (
				calculate_internal_job_rollup_totals(job)
			)
		if _update_internal_job_detail_row(
			r["name"],
			planned_cost,
			planned_revenue,
			actual_cost,
			actual_revenue,
		):
			changed += 1
	return changed


# ---------------------------------------------------------------------------
# Doc event handlers (registered in hooks.py for every internal-job-capable doctype)
# ---------------------------------------------------------------------------

def on_internal_job_after_save(doc: Any, method: str | None = None) -> None:
	"""``on_update`` / draft save: push current planned / actual totals to the Main Service row."""
	if int(getattr(doc, "docstatus", 0) or 0) == 2:
		return
	sync_internal_job_rollup_to_main(doc, cancelled=False)


def on_internal_job_submit(doc: Any, method: str | None = None) -> None:
	"""``on_submit``: persist planned / actual totals onto the Main Service row."""
	sync_internal_job_rollup_to_main(doc, cancelled=False)


def on_internal_job_update_after_submit(doc: Any, method: str | None = None) -> None:
	"""``on_update_after_submit``: refresh totals when a submitted internal job's charges change."""
	sync_internal_job_rollup_to_main(doc, cancelled=False)


def on_internal_job_cancel(doc: Any, method: str | None = None) -> None:
	"""``on_cancel``: clear totals so the Main Service does not reflect cancelled jobs."""
	sync_internal_job_rollup_to_main(doc, cancelled=True)


@frappe.whitelist()
def refresh_main_service_internal_job_rollup(doctype: str, name: str) -> dict:
	"""Manual reconcile entry point — recompute Internal Job Detail totals for one Main Service."""
	from frappe import _

	if not doctype or not name:
		frappe.throw(_("Doctype and name are required."))
	if not frappe.db.exists(doctype, name):
		frappe.throw(_("{0} {1} does not exist.").format(doctype, name))
	frappe.get_doc(doctype, name).check_permission("read")
	changed = refresh_internal_job_details_for_main_service(doctype, name)
	return {"changed_rows": changed}
