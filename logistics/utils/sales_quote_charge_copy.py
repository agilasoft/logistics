# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Helpers for copying selected Sales Quote Charge rows onto operational documents."""

from __future__ import annotations

from typing import Any, Callable

import frappe


def extend_charge_fields_with_scope_and_internal_job(fields: list[str]) -> list[str]:
	"""Append ``charge_scope`` and ``internal_job`` to a ``frappe.get_all`` fields list when missing.

	Used by per-doctype ``_populate_charges_from_sales_quote*`` flows so the per-charge scope
	tagging defined on the Sales Quote survives copy to the booking. Caller is expected to also
	use :func:`apply_scope_tagging_to_mapped_charge` in the row mapper.
	"""
	out = list(fields or [])
	for fn in ("charge_scope", "internal_job"):
		if fn not in out:
			out.append(fn)
	return out


def apply_scope_tagging_to_mapped_charge(source_row: Any, target_dict: dict) -> None:
	"""Copy ``charge_scope`` and (when scope is Internal Job) ``internal_job`` onto *target_dict*.

	``source_row`` may be a dict (from ``frappe.get_all``) or a document-like object. ``internal_job``
	on the source is the Sales-Quote-side IJ name; the booking-side conversion runs
	``remap_internal_job_links_on_booking_charges`` later to translate it to the booking-owned IJ.
	"""
	def _get(key, default=None):
		if isinstance(source_row, dict):
			return source_row.get(key, default)
		return getattr(source_row, key, default)

	scope = (_get("charge_scope") or "Main")
	if isinstance(scope, str):
		scope = scope.strip() or "Main"
	target_dict["charge_scope"] = scope
	if scope == "Internal Job":
		ij = _get("internal_job")
		if isinstance(ij, str):
			ij = ij.strip()
		if ij:
			target_dict["internal_job"] = ij


def filter_charge_rows_by_names(rows, charge_row_names: list[str] | None):
	"""Keep only child rows whose ``name`` is in *charge_row_names* (no-op when empty)."""
	if not charge_row_names:
		return rows
	allowed = {str(n).strip() for n in charge_row_names if n}
	if not allowed:
		return rows
	out = []
	for row in rows or []:
		rn = row_name_from_charge_row(row)
		if rn and rn in allowed:
			out.append(row)
	return out


def fetch_sales_quote_charge_rows_by_names(
	sales_quote_name: str,
	charge_row_names: list[str] | None,
	fields: list[str] | None = None,
) -> list[dict]:
	"""Load ``Sales Quote Charge`` rows by child name (any service type) for blanket call-off."""
	names = [str(n).strip() for n in (charge_row_names or []) if n and str(n).strip()]
	if not names or not sales_quote_name:
		return []
	if not frappe.db.exists("Sales Quote", sales_quote_name):
		return []
	query_fields = list(fields) if fields else ["name", "idx"]
	if "name" not in query_fields:
		query_fields.insert(0, "name")
	return frappe.get_all(
		"Sales Quote Charge",
		filters={
			"parent": sales_quote_name,
			"parenttype": "Sales Quote",
			"name": ["in", names],
		},
		fields=query_fields,
		order_by="idx",
	)


def row_name_from_charge_row(row) -> str | None:
	if isinstance(row, dict):
		return (row.get("name") or "").strip() or None
	return (getattr(row, "name", None) or "").strip() or None


# ---------------------------------------------------------------------------
# Per-scope charge extraction (Main + each Internal Job)
# ---------------------------------------------------------------------------


SCOPE_MAIN = "Main"
SCOPE_INTERNAL_JOB = "Internal Job"


_PROGRAMME_PARENT_DOCTYPES = frozenset(
	("Special Project", "MICE Project", "Project Job", "MICE Job", "MICE Order")
)


def _row_field(row: Any, fieldname: str) -> Any:
	if row is None:
		return None
	if isinstance(row, dict):
		return row.get(fieldname)
	return getattr(row, fieldname, None)


def _charge_row_canonical_service(row: Any) -> str:
	from logistics.utils.charge_service_type import canonical_charge_service_type_for_storage

	return canonical_charge_service_type_for_storage(_row_field(row, "service_type")) or ""


def _crossmode_guard_allows(parent_doctype: str, row_canonical_service: str) -> bool:
	"""Return False when an Air charge row is being copied onto a Sea-side booking (or vice versa)."""
	if row_canonical_service in ("special project", "exhibits"):
		from logistics.utils.charge_service_type import (
			canonical_charge_service_type_for_storage,
			implied_service_type_for_doctype,
		)

		parent_implied = canonical_charge_service_type_for_storage(
			implied_service_type_for_doctype(parent_doctype)
		)
		return parent_implied in ("special project", "exhibits")
	if row_canonical_service == "air" and parent_doctype in ("Sea Booking", "Sea Shipment"):
		return False
	if row_canonical_service == "sea" and parent_doctype in ("Air Booking", "Air Shipment"):
		return False
	return True


