# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Persistence facade for the `internal_job_details` child table on operational bookings.

The booking's child table stores only a pointer (`internal_job` Link). The source of truth for
service parameters (`origin_port`, `airline`, `transport_mode`, customs fields, etc.) is the
top-level `Internal Job` document.

Two synchronisations run from the booking's lifecycle hooks:

* `before_save`: for each row in `internal_job_details`, ensure a backing `Internal Job` exists and
  the row points at it. Any parameter values edited on the row (via the form, since they render as
  `fetch_from` views) are pushed back onto the Internal Job so the form remains the natural edit UX.

* `on_trash`: delete all `Internal Job` documents owned by the booking via the
  `parent_booking_type` / `parent_booking_name` back-link.

Removed rows (rows present in the previous save but absent now) cause their backing Internal Job to
be deleted as well.

A third sync runs from the `Internal Job` side (`on_update` hook): whenever an IJ document is saved
directly (e.g. via the Internal Job form or scripted update), the new parameter values are pushed
into every `Internal Job Detail` row that links to it. This keeps the DB-level child-table snapshot
in sync with the source of truth so reports / API consumers reading the child rows directly see
fresh values without waiting for the next booking save.
"""

from __future__ import annotations

from typing import Any, Iterable

import frappe

from logistics.utils.charge_service_type import default_job_type_for_internal_job_service_type
from logistics.utils.linked_service_compat import (
	CHARGE_SCOPE_LINKED,
	CHARGE_SCOPE_MAIN,
	is_linked_charge_scope,
	linked_service_detail_doctype,
	linked_service_doctype,
	linked_service_doctype_exists,
	linked_service_record_exists,
	linked_service_rows,
	linked_services_fieldname,
	normalize_charge_scope,
	row_linked_service_link,
	set_row_linked_service_link,
)
from logistics.utils.sales_quote_charge_parameters import SALES_QUOTE_CHARGE_PARAMETER_FIELDS
from logistics.utils.virtual_internal_job_details import (
	VIRTUAL_INTERNAL_JOB_DETAILS_PARENTS,
	uses_virtual_internal_job_details,
)


_VIRTUAL_LINKED_SERVICE_PARENTS = frozenset(
	{"Change Request", "MICE Project", "Docket", "Time Sensitive Case"}
) | VIRTUAL_INTERNAL_JOB_DETAILS_PARENTS


# Operational booking doctypes that carry an Internal Job Detail child table, mapped to the
# fieldname on each parent (most use `internal_job_details`; Exhibit uses `internal_jobs`).
#
# ``Sales Quote`` owns Linked Service documents (``IJ-…``) that bookings/orders reuse via
# ``Linked Service Usage`` (see ``sales_quote_one_off_internal_jobs``).
INTERNAL_JOB_DETAIL_PARENTS: dict[str, str] = {
	"Sea Booking": "linked_services",
	"Air Booking": "linked_services",
	"Sea Shipment": "linked_services",
	"Air Shipment": "linked_services",
	"Transport Order": "linked_services",
	"Transport Job": "linked_services",
	"Declaration": "internal_job_details",
	"Declaration Order": "internal_job_details",
	"Warehouse Job": "internal_job_details",
	"Inbound Order": "internal_job_details",
	"Release Order": "internal_job_details",
	"Cross-Docking Order": "internal_job_details",
	"General Job": "internal_job_details",
	"Project Job": "internal_job_details",
	"MICE Job": "internal_job_details",
	"Exhibit Job": "internal_job_details",
	"MICE Project": "linked_services",
	"Docket": "linked_services",
	"Exhibit": "internal_jobs",
	"Sales Quote": "linked_services",
	"Change Request": "linked_services",
	"Time Sensitive Case": "linked_services",
}


def _should_run_internal_job_sync_for_parent(parent_doc: Any) -> bool:
	"""Listed operational parents participate in Linked Service persistence on save.
	"""
	return True


def internal_job_detail_fieldname(parent_doctype: str) -> str | None:
	"""Fieldname of the Linked Service Detail child table on *parent_doctype*, or ``None``."""
	fn = linked_services_fieldname(parent_doctype)
	if fn:
		return fn
	return INTERNAL_JOB_DETAIL_PARENTS.get(parent_doctype)


def internal_job_detail_rows_for_parent(parent_doc: Any) -> list[Any]:
	"""Linked Service rows for *parent_doc*, honouring unsaved desk grid overrides when present.

	An empty override list is treated as no override (virtual Linked Services grids often
	serialize as ``[]`` from the desk; honouring that would wipe rows on persist/sync).

	Desk overrides are scoped by parent doctype so a Docket create payload cannot leak into
	Transport Order / Sea Booking insert sync (which would reparent Docket Linked Services).
	"""
	fieldname = internal_job_detail_fieldname(getattr(parent_doc, "doctype", None) or "")
	parent_doctype = getattr(parent_doc, "doctype", None) or ""
	if parent_doctype == "Docket":
		ov = getattr(frappe.local, "_logistics_dk_ij_client_rows", None)
		if ov is not None and len(ov) > 0:
			return list(ov)
	else:
		ov = getattr(frappe.local, "_logistics_ij_client_rows", None)
		if ov is not None and len(ov) > 0:
			return list(ov)
	if parent_doctype in VIRTUAL_INTERNAL_JOB_DETAILS_PARENTS:
		parent_name = (getattr(parent_doc, "name", None) or "").strip()
		if parent_name and not getattr(parent_doc, "__islocal", False):
			from logistics.logistics.doctype.linked_service.linked_service import (
				get_linked_services_for_booking,
			)

			return list(get_linked_services_for_booking(parent_doctype, parent_name))
		return []
	if not fieldname:
		return []
	if fieldname in ("linked_services", "internal_jobs"):
		return linked_service_rows(parent_doc)
	return list(getattr(parent_doc, fieldname, None) or [])


def sync_internal_job_doc_job_link(row: Any, job_type: str, job_no: str) -> None:
	"""Record Usage for the satellite job; Linked Service no longer stores job_type/job_no."""
	ij_name = _linked_service_name_from_row(row) if row is not None else ""
	jn = _norm(job_no)
	jt = _norm(job_type)
	if not ij_name or not jn:
		return
	if not linked_service_record_exists(ij_name):
		return
	try:
		from logistics.utils.linked_service_usage import (
			USAGE_ROLE_SATELLITE_JOB,
			record_linked_service_usage,
		)

		record_linked_service_usage(
			ij_name,
			jt,
			jn,
			usage_role=USAGE_ROLE_SATELLITE_JOB,
		)
	except Exception:
		frappe.log_error(
			title="Linked Service Usage job link failed",
			message=frappe.get_traceback(),
		)


# Parameter fields stored on `Internal Job` that mirror `Internal Job Detail` and `Sales Quote Charge`.
# `charge_group` is excluded - it's a Sales Quote Charge concept only.
# job_type / job_no / job_description were removed from Linked Service (tracked via Usage).
_PARAM_FIELDS: tuple[str, ...] = tuple(
	fn for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS if fn != "charge_group"
) + (
	"service_type",
	"location_type",
)


def _row_value(row: Any, fieldname: str) -> Any:
	if row is None:
		return None
	if isinstance(row, dict):
		return row.get(fieldname)
	return getattr(row, fieldname, None)


def _norm(val: Any) -> str:
	if val is None:
		return ""
	return str(val).strip()


def _internal_job_doctype_exists() -> bool:
	"""True when Linked Service (or legacy Internal Job) doctype is present."""
	return linked_service_doctype_exists()


def _ls_meta():
	return frappe.get_meta(linked_service_doctype())


def _copy_row_params_to_internal_job(row: Any, ij_doc: Any) -> bool:
	"""Copy parameter values from a Linked Service Detail row onto a Linked Service document.

	Returns True when any field changed.
	"""
	meta = _ls_meta()
	changed = False
	for fn in _PARAM_FIELDS:
		if not meta.has_field(fn):
			continue
		new_val = _row_value(row, fn)
		if new_val is None:
			continue
		cur_val = getattr(ij_doc, fn, None)
		if _norm(cur_val) != _norm(new_val):
			setattr(ij_doc, fn, new_val)
			changed = True
	return changed


def _ensure_job_type_from_service(ij_doc: Any) -> None:
	"""No-op: Linked Service no longer stores ``job_type`` (Usage table tracks jobs)."""
	return


def _create_internal_job_from_row(
	parent_doc: Any, row: Any, *, preferred_name: str | None = None
) -> str:
	"""Create a new `Internal Job` document seeded from an `Internal Job Detail` row's values."""
	ij = frappe.new_doc(linked_service_doctype())
	ij.parent_booking_type = parent_doc.doctype
	ij.parent_booking_name = parent_doc.name or ""
	_copy_row_params_to_internal_job(row, ij)
	_ensure_job_type_from_service(ij)
	ij.flags.ignore_permissions = True
	preferred = _norm(preferred_name)
	if preferred and not linked_service_record_exists(preferred):
		ij.insert(ignore_permissions=True, set_name=preferred)
	else:
		ij.insert(ignore_permissions=True)
	return ij.name


