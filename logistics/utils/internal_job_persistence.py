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
from frappe.utils import cint

from logistics.utils.charge_service_type import default_job_type_for_internal_job_service_type
from logistics.utils.linked_service_compat import (
	linked_service_doctype,
	linked_service_doctype_exists,
	linked_service_detail_doctype,
	linked_services_fieldname,
	row_linked_service_link,
	set_row_linked_service_link,
)
from logistics.utils.sales_quote_charge_parameters import SALES_QUOTE_CHARGE_PARAMETER_FIELDS


# Operational booking doctypes that carry an Internal Job Detail child table, mapped to the
# fieldname on each parent (most use `internal_job_details`; MICE Project / Docket use `internal_jobs`).
#
# ``Sales Quote`` is a non-operational parent that may also own Internal Jobs. A single Sales Quote
# can have multiple Internal Jobs regardless of ``quotation_type`` — the desk UI currently surfaces
# the Internal Jobs tab for One-off quotes only (``depends_on`` on the doctype JSON), but the
# server-side persistence runs uniformly so that any quote-type which exposes
# ``internal_job_details`` rows materialises matching ``Internal Job`` docs. The IJs are mirrored
# onto the Booking/Order created from the quote so the per-charge ``internal_job`` link on
# ``Sales Quote Charge`` survives conversion (see
# ``logistics.utils.sales_quote_one_off_internal_jobs.propagate_one_off_internal_jobs_to_booking``).
INTERNAL_JOB_DETAIL_PARENTS: dict[str, str] = {
	"Sea Booking": "internal_job_details",
	"Air Booking": "internal_job_details",
	"Sea Shipment": "internal_job_details",
	"Air Shipment": "internal_job_details",
	"Transport Order": "internal_job_details",
	"Transport Job": "internal_job_details",
	"Declaration": "internal_job_details",
	"Declaration Order": "internal_job_details",
	"Warehouse Job": "internal_job_details",
	"Inbound Order": "internal_job_details",
	"Release Order": "internal_job_details",
	"General Job": "internal_job_details",
	"Project Job": "internal_job_details",
	"MICE Job": "internal_job_details",
	"MICE Project": "internal_jobs",
	"Docket": "internal_jobs",
	"Exhibit": "internal_jobs",
	"Sales Quote": "linked_services",
}


def _should_run_internal_job_sync_for_parent(parent_doc: Any) -> bool:
	"""All listed parents (including ``Sales Quote`` of any ``quotation_type``) participate in
	Internal Job persistence. A single Sales Quote can carry multiple Internal Jobs, so we do not
	gate creation by ``quotation_type``.
	"""
	return True


def internal_job_detail_fieldname(parent_doctype: str) -> str | None:
	"""Fieldname of the Linked Service Detail child table on *parent_doctype*, or ``None``."""
	fn = linked_services_fieldname(parent_doctype)
	if fn:
		return fn
	return INTERNAL_JOB_DETAIL_PARENTS.get(parent_doctype)


def internal_job_detail_rows_for_parent(parent_doc: Any) -> list[Any]:
	"""Child-table rows for *parent_doc*, honouring unsaved desk grid overrides when present."""
	fieldname = internal_job_detail_fieldname(getattr(parent_doc, "doctype", None) or "")
	if not fieldname:
		return []
	for key in ("_logistics_dk_ij_client_rows", "_logistics_ij_client_rows"):
		ov = getattr(frappe.local, key, None)
		if ov is not None:
			return list(ov)
	return list(getattr(parent_doc, fieldname, None) or [])


def sync_internal_job_doc_job_link(row: Any, job_type: str, job_no: str) -> None:
	"""Push ``job_type`` / ``job_no`` onto the linked ``Internal Job`` (source of truth for fetch_from)."""
	ij_name = (_row_value(row, "internal_job") or "").strip()
	jn = _norm(job_no)
	jt = _norm(job_type)
	if not ij_name or not jn:
		return
	if not frappe.db.exists(linked_service_doctype(), ij_name):
		return
	updates: dict[str, Any] = {"job_type": jt, "job_no": jn}
	frappe.db.set_value(linked_service_doctype(), ij_name, updates, update_modified=False)


