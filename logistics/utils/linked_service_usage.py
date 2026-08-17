# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Record and query Linked Service Usage rows (shared IJ-… consumers).

Sales Quote keeps ownership of Linked Service documents. Bookings, shipments, and
satellite jobs reuse the same ``IJ-…`` ID and are tagged here with per-document
Planned/Actual Cost & Revenue. The Linked Service header Rollup is the sum of all
Usage rows.
"""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import flt

from logistics.utils.linked_service_compat import linked_service_doctype

USAGE_ROLE_PARENT_BOOKING = "Parent Booking"
USAGE_ROLE_SATELLITE_JOB = "Satellite Job"
USAGE_ROLE_SHIPMENT = "Shipment"

_USAGE_CHILD = "Linked Service Usage"
_USAGE_PARENTFIELD = "usages"

_ROLLUP_FIELDS = ("planned_cost", "planned_revenue", "actual_cost", "actual_revenue")


def _norm(val: Any) -> str:
	if val is None:
		return ""
	return str(val).strip()


def _usage_table_exists() -> bool:
	return bool(frappe.db.exists("DocType", _USAGE_CHILD))


def _resolve_sales_quote_for_usage(
	linked_service: str,
	used_on_doctype: str,
	used_on_name: str,
	sales_quote: str | None = None,
) -> str:
	sq = _norm(sales_quote)
	if sq:
		return sq
	ls_dt = linked_service_doctype()
	parent_type = frappe.db.get_value(ls_dt, linked_service, "parent_booking_type")
	parent_name = frappe.db.get_value(ls_dt, linked_service, "parent_booking_name")
	if _norm(parent_type) == "Sales Quote" and _norm(parent_name):
		return _norm(parent_name)
	# Prefer sales_quote on the consumer document when present.
	if used_on_doctype and used_on_name and frappe.db.exists(used_on_doctype, used_on_name):
		meta = frappe.get_meta(used_on_doctype)
		if meta.has_field("sales_quote"):
			return _norm(frappe.db.get_value(used_on_doctype, used_on_name, "sales_quote"))
		if meta.has_field("quote"):
			quote = _norm(frappe.db.get_value(used_on_doctype, used_on_name, "quote"))
			if quote and frappe.db.exists("Sales Quote", quote):
				return quote
	return ""


def _charge_totals_for_doc(doctype: str, name: str) -> dict[str, float]:
	"""Sum planned/actual cost & revenue from a consumer document's charges when possible."""
	zeros = {fn: 0.0 for fn in _ROLLUP_FIELDS}
	if not doctype or not name or not frappe.db.exists(doctype, name):
		return zeros
	try:
		doc = frappe.get_doc(doctype, name)
	except Exception:
		return zeros
	try:
		from logistics.utils.internal_job_main_rollup import calculate_internal_job_rollup_totals

		pc, pr, ac, ar = calculate_internal_job_rollup_totals(doc)
		return {
			"planned_cost": flt(pc),
			"planned_revenue": flt(pr),
			"actual_cost": flt(ac),
			"actual_revenue": flt(ar),
		}
	except Exception:
		return zeros


def recompute_linked_service_header_rollup(linked_service: str) -> None:
	"""Set Linked Service header Rollup = sum of all Usage row amounts."""
	if not linked_service or not _usage_table_exists():
		return
	if not frappe.db.exists(linked_service_doctype(), linked_service):
		return
	rows = frappe.get_all(
		_USAGE_CHILD,
		filters={"parent": linked_service, "parenttype": linked_service_doctype()},
		fields=list(_ROLLUP_FIELDS),
	)
	totals = {fn: 0.0 for fn in _ROLLUP_FIELDS}
	for row in rows:
		for fn in _ROLLUP_FIELDS:
			totals[fn] += flt(row.get(fn))
	frappe.db.set_value(
		linked_service_doctype(),
		linked_service,
		totals,
		update_modified=False,
	)