def create_internal_job_for_parent_from_source(
	parent_doctype: str, parent_name: str, source: Any
) -> str:
	"""Public API: create a fresh ``Internal Job`` doc parented to (parent_doctype, parent_name).

	Parameter values are copied from *source* (an ``Internal Job`` document, ``Internal Job Detail``
	row, or any row-like with the same attribute names). Used by the Sales Quote (One-off) →
	Booking conversion flow to materialise a new IJ on the booking that mirrors the SQ-owned IJ.
	"""
	ij = frappe.new_doc(linked_service_doctype())
	ij.parent_booking_type = parent_doctype
	ij.parent_booking_name = parent_name or ""
	_copy_row_params_to_internal_job(source, ij)
	_ensure_job_type_from_service(ij)
	ij.flags.ignore_permissions = True
	ij.insert(ignore_permissions=True)
	return ij.name


def _update_internal_job_from_row(row: Any, ij_name: str) -> None:
	"""Apply edits from an `Internal Job Detail` row onto the linked `Internal Job` document."""
	if not ij_name or not linked_service_record_exists(ij_name):
		return
	ij = frappe.get_doc(linked_service_doctype(), ij_name)
	changed = _copy_row_params_to_internal_job(row, ij)
	_ensure_job_type_from_service(ij)
	if not changed:
		return
	ij.flags.ignore_permissions = True
	# Skip the reverse IJ -> child-row propagation: we are already writing the same
	# values that the child row carries; doing it again is wasteful (and on an in-progress
	# booking save the parent isn't even persisted yet).
	ij.flags.skip_internal_job_detail_sync = True
	ij.save(ignore_permissions=True)


