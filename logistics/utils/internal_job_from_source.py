# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Create Transport Order / Declaration Order / Air Booking / Sea Booking from shipments or transport jobs using Internal Job Detail rows."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import frappe
from frappe import _

from logistics.utils.charge_service_type import (
	default_job_type_for_internal_job_service_type,
	effective_internal_job_detail_job_type,
)
from logistics.utils.internal_job_detail_copy import (
	get_declaration_order_job_no_from_shipment_doc,
	persist_internal_job_detail_job_link,
)
from logistics.utils.sales_quote_charge_parameters import (
	any_sales_quote_charge_matches_internal_job_detail_params,
	coerce_sales_quote_name,
	extract_sales_quote_charge_parameters,
	parameter_fields_for_service_type,
)


CREATABLE_INTERNAL_JOB_TYPES: frozenset[str] = frozenset(
	{
		"Transport Order",
		"Declaration Order",
		"Air Booking",
		"Sea Booking",
		"VAS Order",
		"MICE Order",
	}
)

_LINKED_CHARGE_IJ_PARENT_DOCTYPES: frozenset[str] = frozenset(
	{"Air Shipment", "Sea Shipment", "Transport Job", "Declaration"}
)


def _uses_linked_charge_internal_job_create(parent_doctype: str) -> bool:
	return (parent_doctype or "").strip() in _LINKED_CHARGE_IJ_PARENT_DOCTYPES


def _iter_linked_scoped_charges(parent_doc: Any):
	from logistics.utils.linked_service_compat import is_linked_charge_scope, normalize_charge_scope

	for ch in getattr(parent_doc, "charges", None) or []:
		scope = normalize_charge_scope(getattr(ch, "charge_scope", None))
		if is_linked_charge_scope(scope):
			yield ch


def _linked_charge_group_key(charge: Any) -> tuple:
	from logistics.utils.linked_service_compat import charge_row_linked_service_link
	from logistics.utils.sales_quote_charge_parameters import extract_service_scoped_quote_parameters

	st = (getattr(charge, "service_type", None) or "").strip()
	ls = charge_row_linked_service_link(charge)
	if ls:
		return ("ls", ls)
	params = extract_service_scoped_quote_parameters(charge, st) if st else {}
	fp = tuple(sorted((k, str(v)) for k, v in params.items() if v not in (None, "")))
	return ("params", st, fp)


def _virtual_ij_row_from_linked_charge(charge: Any) -> Any:
	from logistics.utils.linked_service_compat import charge_row_linked_service_link
	from logistics.utils.sales_quote_charge_parameters import resolve_parameters_for_charge_row

	st = (getattr(charge, "service_type", None) or "").strip()
	jt = default_job_type_for_internal_job_service_type(st)
	ls = charge_row_linked_service_link(charge)
	row = frappe._dict(
		{
			"service_type": st,
			"job_type": jt,
			"internal_job": ls,
			"linked_service": ls,
		}
	)
	for k, v in resolve_parameters_for_charge_row(charge).items():
		row[k] = v
	return row


def _linked_charge_groups_for_create(parent_doc: Any) -> list[tuple[int, Any]]:
	"""1-based virtual Internal Job Detail rows derived from Linked-scoped charge lines."""
	seen: set[tuple] = set()
	groups: list[Any] = []
	for ch in _iter_linked_scoped_charges(parent_doc):
		key = _linked_charge_group_key(ch)
		if key in seen:
			continue
		seen.add(key)
		groups.append(_virtual_ij_row_from_linked_charge(ch))
	return [(i, row) for i, row in enumerate(groups, start=1)]


def _linked_service_doc_for_row(row: Any) -> Any | None:
	"""Load the Linked Service document referenced by a charge or planning row."""
	from logistics.utils.linked_service_compat import linked_service_doctype, row_linked_service_link

	ls = row_linked_service_link(row)
	if not ls or not frappe.db.exists(linked_service_doctype(), ls):
		return None
	return frappe.get_cached_doc(linked_service_doctype(), ls)


def _job_no_for_linked_charge_row(row: Any) -> str:
	from logistics.utils.linked_service_compat import (
		linked_service_doctype,
		linked_service_record_exists,
		row_linked_service_link,
	)

	ls = row_linked_service_link(row)
	jt = effective_internal_job_detail_job_type(row)
	if not ls or not linked_service_record_exists(ls):
		return ""
	info = frappe.db.get_value(
		linked_service_doctype(),
		ls,
		("job_type", "job_no"),
		as_dict=True,
	)
	if not info:
		return ""
	job_no = (info.get("job_no") or "").strip()
	job_type = (info.get("job_type") or "").strip()
	if not job_no:
		return ""
	if jt and job_type and job_type != jt:
		return ""
	return job_no


def _resolve_linked_charge_row_for_create(
	parent_doc: Any,
	job_type: str,
	internal_job_detail_idx: int | None,
) -> tuple[Any | None, int | None]:
	jt = (job_type or "").strip()
	idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	groups = _linked_charge_groups_for_create(parent_doc)
	if idx is not None:
		if idx < 1 or idx > len(groups):
			frappe.throw(_("Invalid linked-service charge group."))
		_row_idx, row = groups[idx - 1]
		if effective_internal_job_detail_job_type(row) != jt:
			frappe.throw(_("The selected line is not for {0}.").format(job_type))
		jn = _job_no_for_linked_charge_row(row)
		if jn:
			frappe.throw(
				_("This linked-service charge line already references {0} {1}.").format(jt, jn),
				title=_("Already linked"),
			)
		return row, idx
	for i, row in groups:
		if effective_internal_job_detail_job_type(row) != jt:
			continue
		if _job_no_for_linked_charge_row(row):
			continue
		return row, i
	return None, None


def persist_internal_job_create_back_link(
	parent_doctype: str,
	parent_name: str,
	job_type: str,
	job_no: str,
	*,
	ij_row: Any | None = None,
	detail_idx: int | None = None,
) -> None:
	"""Back-link after create; linked-charge parents skip the Internal Jobs child table."""
	if parent_doctype == "Sales Quote":
		qt = frappe.db.get_value("Sales Quote", parent_name, "quotation_type")
		if (qt or "").strip() == "Regular":
			return
	from logistics.utils.internal_job_persistence import sync_internal_job_doc_job_link
	from logistics.utils.linked_service_compat import row_linked_service_link

	if ij_row is not None and row_linked_service_link(ij_row):
		sync_internal_job_doc_job_link(ij_row, job_type, job_no)
	if _uses_linked_charge_internal_job_create(parent_doctype):
		return
	persist_internal_job_detail_job_link(
		parent_doctype, parent_name, job_type, job_no, detail_idx=detail_idx
	)


def _apply_internal_job_satellite_flags(doc: Any, main_job_type: str, main_job: str) -> None:
	"""Converted linked service: Service Role=Linked, stamp main refs (new + legacy)."""
	from logistics.utils.service_role_rules import apply_linked_service_satellite_flags

	apply_linked_service_satellite_flags(doc, main_job_type, main_job)


def linked_internal_job_target_is_cancelled(job_type: str, job_no: str) -> bool:
	"""True when Job No points at an operational document with docstatus 2 (cancelled)."""
	jt = (job_type or "").strip()
	jn = (job_no or "").strip()
	if not jt or not jn or jt not in CREATABLE_INTERNAL_JOB_TYPES:
		return False
	if not frappe.db.exists(jt, jn):
		return False
	return (frappe.db.get_value(jt, jn, "docstatus") or 0) == 2


def _source_internal_job_nested_block_message() -> str:
	return _(
		"This document is already an internal job linked to a main job. Create additional internal jobs from the main service document, not from this one."
	)


def is_source_internal_job_linked_to_main(parent_doc: Any) -> bool:
	"""True when the document is a Linked satellite that already references a main."""
	from logistics.utils.service_role_rules import is_linked_service_satellite

	return is_linked_service_satellite(parent_doc)


def _source_service_role_context(doc: Any) -> dict[str, Any]:
	"""Dialog/API keys keep legacy names; values come from service_role helpers."""
	from logistics.utils.service_role_rules import (
		SERVICE_ROLE_LINKED,
		get_main_service_name,
		get_main_service_type,
		get_service_role,
	)

	return {
		"source_is_internal_job": get_service_role(doc) == SERVICE_ROLE_LINKED,
		"source_main_job_type": get_main_service_type(doc) or None,
		"source_main_job": get_main_service_name(doc) or None,
	}