def record_linked_service_usage(
	linked_service: str,
	used_on_doctype: str,
	used_on_name: str,
	*,
	usage_role: str = USAGE_ROLE_PARENT_BOOKING,
	sales_quote: str | None = None,
	planned_cost: float | None = None,
	planned_revenue: float | None = None,
	actual_cost: float | None = None,
	actual_revenue: float | None = None,
	refresh_totals: bool = True,
) -> str | None:
	"""Ensure a Usage row exists for (linked_service, used_on_*); return child row name.

	Idempotent: unique on parent + used_on_doctype + used_on_name.
	"""
	ls = _norm(linked_service)
	dt = _norm(used_on_doctype)
	nm = _norm(used_on_name)
	if not ls or not dt or not nm:
		return None
	if not _usage_table_exists():
		return None
	if not frappe.db.exists(linked_service_doctype(), ls):
		return None

	role = _norm(usage_role) or USAGE_ROLE_PARENT_BOOKING
	sq = _resolve_sales_quote_for_usage(ls, dt, nm, sales_quote)

	if planned_cost is None or planned_revenue is None or actual_cost is None or actual_revenue is None:
		totals = _charge_totals_for_doc(dt, nm)
		if planned_cost is None:
			planned_cost = totals["planned_cost"]
		if planned_revenue is None:
			planned_revenue = totals["planned_revenue"]
		if actual_cost is None:
			actual_cost = totals["actual_cost"]
		if actual_revenue is None:
			actual_revenue = totals["actual_revenue"]

	existing = frappe.db.get_value(
		_USAGE_CHILD,
		{
			"parent": ls,
			"parenttype": linked_service_doctype(),
			"used_on_doctype": dt,
			"used_on_name": nm,
		},
		"name",
	)
	payload = {
		"usage_role": role,
		"sales_quote": sq or None,
		"planned_cost": flt(planned_cost),
		"planned_revenue": flt(planned_revenue),
		"actual_cost": flt(actual_cost),
		"actual_revenue": flt(actual_revenue),
	}
	if existing:
		frappe.db.set_value(_USAGE_CHILD, existing, payload, update_modified=False)
		row_name = existing
	else:
		ls_doc = frappe.get_doc(linked_service_doctype(), ls)
		row = ls_doc.append(
			_USAGE_PARENTFIELD,
			{
				"used_on_doctype": dt,
				"used_on_name": nm,
				**payload,
			},
		)
		ls_doc.flags.ignore_permissions = True
		ls_doc.flags.ignore_links = True
		ls_doc.flags.ignore_validate_update_after_submit = True
		ls_doc.flags.skip_internal_job_detail_sync = True
		ls_doc.save(ignore_permissions=True)
		row_name = row.name

	if refresh_totals:
		recompute_linked_service_header_rollup(ls)
	return row_name


def clear_linked_service_usage(
	used_on_doctype: str,
	used_on_name: str,
	*,
	linked_service: str | None = None,
) -> int:
	"""Remove Usage rows for a consumer document. Returns number of rows removed."""
	if not _usage_table_exists():
		return 0
	dt = _norm(used_on_doctype)
	nm = _norm(used_on_name)
	if not dt or not nm:
		return 0
	filters: dict[str, Any] = {"used_on_doctype": dt, "used_on_name": nm}
	if linked_service:
		filters["parent"] = _norm(linked_service)
		filters["parenttype"] = linked_service_doctype()
	rows = frappe.get_all(_USAGE_CHILD, filters=filters, fields=["name", "parent"])
	if not rows:
		return 0
	parents = {_norm(r.parent) for r in rows if r.parent}
	for r in rows:
		frappe.delete_doc(_USAGE_CHILD, r.name, force=True, ignore_permissions=True)
	for parent in parents:
		recompute_linked_service_header_rollup(parent)
	return len(rows)


def get_usages_for_linked_service(linked_service: str) -> list[dict[str, Any]]:
	"""All Usage rows for one Linked Service (stable creation order)."""
	ls = _norm(linked_service)
	if not ls or not _usage_table_exists():
		return []
	return frappe.get_all(
		_USAGE_CHILD,
		filters={"parent": ls, "parenttype": linked_service_doctype()},
		fields=[
			"name",
			"used_on_doctype",
			"used_on_name",
			"usage_role",
			"sales_quote",
			*_ROLLUP_FIELDS,
			"idx",
			"creation",
		],
		order_by="idx asc, creation asc",
	)


def get_linked_services_used_by(doctype: str, name: str) -> list[str]:
	"""Linked Service names that have a Usage row for this consumer document."""
	dt = _norm(doctype)
	nm = _norm(name)
	if not dt or not nm or not _usage_table_exists():
		return []
	return frappe.get_all(
		_USAGE_CHILD,
		filters={"used_on_doctype": dt, "used_on_name": nm},
		pluck="parent",
		order_by="creation asc",
	)


def sync_usage_rollup_from_job(
	job_doctype: str,
	job_name: str,
	*,
	linked_service: str | None = None,
	cancelled: bool = False,
) -> int:
	"""Push charge totals from a job onto matching Usage row(s); refresh header Rollup.

	Returns number of Usage rows updated.
	"""
	if not _usage_table_exists():
		return 0
	dt = _norm(job_doctype)
	nm = _norm(job_name)
	if not dt or not nm:
		return 0
	filters: dict[str, Any] = {"used_on_doctype": dt, "used_on_name": nm}
	if linked_service:
		filters["parent"] = _norm(linked_service)
		filters["parenttype"] = linked_service_doctype()
	rows = frappe.get_all(_USAGE_CHILD, filters=filters, fields=["name", "parent"])
	if not rows:
		return 0
	if cancelled:
		totals = {fn: 0.0 for fn in _ROLLUP_FIELDS}
	else:
		totals = _charge_totals_for_doc(dt, nm)
	parents: set[str] = set()
	for r in rows:
		frappe.db.set_value(_USAGE_CHILD, r.name, totals, update_modified=False)
		if r.parent:
			parents.add(_norm(r.parent))
	for parent in parents:
		recompute_linked_service_header_rollup(parent)
	return len(rows)