def _linked_service_names_from_db(parent_doctype: str, parent_name: str) -> set[str]:
	"""Linked Service document names parented to a booking/quote."""
	if not parent_name or not _internal_job_doctype_exists():
		return set()
	return set(
		frappe.get_all(
			linked_service_doctype(),
			filters={
				"parent_booking_type": parent_doctype,
				"parent_booking_name": parent_name,
			},
			pluck="name",
		)
		or []
	)


def _linked_service_names_visible_on_parent(parent_doctype: str, parent_name: str) -> set[str]:
	"""Owned Linked Services plus Usage-linked names (desk grid source of truth)."""
	names = _linked_service_names_from_db(parent_doctype, parent_name)
	try:
		from logistics.utils.linked_service_usage import get_linked_services_used_by

		names |= {n for n in (get_linked_services_used_by(parent_doctype, parent_name) or []) if n}
	except Exception:
		pass
	return names


def ensure_linked_service_rows_materialized(parent_doc: Any) -> None:
	"""Ensure Linked Service documents exist for *parent_doc* before booking back-link persist.

	Virtual-grid parents (Docket, MICE Project, …) store legs as top-level Linked Service
	docs, not child-table rows. Create Booking/Order can see desk ``form_rows`` while the
	server-side virtual view is still empty (propagation never ran). This heals that gap:

	1. No-op when Linked Service docs already exist for the parent.
	2. Docket with ``sales_quote`` → clone from the quote via ``_propagate_linked_services_to_docket``.
	3. Otherwise create/update from current detail rows (honours desk client-row overrides).
	4. Drop the virtual ``linked_services`` cache so the next read rebuilds from DB.
	"""
	if not parent_doc:
		return
	parent_doctype = getattr(parent_doc, "doctype", None) or ""
	parent_name = _norm(getattr(parent_doc, "name", None))
	if not parent_doctype or not parent_name:
		return
	if parent_doctype not in _VIRTUAL_LINKED_SERVICE_PARENTS:
		return
	if _linked_service_names_from_db(parent_doctype, parent_name):
		return

	if parent_doctype == "Docket":
		sq_name = _norm(getattr(parent_doc, "sales_quote", None))
		if sq_name and frappe.db.exists("Sales Quote", sq_name):
			from logistics.pricing_center.doctype.sales_quote.sales_quote import (
				_propagate_linked_services_to_docket,
			)

			sq_doc = frappe.get_doc("Sales Quote", sq_name)
			_propagate_linked_services_to_docket(sq_doc, parent_doc)

	if not _linked_service_names_from_db(parent_doctype, parent_name):
		_ensure_internal_job_docs_for_detail_rows(parent_doc)

	if hasattr(parent_doc, "_drop_virtual_linked_services_rows"):
		parent_doc._drop_virtual_linked_services_rows()


