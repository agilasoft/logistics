# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Sales Quote → Booking/Order Internal Job propagation.

A Sales Quote owns ``Internal Job`` documents via ``parent_booking_type = "Sales Quote"`` and
``parent_booking_name = <quote>``. The Sales Quote may hold multiple Internal Jobs regardless of
``quotation_type``. When the quote is converted to a Sea/Air Booking or Transport Order, the IJ
records are **mirrored** onto the new booking:

1. For each SQ-owned Internal Job, a fresh Internal Job is materialised with the same parameter
   values parented to the new booking.
2. An ``Internal Job Detail`` row is appended onto the booking pointing at the new Internal Job
   (so the booking's lifecycle hooks and rollup wiring see it natively).
3. Booking charge rows whose ``internal_job`` link still points at the SQ-owned Internal Job are
   remapped to the new booking-owned Internal Job, and their ``charge_scope`` is normalised to
   ``"Internal Job"``.

The SQ-owned Internal Jobs remain on the quote as historical record of what was offered; the
booking owns its own copies and is independent thereafter.

The module name retains ``one_off`` for backward compatibility — propagation now runs for any
quote-type that owns Internal Jobs (the gate is purely "are there any SQ-owned IJs to mirror?").
"""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import cint

from logistics.utils.internal_job_detail_copy import internal_job_detail_row_as_dict
from logistics.utils.internal_job_persistence import (
	_internal_job_doctype_exists,
	create_internal_job_for_parent_from_source,
	internal_job_detail_fieldname,
)


def is_one_off_sales_quote(sales_quote: Any) -> bool:
	"""Compatibility helper: True when the Sales Quote is One-off.

	Kept for callers that still want to branch on quote type. The propagation entry points no
	longer use this gate — they only check whether SQ-owned Internal Jobs exist.
	"""
	if not sales_quote:
		return False
	return (getattr(sales_quote, "quotation_type", None) or "").strip() == "One-off"


def _sq_owned_internal_jobs(sales_quote_name: str) -> list[str]:
	"""Names of Internal Job docs owned by this Sales Quote (in creation order)."""
	if not sales_quote_name:
		return []
	return frappe.get_all(
		"Internal Job",
		filters={
			"parent_booking_type": "Sales Quote",
			"parent_booking_name": sales_quote_name,
		},
		pluck="name",
		order_by="creation asc",
	)


def _sq_internal_job_detail_rows_by_ij(sales_quote: Any) -> dict[str, Any]:
	"""Map ``internal_job → Internal Job Detail`` row for rows that link an Internal Job.

	Pulled from the in-memory ``sales_quote`` document so we copy the user-edited row values
	(parameter columns) onto the booking, not just the link.
	"""
	out: dict[str, Any] = {}
	for row in getattr(sales_quote, "internal_job_details", None) or []:
		ij = (getattr(row, "internal_job", None) or "").strip()
		if ij and ij not in out:
			out[ij] = row
	return out


def _booking_ij_detail_payload(sq_row: Any, new_ij_name: str) -> dict[str, Any]:
	"""Build an ``Internal Job Detail`` payload for the booking, mirroring *sq_row*.

	The payload copies every user-set parameter column from the SQ side and overrides:

	* ``internal_job`` — points at the fresh booking-side IJ copy.
	* ``job_no`` — cleared because the booking-side IJ has not produced an operational job yet.
	* ``actual_cost`` / ``actual_revenue`` — cleared so rollup starts from zero on the booking.
	"""
	payload = internal_job_detail_row_as_dict(sq_row) if sq_row else {}
	payload["internal_job"] = new_ij_name
	# Operational job links / rollup actuals do not transfer; they accumulate on the booking
	# as downstream operational documents (Transport Order, Declaration Order, etc.) are created.
	for fn in ("job_no", "actual_cost", "actual_revenue"):
		if fn in payload:
			payload[fn] = None
	return payload


def propagate_one_off_internal_jobs_to_booking(
	sales_quote: Any, booking_doc: Any
) -> dict[str, str]:
	"""Mirror SQ-owned Internal Jobs onto *booking_doc* and append matching IJ Detail rows.

	Returns a mapping ``{sq_ij_name → booking_ij_name}`` used by
	:func:`remap_internal_job_links_on_booking_charges` to translate the per-charge ``internal_job``
	link from the SQ-side IJ name to the booking-side IJ name.

	Idempotent guards:

	* No-op when ``sales_quote`` or ``booking_doc`` is missing.
	* No-op when the quote owns no Internal Jobs (any ``quotation_type``).
	* No-op when the booking already carries an IJ Detail row pointing at the booking-side copy of
	  a given SQ IJ (re-runs after the first conversion are safe).
	"""
	if not sales_quote or not booking_doc:
		return {}
	if not _internal_job_doctype_exists():
		return {}
	booking_dt = getattr(booking_doc, "doctype", None) or ""
	booking_nm = getattr(booking_doc, "name", None) or ""
	if not booking_dt or not booking_nm:
		return {}

	ij_fieldname = internal_job_detail_fieldname(booking_dt)
	if not ij_fieldname:
		return {}
	meta = frappe.get_meta(booking_dt)
	if not meta.get_field(ij_fieldname):
		return {}

	sq_ij_names = _sq_owned_internal_jobs(getattr(sales_quote, "name", None) or "")
	if not sq_ij_names:
		return {}

	# Idempotency: detect existing mappings recorded on previous IJ Detail rows via a marker.
	# We store the source SQ IJ name on the booking-side IJ as ``flags`` are non-persistent, so the
	# safest deduplication is to skip when an IJ Detail row already links to a booking-side IJ
	# whose parameter snapshot matches an SQ IJ exactly. For simplicity v1: re-runs append fresh
	# rows only when the existing detail rows are empty.
	existing_rows = list(getattr(booking_doc, ij_fieldname, None) or [])
	booking_already_has_ij_rows = any(
		(getattr(r, "internal_job", None) or "").strip() for r in existing_rows
	)

	# Preserve the SQ-side IJ Detail row values so we can mirror parameter columns (airline,
	# shipping_line, locations, customs_broker, …), not just the link/service_type/job_type.
	sq_detail_by_ij = _sq_internal_job_detail_rows_by_ij(sales_quote)

	mapping: dict[str, str] = {}
	for sq_ij_name in sq_ij_names:
		try:
			sq_ij = frappe.get_doc("Internal Job", sq_ij_name)
		except frappe.DoesNotExistError:
			continue
		new_ij_name = create_internal_job_for_parent_from_source(booking_dt, booking_nm, sq_ij)
		mapping[sq_ij_name] = new_ij_name
		if booking_already_has_ij_rows:
			continue
		sq_row = sq_detail_by_ij.get(sq_ij_name)
		if sq_row is not None:
			# Full mirror: every parameter the user set on the SQ row carries over to the booking.
			payload = _booking_ij_detail_payload(sq_row, new_ij_name)
		else:
			# Fall back to the IJ doc snapshot (e.g. SQ document not in memory): the IJ persistence
			# layer already pushed all relevant params from the row to the IJ when the SQ was saved.
			payload = {
				"internal_job": new_ij_name,
				"service_type": getattr(sq_ij, "service_type", None),
				"job_type": getattr(sq_ij, "job_type", None),
			}
			for fn in (
				"job_description",
				"location_type",
				"air_house_type",
				"airline",
				"freight_agent",
				"sea_house_type",
				"freight_agent_sea",
				"shipping_line",
				"transport_mode",
				"load_type",
				"direction",
				"origin_port",
				"destination_port",
				"transport_template",
				"vehicle_type",
				"container_type",
				"container_no",
				"location_from",
				"location_to",
				"pick_mode",
				"drop_mode",
				"customs_authority",
				"declaration_type",
				"customs_broker",
				"customs_charge_category",
			):
				val = getattr(sq_ij, fn, None)
				if val is not None:
					payload[fn] = val
		booking_doc.append(ij_fieldname, payload)

	if mapping and not booking_already_has_ij_rows:
		# Skip the IJ persistence sync on this save (we already materialised the IJ docs ourselves).
		booking_doc.flags.ignore_links = True
		booking_doc.flags.ignore_validate_update_after_submit = True
		booking_doc.save(ignore_permissions=True)
		booking_doc.reload()
	return mapping


def remap_internal_job_links_on_booking_charges(
	booking_doc: Any, mapping: dict[str, str]
) -> bool:
	"""Rewrite ``charge_scope`` / ``internal_job`` on booking charges using *mapping*.

	Charges whose ``internal_job`` is a SQ-side IJ name are updated to the booking-side IJ name and
	their ``charge_scope`` set to ``"Internal Job"``. Charges with no mapping entry are left alone.

	Returns True when any row changed (and the doc was saved).
	"""
	if not mapping or not booking_doc:
		return False
	rows = getattr(booking_doc, "charges", None) or []
	if not rows:
		return False

	try:
		meta = frappe.get_meta(booking_doc.doctype)
	except Exception:
		return False
	charges_df = meta.get_field("charges") if meta else None
	child_dt = (charges_df.options or "").strip() if charges_df else ""
	if not child_dt:
		return False
	try:
		child_meta = frappe.get_meta(child_dt)
	except Exception:
		return False
	if not child_meta.has_field("internal_job"):
		return False
	has_scope_field = bool(child_meta.has_field("charge_scope"))

	changed = False
	for row in rows:
		cur = (getattr(row, "internal_job", None) or "").strip()
		if not cur or cur not in mapping:
			continue
		new_name = mapping[cur]
		if new_name == cur:
			continue
		row.internal_job = new_name
		if has_scope_field:
			row.charge_scope = "Internal Job"
		changed = True

	if not changed:
		return False

	booking_doc.flags.ignore_links = True
	booking_doc.flags.ignore_validate_update_after_submit = True
	booking_doc.save(ignore_permissions=True)
	booking_doc.reload()
	return True


def propagate_one_off_internal_jobs_and_remap_charges(
	sales_quote: Any, booking_doc: Any
) -> dict[str, str]:
	"""Convenience: run both propagation and per-charge remap on the booking.

	Safe to call on any ``quotation_type`` — no-op when the quote owns no Internal Jobs.
	"""
	mapping = propagate_one_off_internal_jobs_to_booking(sales_quote, booking_doc)
	if mapping:
		remap_internal_job_links_on_booking_charges(booking_doc, mapping)
	return mapping


def stamp_scope_main_when_untagged(booking_doc: Any) -> None:
	"""Ensure every booking charge has a non-empty ``charge_scope`` after conversion.

	Quote charges tagged ``Internal Job`` are remapped to the booking-side IJ; quote charges left
	as ``Main`` may have been copied without a scope value (depending on the per-doctype mapper).
	This helper guarantees the booking child table is always populated, matching the desk default
	of ``"Main"`` for non-IJ charges.
	"""
	if not booking_doc:
		return
	rows = getattr(booking_doc, "charges", None) or []
	if not rows:
		return
	try:
		meta = frappe.get_meta(booking_doc.doctype)
	except Exception:
		return
	charges_df = meta.get_field("charges") if meta else None
	child_dt = (charges_df.options or "").strip() if charges_df else ""
	if not child_dt:
		return
	try:
		child_meta = frappe.get_meta(child_dt)
	except Exception:
		return
	if not child_meta.has_field("charge_scope"):
		return

	changed = False
	is_internal_booking = bool(cint(getattr(booking_doc, "is_internal_job", 0)))
	for row in rows:
		scope = (getattr(row, "charge_scope", None) or "").strip()
		if scope:
			continue
		row.charge_scope = "Internal Job" if is_internal_booking else "Main"
		changed = True
	if changed:
		booking_doc.flags.ignore_links = True
		booking_doc.flags.ignore_validate_update_after_submit = True
		booking_doc.save(ignore_permissions=True)
		booking_doc.reload()