def record_usages_for_linked_services(
	linked_services: list[str] | tuple[str, ...] | None,
	used_on_doctype: str,
	used_on_name: str,
	*,
	usage_role: str = USAGE_ROLE_PARENT_BOOKING,
	sales_quote: str | None = None,
) -> dict[str, str]:
	"""Record Usage for many Linked Services; returns ``{ls_name: ls_name}`` identity map."""
	mapping: dict[str, str] = {}
	for ls in linked_services or []:
		name = _norm(ls)
		if not name:
			continue
		record_linked_service_usage(
			name,
			used_on_doctype,
			used_on_name,
			usage_role=usage_role,
			sales_quote=sales_quote,
		)
		mapping[name] = name
	return mapping


# Booking/order doctypes stored on Usage as Satellite Job → grid ``order_no``.
LINKED_SERVICE_ORDER_TYPES: frozenset[str] = frozenset(
	{
		"Air Booking",
		"Sea Booking",
		"Transport Order",
		"Declaration Order",
		"VAS Order",
		"Inbound Order",
		"Release Order",
		"Transfer Order",
		"Cross-Docking Order",
		"Project Order",
		"MICE Order",
	}
)

# Job/shipment doctypes stored on Usage as Shipment → grid ``job_no``.
LINKED_SERVICE_EXECUTION_TYPES: frozenset[str] = frozenset(
	{
		"Air Shipment",
		"Sea Shipment",
		"Transport Job",
		"Declaration",
		"Warehouse Job",
		"Project Job",
		"MICE Job",
		"Air Consolidation",
	}
)


def is_linked_service_order_type(doctype: str) -> bool:
	return _norm(doctype) in LINKED_SERVICE_ORDER_TYPES


def is_linked_service_execution_type(doctype: str) -> bool:
	return _norm(doctype) in LINKED_SERVICE_EXECUTION_TYPES


def latest_satellite_job_from_usage(linked_service: str) -> tuple[str, str]:
	"""Return ``(order_type, order_no)`` from the latest Satellite Job Usage row, if any.

	Satellite Job Usage is the booking/order pointer. Job/Shipment numbers come from
	``latest_shipment_from_usage``.
	"""
	ls = _norm(linked_service)
	if not ls or not _usage_table_exists():
		return "", ""
	rows = get_usages_for_linked_service(ls)
	for row in reversed(rows):
		role = _norm(row.get("usage_role"))
		if role != USAGE_ROLE_SATELLITE_JOB:
			continue
		jt = _norm(row.get("used_on_doctype"))
		jn = _norm(row.get("used_on_name"))
		if jt and jn:
			return jt, jn
	return "", ""


def latest_shipment_from_usage(linked_service: str) -> tuple[str, str]:
	"""Return ``(execution_doctype, job_no)`` from the latest Shipment Usage row, if any."""
	ls = _norm(linked_service)
	if not ls or not _usage_table_exists():
		return "", ""
	rows = get_usages_for_linked_service(ls)
	for row in reversed(rows):
		role = _norm(row.get("usage_role"))
		if role != USAGE_ROLE_SHIPMENT:
			continue
		jt = _norm(row.get("used_on_doctype"))
		jn = _norm(row.get("used_on_name"))
		if jt and jn:
			return jt, jn
	return "", ""


def linked_service_has_satellite_job(linked_service: str, job_type: str) -> str | bool:
	"""Return the ``used_on_name`` for a Satellite Job Usage of *job_type*, else ``False``.

	Used by tests and callers that previously read ``Linked Service.job_no`` for a given
	``job_type``. Prefer the latest matching Usage row when several exist.
	"""
	ls = _norm(linked_service)
	jt = _norm(job_type)
	if not ls or not jt or not _usage_table_exists():
		return False
	rows = get_usages_for_linked_service(ls)
	for row in reversed(rows):
		if _norm(row.get("usage_role")) != USAGE_ROLE_SATELLITE_JOB:
			continue
		if _norm(row.get("used_on_doctype")) != jt:
			continue
		jn = _norm(row.get("used_on_name"))
		if jn:
			return jn
	return False