def _linked_service_name_from_row(row: Any) -> str:
	"""Resolve the canonical Linked Service name from a detail row or LS document."""
	name = row_linked_service_link(row)
	if name:
		return name
	if getattr(row, "doctype", None) == linked_service_doctype():
		return _norm(getattr(row, "name", None))
	return ""


def _currently_linked_internal_jobs(parent_doc: Any, fieldname: str) -> set[str]:
	return {
		name
		for r in internal_job_detail_rows_for_parent(parent_doc)
		for name in [_linked_service_name_from_row(r)]
		if name
	}


def _previously_linked_internal_jobs(parent_doc: Any, fieldname: str) -> set[str]:
	"""Internal Job names that were linked to this booking on its last persisted state."""
	if parent_doc.doctype in _VIRTUAL_LINKED_SERVICE_PARENTS and parent_doc.name:
		return _linked_service_names_visible_on_parent(parent_doc.doctype, parent_doc.name)
	prev = parent_doc.get_doc_before_save() if hasattr(parent_doc, "get_doc_before_save") else None
	if prev is None:
		return set()
	return {
		row_linked_service_link(r)
		for r in (getattr(prev, fieldname, None) or [])
		if row_linked_service_link(r)
	}


def _linked_service_strictly_parented_to(ij_name: str, parent_doc: Any) -> bool:
	"""True when *ij_name* is parented to *parent_doc* (blank parent does not count)."""
	if not ij_name or not parent_doc:
		return False
	row = frappe.db.get_value(
		linked_service_doctype(),
		ij_name,
		["parent_booking_type", "parent_booking_name"],
		as_dict=True,
	)
	if not row:
		return False
	return _norm(row.get("parent_booking_type")) == _norm(
		getattr(parent_doc, "doctype", None)
	) and _norm(row.get("parent_booking_name")) == _norm(getattr(parent_doc, "name", None))


def _delete_orphan_internal_jobs_from_sets(
	prev: set[str], cur: set[str], parent_doc: Any | None = None
) -> None:
	for ij_name in prev - cur:
		if not ij_name or not linked_service_record_exists(ij_name):
			continue
		try:
			# Shared / quote-owned IJ-…: drop Usage for this consumer only.
			if parent_doc and not _linked_service_strictly_parented_to(ij_name, parent_doc):
				from logistics.utils.linked_service_usage import clear_linked_service_usage

				clear_linked_service_usage(
					parent_doc.doctype,
					parent_doc.name or "",
					linked_service=ij_name,
				)
				continue
			frappe.delete_doc(linked_service_doctype(), ij_name, ignore_permissions=True, force=True)
		except Exception:
			frappe.log_error(
				title="Internal Job orphan cleanup failed",
				message=frappe.get_traceback(),
			)


def _linked_service_owned_by_parent_doc(ij_name: str, parent_doc: Any) -> bool:
	"""True when *ij_name* is already parented to *parent_doc* (or has no parent yet)."""
	if not ij_name or not parent_doc:
		return False
	row = frappe.db.get_value(
		linked_service_doctype(),
		ij_name,
		["parent_booking_type", "parent_booking_name"],
		as_dict=True,
	)
	if not row:
		return False
	existing_dt = _norm(row.get("parent_booking_type"))
	existing_name = _norm(row.get("parent_booking_name"))
	# Unowned / blank parent can be claimed by the current parent.
	if not existing_dt and not existing_name:
		return True
	return existing_dt == _norm(getattr(parent_doc, "doctype", None)) and existing_name == _norm(
		getattr(parent_doc, "name", None)
	)