# Parameter fields stored on `Internal Job` that mirror `Internal Job Detail` and `Sales Quote Charge`.
# `charge_group` is excluded - it's a Sales Quote Charge concept only.
_PARAM_FIELDS: tuple[str, ...] = tuple(
	fn for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS if fn != "charge_group"
) + (
	"service_type",
	"job_type",
	"job_no",
	"job_description",
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
	st = (getattr(ij_doc, "service_type", None) or "").strip()
	if not st:
		return
	expected = default_job_type_for_internal_job_service_type(st)
	if not expected:
		return
	jt = (getattr(ij_doc, "job_type", None) or "").strip()
	if st == "Warehousing":
		if jt in ("Inbound Order", "Release Order", "Transfer Order"):
			return
		ij_doc.job_type = "Inbound Order"
		return
	ij_doc.job_type = expected


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
	if preferred and not frappe.db.exists(linked_service_doctype(), preferred):
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
	if not ij_name or not frappe.db.exists(linked_service_doctype(), ij_name):
		return
	ij = frappe.get_doc(linked_service_doctype(), ij_name)
	changed = _copy_row_params_to_internal_job(row, ij)
	_ensure_job_type_from_service(ij)
	if not changed and (ij.job_type == _row_value(row, "job_type") or not _row_value(row, "job_type")):
		return
	ij.flags.ignore_permissions = True
	# Skip the reverse IJ -> child-row propagation: we are already writing the same
	# values that the child row carries; doing it again is wasteful (and on an in-progress
	# booking save the parent isn't even persisted yet).
	ij.flags.skip_internal_job_detail_sync = True
	ij.save(ignore_permissions=True)


def _previously_linked_internal_jobs(parent_doc: Any, fieldname: str) -> set[str]:
	"""Internal Job names that were linked to this booking on its last persisted state."""
	prev = parent_doc.get_doc_before_save() if hasattr(parent_doc, "get_doc_before_save") else None
	if prev is None:
		return set()
	return {
		(_row_value(r, "internal_job") or "").strip()
		for r in (getattr(prev, fieldname, None) or [])
		if _row_value(r, "internal_job")
	}


def _currently_linked_internal_jobs(parent_doc: Any, fieldname: str) -> set[str]:
	return {
		(_row_value(r, "internal_job") or "").strip()
		for r in (getattr(parent_doc, fieldname, None) or [])
		if _row_value(r, "internal_job")
	}


def _backfill_internal_job_parent_link(ij_doc: Any, parent_doc: Any) -> bool:
	"""Ensure ``parent_booking_type`` / ``parent_booking_name`` on an IJ when the parent has a name."""
	parent_name = _norm(getattr(parent_doc, "name", None))
	if not parent_name:
		return False
	changed = False
	parent_dt = getattr(parent_doc, "doctype", None) or ""
	if parent_dt and _norm(getattr(ij_doc, "parent_booking_type", None)) != parent_dt:
		ij_doc.parent_booking_type = parent_dt
		changed = True
	if _norm(getattr(ij_doc, "parent_booking_name", None)) != parent_name:
		ij_doc.parent_booking_name = parent_name
		changed = True
	return changed


def _ensure_internal_job_docs_for_detail_rows(parent_doc: Any) -> dict[str, str]:
	"""Create or update backing ``Internal Job`` docs for every IJ-detail row on *parent_doc*.

	Returns a map ``{stale_ij_name: new_ij_name}`` for detail rows that carried a link to a
	non-existent Internal Job and were re-pointed at a freshly materialised document.

	Does **not** delete Internal Jobs whose detail row was removed (see ``before_save`` sync).
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
	if not meta.get_field(fieldname):
		return remap

	for row in getattr(parent_doc, fieldname, None) or []:
		ij_name = (_row_value(row, "internal_job") or "").strip()
		if ij_name and frappe.db.exists(linked_service_doctype(), ij_name):
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
		if isinstance(row, dict):
			row["internal_job"] = new_name
		else:
			setattr(row, "internal_job", new_name)
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
	for row in getattr(parent_doc, fieldname, None) or []:
		st = _norm(_row_value(row, "service_type"))
		ij = (_row_value(row, "internal_job") or "").strip()
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
		if not cur:
			continue
		if frappe.db.exists(linked_service_doctype(), cur):
			continue
		replacement = remap.get(cur)
		if not replacement:
			st = _norm(_row_value(row, "service_type"))
			replacement = ij_by_service.get(st) if st else None
		if replacement and frappe.db.exists(linked_service_doctype(), replacement):
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
	for ij_name in prev - cur:
		if not ij_name or not frappe.db.exists(linked_service_doctype(), ij_name):
			continue
		try:
			frappe.delete_doc(linked_service_doctype(), ij_name, ignore_permissions=True, force=True)
		except Exception:
			frappe.log_error(
				title="Internal Job orphan cleanup failed",
				message=frappe.get_traceback(),
			)


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
	_ensure_internal_job_docs_for_detail_rows(doc)
	_delete_orphan_internal_jobs(doc, fieldname)


def delete_internal_jobs_for_booking(doc: Any, *_method) -> None:
	"""`on_trash` hook: delete every Internal Job owned by this booking."""
	if not doc or doc.doctype not in INTERNAL_JOB_DETAIL_PARENTS:
		return
	if not _internal_job_doctype_exists():
		return
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
	rows = getattr(parent_doc, fieldname, None) if fieldname else None
	rows = rows or []
	names: list[str] = []
	for r in rows:
		n = (_row_value(r, "internal_job") or "").strip()
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
		if frappe.db.exists(linked_service_doctype(), n):
			out.append(frappe.get_doc(linked_service_doctype(), n))
	return out


def iter_internal_job_detail_parent_doctypes() -> Iterable[str]:
	"""All operational booking doctypes that carry an Internal Job Detail child table."""
	return INTERNAL_JOB_DETAIL_PARENTS.keys()


def resolve_internal_job_for_internal_job_booking(doc: Any) -> str | None:
	"""Return the linked ``Internal Job`` DocType name for a booking flagged as an internal job.

	The link is resolved via the booking's parent main job: each main job carries an
	``internal_job_details`` row with ``job_type`` / ``job_no`` matching this booking and an
	``internal_job`` field pointing at the canonical IJ record. As a fallback the lookup falls
	through to ``tabInternal Job Detail`` directly so it works on partially-loaded docs (e.g.
	freshly created from a Create > Booking/Order dialog before the parent has been reloaded).
	"""
	if not doc:
		return None
	if not cint(getattr(doc, "is_internal_job", 0)):
		return None
	doctype = getattr(doc, "doctype", None)
	name = getattr(doc, "name", None)
	if not doctype or not name:
		return None
	main_job_type = (getattr(doc, "main_job_type", None) or "").strip()
	main_job = (getattr(doc, "main_job", None) or "").strip()
	if main_job_type and main_job:
		fieldname = internal_job_detail_fieldname(main_job_type)
		if fieldname:
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
					fields=["internal_job"],
					limit=1,
				)
			except Exception:
				rows = []
			for r in rows:
				ij = (r.get("internal_job") or "").strip()
				if ij:
					return ij
	if not _internal_job_doctype_exists():
		return None
	try:
		ij_names = frappe.get_all(
			linked_service_doctype(),
			filters={
				"parent_booking_type": main_job_type or None,
				"parent_booking_name": main_job or None,
				"job_type": doctype,
				"job_no": name,
			},
			pluck="name",
			limit=1,
		)
	except Exception:
		ij_names = []
	return ij_names[0] if ij_names else None


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
	if "internal_job" not in columns:
		return

	writable = [fn for fn in _PARAM_FIELDS if fn in columns]
	if not writable:
		return

	rows = frappe.get_all(
		linked_service_detail_doctype(),
		filters={"internal_job": ij_name},
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
