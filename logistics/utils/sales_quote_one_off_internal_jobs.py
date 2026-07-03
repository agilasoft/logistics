# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Sales Quote → Booking/Order Linked Service propagation.

A Sales Quote owns ``Linked Service`` documents via ``parent_booking_type = "Sales Quote"`` and
``parent_booking_name = <quote>``. When the quote is converted to a Sea/Air Booking, Transport
Order, Declaration Order, or similar operational document, those Linked Service records are
transferred:

1. **Re-parent** (default for One-off full conversion): same ``LS-…`` document moves to
   the booking; charge ``linked_service`` links need no remapping.
2. **Clone** (Regular quotes, blanket call-offs, and Special Project bookings): a new ``LS-…`` is created on the
   booking from the quote-owned source; charge links are remapped via the returned mapping.

The same Linked Service record continues through Booking → Shipment → Job via existing
``internal_job_details`` rows and the persistence hooks on each operational parent.

The module name retains ``one_off`` for backward compatibility — propagation runs for any quote-type
that owns Linked Services.
"""

from __future__ import annotations

from typing import Any, Iterable

import frappe
from frappe import _
from frappe.utils import cint

from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal
from logistics.utils.internal_job_detail_copy import internal_job_detail_row_as_dict
from logistics.utils.internal_job_persistence import (
	_internal_job_doctype_exists,
	create_internal_job_for_parent_from_source,
	internal_job_detail_fieldname,
)
from logistics.utils.linked_service_compat import (
	CHARGE_SCOPE_LINKED,
	CHARGE_SCOPE_MAIN,
	charge_row_linked_service_link,
	is_linked_charge_scope,
	linked_service_doctype,
	linked_service_rows,
	linked_services_fieldname,
	normalize_charge_scope,
	row_linked_service_link,
	set_charge_row_linked_service_link,
	set_row_linked_service_link,
)
from logistics.utils.virtual_internal_job_details import uses_virtual_internal_job_details


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


def linked_service_names_from_charge_rows(
	charge_rows: Iterable[Any] | None,
	*,
	charge_row_names: list[str] | None = None,
) -> list[str]:
	"""Collect ``linked_service`` / ``internal_job`` names from charge rows (in stable order)."""
	allowed = {str(n).strip() for n in (charge_row_names or []) if n and str(n).strip()}
	names: list[str] = []
	seen: set[str] = set()
	for row in charge_rows or []:
		if allowed:
			rn = getattr(row, "name", None) if not isinstance(row, dict) else row.get("name")
			if not rn or str(rn).strip() not in allowed:
				continue
		ls = charge_row_linked_service_link(row)
		if not ls or ls in seen:
			continue
		seen.add(ls)
		names.append(ls)
	return names


def linked_service_names_from_quote_charges(
	sales_quote: Any,
	charge_row_names: list[str] | None = None,
) -> list[str]:
	"""Linked Service names referenced on Sales Quote charge rows."""
	return linked_service_names_from_charge_rows(
		getattr(sales_quote, "charges", None) or [],
		charge_row_names=charge_row_names,
	)


def _filter_linked_service_names(
	ls_names: list[str],
	*,
	exclude_service_types: list[str] | None = None,
) -> list[str]:
	if not ls_names or not exclude_service_types:
		return list(ls_names or [])
	out: list[str] = []
	for ls_name in ls_names:
		st = frappe.db.get_value(linked_service_doctype(), ls_name, "service_type")
		if st and any(
			sales_quote_charge_service_types_equal(st, ex) for ex in exclude_service_types
		):
			continue
		out.append(ls_name)
	return out


def _sq_linked_service_detail_rows_by_ls(sales_quote: Any) -> dict[str, Any]:
	"""Map ``linked_service → Linked Service Detail`` row for rows on the quote."""
	out: dict[str, Any] = {}
	for row in linked_service_rows(sales_quote):
		ls = row_linked_service_link(row)
		if ls and ls not in out:
			out[ls] = row
	return out


def _transfer_linked_service_to_booking(
	ls_name: str, booking_dt: str, booking_nm: str
) -> None:
	"""Re-parent *ls_name* onto the booking."""
	ls = frappe.get_doc(linked_service_doctype(), ls_name)
	ls.parent_booking_type = booking_dt
	ls.parent_booking_name = booking_nm
	ls.flags.ignore_permissions = True
	ls.flags.skip_internal_job_detail_sync = True
	ls.save(ignore_permissions=True)


def _clone_linked_service_to_booking(
	ls_name: str, booking_dt: str, booking_nm: str
) -> str:
	"""Create a new Linked Service on *booking* seeded from quote-owned *ls_name*."""
	ls_doc = frappe.get_doc(linked_service_doctype(), ls_name)
	return create_internal_job_for_parent_from_source(booking_dt, booking_nm, ls_doc)


def _booking_ij_detail_payload(sq_row: Any, ls_name: str) -> dict[str, Any]:
	"""Build an ``Internal Job Detail`` payload for the booking, mirroring *sq_row*."""
	payload = internal_job_detail_row_as_dict(sq_row) if sq_row else {}
	set_row_linked_service_link(payload, ls_name)
	for fn in ("job_no", "actual_cost", "actual_revenue"):
		if fn in payload:
			payload[fn] = None
	return payload


def _payload_from_linked_service_doc(ls_doc: Any, ls_name: str) -> dict[str, Any]:
	payload: dict[str, Any] = {
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
	return payload


def propagate_linked_services_to_booking(
	sales_quote: Any,
	booking_doc: Any,
	*,
	clone: bool = False,
	ls_names: list[str] | None = None,
	exclude_service_types: list[str] | None = None,
) -> dict[str, str]:
	"""Transfer or clone SQ-owned Linked Services onto *booking_doc*.

	Returns ``{source_ls_name → target_ls_name}`` for charge remapping.

	* ``clone=False`` (default): re-parent the same document (identity mapping).
	* ``clone=True``: create a booking-owned copy; quote retains the original.
	* ``ls_names``: restrict to these Linked Service names (``None`` = all still on the quote).
	* ``exclude_service_types``: drop LS whose ``service_type`` matches any listed label.
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

	ij_fieldname = linked_services_fieldname(booking_dt) or internal_job_detail_fieldname(booking_dt)
	if not ij_fieldname:
		return {}
	meta = frappe.get_meta(booking_dt)
	virtual_parent = uses_virtual_internal_job_details(booking_dt)
	persisted_grid = meta.get_field(ij_fieldname) if ij_fieldname else None
	if not virtual_parent and not persisted_grid:
		return {}

	candidate_names = list(ls_names) if ls_names is not None else _sq_owned_linked_services(sq_name)
	candidate_names = _filter_linked_service_names(
		candidate_names, exclude_service_types=exclude_service_types
	)
	if not candidate_names:
		return {}

	# Only process Linked Services still owned by the Sales Quote (clone source of truth).
	sq_owned = set(_sq_owned_linked_services(sq_name))
	ls_names_to_process = [n for n in candidate_names if n in sq_owned]
	if not ls_names_to_process:
		return {}

	existing_rows = list(linked_service_rows(booking_doc) or [])
	existing_ls = {
		row_linked_service_link(r) for r in existing_rows if row_linked_service_link(r)
	}

	def _row_value(row: Any, fieldname: str) -> Any:
		if isinstance(row, dict):
			return row.get(fieldname)
		return getattr(row, fieldname, None)

	existing_service_types: set[str] = set()
	for row in existing_rows:
		st = (_row_value(row, "service_type") or "").strip()
		if st:
			existing_service_types.add(st)
	if booking_nm:
		from logistics.logistics.doctype.linked_service.linked_service import (
			get_linked_services_for_booking,
		)

		for ls_doc in get_linked_services_for_booking(booking_dt, booking_nm):
			st = (getattr(ls_doc, "service_type", None) or "").strip()
			if st:
				existing_service_types.add(st)
	sq_detail_by_ls = _sq_linked_service_detail_rows_by_ls(sales_quote)

	mapping: dict[str, str] = {}
	appended = False
	for ls_name in ls_names_to_process:
		try:
			ls_doc = frappe.get_doc(linked_service_doctype(), ls_name)
		except frappe.DoesNotExistError:
			continue

		ls_st = (getattr(ls_doc, "service_type", None) or "").strip()
		if clone and ls_st and ls_st in existing_service_types:
			continue

		if clone:
			target_ls = _clone_linked_service_to_booking(ls_name, booking_dt, booking_nm)
		else:
			target_ls = ls_name
			if (
				target_ls in existing_ls
				and frappe.db.get_value(linked_service_doctype(), target_ls, "parent_booking_name")
				== booking_nm
			):
				mapping[ls_name] = target_ls
				continue
			_transfer_linked_service_to_booking(ls_name, booking_dt, booking_nm)

		mapping[ls_name] = target_ls
		if target_ls in existing_ls:
			continue

		sq_row = sq_detail_by_ls.get(ls_name)
		if persisted_grid and not getattr(persisted_grid, "is_virtual", 0):
			if sq_row is not None:
				payload = _booking_ij_detail_payload(sq_row, target_ls)
			else:
				payload = _payload_from_linked_service_doc(ls_doc, target_ls)
			booking_doc.append(ij_fieldname, payload)
			appended = True
		if ls_st:
			existing_service_types.add(ls_st)

	if appended:
		booking_doc.flags.ignore_links = True
		booking_doc.flags.ignore_validate_update_after_submit = True
		booking_doc.save(ignore_permissions=True)
		booking_doc.reload()
	return mapping