def _backfill_internal_job_parent_link(ij_doc: Any, parent_doc: Any) -> bool:
	"""Ensure ``parent_booking_type`` / ``parent_booking_name`` on an IJ when the parent has a name."""
	parent_name = _norm(getattr(parent_doc, "name", None))
	if not parent_name:
		return False
	# Never steal a Linked Service already owned by another booking/quote.
	existing_dt = _norm(getattr(ij_doc, "parent_booking_type", None))
	existing_name = _norm(getattr(ij_doc, "parent_booking_name", None))
	if existing_dt and existing_name and (
		existing_dt != _norm(getattr(parent_doc, "doctype", None))
		or existing_name != parent_name
	):
		return False
	changed = False
	parent_dt = getattr(parent_doc, "doctype", None) or ""
	if parent_dt and existing_dt != parent_dt:
		ij_doc.parent_booking_type = parent_dt
		changed = True
	if existing_name != parent_name:
		ij_doc.parent_booking_name = parent_name
		changed = True
	return changed


def _ensure_internal_job_docs_for_detail_rows(parent_doc: Any) -> dict[str, str]:
	"""Create or update backing ``Internal Job`` docs for every IJ-detail row on *parent_doc*.

	Returns a map ``{stale_ij_name: new_ij_name}`` for detail rows that carried a link to a
	non-existent Internal Job and were re-pointed at a freshly materialised document.

	Does **not** delete Internal Jobs whose detail row was removed (see ``before_save`` sync).
	Skips Linked Services owned by a different parent (e.g. Docket LS leaked into TRO insert).
	"""
	remap: dict[str, str] = {}
	if not parent_doc:
		return remap
	fieldname = internal_job_detail_fieldname(parent_doc.doctype)
	if not fieldname:
		return remap
	if not _internal_job_doctype_exists():
		return remap
	if not _should_run_internal_job_sync_for_parent(parent_doc):
		return remap
	meta = frappe.get_meta(parent_doc.doctype)
	if not meta.get_field(fieldname) and parent_doc.doctype not in VIRTUAL_INTERNAL_JOB_DETAILS_PARENTS:
		return remap

	for row in internal_job_detail_rows_for_parent(parent_doc):
		ij_name = _linked_service_name_from_row(row)
		if ij_name and linked_service_record_exists(ij_name):
			if not _linked_service_owned_by_parent_doc(ij_name, parent_doc):
				# Foreign Linked Service (wrong parent) — do not update or reparent.
				continue
			_update_internal_job_from_row(row, ij_name)
			if _norm(getattr(parent_doc, "name", None)):
				ij = frappe.get_doc(linked_service_doctype(), ij_name)
				if _backfill_internal_job_parent_link(ij, parent_doc):
					ij.flags.ignore_permissions = True
					ij.flags.skip_internal_job_detail_sync = True
					ij.save(ignore_permissions=True)
			continue
		stale_name = ij_name or None
		new_name = _create_internal_job_from_row(
			parent_doc, row, preferred_name=stale_name
		)
		if stale_name and stale_name != new_name:
			remap[stale_name] = new_name
		set_row_linked_service_link(row, new_name)
	return remap

def _charges_child_meta(parent_doc: Any) -> tuple[Any | None, Any | None]:
	"""Return (charges_table_field, child_doctype_meta) when the parent has a charges table."""
	if not parent_doc:
		return None, None
	try:
		meta = frappe.get_meta(parent_doc.doctype)
	except Exception:
		return None, None
	charges_df = meta.get_field("charges") if meta else None
	if not charges_df:
		return None, None
	child_dt = (charges_df.options or "").strip()
	if not child_dt:
		return charges_df, None
	try:
		return charges_df, frappe.get_meta(child_dt)
	except Exception:
		return charges_df, None


def _internal_job_by_service_type(parent_doc: Any, fieldname: str) -> dict[str, str]:
	"""Map normalised ``service_type`` on IJ-detail rows to their linked Internal Job name."""
	out: dict[str, str] = {}
	for row in internal_job_detail_rows_for_parent(parent_doc):
		st = _norm(_row_value(row, "service_type"))
		ij = _linked_service_name_from_row(row)
		if st and ij:
			out[st] = ij
	return out


