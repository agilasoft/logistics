# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Cross Dock warehouse job: stage-in then stage-out (no storage putaway/pick)."""

from __future__ import annotations

from typing import Any, Dict, List, Set

import frappe
from frappe import _
from frappe.utils import flt

from .common import (
	_append_job_items,
	_fetch_job_order_items,
	_get_job_scope,
	_insert_ledger_entry,
	_mark_row_posted,
	_maybe_set_staging_area_on_row,
	_posting_datetime,
	_row_is_already_posted,
	_safe_meta_fieldnames,
	_set_hu_status_by_balance,
	_set_sl_status_by_balance,
	_validate_status_for_action,
)


def _handling_units_allowed_at_storage_type(
	company: str | None,
	branch: str | None,
	storage_type: str | None,
) -> Set[str] | None:
	"""Handling units whose type may sit in this storage type.

	Returns None when the staging location has no storage type, so every
	available unit in company and branch can be used. A handling unit type
	with no Allowed Storage Type rows is allowed anywhere.
	"""
	if not storage_type:
		return None

	rows = frappe.db.sql(
		"""
		SELECT hu.name
		FROM `tabHandling Unit` hu
		WHERE hu.status IN ('Available', 'In Use')
		  AND (%(company)s IS NULL OR IFNULL(hu.company, '') = '' OR hu.company = %(company)s)
		  AND (%(branch)s IS NULL OR IFNULL(hu.branch, '') = '' OR hu.branch = %(branch)s)
		  AND (
			NOT EXISTS (
				SELECT 1
				FROM `tabHandling Unit Type Storage` ts
				WHERE ts.parent = hu.type
				  AND ts.parenttype = 'Handling Unit Type'
				  AND ts.parentfield = 'allowed_storage_type'
				  AND IFNULL(ts.storage_type, '') != ''
			)
			OR EXISTS (
				SELECT 1
				FROM `tabHandling Unit Type Storage` ts
				WHERE ts.parent = hu.type
				  AND ts.parenttype = 'Handling Unit Type'
				  AND ts.parentfield = 'allowed_storage_type'
				  AND ts.storage_type = %(storage_type)s
			)
		  )
		""",
		{"company": company, "branch": branch, "storage_type": storage_type},
		as_dict=True,
	) or []
	return {row["name"] for row in rows if row.get("name")}


def _hu_type_allows_storage_type(handling_unit: str | None, storage_type: str | None) -> bool:
	"""True when the unit's type lists this storage type, or lists nothing."""
	if not handling_unit or not storage_type:
		return True
	hu_type = frappe.db.get_value("Handling Unit", handling_unit, "type")
	if not hu_type:
		return True
	rows = frappe.db.sql(
		"""
		SELECT storage_type
		FROM `tabHandling Unit Type Storage`
		WHERE parent = %s
		  AND parenttype = 'Handling Unit Type'
		  AND parentfield = 'allowed_storage_type'
		  AND IFNULL(storage_type, '') != ''
		""",
		(hu_type,),
		as_dict=True,
	) or []
	allowed = {row["storage_type"] for row in rows}
	return (not allowed) or (storage_type in allowed)


def _append_cross_dock_row(
	job,
	order: Dict[str, Any],
	staging_area: str,
	handling_unit: str | None,
	qty: float,
	note: str,
) -> tuple[int, float]:
	before = len(job.items or [])
	rows, qty_sum = _append_job_items(
		job,
		source_parent=job.name,
		source_child=order.get("name"),
		item=order.get("item"),
		uom=order.get("uom"),
		allocations=[
			{
				"location": staging_area,
				"handling_unit": handling_unit,
				"qty": qty,
				"serial_no": order.get("serial_no"),
				"batch_no": order.get("batch_no"),
			}
		],
		order_data=order,
	)
	if note and "allocation_notes" in _safe_meta_fieldnames("Warehouse Job Item"):
		for row in (job.items or [])[before:]:
			row.allocation_notes = note
	return rows, qty_sum


def _staging_location_note(staging_area: str) -> str:
	return "\n".join([
		f"Location Allocation: {staging_area}",
		"  • Cross-dock staging. Cargo stays on this staging area.",
	])