def ensure_operational_source_can_create_internal_job(parent_doc: Any) -> None:
	"""Reject Create Internal Job when the source is already a linked internal job."""
	if is_source_internal_job_linked_to_main(parent_doc):
		frappe.throw(
			_source_internal_job_nested_block_message(),
			title=_("Cannot create internal job"),
		)


_SERVICE_LOWER_FOR_JOB_TYPE: dict[str, str] = {
	"Transport Order": "transport",
	"Declaration Order": "customs",
	"Air Booking": "air",
	"Sea Booking": "sea",
	"VAS Order": "warehousing",
}

_SERVICE_LABEL_FOR_JOB_TYPE: dict[str, str] = {
	"Transport Order": "Transport",
	"Declaration Order": "Customs",
	"Air Booking": "Air",
	"Sea Booking": "Sea",
	"VAS Order": "Warehousing",
}

INTERNAL_JOB_QUOTE_PARAMETER_MISMATCH_MESSAGE = _(
	"No parameters match on your input in internal job parameters"
)


def internal_job_detail_params_match_quotation(
	parent_doc: Any,
	job_type: str,
	ij_row: Any,
) -> bool:
	"""True when Internal Job Detail parameters match at least one Sales Quote Charge row (or no check needed)."""
	if not ij_row:
		return True
	service_label = _SERVICE_LABEL_FOR_JOB_TYPE.get((job_type or "").strip())
	if not service_label:
		return True
	return any_sales_quote_charge_matches_internal_job_detail_params(
		getattr(parent_doc, "sales_quote", None),
		ij_row,
		service_label,
	)


def validate_internal_job_detail_params_match_quotation(
	parent_doc: Any,
	job_type: str,
	internal_job_detail_idx: int | None = None,
) -> None:
	"""Reject create when charges or matching Internal Job setup are missing."""
	if _uses_linked_charge_internal_job_create(getattr(parent_doc, "doctype", None) or ""):
		row, _resolved_idx = resolve_internal_job_detail_row_for_create(
			parent_doc, job_type, internal_job_detail_idx
		)
		if not row:
			frappe.throw(
				_("No linked-service charge line found for {0}.").format(job_type),
				title=_("Cannot create internal job"),
			)
		from logistics.utils.internal_job_creation_eligibility import (
			require_internal_job_eligibility_for_create,
		)

		jt = (job_type or "").strip()
		service_label = _SERVICE_LABEL_FOR_JOB_TYPE.get(jt)
		ls_doc = _linked_service_doc_for_row(row)
		require_internal_job_eligibility_for_create(
			sales_quote=getattr(parent_doc, "sales_quote", None),
			parent_doc=parent_doc,
			ij_row=row,
			linked_service_doc=ls_doc,
			service_type_label=service_label,
			uses_linked_charge_create=True,
		)
		return

	from logistics.utils.internal_job_creation_eligibility import (
		require_internal_job_eligibility_for_create,
	)

	jt = (job_type or "").strip()
	ij_row, _resolved_idx = resolve_internal_job_detail_row_for_create(
		parent_doc, jt, internal_job_detail_idx
	)
	service_label = _SERVICE_LABEL_FOR_JOB_TYPE.get(jt)
	require_internal_job_eligibility_for_create(
		sales_quote=getattr(parent_doc, "sales_quote", None),
		parent_doc=parent_doc,
		ij_row=ij_row,
		service_type_label=service_label,
		uses_linked_charge_create=False,
	)


_LOGISTICS_IJ_CLIENT_ROWS = "_logistics_ij_client_rows"


def _coerce_client_internal_job_details(client_value: Any) -> list | None:
	"""List of Internal Job Detail row dicts from the desk form, or None to use the saved document."""
	if client_value is None or client_value == "":
		return None
	if isinstance(client_value, str):
		try:
			client_value = frappe.parse_json(client_value)
		except Exception:
			return None
	if not isinstance(client_value, list):
		return None
	return client_value


@contextmanager
def internal_job_details_client_rows(client_value: Any):
	"""Use grid rows from the form (including unsaved lines) for resolve/create while this block runs."""
	key = _LOGISTICS_IJ_CLIENT_ROWS
	parsed = _coerce_client_internal_job_details(client_value)
	had_before = hasattr(frappe.local, key)
	old_val = getattr(frappe.local, key, None) if had_before else None
	try:
		if parsed is not None:
			setattr(
				frappe.local,
				key,
				[frappe._dict(r) if isinstance(r, dict) else r for r in parsed],
			)
		yield
	finally:
		if parsed is not None:
			if had_before:
				setattr(frappe.local, key, old_val)
			else:
				try:
					delattr(frappe.local, key)
				except AttributeError:
					pass


def _ij_rows_list(parent_doc: Any) -> list[Any]:
	ov = getattr(frappe.local, _LOGISTICS_IJ_CLIENT_ROWS, None)
	if ov is not None:
		return list(ov)
	return list(getattr(parent_doc, "internal_job_details", None) or [])


def coerce_internal_job_detail_idx(value: Any) -> int | None:
	if value is None or value == "":
		return None
	try:
		i = int(value)
		return i if i > 0 else None
	except (TypeError, ValueError):
		return None


def resolve_internal_job_detail_row_for_create(
	parent_doc: Any,
	job_type: str,
	internal_job_detail_idx: int | None,
) -> tuple[Any | None, int | None]:
	"""Resolve the row used for create: Linked charges on freight shipments, else Internal Job Detail."""
	if _uses_linked_charge_internal_job_create(getattr(parent_doc, "doctype", None) or ""):
		return _resolve_linked_charge_row_for_create(parent_doc, job_type, internal_job_detail_idx)

	jt = (job_type or "").strip()
	idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	if idx is not None:
		return resolve_internal_job_detail_row(parent_doc, idx, jt), idx

	rows = _ij_rows_list(parent_doc)
	for i, r in enumerate(rows, start=1):
		if effective_internal_job_detail_job_type(r) != jt:
			continue
		if (getattr(r, "job_no", None) or "").strip():
			continue
		return r, i

	return None, None


def resolve_internal_job_detail_row(
	parent_doc: Any, internal_job_detail_idx: int | None, expected_job_type: str
) -> Any | None:
	"""Return the child row at 1-based idx or None. Validates job_type when idx is set."""
	if internal_job_detail_idx is None:
		return None
	rows = _ij_rows_list(parent_doc)
	if internal_job_detail_idx < 1 or internal_job_detail_idx > len(rows):
		frappe.throw(_("Invalid Internal Job Detail row."))
	row = rows[internal_job_detail_idx - 1]
	row_jt = effective_internal_job_detail_job_type(row)
	if row_jt != (expected_job_type or "").strip():
		frappe.throw(_("The selected line is not for {0}.").format(expected_job_type))
	jn = (getattr(row, "job_no", None) or "").strip()
	if jn:
		frappe.throw(
			_("This Internal Job Detail line already references {0} {1}.").format(row_jt, jn),
			title=_("Already linked"),
		)
	return row


def apply_internal_job_detail_row_to_operational_doc(
	doc: Any, row: Any, *, overwrite: bool = False
) -> None:
	"""Apply parameter fields from an Internal Job Detail row onto a new operational document.

	When ``overwrite`` is True, values from the row replace existing header fields (quote/routing defaults).
	"""
	if not row:
		return
	meta = frappe.get_meta(doc.doctype)

	# Always carry the canonical Linked Service link onto the new operational doc (when the target
	# doctype defines the field). This is set before the parameter early-return below so we still
	# stamp the link even on rows that have no service-scoped parameters (rare, but possible for
	# warehousing-only IJs and similar minimal rows).
	from logistics.utils.linked_service_compat import row_linked_service_link

	ij_link_val = row_linked_service_link(row)
	if ij_link_val and meta.get_field("internal_job"):
		cur_ij = (getattr(doc, "internal_job", None) or "").strip()
		if overwrite or not cur_ij:
			doc.set("internal_job", ij_link_val)
	if ij_link_val and meta.get_field("linked_service"):
		cur_ls = (getattr(doc, "linked_service", None) or "").strip()
		if overwrite or not cur_ls:
			doc.set("linked_service", ij_link_val)

	from logistics.utils.sales_quote_charge_parameters import (
		apply_scope_fields_to_operational_doc,
		resolve_operational_doc_scope_parameters,
	)

	if not resolve_operational_doc_scope_parameters(row):
		return

	apply_scope_fields_to_operational_doc(doc, row, overwrite=overwrite)


_CONTACTS_ADDRESSES_FIELD_NAMES: tuple[str, ...] = (
	"shipper_address",
	"shipper_address_display",
	"consignee_address",
	"consignee_address_display",
	"shipper_contact",
	"shipper_contact_display",
	"consignee_contact",
	"consignee_contact_display",
	"notify_party",
	"notify_party_address",
)


