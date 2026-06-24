# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Sales Quote → Booking/Order Linked Service propagation.

A Sales Quote owns ``Linked Service`` documents via ``parent_booking_type = "Sales Quote"`` and
``parent_booking_name = <quote>``. When the quote is converted to a Sea/Air Booking, Transport
Order, or similar operational document, those **same** Linked Service records are transferred:

1. Each SQ-owned Linked Service is re-parented to the new booking
   (``parent_booking_type`` / ``parent_booking_name`` updated).
2. ``service_scope`` is stamped with the Sales Quote name so the quote's Services tab still shows
   the historical rows after conversion.
3. An ``Internal Job Detail`` row is appended on the booking pointing at the **same** Linked Service
   name (no duplicate documents).
4. Booking charge rows whose ``linked_service`` / ``internal_job`` link still points at the SQ-side
   name need no remapping — it is the same document — but ``charge_scope`` is normalised to
   ``"Linked"`` when applicable.

The same Linked Service record continues through Booking → Shipment → Job via existing
``internal_job_details`` rows and the persistence hooks on each operational parent.

The module name retains ``one_off`` for backward compatibility — propagation runs for any quote-type
that owns Linked Services.
"""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import cint

from logistics.utils.internal_job_detail_copy import internal_job_detail_row_as_dict
from logistics.utils.internal_job_persistence import (
	_internal_job_doctype_exists,
	internal_job_detail_fieldname,
)
from logistics.utils.linked_service_compat import (
	CHARGE_SCOPE_LINKED,
	CHARGE_SCOPE_MAIN,
	charge_row_linked_service_link,
	linked_service_doctype,
	linked_service_rows,
	normalize_charge_scope,
	row_linked_service_link,
	set_charge_row_linked_service_link,
	set_row_linked_service_link,
)


def is_one_off_sales_quote(sales_quote: Any) -> bool:
	"""Compatibility helper: True when the Sales Quote is One-off."""
	if not sales_quote:
		return False
	return (getattr(sales_quote, "quotation_type", None) or "").strip() == "One-off"


def _sq_owned_linked_services(sales_quote_name: str) -> list[str]:
	"""Names of Linked Service docs still parented to this Sales Quote (in creation order)."""
	if not sales_quote_name:
		return []
	return frappe.get_all(
		linked_service_doctype(),
		filters={
			"parent_booking_type": "Sales Quote",
			"parent_booking_name": sales_quote_name,
		},
		pluck="name",
		order_by="creation asc",
	)


def _sq_linked_service_detail_rows_by_ls(sales_quote: Any) -> dict[str, Any]:
	"""Map ``linked_service → Linked Service Detail`` row for rows on the quote."""
	out: dict[str, Any] = {}
	for row in linked_service_rows(sales_quote):
		ls = row_linked_service_link(row)
		if ls and ls not in out:
			out[ls] = row
	return out


def _transfer_linked_service_to_booking(
	ls_name: str, sq_name: str, booking_dt: str, booking_nm: str
) -> None:
	"""Re-parent *ls_name* onto the booking and stamp ``service_scope`` with the quote."""
	ls = frappe.get_doc(linked_service_doctype(), ls_name)
	ls.parent_booking_type = booking_dt
	ls.parent_booking_name = booking_nm
	if ls.meta.has_field("service_scope") and sq_name:
		ls.service_scope = sq_name
	ls.flags.ignore_permissions = True
	ls.flags.skip_internal_job_detail_sync = True
	ls.save(ignore_permissions=True)


def _booking_ij_detail_payload(sq_row: Any, ls_name: str) -> dict[str, Any]:
	"""Build an ``Internal Job Detail`` payload for the booking, mirroring *sq_row*.

	The payload copies every user-set parameter column from the SQ side and overrides:

	* ``internal_job`` / ``linked_service`` — same Linked Service document as on the quote.
	* ``job_no`` — cleared because the operational job has not been created yet.
	* ``actual_cost`` / ``actual_revenue`` — cleared so rollup starts from zero on the booking.
	"""
	payload = internal_job_detail_row_as_dict(sq_row) if sq_row else {}
	set_row_linked_service_link(payload, ls_name)
	for fn in ("job_no", "actual_cost", "actual_revenue"):
		if fn in payload:
			payload[fn] = None
	return payload


def propagate_one_off_internal_jobs_to_booking(
	sales_quote: Any, booking_doc: Any
) -> dict[str, str]:
	"""Transfer SQ-owned Linked Services onto *booking_doc* and append matching IJ Detail rows.

	Returns a mapping ``{sq_ls_name → booking_ls_name}`` (identity for transferred records) used by
	:func:`remap_internal_job_links_on_booking_charges` to normalise charge scope.

	Idempotent guards:

	* No-op when ``sales_quote`` or ``booking_doc`` is missing.
	* No-op when the quote owns no Linked Services still parented to it.
	* Skips Linked Services already referenced on an existing booking detail row.
	"""
	if not sales_quote or not booking_doc:
		return {}
	if not _internal_job_doctype_exists():
		return {}
	booking_dt = getattr(booking_doc, "doctype", None) or ""
	booking_nm = getattr(booking_doc, "name", None) or ""
	sq_name = getattr(sales_quote, "name", None) or ""
	if not booking_dt or not booking_nm or not sq_name:
		return {}

	ij_fieldname = internal_job_detail_fieldname(booking_dt)
	if not ij_fieldname:
		return {}
	meta = frappe.get_meta(booking_dt)
	if not meta.get_field(ij_fieldname):
		return {}

	ls_names = _sq_owned_linked_services(sq_name)
	if not ls_names:
		return {}

	existing_rows = list(getattr(booking_doc, ij_fieldname, None) or [])
	existing_ls = {
		row_linked_service_link(r) for r in existing_rows if row_linked_service_link(r)
	}
	sq_detail_by_ls = _sq_linked_service_detail_rows_by_ls(sales_quote)

	mapping: dict[str, str] = {}
	appended = False
	for ls_name in ls_names:
		mapping[ls_name] = ls_name
		if ls_name in existing_ls:
			if (
				frappe.db.get_value(linked_service_doctype(), ls_name, "parent_booking_name")
				!= booking_nm
			):
				_transfer_linked_service_to_booking(ls_name, sq_name, booking_dt, booking_nm)
			continue
		try:
			frappe.get_doc(linked_service_doctype(), ls_name)
		except frappe.DoesNotExistError:
			continue
		_transfer_linked_service_to_booking(ls_name, sq_name, booking_dt, booking_nm)
		sq_row = sq_detail_by_ls.get(ls_name)
		if sq_row is not None:
			payload = _booking_ij_detail_payload(sq_row, ls_name)
		else:
			ls_doc = frappe.get_doc(linked_service_doctype(), ls_name)
			payload = {
				"service_type": getattr(ls_doc, "service_type", None),
				"job_type": getattr(ls_doc, "job_type", None),
			}
			set_row_linked_service_link(payload, ls_name)
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
				val = getattr(ls_doc, fn, None)
				if val is not None:
					payload[fn] = val
		booking_doc.append(ij_fieldname, payload)
		appended = True

	if appended:
		booking_doc.flags.ignore_links = True
		booking_doc.flags.ignore_validate_update_after_submit = True
		booking_doc.save(ignore_permissions=True)
		booking_doc.reload()
	return mapping


def remap_internal_job_links_on_booking_charges(
	booking_doc: Any, mapping: dict[str, str]
) -> bool:
	"""Normalise ``charge_scope`` on booking charges that reference transferred Linked Services.

	Linked Service names are unchanged (``mapping`` is identity); this helper only ensures
	``charge_scope = "Linked"`` where a linked-service pointer is present.
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
	if not (
		child_meta.has_field("linked_service") or child_meta.has_field("internal_job")
	):
		return False
	has_scope_field = bool(child_meta.has_field("charge_scope"))

	changed = False
	for row in rows:
		cur = charge_row_linked_service_link(row)
		if not cur or cur not in mapping:
			continue
		if has_scope_field and normalize_charge_scope(getattr(row, "charge_scope", None)) != CHARGE_SCOPE_LINKED:
			row.charge_scope = CHARGE_SCOPE_LINKED
			changed = True
		if charge_row_linked_service_link(row) != cur:
			set_charge_row_linked_service_link(row, cur)
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
	"""Convenience: transfer Linked Services and normalise charge scope on the booking."""
	mapping = propagate_one_off_internal_jobs_to_booking(sales_quote, booking_doc)
	if mapping:
		remap_internal_job_links_on_booking_charges(booking_doc, mapping)
	return mapping


def stamp_scope_main_when_untagged(booking_doc: Any) -> None:
	"""Ensure every booking charge has a non-empty ``charge_scope`` after conversion."""
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
		row.charge_scope = CHARGE_SCOPE_LINKED if is_internal_booking else CHARGE_SCOPE_MAIN
		changed = True
	if changed:
		booking_doc.flags.ignore_links = True
		booking_doc.flags.ignore_validate_update_after_submit = True
		booking_doc.save(ignore_permissions=True)
		booking_doc.reload()