def _resolve_service_label_for_match(row: Any, parent_doc: Any) -> str:
	"""Pick the service label used to scope the parameter projection.

	Falls back to the parent's implied service type when the row has no service_type
	(legacy rows). This mirrors what ``charge_service_type.implied_service_type_for_doctype``
	already does in Stage-1 SQL filtering.
	"""
	from logistics.utils.charge_service_type import implied_service_type_for_doctype

	st = (_row_field(row, "service_type") or "").strip()
	if st:
		return st
	implied = implied_service_type_for_doctype(getattr(parent_doc, "doctype", None) or "") or ""
	return implied


def _service_types_match(a: str | None, b: str | None) -> bool:
	from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal

	if not a and not b:
		return True
	if not a or not b:
		return False
	return bool(sales_quote_charge_service_types_equal(a, b))


def _row_matches_scope(row: Any, scope_obj: Any, service_label: str) -> bool:
	"""Reuse the IJ-detail comparator: blank scope field = no constraint; blank row field = wildcard."""
	from logistics.utils.sales_quote_charge_parameters import (
		extract_service_scoped_quote_parameters,
		sales_quote_charge_row_matches_internal_job_detail_params,
	)

	scope_params = extract_service_scoped_quote_parameters(scope_obj, service_label)
	return sales_quote_charge_row_matches_internal_job_detail_params(row, scope_params)


def _iter_quote_charge_rows(
	sales_quote_doc: Any,
	*,
	charge_row_names: list[str] | None = None,
	rows_override: list[Any] | None = None,
) -> list[Any]:
	if rows_override is not None:
		rows = list(rows_override)
	else:
		rows = list(getattr(sales_quote_doc, "charges", None) or [])
	if charge_row_names:
		rows = filter_charge_rows_by_names(rows, charge_row_names)
	return rows


def populate_charges_from_quote_by_scope(
	parent_doc: Any,
	sales_quote_doc: Any,
	append_charge_callback: Callable[[Any, str, str | None], None],
	*,
	charge_row_names: list[str] | None = None,
	service_label_filter: str | None = None,
	rows_override: list[Any] | None = None,
) -> dict[str, int]:
	"""Sequentially copy Sales Quote Charge rows from the quote onto a booking, per scope.

	The flow is:

	1. **Main pass**: a charge row is included when its parameters match the booking's header
	   (the "Main" parameters); the appended booking row is tagged ``charge_scope = "Main"``.
	2. **Per-Internal-Job passes**: for each Internal Job linked to the booking
	   (via ``internal_job_details``), iterate the same Sales Quote Charge rows whose
	   service type matches the IJ's, include any whose parameters match the IJ, and tag
	   the appended row ``charge_scope = "Internal Job"`` with ``internal_job = ij.name``.

	The same Sales Quote Charge row may be appended multiple times - once per scope it
	matches (Main + each Internal Job). This is intentional: each scope carries its own
	billing/operational instance of the charge.

	The caller supplies ``append_charge_callback(quote_row, scope, internal_job_name)``;
	it is responsible for constructing the actual booking child row (per-doctype mapping)
	and appending it to ``parent_doc.charges``.

	Returns a count breakdown ``{"main": N, "internal_job": M}`` for diagnostics.
	"""
	from logistics.utils.charge_service_type import (
		canonical_charge_service_type_for_storage,
		implied_service_type_for_doctype,
	)
	from logistics.utils.internal_job_persistence import get_internal_jobs_for_booking

	counts = {"main": 0, "internal_job": 0}
	if not parent_doc or not sales_quote_doc:
		return counts

	rows = _iter_quote_charge_rows(
		sales_quote_doc,
		charge_row_names=charge_row_names,
		rows_override=rows_override,
	)
	if not rows:
		return counts

	parent_dt = getattr(parent_doc, "doctype", None) or ""
	parent_implied = implied_service_type_for_doctype(parent_dt) or ""
	is_programme_parent = parent_dt in _PROGRAMME_PARENT_DOCTYPES

	for row in rows:
		row_st_raw = _resolve_service_label_for_match(row, parent_doc)
		row_st_canon = canonical_charge_service_type_for_storage(row_st_raw)

		if service_label_filter:
			if not _service_types_match(row_st_raw, service_label_filter):
				continue

		if not _crossmode_guard_allows(parent_dt, row_st_canon):
			continue

		if is_programme_parent:
			# Programme parents do not loop per IJ - they pull everything as Main (matches existing behavior).
			append_charge_callback(row, SCOPE_MAIN, None)
			counts["main"] += 1
			continue

		main_label = row_st_raw or parent_implied
		if _row_matches_scope(row, parent_doc, main_label):
			append_charge_callback(row, SCOPE_MAIN, None)
			counts["main"] += 1

	if is_programme_parent:
		return counts

	for ij in get_internal_jobs_for_booking(parent_doc):
		ij_st = (getattr(ij, "service_type", None) or "").strip()
		if not ij_st:
			continue
		for row in rows:
			row_st_raw = (_row_field(row, "service_type") or "").strip()
			row_st_canon = canonical_charge_service_type_for_storage(row_st_raw)
			if row_st_raw and not _service_types_match(row_st_raw, ij_st):
				continue
			if not _crossmode_guard_allows(parent_dt, row_st_canon):
				continue
			if service_label_filter and not _service_types_match(row_st_raw or ij_st, service_label_filter):
				continue
			if _row_matches_scope(row, ij, ij_st):
				append_charge_callback(row, SCOPE_INTERNAL_JOB, ij.name)
				counts["internal_job"] += 1

	return counts