def _copy_contacts_addresses_between_operational_docs(source_doc: Any, target_doc: Any) -> None:
	"""Copy Contacts & Addresses tab scalars when the target DocType defines the field."""
	if not source_doc or not target_doc:
		return
	meta = frappe.get_meta(target_doc.doctype)
	for fn in _CONTACTS_ADDRESSES_FIELD_NAMES:
		if not meta.get_field(fn):
			continue
		if not hasattr(source_doc, fn):
			continue
		setattr(target_doc, fn, getattr(source_doc, fn, None))


_SKIP_PACKAGE_TABLE_LAYOUT_TYPES: frozenset[str] = frozenset(
	("Section Break", "Column Break", "Tab Break", "HTML", "Button")
)
_SKIP_PACKAGE_ROW_SYSTEM_FIELDS: frozenset[str] = frozenset(
	(
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"parent",
		"parenttype",
		"parentfield",
		"idx",
		"docstatus",
	)
)


def _child_doctype_for_table_field(parent_doctype: str, table_fieldname: str) -> str | None:
	df = frappe.get_meta(parent_doctype).get_field(table_fieldname)
	if df and df.fieldtype == "Table" and df.options:
		return (df.options or "").strip() or None
	return None


def _copy_table_rows_matching_target_child_fields(
	source_rows: list[Any] | tuple[Any, ...] | None,
	target_doc: Any,
	*,
	table_fieldname: str,
	target_child_doctype: str,
) -> None:
	"""Append child rows using field names that exist on ``target_child_doctype`` (values from each source row)."""
	if not source_rows or not target_doc or not table_fieldname or not target_child_doctype:
		return
	if not hasattr(target_doc, table_fieldname):
		return
	tgt_child_meta = frappe.get_meta(target_child_doctype)
	allowed = {
		f.fieldname
		for f in tgt_child_meta.fields
		if f.fieldtype not in _SKIP_PACKAGE_TABLE_LAYOUT_TYPES
	} - _SKIP_PACKAGE_ROW_SYSTEM_FIELDS

	for src_row in source_rows:
		row_dict: dict[str, Any] = {}
		for fn in allowed:
			if not hasattr(src_row, fn):
				continue
			row_dict[fn] = getattr(src_row, fn, None)
		if not row_dict:
			continue
		if all(v is None or v == "" for v in row_dict.values()):
			continue
		target_doc.append(table_fieldname, row_dict)


def _copy_packages_from_shipment_to_internal_freight_booking(shipment_doc: Any, booking_doc: Any) -> None:
	"""Copy ``packages`` from Sea/Air Shipment onto a new internal Air/Sea Booking.

	Uses the booking's package child DocType (e.g. Sea Freight Packages → Air Booking Packages).
	"""
	packages = getattr(shipment_doc, "packages", None) or []
	if not packages:
		return
	child_dt = _child_doctype_for_table_field(booking_doc.doctype, "packages")
	if not child_dt:
		return
	_copy_table_rows_matching_target_child_fields(
		packages, booking_doc, table_fieldname="packages", target_child_doctype=child_dt
	)


def _shipment_charge_matches_service(shipment: Any, *service_lower: str) -> bool:
	targets = {s.lower() for s in service_lower if s}
	if not targets:
		return False
	for ch in getattr(shipment, "charges", None) or []:
		st = (getattr(ch, "service_type", None) or "").strip().lower()
		ost = (getattr(ch, "other_service_type", None) or "").strip().lower()
		if st in targets or ost in targets:
			return True
	return False


def _open_internal_job_detail_rows(parent_doc: Any) -> list[tuple[int, Any]]:
	"""1-based indices of internal_job_details rows with no Job No yet (any job type)."""
	out: list[tuple[int, Any]] = []
	for i, row in enumerate(getattr(parent_doc, "internal_job_details", None) or [], start=1):
		if (getattr(row, "job_no", None) or "").strip():
			continue
		out.append((i, row))
	return out


def _open_internal_job_detail_rows_for_form(
	parent_doc: Any, client_internal_job_details: Any
) -> list[tuple[int, Any]]:
	"""Open rows for Create > Internal Job: prefer the desk grid (unsaved) when the client sends it."""
	parsed = _coerce_client_internal_job_details(client_internal_job_details)
	if parsed is None:
		return _open_internal_job_detail_rows(parent_doc)
	# Client often sends JSON "[]" when the child table is not yet in memory; use saved rows for named docs.
	if (
		not parsed
		and getattr(parent_doc, "name", None)
		and not getattr(parent_doc, "__islocal", False)
	):
		return _open_internal_job_detail_rows(parent_doc)
	out: list[tuple[int, Any]] = []
	for i, rowd in enumerate(parsed, start=1):
		rw = frappe._dict(rowd) if isinstance(rowd, dict) else rowd
		if (getattr(rw, "job_no", None) or "").strip():
			continue
		out.append((i, rw))
	return out


def _all_internal_job_detail_rows_for_form(
	parent_doc: Any, client_internal_job_details: Any
) -> list[tuple[int, Any]]:
	"""All Internal Job Detail rows for the dialog, including lines that already have Job No (read-only cards)."""
	parsed = _coerce_client_internal_job_details(client_internal_job_details)
	if parsed is None:
		rows = getattr(parent_doc, "internal_job_details", None) or []
		return [(i, r) for i, r in enumerate(rows, start=1)]
	if (
		not parsed
		and getattr(parent_doc, "name", None)
		and not getattr(parent_doc, "__islocal", False)
	):
		rows = getattr(parent_doc, "internal_job_details", None) or []
		return [(i, r) for i, r in enumerate(rows, start=1)]
	out: list[tuple[int, Any]] = []
	for i, rowd in enumerate(parsed, start=1):
		rw = frappe._dict(rowd) if isinstance(rowd, dict) else rowd
		out.append((i, rw))
	return out


def _job_type_allowed_for_source(
	source_doctype: str, parent_doc: Any, job_type: str, flags: dict[str, Any]
) -> bool:
	"""Whether Create > Internal Job can create this document type from this source."""
	jt = (job_type or "").strip()
	if jt not in CREATABLE_INTERNAL_JOB_TYPES:
		return False
	sq = getattr(parent_doc, "sales_quote", None)
	if source_doctype in ("Air Shipment", "Sea Shipment"):
		if jt == "Transport Order":
			return True
		if jt == "Declaration Order":
			return bool(sq and not get_declaration_order_job_no_from_shipment_doc(parent_doc))
		if jt == "Sea Booking":
			# Allow cross-mode (Sea-under-Air) and same-mode (Sea-under-Sea) Internal Job bookings.
			# Same-mode is unusual but valid (e.g. a Domestic Sea leg under an Import Sea Main).
			if source_doctype == "Air Shipment":
				return True
			return _shipment_charge_matches_service(parent_doc, "sea")
		if jt == "Air Booking":
			# Allow cross-mode (Air-under-Sea) and same-mode (Air-under-Air) Internal Job bookings.
			# Same-mode is unusual but valid (e.g. a Domestic Air leg under an Import Air Main).
			return _shipment_charge_matches_service(parent_doc, "air")
		if jt == "VAS Order":
			return bool(flags.get("allow_inbound"))
		return False
	if source_doctype == "Transport Job":
		if jt == "Transport Order":
			return True
		if jt == "Declaration Order":
			return bool(flags.get("allow_declaration"))
		if jt in ("Air Booking", "Sea Booking"):
			return True
		if jt == "VAS Order":
			return bool(flags.get("allow_inbound"))
		return False
	if source_doctype == "Declaration":
		sq = getattr(parent_doc, "sales_quote", None)
		if jt == "Transport Order":
			if not sq:
				return False
			if (getattr(parent_doc, "transport_order", None) or "").strip():
				return False
			from logistics.utils.service_role_rules import (
				SERVICE_ROLE_LINKED,
				SERVICE_ROLE_MAIN,
				get_service_role,
			)

			return get_service_role(parent_doc) in (SERVICE_ROLE_MAIN, SERVICE_ROLE_LINKED)
		if jt == "VAS Order":
			return bool(flags.get("allow_inbound")) and bool(sq)
		return False
	return False