def propagate_one_off_internal_jobs_to_booking(
	sales_quote: Any, booking_doc: Any
) -> dict[str, str]:
	"""Backward-compatible alias: re-parent all quote-owned Linked Services."""
	return propagate_linked_services_to_booking(sales_quote, booking_doc, clone=False)


def remap_internal_job_links_on_booking_charges(
	booking_doc: Any, mapping: dict[str, str]
) -> bool:
	"""Normalise charge scope and apply *mapping* to ``linked_service`` on booking charges."""
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
		if not cur:
			continue
		if cur not in mapping:
			continue
		target = mapping[cur]
		if has_scope_field:
			scope = normalize_charge_scope(getattr(row, "charge_scope", None))
			if is_linked_charge_scope(scope) or target != cur:
				if scope != CHARGE_SCOPE_LINKED:
					row.charge_scope = CHARGE_SCOPE_LINKED
					changed = True
		if charge_row_linked_service_link(row) != target:
			set_charge_row_linked_service_link(row, target)
			changed = True

	if not changed:
		return False

	booking_doc.flags.ignore_links = True
	booking_doc.flags.ignore_validate_update_after_submit = True
	booking_doc.save(ignore_permissions=True)
	booking_doc.reload()
	return True


def propagate_linked_services_and_remap_charges(
	sales_quote: Any,
	booking_doc: Any,
	*,
	clone: bool = False,
	ls_names: list[str] | None = None,
	exclude_service_types: list[str] | None = None,
) -> dict[str, str]:
	"""Convenience: transfer/clone Linked Services and remap charge links on the booking."""
	mapping = propagate_linked_services_to_booking(
		sales_quote,
		booking_doc,
		clone=clone,
		ls_names=ls_names,
		exclude_service_types=exclude_service_types,
	)
	if mapping:
		remap_internal_job_links_on_booking_charges(booking_doc, mapping)
	return mapping