def compute_quote_charge_scope_groups(
	parent_doc: Any,
	sales_quote_doc: Any,
	*,
	charge_row_names: list[str] | None = None,
) -> list[dict]:
	"""Return ``[{scope, internal_job, internal_job_label, rows: [...]}, ...]`` for preview rendering.

	Each ``rows`` entry is a lightweight dict with display-relevant fields. The same Sales Quote
	Charge row may appear in multiple groups (Main + each matching Internal Job) - mirroring the
	server-side per-scope extraction implemented by ``populate_charges_from_quote_by_scope``.
	"""
	groups: list[dict] = []
	main_rows: list[dict] = []
	per_ij_rows: dict[str, list[dict]] = {}

	def _serialise(row: Any) -> dict:
		def _g(fn):
			if isinstance(row, dict):
				return row.get(fn)
			return getattr(row, fn, None)

		return {
			"name": _g("name"),
			"item_code": _g("item_code"),
			"item_name": _g("item_name"),
			"service_type": _g("service_type"),
			"charge_type": _g("charge_type"),
			"charge_category": _g("charge_category"),
			"unit_rate": _g("unit_rate"),
			"currency": _g("currency"),
		}

	def _append(quote_row, scope, internal_job):
		serialised = _serialise(quote_row)
		if scope == SCOPE_INTERNAL_JOB and internal_job:
			per_ij_rows.setdefault(internal_job, []).append(serialised)
		else:
			main_rows.append(serialised)

	populate_charges_from_quote_by_scope(
		parent_doc,
		sales_quote_doc,
		_append,
		charge_row_names=charge_row_names,
	)

	if main_rows:
		groups.append({
			"scope": SCOPE_MAIN,
			"internal_job": None,
			"internal_job_label": None,
			"rows": main_rows,
		})

	for ij_name, rows in per_ij_rows.items():
		label = ij_name
		try:
			meta_info = frappe.db.get_value(
				"Internal Job",
				ij_name,
				("service_type", "job_no", "job_type"),
				as_dict=True,
			) or {}
			descriptor_bits = [b for b in (
				meta_info.get("service_type"),
				meta_info.get("job_no") or meta_info.get("job_type"),
			) if b]
			if descriptor_bits:
				label = f"{ij_name} ({' · '.join(descriptor_bits)})"
		except Exception:
			pass
		groups.append({
			"scope": SCOPE_INTERNAL_JOB,
			"internal_job": ij_name,
			"internal_job_label": label,
			"rows": rows,
		})

	return groups


def stamp_scope_fields_on_charge_row(child_row: Any, scope: str, internal_job: str | None) -> None:
	"""Set ``charge_scope`` / ``internal_job`` on a booking charge row if the child supports them.

	Defensive: child charge tables that do not have the new scope fields (e.g. unrelated charge
	tables) are left untouched.

	Operational charge child tables store linked scope as ``"Linked"`` (legacy callers may still pass
	``SCOPE_INTERNAL_JOB`` / ``"Internal Job"``).
	"""
	from logistics.utils.linked_service_compat import (
		CHARGE_SCOPE_LINKED,
		CHARGE_SCOPE_MAIN,
		is_linked_charge_scope,
		normalize_charge_scope,
		set_charge_row_linked_service_link,
	)

	if child_row is None:
		return
	stored_scope = normalize_charge_scope(scope)
	is_linked = is_linked_charge_scope(scope)
	if isinstance(child_row, dict):
		if scope:
			child_row["charge_scope"] = stored_scope
		if is_linked and internal_job:
			set_charge_row_linked_service_link(child_row, internal_job)
		return
	try:
		meta = frappe.get_meta(getattr(child_row, "doctype", None))
	except Exception:
		meta = None
	if meta and meta.has_field("charge_scope"):
		setattr(child_row, "charge_scope", stored_scope or CHARGE_SCOPE_MAIN)
	if is_linked and internal_job:
		if meta and meta.has_field("linked_service"):
			set_charge_row_linked_service_link(child_row, internal_job)
		elif meta and meta.has_field("internal_job"):
			setattr(child_row, "internal_job", internal_job)