def _choice_label(job_type: str, row: Any | None, idx: int | None) -> str:
	"""Choice label for an Internal Job Detail row."""
	st = (getattr(row, "service_type", None) or "").strip() if row else ""
	jt_label = (job_type or "").strip()
	parts: list[str] = []
	if idx is not None:
		if st:
			parts.append(_("[idx {0}] {1}").format(idx, _(st)))
		elif jt_label:
			parts.append(_("[idx {0}] {1}").format(idx, _(jt_label)))
		else:
			parts.append(_("[idx {0}] — {1}").format(idx, _("(no service type)")))
	else:
		parts.append(_(jt_label) if jt_label else _("(no job type)"))
	if st and idx is None:
		parts.append(st)
	return " — ".join(parts)


def _choice_header_fields(
	job_type: str,
	row: Any | None,
	idx: int | None,
) -> dict[str, str]:
	"""Structured card header (title, pill, subtitle, IJ link) for Create Internal Job UI."""
	jt_label = (job_type or "").strip()
	st = (getattr(row, "service_type", None) or "").strip() if row else ""
	jn = (getattr(row, "job_no", None) or "").strip() if row else ""
	ij_link = ""
	if row is not None:
		from logistics.utils.linked_service_compat import row_linked_service_link

		ij_link = row_linked_service_link(row)
	title = _(st) if st else (_(jt_label) if jt_label else _("(no service type)"))
	if jn:
		badge = jn
	elif idx is not None:
		badge = _("Pending")
	else:
		badge = _("Job Details")
	if jn:
		subtitle = _("Already linked — open the job from Job No above.")
	elif not st:
		subtitle = _("Select a service type on this line to set the target document type.")
	elif not jt_label:
		subtitle = _("Could not resolve target document type for this service.")
	else:
		subtitle = _("Creates {0}. Row parameters are applied on create.").format(_(jt_label))
	out: dict[str, str] = {
		"header_title": title,
		"header_badge": badge,
		"header_subtitle": subtitle,
	}
	if ij_link:
		out["internal_job"] = ij_link
	return out


def _empty_internal_job_create_blocked_message(parent_doc: Any) -> str:
	if _uses_linked_charge_internal_job_create(getattr(parent_doc, "doctype", None) or ""):
		return _(
			"No linked-service charges (Scope = Linked) were found on this document. "
			"Pull charges from the Sales Quote or tag charge lines with Scope = Linked before creating internal jobs."
		)
	return _("No internal jobs can be created from this document.")


@frappe.whitelist()
def get_internal_job_creation_choices(
	source_doctype: str,
	source_name: str,
	internal_job_details: Any = None,
):
	"""Build Create > Internal Job options from Linked charges or Internal Job Detail rows."""
	if not source_name or not frappe.db.exists(source_doctype, source_name):
		frappe.throw(_("Invalid source document."))
	if source_doctype not in ("Air Shipment", "Sea Shipment", "Transport Job", "Declaration"):
		frappe.throw(_("Unsupported source type."))

	doc = frappe.get_doc(source_doctype, source_name)
	doc.check_permission("read")

	if is_source_internal_job_linked_to_main(doc):
		return {
			"choices": [],
			"blocked_message": _source_internal_job_nested_block_message(),
		}

	from logistics.utils.sales_quote_service_eligibility import get_quote_module_flags

	flags = get_quote_module_flags(
		getattr(doc, "sales_quote", None),
		source_doctype=source_doctype,
		source_name=source_name,
	)

	choices: list[dict[str, Any]] = []
	if _uses_linked_charge_internal_job_create(source_doctype):
		row_iter = _linked_charge_groups_for_create(doc)
	else:
		row_iter = _all_internal_job_detail_rows_for_form(doc, internal_job_details)

	for idx, row in row_iter:
		st = (getattr(row, "service_type", None) or "").strip()
		if isinstance(row, dict):
			st = (row.get("service_type") or st or "").strip()
		jt = effective_internal_job_detail_job_type(row)
		if _uses_linked_charge_internal_job_create(source_doctype):
			jn = _job_no_for_linked_charge_row(row)
		else:
			jn = (getattr(row, "job_no", None) or "").strip()
			if isinstance(row, dict):
				jn = (row.get("job_no") or jn or "").strip()
		not_creatable_message: str | None = None
		if jn:
			creatable = False
		else:
			creatable = bool(st) and bool(jt) and _job_type_allowed_for_source(source_doctype, doc, jt, flags)
			if creatable:
				from logistics.utils.internal_job_creation_eligibility import (
					evaluate_internal_job_eligibility_for_create,
				)

				service_label = _SERVICE_LABEL_FOR_JOB_TYPE.get(jt)
				ls_doc = _linked_service_doc_for_row(row) if _uses_linked_charge_internal_job_create(source_doctype) else None
				elig = evaluate_internal_job_eligibility_for_create(
					sales_quote=getattr(doc, "sales_quote", None),
					parent_doc=doc,
					ij_row=row,
					linked_service_doc=ls_doc,
					service_type_label=service_label or st,
					uses_linked_charge_create=_uses_linked_charge_internal_job_create(source_doctype),
				)
				if not elig.get("eligible"):
					creatable = False
					not_creatable_message = elig.get("message") or INTERNAL_JOB_QUOTE_PARAMETER_MISMATCH_MESSAGE
		label = _choice_label(jt, row, idx)
		if jt and not creatable and not jn:
			label = "{0} — {1}".format(label, _("cannot create from here"))
		header = _choice_header_fields(jt, row, idx)
		if not_creatable_message:
			header = {
				**header,
				"header_subtitle": not_creatable_message,
			}
		if jn and linked_internal_job_target_is_cancelled(jt, jn):
			header = {
				**header,
				"header_subtitle": _("Linked to {0} (cancelled).").format(jn),
				"linked_job_cancelled": True,
			}
		ij_link_for_row = ""
		if row is not None:
			from logistics.utils.linked_service_compat import row_linked_service_link

			ij_link_for_row = row_linked_service_link(row)
		row_container_no = (getattr(row, "container_no", None) or "").strip()
		if isinstance(row, dict):
			row_container_no = (row.get("container_no") or row_container_no or "").strip()
		choice: dict[str, Any] = {
			"mode": "detail",
			"detail_idx": idx,
			"job_type": jt,
			"service_type": st or None,
			"job_no": jn or None,
			"internal_job": ij_link_for_row or None,
			"label": label,
			"creatable": creatable,
			**header,
		}
		if row_container_no:
			choice["container_no"] = row_container_no
		if not_creatable_message:
			choice["not_creatable_message"] = not_creatable_message
		choices.append(choice)

	result: dict[str, Any] = {"choices": choices}
	if not choices:
		result["blocked_message"] = _empty_internal_job_create_blocked_message(doc)
	return result


def _job_preview_parameters_for_display(params: dict[str, Any] | None) -> dict[str, Any]:
	"""Strip charge_group from Create Internal Job preview (not part of Internal Job Detail anymore)."""
	if not params:
		return {}
	return {k: v for k, v in params.items() if k != "charge_group"}