@frappe.whitelist()
def allocate_cross_dock(warehouse_job: str) -> Dict[str, Any]:
	"""Copy order lines onto the job staging area and assign a handling unit.

	A handling unit already on the order line is kept. Otherwise an available
	handling unit in the job company and branch is chosen, preferring the order
	line's handling unit type. The handling unit type must allow the staging
	location's storage type when that type has Allowed Storage Type rows.
	"""
	job = frappe.get_doc("Warehouse Job", warehouse_job)
	if (job.type or "").strip() != "Cross Dock":
		frappe.throw(_("allocate_cross_dock is only valid for Cross Dock jobs."))

	staging_area = getattr(job, "staging_area", None)
	if not staging_area:
		return {"ok": False, "message": _("Staging Area is required on the Warehouse Job.")}

	orders = _fetch_job_order_items(job.name)
	if not orders:
		return {"ok": False, "message": _("No order lines found on the Warehouse Job.")}

	company, branch = _get_job_scope(job)
	staging_storage_type = frappe.db.get_value("Storage Location", staging_area, "storage_type")
	allowed_hus = _handling_units_allowed_at_storage_type(company, branch, staging_storage_type)

	job.set("items", [])
	created_rows = 0
	created_qty = 0.0
	warnings: List[str] = []
	orders_without_hu: List[Dict[str, Any]] = []

	for order in orders:
		item = order.get("item")
		qty = abs(flt(order.get("quantity") or 0))
		if not item or qty == 0:
			warnings.append(_("Order row {0}: missing item or quantity.").format(order.get("name")))
			continue
		prepared = dict(order)
		prepared["quantity"] = qty
		prepared["company"] = company
		if (prepared.get("handling_unit") or "").strip():
			hu = prepared.get("handling_unit")
			if not _hu_type_allows_storage_type(hu, staging_storage_type):
				warnings.append(
					_("Order row {0}: handling unit {1} type does not allow staging storage type {2}. It was still used because it is set on the order.")
					.format(prepared.get("name"), hu, staging_storage_type)
				)
			note = "\n".join([
				f"Handling Unit Allocation: {hu}",
				"  • Handling Unit Source: defined on the order",
				_staging_location_note(staging_area),
			])
			rows, qty_sum = _append_cross_dock_row(job, prepared, staging_area, hu, qty, note)
			created_rows += rows
			created_qty += qty_sum
		else:
			orders_without_hu.append(prepared)

	allocations_by_order: Dict[str, List[tuple]] = {}
	if orders_without_hu:
		from .capacity_management import CapacityManager
		from .putaway import _allocate_hu_to_orders

		hu_allocations, hu_warnings = _allocate_hu_to_orders(
			orders_without_hu,
			company,
			branch,
			CapacityManager(),
			set(),
			allowed_hu_names=allowed_hus,
		)
		warnings.extend(hu_warnings)
		for hu_name, order_row, allocated_qty, allocation_note in hu_allocations:
			allocations_by_order.setdefault(order_row.get("name"), []).append(
				(hu_name, allocated_qty, allocation_note)
			)

	for order in orders_without_hu:
		parts = allocations_by_order.get(order.get("name"), [])
		allocated_qty = 0.0
		for hu_name, qty, allocation_note in parts:
			note = "\n\n".join(part for part in (allocation_note, _staging_location_note(staging_area)) if part)
			rows, qty_sum = _append_cross_dock_row(job, order, staging_area, hu_name, qty, note)
			created_rows += rows
			created_qty += qty_sum
			allocated_qty += flt(qty)

		original_qty = flt(order.get("quantity") or 0)
		remaining = original_qty - allocated_qty
		if remaining > 0.0001:
			from .putaway import _generate_unallocated_hu_note

			note_lines = [
				_generate_unallocated_hu_note(order, remaining, original_qty, allocated_qty),
				_staging_location_note(staging_area),
			]
			if staging_storage_type:
				note_lines.append(
					f"  • Staging storage type: {staging_storage_type}. "
					"The handling unit type must include this storage type, or have no Allowed Storage Type."
				)
			rows, qty_sum = _append_cross_dock_row(
				job, order, staging_area, None, remaining, "\n\n".join(note_lines)
			)
			created_rows += rows
			created_qty += qty_sum
			warnings.append(
				_("Order row {0}: {1} of {2} could not be placed on a handling unit.")
				.format(order.get("name"), remaining, original_qty)
			)

	job.save(ignore_permissions=True)
	frappe.db.commit()

	return {
		"ok": True,
		"message": _("Allocated {0} cross-dock line(s) to staging.").format(created_rows),
		"created_rows": created_rows,
		"created_qty": created_qty,
		"warnings": warnings,
	}