def propagate_one_off_internal_jobs_and_remap_charges(
	sales_quote: Any, booking_doc: Any
) -> dict[str, str]:
	"""Backward-compatible alias."""
	return propagate_linked_services_and_remap_charges(sales_quote, booking_doc, clone=False)


def apply_linked_services_from_sales_quote_on_fetch(
	sales_quote: Any,
	operational_doc: Any,
	*,
	selected_charge_row_names: list[str] | None = None,
) -> dict[str, str]:
	"""Clone or re-parent quote Linked Services when applying/fetching onto an existing job.

	Regular quotes keep their canonical ``LS-…`` records; subsidiary services are **cloned** onto
	the job so the quote remains the source of truth for later call-offs. One-off / Project quotes
	that still own Linked Services use **re-parent** (same ids).
	"""
	if not sales_quote or not operational_doc:
		return {}
	qt = (getattr(sales_quote, "quotation_type", None) or "").strip()
	use_clone = qt == "Regular"
	ls_names = linked_service_names_from_quote_charges(
		sales_quote, selected_charge_row_names
	) or None
	try:
		mapping = propagate_linked_services_and_remap_charges(
			sales_quote,
			operational_doc,
			clone=use_clone,
			ls_names=ls_names,
		)
		stamp_scope_main_when_untagged(operational_doc)
		return mapping
	except Exception:
		frappe.log_error(
			title="Sales Quote fetch — Linked Service propagation failed",
			message=(
				f"Sales Quote: {getattr(sales_quote, 'name', None)}; "
				f"Job: {getattr(operational_doc, 'doctype', None)} "
				f"{getattr(operational_doc, 'name', None)}\n{frappe.get_traceback()}"
			),
		)
		return {}