def _charges_preview_list(
	parent_doc: Any,
	service_lower: str,
	routing_params: dict[str, Any],
	ij_row: Any | None = None,
	service_label: str | None = None,
) -> list[dict[str, Any]]:
	"""Charge rows that will be copied onto a new Internal Job (used by the Create > Internal Job dialog).

	Selection order:

	1. **Internal Job ID tag on parent** — when ``ij_row.internal_job`` is set and the parent already
	   carries charge rows tagged with that link (``charge_scope='Internal Job'`` and
	   ``internal_job == ij_row.internal_job``), those rows are the source of truth (they were placed
	   on the parent by a previous "Get Charges from Quotation" run on the Main).
	2. **Sales Quote pull by IJ ID** — when the IJ row carries an ``internal_job`` link but the parent
	   has no rows tagged with it, pull rows directly from the Sales Quote that match the IJ row's
	   service type and parameters. This is what
	   :func:`logistics.utils.charge_service_type.filter_sales_quote_charge_rows_for_operational_doc`
	   will materialise onto the new Internal Job Booking/Order, so the preview stays accurate even
	   before any GCFQ run on the Main.
	3. **Legacy parameter match against parent charges** — fallback for callers without an IJ link.
	4. **Sales Quote fallback (no IJ link)** — last resort for callers without an IJ link and a parent
	   that has no matching rows.

	``service_label`` is the canonical Title-Case service name used by
	:func:`extract_service_scoped_quote_parameters`; when omitted, falls back to ``service_lower.title()``.
	"""
	from frappe.utils import flt

	from logistics.utils.sales_quote_charge_parameters import (
		extract_service_scoped_quote_parameters,
		sales_quote_charge_row_matches_internal_job_detail_params,
	)
	from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal

	params = dict(routing_params or {})
	ij_match_params: dict[str, Any] = {}
	svc_label = service_label or (service_lower.title() if service_lower else "")
	if ij_row is not None and svc_label:
		ij_match_params = extract_service_scoped_quote_parameters(ij_row, svc_label)

	ij_link = ""
	if ij_row is not None:
		from logistics.utils.linked_service_compat import row_linked_service_link

		ij_link = row_linked_service_link(ij_row)

	def _row_to_preview(ch: Any) -> dict[str, Any]:
		return {
			"service_type": getattr(ch, "service_type", None) or (
				ch.get("service_type") if isinstance(ch, dict) else None
			),
			"item_code": getattr(ch, "item_code", None) or (
				ch.get("item_code") if isinstance(ch, dict) else None
			),
			"item_name": getattr(ch, "item_name", None) or (
				ch.get("item_name") if isinstance(ch, dict) else None
			),
			"unit_rate": flt(
				getattr(ch, "unit_rate", None)
				if not isinstance(ch, dict)
				else ch.get("unit_rate")
			)
			or None,
			"per_unit_rate": flt(
				getattr(ch, "per_unit_rate", None)
				if not isinstance(ch, dict)
				else ch.get("per_unit_rate")
			)
			or None,
			"currency": getattr(ch, "currency", None) or (
				ch.get("currency") if isinstance(ch, dict) else None
			),
			"selling_currency": getattr(ch, "selling_currency", None) or (
				ch.get("selling_currency") if isinstance(ch, dict) else None
			),
			"estimated_revenue": flt(
				getattr(ch, "estimated_revenue", None)
				if not isinstance(ch, dict)
				else ch.get("estimated_revenue")
			)
			or None,
			"parameters": params,
		}

	# Step 1 — Linked Service–tagged rows on the parent (canonical when GCFQ has already run on the Main).
	if ij_link:
		from logistics.utils.linked_service_compat import charge_row_linked_service_link

		tagged: list[dict[str, Any]] = []
		for ch in getattr(parent_doc, "charges", None) or []:
			row_ij = charge_row_linked_service_link(ch)
			if row_ij != ij_link:
				continue
			st = (getattr(ch, "service_type", None) or "").strip().lower()
			if st and service_lower and st != service_lower:
				continue
			tagged.append(_row_to_preview(ch))
		if tagged:
			return tagged

	# Step 2 — Sales Quote pull (mirrors what the create endpoint will materialise).
	# When the IJ row carries an ``internal_job`` link, we go straight to the Sales Quote so the
	# preview reflects the rows that will be copied onto the new Internal Job Booking. The parent's
	# own ``charges`` rows are scope=Main and don't carry the SQ parameter columns, so matching them
	# by IJ params yields false-positive wildcards.
	sq_name = coerce_sales_quote_name(getattr(parent_doc, "sales_quote", None))
	if ij_link and sq_name and svc_label and frappe.db.exists("Sales Quote", sq_name):
		try:
			sq_doc = frappe.get_cached_doc("Sales Quote", sq_name)
		except Exception:
			sq_doc = None
		if sq_doc is not None:
			sq_out: list[dict[str, Any]] = []
			for ch in sq_doc.get("charges") or []:
				if not sales_quote_charge_service_types_equal(
					getattr(ch, "service_type", None), svc_label
				):
					continue
				if ij_match_params and not sales_quote_charge_row_matches_internal_job_detail_params(
					ch, ij_match_params
				):
					continue
				sq_out.append(_row_to_preview(ch))
			if sq_out:
				return sq_out

	# Step 3 — Parameter match against the parent's charges (Linked scope on freight shipments).
	out: list[dict[str, Any]] = []
	from logistics.utils.linked_service_compat import is_linked_charge_scope, normalize_charge_scope

	linked_charge_parent = _uses_linked_charge_internal_job_create(
		getattr(parent_doc, "doctype", None) or ""
	)
	for ch in getattr(parent_doc, "charges", None) or []:
		if linked_charge_parent:
			scope = normalize_charge_scope(getattr(ch, "charge_scope", None))
			if not is_linked_charge_scope(scope):
				continue
		from logistics.utils.linked_service_compat import charge_row_linked_service_link

		row_ij = charge_row_linked_service_link(ch)
		if row_ij and ij_link and row_ij != ij_link:
			# Tagged for a different IJ → skip in this preview.
			continue
		st = (getattr(ch, "service_type", None) or "").strip().lower()
		if st != service_lower:
			continue
		if ij_match_params and not sales_quote_charge_row_matches_internal_job_detail_params(
			ch, ij_match_params
		):
			continue
		out.append(_row_to_preview(ch))
	if out:
		return out

	# Step 4 — Sales Quote fallback when there's no IJ link (legacy callers).
	if not sq_name or not svc_label or not frappe.db.exists("Sales Quote", sq_name):
		return out
	try:
		sq_doc = frappe.get_cached_doc("Sales Quote", sq_name)
	except Exception:
		return out
	sq_out2: list[dict[str, Any]] = []
	for ch in sq_doc.get("charges") or []:
		if not sales_quote_charge_service_types_equal(getattr(ch, "service_type", None), svc_label):
			continue
		if ij_match_params and not sales_quote_charge_row_matches_internal_job_detail_params(
			ch, ij_match_params
		):
			continue
		sq_out2.append(_row_to_preview(ch))
	return sq_out2


@frappe.whitelist()
def get_internal_job_creation_preview(
	source_doctype: str,
	source_name: str,
	job_type: str,
	internal_job_detail_idx: int | None = None,
	internal_job_details: Any = None,
):
	"""Job-detail parameters and parent charge rows that will be copied into the new internal job."""
	if not source_name or not frappe.db.exists(source_doctype, source_name):
		frappe.throw(_("Invalid source document."))
	if source_doctype not in ("Air Shipment", "Sea Shipment", "Transport Job", "Declaration"):
		frappe.throw(_("Unsupported source type."))

	doc = frappe.get_doc(source_doctype, source_name)
	doc.check_permission("read")

	if is_source_internal_job_linked_to_main(doc):
		idx_block = coerce_internal_job_detail_idx(internal_job_detail_idx)
		customer = getattr(doc, "local_customer", None) or getattr(doc, "customer", None)
		jt_preview = (job_type or "").strip()
		return {
			"job_type": jt_preview,
			"detail_idx": idx_block,
			"uses_job_detail_row": idx_block is not None,
			"creatable": False,
			"not_creatable_message": _source_internal_job_nested_block_message(),
			"source_context": {
				"source_doctype": source_doctype,
				"source_name": source_name,
				"customer": customer,
				"company": getattr(doc, "company", None),
				"sales_quote": getattr(doc, "sales_quote", None),
				**_source_service_role_context(doc),
				"from_main_service_shipment": False,
			},
			"target_internal_job": None,
			"job_detail_parameters": {},
			"charges": [],
		}

	from logistics.utils.sales_quote_service_eligibility import get_quote_module_flags

	flags = get_quote_module_flags(
		getattr(doc, "sales_quote", None),
		source_doctype=source_doctype,
		source_name=source_name,
	)

	jt = (job_type or "").strip()
	idx = coerce_internal_job_detail_idx(internal_job_detail_idx)

	with internal_job_details_client_rows(internal_job_details):
		return _get_internal_job_creation_preview_body(
			source_doctype,
			source_name,
			doc,
			flags,
			jt,
			idx,
		)


