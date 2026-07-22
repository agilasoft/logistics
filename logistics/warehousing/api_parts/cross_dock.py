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


@frappe.whitelist()
def allocate_cross_dock(warehouse_job: str) -> Dict[str, Any]:
	"""Copy order lines onto job items anchored at the job staging area (no storage allocation)."""
	job = frappe.get_doc("Warehouse Job", warehouse_job)
	if (job.type or "").strip() != "Cross Dock":
		frappe.throw(_("allocate_cross_dock is only valid for Cross Dock jobs."))

	staging_area = getattr(job, "staging_area", None)
	if not staging_area:
		return {"ok": False, "message": _("Staging Area is required on the Warehouse Job.")}

	orders = _fetch_job_order_items(job.name)
	if not orders:
		return {"ok": False, "message": _("No order lines found on the Warehouse Job.")}

	# Clear existing allocation rows for a clean re-allocate
	job.set("items", [])
	created_rows = 0
	created_qty = 0.0
	warnings: List[str] = []

	for order in orders:
		item = order.get("item")
		qty = abs(flt(order.get("quantity") or 0))
		if not item or qty == 0:
			warnings.append(_("Order row {0}: missing item or quantity.").format(order.get("name")))
			continue

		allocations = [
			{
				"location": staging_area,
				"handling_unit": order.get("handling_unit"),
				"qty": qty,
				"serial_no": order.get("serial_no"),
				"batch_no": order.get("batch_no"),
			}
		]
		rows, qty_sum = _append_job_items(
			job,
			source_parent=job.name,
			source_child=order.get("name"),
			item=item,
			uom=order.get("uom"),
			allocations=allocations,
			order_data=order,
		)
		created_rows += rows
		created_qty += qty_sum

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