@frappe.whitelist()
def apply_sales_quote_linked_services_to_job(
	doctype: str,
	docname: str,
	sales_quote: str | None = None,
) -> dict[str, Any]:
	"""Desk/API: clone or re-parent quote Linked Services onto a saved operational document."""
	if not doctype or not docname:
		return {"success": False, "message": _("Document type and name are required.")}
	if not frappe.db.exists(doctype, docname):
		return {"success": False, "message": _("Document not found.")}
	doc = frappe.get_doc(doctype, docname)
	sq_name = (sales_quote or getattr(doc, "sales_quote", None) or "").strip()
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return {"success": False, "message": _("Sales Quote not found.")}
	sq = frappe.get_doc("Sales Quote", sq_name)
	mapping = apply_linked_services_from_sales_quote_on_fetch(sq, doc)
	return {
		"success": True,
		"linked_services_count": len(mapping),
		"mapping": mapping,
	}


def propagate_linked_services_for_special_project_booking(
	sp_doc: Any, booking_doc: Any
) -> dict[str, str]:
	"""Clone subsidiary quote-owned Linked Services onto a Special Project booking/order."""
	sq_name = (
		(getattr(sp_doc, "sales_quote", None) or getattr(booking_doc, "sales_quote", None) or "")
		.strip()
	)
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return {}
	sq = frappe.get_doc("Sales Quote", sq_name)

	from logistics.utils.charge_service_type import implied_service_type_for_doctype

	main_st = implied_service_type_for_doctype(getattr(booking_doc, "doctype", None) or "")
	exclude = [main_st] if main_st else None

	sq_owned = _sq_owned_linked_services(sq_name)
	ls_names = _filter_linked_service_names(sq_owned, exclude_service_types=exclude)

	for ls in linked_service_names_from_charge_rows(getattr(booking_doc, "charges", None) or []):
		if ls in sq_owned and ls not in ls_names:
			ls_names.append(ls)

	if not ls_names:
		return {}

	try:
		mapping = propagate_linked_services_and_remap_charges(
			sq, booking_doc, clone=True, ls_names=ls_names
		)
		stamp_scope_main_when_untagged(booking_doc)
		return mapping
	except Exception:
		frappe.log_error(
			title="Special Project Linked Service propagation failed",
			message=(
				f"Special Project: {getattr(sp_doc, 'name', None)}; "
				f"Booking: {getattr(booking_doc, 'doctype', None)} "
				f"{getattr(booking_doc, 'name', None)}\n{frappe.get_traceback()}"
			),
		)
		return {}


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