def _get_internal_job_creation_preview_body(
	source_doctype: str,
	source_name: str,
	doc: Any,
	flags: dict[str, Any],
	jt: str,
	idx: int | None,
) -> dict[str, Any]:
	from logistics.utils import module_integration as mi

	def _line_only_preview(
		row: Any,
		res_idx: int,
		*,
		message: str,
		job_type_label: str | None = None,
		linked_job_cancelled: bool = False,
	) -> dict[str, Any]:
		params = extract_sales_quote_charge_parameters(row) if row else {}
		preview_params = _job_preview_parameters_for_display(params)
		customer = getattr(doc, "local_customer", None) or getattr(doc, "customer", None)
		jtl = (job_type_label if job_type_label is not None else jt) or ""
		if not jtl and row is not None:
			jtl = effective_internal_job_detail_job_type(row)
		ij_link_for_row = ""
		if row is not None:
			from logistics.utils.linked_service_compat import row_linked_service_link

			ij_link_for_row = row_linked_service_link(row)
		out: dict[str, Any] = {
			"job_type": jtl,
			"detail_idx": res_idx,
			"uses_job_detail_row": True,
			"creatable": False,
			"not_creatable_message": message,
			"internal_job": ij_link_for_row or None,
			"source_context": {
				"source_doctype": source_doctype,
				"source_name": source_name,
				"customer": customer,
				"company": getattr(doc, "company", None),
				"sales_quote": getattr(doc, "sales_quote", None),
				**_source_service_role_context(doc),
				"from_main_service_shipment": False,
			},
			"target_internal_job": None,
			"job_detail_parameters": preview_params,
			"charges": [],
		}
		if linked_job_cancelled:
			out["linked_job_cancelled"] = True
		return out

	if idx is not None:
		rows_ij = _ij_rows_list(doc)
		if 1 <= idx <= len(rows_ij):
			row_linked = rows_ij[idx - 1]
			jn_linked = (getattr(row_linked, "job_no", None) or "").strip()
			if jn_linked:
				row_jt = effective_internal_job_detail_job_type(row_linked)
				jtl = (jt or "").strip() or row_jt
				cancelled = linked_internal_job_target_is_cancelled(row_jt, jn_linked)
				msg = _("This line is already linked to {0}.").format(jn_linked)
				if cancelled:
					msg = _("This line still references {0}, which is cancelled. Reload this document if the link should have been removed.").format(
						jn_linked
					)
				return _line_only_preview(
					row_linked,
					idx,
					message=msg,
					job_type_label=jtl or row_jt,
					linked_job_cancelled=cancelled,
				)

	if not jt:
		if idx is None:
			frappe.throw(_("Invalid selection."))
		rows = _ij_rows_list(doc)
		if idx < 1 or idx > len(rows):
			frappe.throw(_("Invalid Internal Job Detail row."))
		row = rows[idx - 1]
		if (getattr(row, "job_no", None) or "").strip():
			frappe.throw(_("This Internal Job Detail line already has a Job No."))
		return _line_only_preview(
			row,
			idx,
			message=_("Set Service Type on this line before creating."),
			job_type_label="",
		)

	if jt not in CREATABLE_INTERNAL_JOB_TYPES:
		if idx is None:
			frappe.throw(_("Invalid job type."))
		row = resolve_internal_job_detail_row(doc, idx, jt)
		return _line_only_preview(
			row,
			idx,
			message=_(
				"This job type cannot be created from this screen. Create or link the job another way, or choose a supported type."
			),
		)

	if (
		idx is not None
		and jt in CREATABLE_INTERNAL_JOB_TYPES
		and not _job_type_allowed_for_source(source_doctype, doc, jt, flags)
	):
		row = resolve_internal_job_detail_row(doc, idx, jt)
		return _line_only_preview(
			row,
			idx,
			message=_(
				"This option is not available for the current source (for example, sales quote, linked declaration, or module flags)."
			),
		)

	svc = _SERVICE_LOWER_FOR_JOB_TYPE[jt]

	ij_row, res_idx = resolve_internal_job_detail_row_for_create(doc, jt, idx)

	routing_params: dict[str, Any] = extract_sales_quote_charge_parameters(ij_row) if ij_row else {}
	from_main = False
	from logistics.utils.service_role_rules import (
		SERVICE_ROLE_LINKED,
		get_main_service_name,
		get_main_service_type,
		get_service_role,
	)

	# Client-compat keys (is_internal_job / main_job_*); values derived from service_role helpers.
	ij, mjt, mj = (
		1 if get_service_role(doc) == SERVICE_ROLE_LINKED else 0,
		get_main_service_type(doc) or None,
		get_main_service_name(doc) or None,
	)
	target_internal: dict[str, Any] | None = None

	if source_doctype in ("Air Shipment", "Sea Shipment"):
		if jt == "Transport Order":
			ij, mjt, mj = mi.final_transport_order_job_context_from_freight_shipment(
				doc, source_doctype, source_name
			)
			ij, mjt, mj = mi.resolve_transport_order_freight_main_job_if_empty(
				doc, source_doctype, source_name, ij, mjt, mj
			)
			from_main = mi._preview_from_main_service_internal_for_target(doc, "transport")
			target_internal = {"is_internal_job": bool(ij), "main_job_type": mjt, "main_job": mj}
		elif jt == "Declaration Order":
			ij, mjt, mj = mi._declaration_order_job_context_from_freight_shipment(doc, source_doctype, source_name)
			from_main = mi._preview_from_main_service_internal_for_target(doc, "customs")
			target_internal = {"is_internal_job": bool(ij), "main_job_type": mjt, "main_job": mj}
		elif jt == "VAS Order":
			ij, mjt, mj = mi.final_inbound_order_job_context_from_freight_shipment(
				doc, source_doctype, source_name
			)
			ij, mjt, mj = mi.resolve_inbound_order_freight_main_job_if_empty(
				doc, source_doctype, source_name, ij, mjt, mj
			)
			if not ij:
				ij, mjt, mj = 1, source_doctype, source_name
			from_main = True
			target_internal = {"is_internal_job": bool(ij), "main_job_type": mjt, "main_job": mj}
		else:
			target_internal = None
	elif source_doctype == "Transport Job":
		if jt in ("Declaration Order", "Transport Order", "VAS Order"):
			target_internal = {
				"is_internal_job": True,
				"main_job_type": "Transport Job",
				"main_job": doc.name,
			}
	elif source_doctype == "Declaration":
		if jt == "Transport Order" and (
			get_service_role(doc) == SERVICE_ROLE_LINKED or ij_row is not None
		):
			target_internal = {
				"is_internal_job": True,
				"main_job_type": "Declaration",
				"main_job": doc.name,
			}
		elif jt == "VAS Order":
			target_internal = {
				"is_internal_job": True,
				"main_job_type": "Declaration",
				"main_job": doc.name,
			}

	customer = getattr(doc, "local_customer", None) or getattr(doc, "customer", None)
	# Per-scope alignment: the preview now reflects what the create endpoint will copy by
	# filtering the parent's charges through the IJ row's parameters (when present).
	_SERVICE_LABEL_FOR_LOWER = {
		"air": "Air",
		"sea": "Sea",
		"transport": "Transport",
		"customs": "Customs",
		"warehousing": "Warehousing",
	}
	charges = _charges_preview_list(
		doc,
		svc,
		routing_params,
		ij_row=ij_row,
		service_label=_SERVICE_LABEL_FOR_LOWER.get(svc, svc.title() if svc else ""),
	)
	preview_params = _job_preview_parameters_for_display(routing_params)
	charges_for_preview = [{**c, "parameters": preview_params} for c in charges]

	ij_link_for_preview = ""
	if ij_row is not None:
		if isinstance(ij_row, dict):
			ij_link_for_preview = (ij_row.get("internal_job") or "").strip()
		else:
			ij_link_for_preview = (getattr(ij_row, "internal_job", None) or "").strip()

	from logistics.utils.internal_job_creation_eligibility import apply_eligibility_to_preview_flags

	service_label = _SERVICE_LABEL_FOR_LOWER.get(svc, svc.title() if svc else "")
	preview = {
		"job_type": jt,
		"detail_idx": res_idx,
		"uses_job_detail_row": ij_row is not None,
		"creatable": True,
		"internal_job": ij_link_for_preview or None,
		"source_context": {
			"source_doctype": source_doctype,
			"source_name": source_name,
			"customer": customer,
			"company": getattr(doc, "company", None),
			"sales_quote": getattr(doc, "sales_quote", None),
			**_source_service_role_context(doc),
			"from_main_service_shipment": from_main,
		},
		"target_internal_job": target_internal,
		"job_detail_parameters": preview_params,
		"charges": charges_for_preview,
	}
	return apply_eligibility_to_preview_flags(
		preview,
		sales_quote=getattr(doc, "sales_quote", None),
		parent_doc=doc,
		ij_row=ij_row,
		service_type_label=service_label,
		uses_linked_charge_create=_uses_linked_charge_internal_job_create(source_doctype),
	)