def reconcile_orphan_charge_internal_job_links(
	parent_doc: Any, ij_remap: dict[str, str] | None = None
) -> None:
	"""Fix charge rows whose ``internal_job`` link does not resolve to a saved Internal Job.

	Uses *ij_remap* (stale name → materialised name) first, then matches by ``service_type`` on
	the charge row against the parent's Internal Job Detail grid. Remaining orphans are reset to
	``charge_scope = "Main"`` with a cleared ``internal_job`` link so Frappe link validation can
	proceed.
	"""
	if not parent_doc:
		return
	_, child_meta = _charges_child_meta(parent_doc)
	if not child_meta or not (
		child_meta.has_field("linked_service") or child_meta.has_field("internal_job")
	):
		return
	has_scope_field = bool(child_meta.has_field("charge_scope"))
	rows = getattr(parent_doc, "charges", None) or []
	if not rows:
		return

	fieldname = internal_job_detail_fieldname(parent_doc.doctype)
	ij_by_service = _internal_job_by_service_type(parent_doc, fieldname) if fieldname else {}
	remap = ij_remap or {}

	for row in rows:
		cur = row_linked_service_link(row)
		scope = (
			normalize_charge_scope(_row_value(row, "charge_scope"))
			if has_scope_field
			else CHARGE_SCOPE_MAIN
		)
		if not cur:
			if has_scope_field and is_linked_charge_scope(scope):
				st = _norm(_row_value(row, "service_type"))
				replacement = ij_by_service.get(st) if st else None
				if replacement and linked_service_record_exists(replacement):
					set_row_linked_service_link(row, replacement)
					if isinstance(row, dict):
						row["charge_scope"] = CHARGE_SCOPE_LINKED
					else:
						setattr(row, "charge_scope", CHARGE_SCOPE_LINKED)
				else:
					set_row_linked_service_link(row, None)
					if isinstance(row, dict):
						row["charge_scope"] = CHARGE_SCOPE_MAIN
					else:
						setattr(row, "charge_scope", CHARGE_SCOPE_MAIN)
			continue
		if linked_service_record_exists(cur):
			continue
		replacement = remap.get(cur)
		if not replacement:
			st = _norm(_row_value(row, "service_type"))
			replacement = ij_by_service.get(st) if st else None
		if replacement and linked_service_record_exists(replacement):
			set_row_linked_service_link(row, replacement)
			if has_scope_field:
				if isinstance(row, dict):
					row["charge_scope"] = "Linked"
				else:
					setattr(row, "charge_scope", "Linked")
			continue
		set_row_linked_service_link(row, None)
		if has_scope_field:
			if isinstance(row, dict):
				row["charge_scope"] = "Main"
			else:
				setattr(row, "charge_scope", "Main")


def prepare_internal_jobs_before_link_validation(parent_doc: Any) -> None:
	"""Materialise missing Internal Jobs and heal charge links before Frappe ``_validate_links``.

	Frappe validates Link fields before ``before_save`` hooks run. Operational parents that carry
	an ``internal_job_details`` grid may reference Internal Job names that have not been inserted
	yet (or were deleted while charge rows still point at them). This pre-flight keeps desk saves
	from failing with ``LinkValidationError``.
	"""
	if not parent_doc or getattr(parent_doc.flags, "ignore_links", False):
		return
	if parent_doc.doctype not in INTERNAL_JOB_DETAIL_PARENTS:
		return
	remap = _ensure_internal_job_docs_for_detail_rows(parent_doc)
	reconcile_orphan_charge_internal_job_links(parent_doc, remap)


def _delete_orphan_internal_jobs(parent_doc: Any, fieldname: str) -> None:
	"""Delete Internal Job docs that were previously linked but are no longer in the table."""
	prev = _previously_linked_internal_jobs(parent_doc, fieldname)
	cur = _currently_linked_internal_jobs(parent_doc, fieldname)
	_delete_orphan_internal_jobs_from_sets(prev, cur, parent_doc=parent_doc)