def stamp_main_or_internal_job_scope_on_booking_charges(parent_doc: Any) -> None:
	"""Default-stamp ``charge_scope`` / ``internal_job`` on the booking's charge table.

	Behaviour:

	* When the booking has ``is_internal_job = 1``: every row whose ``charge_scope`` is empty gets
	  ``charge_scope = "Internal Job"``; the canonical Internal Job DocType is resolved (best effort)
	  and stamped on rows whose ``internal_job`` is empty. Existing scope/link values are preserved.
	* Otherwise (Main booking, or programme parent): every row whose ``charge_scope`` is empty gets
	  ``charge_scope = "Main"``. Rows that explicitly carry ``charge_scope = "Internal Job"`` together
	  with an ``internal_job`` link are left untouched (so a Main booking may carry both scopes side
	  by side - e.g. when the per-scope flow appends extra IJ-scoped rows).

	The function is a no-op for booking doctypes whose charge child table does not declare the
	``charge_scope`` / ``internal_job`` fields.
	"""
	from frappe.utils import cint

	if not parent_doc:
		return
	rows = getattr(parent_doc, "charges", None) or []
	if not rows:
		return
	try:
		meta = frappe.get_meta(getattr(parent_doc, "doctype", None))
	except Exception:
		meta = None
	charges_df = meta.get_field("charges") if meta else None
	child_dt = (charges_df.options or "").strip() if charges_df else ""
	try:
		child_meta = frappe.get_meta(child_dt) if child_dt else None
	except Exception:
		child_meta = None
	has_scope_field = bool(child_meta and child_meta.has_field("charge_scope"))
	has_ij_field = bool(child_meta and child_meta.has_field("internal_job"))
	if not has_scope_field and not has_ij_field:
		return

	is_internal = bool(cint(getattr(parent_doc, "is_internal_job", 0)))
	resolved_ij: str | None = None
	if is_internal and has_ij_field:
		# Prefer the link already on the doc (populated by ``apply_internal_job_detail_row_to_operational_doc``
		# during Create > Internal Job and by ``_resolve_and_set_internal_job_link`` during validate). This
		# is the only source available on the very first ``insert``, before the parent's Internal Job
		# Detail row has been persisted with ``job_no = doc.name``.
		header_ij = (getattr(parent_doc, "internal_job", None) or "").strip()
		if header_ij:
			resolved_ij = header_ij
		else:
			try:
				from logistics.utils.internal_job_persistence import (
					resolve_internal_job_for_internal_job_booking,
				)

				resolved_ij = resolve_internal_job_for_internal_job_booking(parent_doc)
			except Exception:
				resolved_ij = None

	from logistics.utils.linked_service_compat import (
		CHARGE_SCOPE_LINKED,
		CHARGE_SCOPE_MAIN,
		charge_row_linked_service_link,
		is_linked_charge_scope,
		set_charge_row_linked_service_link,
	)

	for row in rows:
		current_scope = (getattr(row, "charge_scope", None) or "").strip()
		current_ij = charge_row_linked_service_link(row)
		if is_linked_charge_scope(current_scope) and has_scope_field and current_scope != CHARGE_SCOPE_LINKED:
			setattr(row, "charge_scope", CHARGE_SCOPE_LINKED)
			current_scope = CHARGE_SCOPE_LINKED
		if is_internal:
			# An IJ booking only owns linked-scoped rows; correct any "Main" stamps inherited from a copy.
			if has_scope_field and not is_linked_charge_scope(current_scope):
				setattr(row, "charge_scope", CHARGE_SCOPE_LINKED)
			if has_ij_field and resolved_ij and current_ij != resolved_ij:
				set_charge_row_linked_service_link(row, resolved_ij)
			continue
		if is_linked_charge_scope(current_scope) and current_ij:
			continue
		if has_scope_field and not current_scope:
			setattr(row, "charge_scope", CHARGE_SCOPE_MAIN)