@frappe.whitelist()
def create_internal_job_from_operational_source(
	source_doctype: str,
	source_name: str,
	job_type: str,
	internal_job_detail_idx: int | None = None,
	internal_job_details: Any = None,
	container_no: str | None = None,
):
	"""Dispatch create by source + job type; optional 1-based Internal Job Detail row index applies row defaults."""
	jt = (job_type or "").strip()
	if jt not in CREATABLE_INTERNAL_JOB_TYPES:
		frappe.throw(_("Invalid job type."))

	if not source_name or not frappe.db.exists(source_doctype, source_name):
		frappe.throw(_("Invalid source document."))
	if source_doctype not in ("Air Shipment", "Sea Shipment", "Transport Job", "Declaration"):
		frappe.throw(_("Unsupported source type."))
	_src = frappe.get_doc(source_doctype, source_name)
	_src.check_permission("read")
	ensure_operational_source_can_create_internal_job(_src)

	idx = coerce_internal_job_detail_idx(internal_job_detail_idx)

	from logistics.utils import module_integration as mi

	with internal_job_details_client_rows(internal_job_details):
		validate_internal_job_detail_params_match_quotation(_src, jt, idx)
		if source_doctype == "Air Shipment":
			if jt == "Transport Order":
				return mi.create_transport_order_from_air_shipment(
					source_name, internal_job_detail_idx=idx
				)
			if jt == "Declaration Order":
				return mi.create_declaration_order_from_air_shipment(
					source_name, internal_job_detail_idx=idx
				)
			if jt == "Sea Booking":
				return _create_sea_booking_from_air_shipment(source_name, internal_job_detail_idx=idx)
			if jt == "Air Booking":
				# Same-mode IJ (e.g. Domestic Air leg under Import Air Main).
				return _create_air_booking_from_air_shipment(source_name, internal_job_detail_idx=idx)
			if jt == "VAS Order":
				return mi.create_vas_order_from_air_shipment(
					source_name, internal_job_detail_idx=idx
				)
		if source_doctype == "Sea Shipment":
			if jt == "Transport Order":
				return mi.create_transport_order_from_sea_shipment(
					source_name, internal_job_detail_idx=idx, container_no=container_no
				)
			if jt == "Declaration Order":
				return mi.create_declaration_order_from_sea_shipment(
					source_name, internal_job_detail_idx=idx
				)
			if jt == "Air Booking":
				return _create_air_booking_from_sea_shipment(source_name, internal_job_detail_idx=idx)
			if jt == "Sea Booking":
				# Same-mode IJ (e.g. Domestic Sea leg under Import Sea Main).
				return _create_sea_booking_from_sea_shipment(source_name, internal_job_detail_idx=idx)
			if jt == "VAS Order":
				return mi.create_vas_order_from_sea_shipment(
					source_name, internal_job_detail_idx=idx
				)
		if source_doctype == "Transport Job":
			if jt == "Transport Order":
				return _create_transport_order_from_transport_job(source_name, internal_job_detail_idx=idx)
			if jt == "Declaration Order":
				return _create_declaration_order_from_transport_job(source_name, internal_job_detail_idx=idx)
			if jt == "Air Booking":
				return _create_air_booking_from_transport_job(source_name, internal_job_detail_idx=idx)
			if jt == "Sea Booking":
				return _create_sea_booking_from_transport_job(source_name, internal_job_detail_idx=idx)
			if jt == "VAS Order":
				return mi.create_vas_order_from_transport_job(
					source_name, internal_job_detail_idx=idx
				)
		if source_doctype == "Declaration":
			if jt == "Transport Order":
				return mi.create_transport_order_from_declaration(
					source_name, internal_job_detail_idx=idx
				)
			if jt == "VAS Order":
				return mi.create_vas_order_from_declaration(
					source_name, internal_job_detail_idx=idx
				)

	frappe.throw(_("Unsupported source type."))


def _populate_sea_booking_charges_from_linked_quote_on_internal_create(doc) -> None:
	"""Apply Sales Quote routing and Sea charges when an internal Sea Booking is created from another job.

	Mirrors the ``sales_quote`` ``on_change`` / fetch-quotations path so charges are not left empty
	just because the link was set before the first save (no ``has_value_changed``).
	Prefers Sea ``service_type`` charge rows copied from the Main Job when present, otherwise Sales Quote.
	Routing is always applied from the linked quote when legs exist (independent of charge overlay).
	"""
	from logistics.utils.internal_job_charge_copy import (
		populate_internal_job_charges_from_main_service,
		should_apply_internal_job_main_charge_overlay,
	)
	from logistics.utils.sales_quote_routing import (
		apply_linked_sales_quote_routing_to_booking,
		apply_main_job_routing_operational_overlay,
	)

	apply_linked_sales_quote_routing_to_booking(doc)
	apply_main_job_routing_operational_overlay(doc)

	overlay_populated = False
	if should_apply_internal_job_main_charge_overlay(doc):
		try:
			n, _st = populate_internal_job_charges_from_main_service(doc)
			if n:
				overlay_populated = True
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				"Sea Booking internal job — charges from Main Job on create",
			)

	if overlay_populated:
		return

	sq_name = getattr(doc, "sales_quote", None)
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return
	try:
		doc._populate_charges_from_sales_quote_doc()
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			"Sea Booking internal job — charge population on create",
		)


def _populate_air_booking_charges_from_linked_quote_on_internal_create(doc) -> None:
	"""Apply Sales Quote routing and Air charges when an internal Air Booking is created from another job.

	Mirrors the internal Sea Booking create path so charges are not left empty because ``sales_quote``
	was set before the first save (``on_change`` does not run without ``has_value_changed``).
	Prefers Air ``service_type`` charge rows copied from the Main Job when present, otherwise Sales Quote.
	Routing is always applied from the linked quote when legs exist (independent of charge overlay).
	"""
	from logistics.utils.internal_job_charge_copy import (
		populate_internal_job_charges_from_main_service,
		should_apply_internal_job_main_charge_overlay,
	)
	from logistics.utils.sales_quote_routing import (
		apply_linked_sales_quote_routing_to_booking,
		apply_main_job_routing_operational_overlay,
	)

	apply_linked_sales_quote_routing_to_booking(doc)
	apply_main_job_routing_operational_overlay(doc)

	overlay_populated = False
	if should_apply_internal_job_main_charge_overlay(doc):
		try:
			n, _st = populate_internal_job_charges_from_main_service(doc)
			if n:
				overlay_populated = True
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				"Air Booking internal job — charges from Main Job on create",
			)

	if overlay_populated:
		return

	sq_name = getattr(doc, "sales_quote", None)
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return
	try:
		doc._populate_charges_from_sales_quote(doc.sales_quote)
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			"Air Booking internal job — charge population on create",
		)


def _create_freight_booking_from_freight_shipment(
	source_doctype: str,
	source_name: str,
	target_doctype: str,
	target_service_lower: str,
	internal_job_detail_idx: int | None,
):
	"""Shared implementation for creating a freight Internal Job Booking from a freight Shipment.

	Covers all four combinations:

	* Sea Shipment → Air Booking (cross-mode)
	* Sea Shipment → Sea Booking (same-mode)
	* Air Shipment → Air Booking (same-mode)
	* Air Shipment → Sea Booking (cross-mode)

	Same-mode is unusual but valid: e.g. a Domestic Air leg under an Import Air Main. The
	``apply_internal_job_detail_row_to_operational_doc`` call below overwrites the header
	routing (origin/destination/direction) with the IJ Detail row's values, so the new booking
	carries its own corridor rather than the Main shipment's.
	"""
	shipment = frappe.get_doc(source_doctype, source_name)
	idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	row, resolved_idx = resolve_internal_job_detail_row_for_create(shipment, target_doctype, idx)
	if row is None and not _shipment_charge_matches_service(shipment, target_service_lower):
		frappe.throw(
			_("{0} is only available when this shipment has {1}-related charges or an Internal Job Detail line for {0}.").format(
				_(target_doctype), _(target_service_lower.title())
			)
		)
	doc = frappe.new_doc(target_doctype)
	doc.local_customer = shipment.local_customer
	doc.shipper = getattr(shipment, "shipper", None)
	doc.consignee = getattr(shipment, "consignee", None)
	doc.booking_date = shipment.booking_date or frappe.utils.today()
	doc.company = shipment.company or frappe.defaults.get_defaults().get("company")
	doc.branch = getattr(shipment, "branch", None)
	doc.cost_center = getattr(shipment, "cost_center", None)
	doc.profit_center = getattr(shipment, "profit_center", None)
	doc.project = getattr(shipment, "project", None)
	doc.origin_port = getattr(shipment, "origin_port", None)
	doc.destination_port = getattr(shipment, "destination_port", None)
	doc.direction = getattr(shipment, "direction", None)
	from logistics.utils.module_integration import copy_sales_quote_fields_to_target

	copy_sales_quote_fields_to_target(shipment, doc)
	_apply_internal_job_satellite_flags(doc, source_doctype, source_name)
	if row:
		apply_internal_job_detail_row_to_operational_doc(doc, row, overwrite=True)
	_copy_contacts_addresses_between_operational_docs(shipment, doc)
	_copy_packages_from_shipment_to_internal_freight_booking(shipment, doc)
	if target_doctype == "Air Booking":
		_populate_air_booking_charges_from_linked_quote_on_internal_create(doc)
	else:
		_populate_sea_booking_charges_from_linked_quote_on_internal_create(doc)
	doc.insert(ignore_permissions=True)
	persist_internal_job_create_back_link(
		source_doctype,
		source_name,
		target_doctype,
		doc.name,
		ij_row=row,
		detail_idx=resolved_idx,
	)
	frappe.db.commit()
	key = "air_booking" if target_doctype == "Air Booking" else "sea_booking"
	return {key: doc.name, "message": _("{0} {1} created.").format(_(target_doctype), doc.name)}