def sync_internal_job_details_to_internal_jobs(doc: Any, *_method) -> None:
	"""`before_save` hook: keep Internal Job records in sync with the booking's IJ-detail child rows.

	* New row with blank `internal_job` -> create an Internal Job and link the row to it.
	* Existing row with `internal_job` set -> push parameter edits back to the Internal Job.
	* Row removed since last save -> delete the orphaned Internal Job.

	Defensive against running before model sync or before the `Internal Job` doctype is migrated.
	"""
	if not doc:
		return
	fieldname = internal_job_detail_fieldname(doc.doctype)
	if not fieldname:
		return
	prev_orphans: set[str] | None = None
	if doc.doctype in _VIRTUAL_LINKED_SERVICE_PARENTS and doc.name:
		prev_orphans = _linked_service_names_visible_on_parent(doc.doctype, doc.name)
	_ensure_internal_job_docs_for_detail_rows(doc)
	if prev_orphans is not None:
		cur = _currently_linked_internal_jobs(doc, fieldname)
		_delete_orphan_internal_jobs_from_sets(prev_orphans, cur, parent_doc=doc)
	else:
		_delete_orphan_internal_jobs(doc, fieldname)


def delete_internal_jobs_for_booking(doc: Any, *_method) -> None:
	"""`on_trash` hook: delete booking-owned Linked Services; clear Usage tags only for shared IJs."""
	if not doc or doc.doctype not in INTERNAL_JOB_DETAIL_PARENTS:
		return
	if not _internal_job_doctype_exists():
		return

	# Shared IJ-… (quote-owned): drop Usage rows for this consumer only.
	try:
		from logistics.utils.linked_service_usage import clear_linked_service_usage

		clear_linked_service_usage(doc.doctype, doc.name or "")
	except Exception:
		frappe.log_error(
			title="Linked Service Usage trash cleanup failed",
			message=frappe.get_traceback(),
		)

	# Legacy / booking-owned Linked Services: still delete on parent trash.
	names = frappe.get_all(
		linked_service_doctype(),
		filters={
			"parent_booking_type": doc.doctype,
			"parent_booking_name": doc.name or "",
		},
		pluck="name",
	)
	for n in names:
		try:
			frappe.delete_doc(linked_service_doctype(), n, ignore_permissions=True, force=True)
		except Exception:
			frappe.log_error(
				title="Internal Job parent-trash cleanup failed",
				message=frappe.get_traceback(),
			)


def get_internal_jobs_for_booking(parent_doc: Any) -> list[Any]:
	"""Return Internal Job documents linked to a booking (used by the per-scope charge extractor)."""
	if not parent_doc or not _internal_job_doctype_exists():
		return []
	fieldname = internal_job_detail_fieldname(getattr(parent_doc, "doctype", None) or "")
	rows = internal_job_detail_rows_for_parent(parent_doc) if fieldname else []
	names: list[str] = []
	for r in rows:
		n = row_linked_service_link(r)
		if n and n not in names:
			names.append(n)
	if not names:
		names = frappe.get_all(
			linked_service_doctype(),
			filters={
				"parent_booking_type": parent_doc.doctype,
				"parent_booking_name": parent_doc.name or "",
			},
			pluck="name",
			order_by="creation asc",
		)
	out: list[Any] = []
	for n in names:
		if linked_service_record_exists(n):
			out.append(frappe.get_doc(linked_service_doctype(), n))
	return out


def iter_internal_job_detail_parent_doctypes() -> Iterable[str]:
	"""All operational booking doctypes that carry an Internal Job Detail child table."""
	return INTERNAL_JOB_DETAIL_PARENTS.keys()