@frappe.whitelist()
def post_cross_dock_receiving(warehouse_job: str) -> Dict[str, Any]:
	"""Cross Dock step 1: In to Staging (+ABS); marks staging_posted."""
	job = frappe.get_doc("Warehouse Job", warehouse_job)
	if (job.type or "").strip() != "Cross Dock":
		frappe.throw(_("post_cross_dock_receiving is only valid for Cross Dock jobs."))

	staging_area = getattr(job, "staging_area", None)
	if not staging_area:
		frappe.throw(_("Staging Area is required on the Warehouse Job."))

	from logistics.warehousing.api_parts.capacity_management import validate_warehouse_job_capacity
	validate_warehouse_job_capacity(job)

	posting_dt = _posting_datetime(job)
	created = 0
	skipped: List[str] = []
	action_key = "staging" if "staging_posted" in _safe_meta_fieldnames("Warehouse Job Item") else "receiving"

	for it in (job.items or []):
		if _row_is_already_posted(it, action_key):
			skipped.append(_("Item Row {0}: staging already posted.").format(getattr(it, "idx", "?")))
			continue
		item = getattr(it, "item", None)
		qty = abs(flt(getattr(it, "quantity", 0)))
		if not item or qty == 0:
			continue
		hu = getattr(it, "handling_unit", None)
		bn = getattr(it, "batch_no", None)
		sn = getattr(it, "serial_no", None)

		_validate_status_for_action(action="Receiving", location=staging_area, handling_unit=hu)
		_insert_ledger_entry(
			job, item=item, qty=qty, location=staging_area,
			handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt,
		)
		_mark_row_posted(it, action_key, posting_dt)
		_maybe_set_staging_area_on_row(it, staging_area)
		created += 1

	job.save(ignore_permissions=True)
	_set_sl_status_by_balance(staging_area)
	seen_hus = {getattr(r, "handling_unit", None) for r in (job.items or []) if getattr(r, "handling_unit", None)}
	for h in seen_hus:
		_set_hu_status_by_balance(h, after_release=False)
	frappe.db.commit()

	msg = _("Cross-dock receiving posted into staging: {0} entry(ies).").format(created)
	if skipped:
		msg += " " + _("Skipped") + f": {len(skipped)}"
	return {"ok": True, "message": msg, "created": created, "skipped": skipped}


@frappe.whitelist()
def post_cross_dock_release(warehouse_job: str) -> Dict[str, Any]:
	"""Cross Dock step 2: Out from Staging (−ABS); requires staging_posted; marks release_posted."""
	job = frappe.get_doc("Warehouse Job", warehouse_job)
	if (job.type or "").strip() != "Cross Dock":
		frappe.throw(_("post_cross_dock_release is only valid for Cross Dock jobs."))

	staging_area = getattr(job, "staging_area", None)
	if not staging_area:
		frappe.throw(_("Staging Area is required on the Warehouse Job."))

	jf = _safe_meta_fieldnames("Warehouse Job Item")
	if "release_posted" not in jf:
		frappe.throw(_("Warehouse Job Item is missing release_posted; cannot post cross-dock release."))

	posting_dt = _posting_datetime(job)
	created = 0
	skipped: List[str] = []
	affected_hus: Set[str] = set()

	for it in (job.items or []):
		# Must have been received into staging first
		if "staging_posted" in jf and not _row_is_already_posted(it, "staging"):
			skipped.append(_("Item Row {0}: not yet received into staging.").format(getattr(it, "idx", "?")))
			continue
		if _row_is_already_posted(it, "release"):
			skipped.append(_("Item Row {0}: already released.").format(getattr(it, "idx", "?")))
			continue

		item = getattr(it, "item", None)
		qty = abs(flt(getattr(it, "quantity", 0)))
		if not item or qty == 0:
			continue
		hu = getattr(it, "handling_unit", None)
		bn = getattr(it, "batch_no", None)
		sn = getattr(it, "serial_no", None)

		_validate_status_for_action(action="Release", location=staging_area, handling_unit=hu)
		_insert_ledger_entry(
			job, item=item, qty=-qty, location=staging_area,
			handling_unit=hu, batch_no=bn, serial_no=sn, posting_dt=posting_dt,
		)
		_mark_row_posted(it, "release", posting_dt)
		created += 1
		if hu:
			affected_hus.add(hu)

	job.save(ignore_permissions=True)
	_set_sl_status_by_balance(staging_area)
	for h in affected_hus:
		_set_hu_status_by_balance(h, after_release=True)
	frappe.db.commit()

	msg = _("Cross-dock release posted from staging: {0} entry(ies).").format(created)
	if skipped:
		msg += " " + _("Skipped") + f": {len(skipped)}"
	return {"ok": True, "message": msg, "created": created, "skipped": skipped}