def _create_air_booking_from_sea_shipment(sea_shipment_name: str, internal_job_detail_idx: int | None):
	return _create_freight_booking_from_freight_shipment(
		"Sea Shipment", sea_shipment_name, "Air Booking", "air", internal_job_detail_idx
	)


def _create_sea_booking_from_air_shipment(air_shipment_name: str, internal_job_detail_idx: int | None):
	return _create_freight_booking_from_freight_shipment(
		"Air Shipment", air_shipment_name, "Sea Booking", "sea", internal_job_detail_idx
	)


def _create_air_booking_from_air_shipment(air_shipment_name: str, internal_job_detail_idx: int | None):
	"""Same-mode IJ: e.g. a Domestic Air leg under an Import Air Main."""
	return _create_freight_booking_from_freight_shipment(
		"Air Shipment", air_shipment_name, "Air Booking", "air", internal_job_detail_idx
	)


def _create_sea_booking_from_sea_shipment(sea_shipment_name: str, internal_job_detail_idx: int | None):
	"""Same-mode IJ: e.g. a Domestic Sea leg under an Import Sea Main."""
	return _create_freight_booking_from_freight_shipment(
		"Sea Shipment", sea_shipment_name, "Sea Booking", "sea", internal_job_detail_idx
	)


def _create_air_booking_from_transport_job(transport_job_name: str, internal_job_detail_idx: int | None):
	job = frappe.get_doc("Transport Job", transport_job_name)
	idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	row, resolved_idx = resolve_internal_job_detail_row_for_create(job, "Air Booking", idx)
	doc = frappe.new_doc("Air Booking")
	doc.local_customer = job.customer
	doc.shipper = getattr(job, "shipper", None)
	doc.consignee = getattr(job, "consignee", None)
	doc.booking_date = frappe.utils.today()
	doc.company = job.company or frappe.defaults.get_defaults().get("company")
	doc.branch = getattr(job, "branch", None)
	doc.cost_center = getattr(job, "cost_center", None)
	doc.profit_center = getattr(job, "profit_center", None)
	doc.project = getattr(job, "project", None)
	from logistics.utils.module_integration import copy_sales_quote_fields_to_target

	copy_sales_quote_fields_to_target(job, doc)
	_apply_internal_job_satellite_flags(doc, "Transport Job", job.name)
	if row:
		apply_internal_job_detail_row_to_operational_doc(doc, row, overwrite=True)
	if doc.sales_quote and not getattr(doc, "origin_port", None):
		try:
			sq = frappe.get_doc("Sales Quote", doc.sales_quote)
			doc.origin_port = getattr(sq, "origin_port", None) or doc.origin_port
			doc.destination_port = getattr(sq, "destination_port", None) or doc.destination_port
		except Exception:
			pass
	_populate_air_booking_charges_from_linked_quote_on_internal_create(doc)
	doc.insert(ignore_permissions=True)
	persist_internal_job_create_back_link(
		"Transport Job",
		transport_job_name,
		"Air Booking",
		doc.name,
		ij_row=row,
		detail_idx=resolved_idx,
	)
	frappe.db.commit()
	return {"air_booking": doc.name, "message": _("Air Booking {0} created.").format(doc.name)}


def _create_sea_booking_from_transport_job(transport_job_name: str, internal_job_detail_idx: int | None):
	job = frappe.get_doc("Transport Job", transport_job_name)
	idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	row, resolved_idx = resolve_internal_job_detail_row_for_create(job, "Sea Booking", idx)
	doc = frappe.new_doc("Sea Booking")
	doc.local_customer = job.customer
	doc.shipper = getattr(job, "shipper", None)
	doc.consignee = getattr(job, "consignee", None)
	doc.booking_date = frappe.utils.today()
	doc.company = job.company or frappe.defaults.get_defaults().get("company")
	doc.branch = getattr(job, "branch", None)
	doc.cost_center = getattr(job, "cost_center", None)
	doc.profit_center = getattr(job, "profit_center", None)
	doc.project = getattr(job, "project", None)
	from logistics.utils.module_integration import copy_sales_quote_fields_to_target

	copy_sales_quote_fields_to_target(job, doc)
	_apply_internal_job_satellite_flags(doc, "Transport Job", job.name)
	if row:
		apply_internal_job_detail_row_to_operational_doc(doc, row, overwrite=True)
	_populate_sea_booking_charges_from_linked_quote_on_internal_create(doc)
	doc.insert(ignore_permissions=True)
	persist_internal_job_create_back_link(
		"Transport Job",
		transport_job_name,
		"Sea Booking",
		doc.name,
		ij_row=row,
		detail_idx=resolved_idx,
	)
	frappe.db.commit()
	return {"sea_booking": doc.name, "message": _("Sea Booking {0} created.").format(doc.name)}


def _create_declaration_order_from_transport_job(transport_job_name: str, internal_job_detail_idx: int | None):
	from frappe.utils import today

	job = frappe.get_doc("Transport Job", transport_job_name)
	idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	row, resolved_idx = resolve_internal_job_detail_row_for_create(job, "Declaration Order", idx)
	order = frappe.new_doc("Declaration Order")
	_apply_internal_job_satellite_flags(order, "Transport Job", job.name)
	order.transport_mode = "Road"
	order.order_date = today()
	order.customer = job.customer
	order.sales_quote = getattr(job, "sales_quote", None)
	order.exporter_shipper = getattr(job, "shipper", None)
	order.importer_consignee = getattr(job, "consignee", None)
	if getattr(job, "company", None):
		order.company = job.company
	if getattr(job, "branch", None):
		order.branch = job.branch
	if getattr(job, "cost_center", None):
		order.cost_center = job.cost_center
	if getattr(job, "profit_center", None):
		order.profit_center = job.profit_center
	from logistics.utils.module_integration import copy_sales_quote_fields_to_target

	copy_sales_quote_fields_to_target(job, order)
	if row:
		apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	order.insert(ignore_permissions=True)
	persist_internal_job_create_back_link(
		"Transport Job",
		transport_job_name,
		"Declaration Order",
		order.name,
		ij_row=row,
		detail_idx=resolved_idx,
	)
	frappe.db.commit()
	return {"declaration_order": order.name, "message": _("Declaration Order {0} created.").format(order.name)}


def _create_transport_order_from_transport_job(transport_job_name: str, internal_job_detail_idx: int | None):
	job = frappe.get_doc("Transport Job", transport_job_name)
	idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	row, resolved_idx = resolve_internal_job_detail_row_for_create(job, "Transport Order", idx)
	if row is None:
		frappe.throw(
			_("No linked-service Transport charge line found for creating a Transport Order from this Transport Job.")
		)
	order = frappe.new_doc("Transport Order")
	order.customer = job.customer
	order.shipper = getattr(job, "shipper", None)
	order.consignee = getattr(job, "consignee", None)
	order.sales_quote = getattr(job, "sales_quote", None)
	order.company = job.company
	order.branch = job.branch
	order.cost_center = job.cost_center
	order.profit_center = job.profit_center
	order.scheduled_date = getattr(job, "scheduled_date", None) or frappe.utils.today()
	order.booking_date = frappe.utils.today()
	order.transport_job_type = "Non-Container"
	if getattr(job, "transport_mode", None):
		order.transport_mode = job.transport_mode
	if getattr(job, "load_type", None):
		order.load_type = job.load_type
	_apply_internal_job_satellite_flags(order, "Transport Job", job.name)
	from logistics.utils.module_integration import copy_sales_quote_fields_to_target
	from logistics.utils.transport_job_type import (
		apply_container_transport_context_to_order,
		set_internal_transport_order_draft_insert_flags,
	)

	copy_sales_quote_fields_to_target(job, order)
	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	apply_container_transport_context_to_order(order, row)
	set_internal_transport_order_draft_insert_flags(order)
	order.insert(ignore_permissions=True)
	persist_internal_job_create_back_link(
		"Transport Job",
		transport_job_name,
		"Transport Order",
		order.name,
		ij_row=row,
		detail_idx=resolved_idx,
	)
	frappe.db.commit()
	return {"transport_order": order.name, "message": _("Transport Order {0} created.").format(order.name)}