def resolve_internal_job_for_internal_job_booking(doc: Any) -> str | None:
	"""Return the linked ``Internal Job`` DocType name for a booking flagged as a Linked service.

	The link is resolved via the booking's parent main service: each main carries an
	``internal_job_details`` row with ``job_type`` / ``job_no`` matching this booking and a
	``linked_service`` / ``internal_job`` field pointing at the canonical record. As a fallback
	the lookup falls through to the Linked Service doctype directly so it works on partially-loaded
	docs (e.g. freshly created from a Create > Booking/Order dialog before the parent has been
	reloaded).
	"""
	from logistics.utils.service_role_rules import (
		get_main_service_name,
		get_main_service_type,
		get_service_role,
		SERVICE_ROLE_LINKED,
	)

	if not doc:
		return None
	if get_service_role(doc) != SERVICE_ROLE_LINKED:
		return None
	doctype = getattr(doc, "doctype", None)
	name = getattr(doc, "name", None)
	if not doctype or not name:
		return None
	main_job_type = get_main_service_type(doc)
	main_job = get_main_service_name(doc)
	if main_job_type and main_job:
		fieldname = internal_job_detail_fieldname(main_job_type)
		if fieldname:
			columns = _internal_job_detail_table_columns()
			link_fields = [f for f in ("linked_service", "internal_job") if f in columns] or [
				"internal_job"
			]
			try:
				rows = frappe.get_all(
					linked_service_detail_doctype(),
					filters={
						"parent": main_job,
						"parenttype": main_job_type,
						"parentfield": fieldname,
						"job_type": doctype,
						"job_no": name,
					},
					fields=link_fields,
					limit=1,
				)
			except Exception:
				rows = []
			for r in rows:
				ij = row_linked_service_link(r)
				if ij:
					return ij
	if not _internal_job_doctype_exists():
		return None
	# Fallback: Usage table (Linked Service no longer stores job_type / job_no).
	try:
		from logistics.utils.linked_service_usage import get_linked_services_used_by

		for ls_name in get_linked_services_used_by(doctype, name):
			if not linked_service_record_exists(ls_name):
				continue
			parent_type = frappe.db.get_value(
				linked_service_doctype(), ls_name, "parent_booking_type"
			)
			parent_name = frappe.db.get_value(
				linked_service_doctype(), ls_name, "parent_booking_name"
			)
			if main_job_type and main_job:
				if _norm(parent_type) != _norm(main_job_type):
					continue
				if _norm(parent_name) != _norm(main_job):
					continue
			return ls_name
	except Exception:
		pass
	return None


def _internal_job_detail_table_columns() -> set[str]:
	"""Columns present on `tabInternal Job Detail` (for safe DB writes)."""
	try:
		return set(frappe.db.get_table_columns(linked_service_detail_doctype()) or [])
	except Exception:
		return set()


def sync_internal_job_to_detail_rows(ij_doc: Any, *_method) -> None:
	"""`on_update` hook on `Internal Job`: push parameter values into every linked detail row.

	Detail rows render their parameter columns via ``fetch_from``, but those values are also
	persisted as a snapshot on ``tabInternal Job Detail``. Reports / API consumers that read the
	child table directly need that snapshot kept in sync with the IJ. We write at the DB level
	(``frappe.db.set_value``) without ``update_modified`` so the parent booking's modified stamp
	isn't bumped by an IJ edit.

	Recursion guard: ``_update_internal_job_from_row`` sets ``flags.skip_internal_job_detail_sync``
	on the IJ doc before saving from inside the booking's own ``before_save``, so this hook is a
	no-op for the booking -> IJ leg.
	"""
	if not ij_doc:
		return
	if getattr(getattr(ij_doc, "flags", None), "skip_internal_job_detail_sync", False):
		return
	ij_name = getattr(ij_doc, "name", None)
	if not ij_name:
		return
	if not _internal_job_doctype_exists():
		return

	columns = _internal_job_detail_table_columns()
	link_col = "linked_service" if "linked_service" in columns else "internal_job"
	if link_col not in columns:
		return

	writable = [fn for fn in _PARAM_FIELDS if fn in columns]
	if not writable:
		return

	rows = frappe.get_all(
		linked_service_detail_doctype(),
		filters={
			link_col: ij_name,
			"parenttype": ["not in", list(_VIRTUAL_LINKED_SERVICE_PARENTS)],
		},
		fields=["name"] + writable,
	)
	if not rows:
		return

	for row in rows:
		updates: dict[str, Any] = {}
		for fn in writable:
			new_val = getattr(ij_doc, fn, None)
			if _norm(row.get(fn)) != _norm(new_val):
				updates[fn] = new_val if new_val is not None else ""
		if not updates:
			continue
		try:
			frappe.db.set_value(
				linked_service_detail_doctype(),
				row["name"],
				updates,
				update_modified=False,
			)
		except Exception:
			frappe.log_error(
				title="Internal Job -> Detail row sync failed",
				message=f"IJ {ij_name} row {row.get('name')}: {frappe.get_traceback()}",
			)
