# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Sales Quote Charge parameter field names and JSON normalization (quote charge rows and routing leg JSON)."""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe.utils import flt

# Fields from Sales Quote Charge "parameter" sections (Air / Sea / common / Transport / Customs).
SALES_QUOTE_CHARGE_PARAMETER_FIELDS: tuple[str, ...] = (
	"charge_group",
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
	"location_type",
	"location_from",
	"location_to",
	"pick_mode",
	"drop_mode",
	"customs_authority",
	"declaration_type",
	"customs_broker",
	"customs_charge_category",
	"sp_site",
	"sp_manpower",
	"sp_skilled",
	"sp_equipment_type",
	"sp_handling",
	"sp_resource_notes",
)

# User-visible parameter fields per charge service (Lifecycle Job / Internal Job Detail / Sales Quote Charge).
_SERVICE_SCOPED_PARAMETER_FIELDS: dict[str, tuple[str, ...]] = {
	"air": (
		"air_house_type",
		"airline",
		"freight_agent",
		"load_type",
		"direction",
		"origin_port",
		"destination_port",
		"transport_mode",
	),
	"sea": (
		"sea_house_type",
		"freight_agent_sea",
		"shipping_line",
		"transport_mode",
		"load_type",
		"direction",
		"origin_port",
		"destination_port",
	),
	"transport": (
		"transport_mode",
		"transport_template",
		"load_type",
		"vehicle_type",
		"container_type",
		"container_no",
		"location_type",
		"location_from",
		"location_to",
		"pick_mode",
		"drop_mode",
	),
	"custom": (
		"customs_authority",
		"declaration_type",
		"customs_broker",
		"customs_charge_category",
	),
	"warehousing": (),
	"special project": (
		"sp_site",
		"sp_manpower",
		"sp_skilled",
		"sp_equipment_type",
		"sp_handling",
		"sp_resource_notes",
	),
	"exhibits": (
		"sp_site",
		"sp_manpower",
		"sp_skilled",
		"sp_equipment_type",
		"sp_handling",
		"sp_resource_notes",
	),
}

_ZERO_LIKE_PARAM_FIELDS: frozenset[str] = frozenset({"sp_manpower", "sp_skilled"})


def _row_val(row: Any, fieldname: str):
	if row is None:
		return None
	if isinstance(row, dict):
		return row.get(fieldname)
	return getattr(row, fieldname, None)


def filter_fields_existing_in_doctype(doctype: str, fields: list[str]) -> list[str]:
	"""Return only fieldnames that exist as columns on the doctype table.

	Legacy Sales Quote Air/Sea Freight child tables omit fields present on unified
	``Sales Quote Charge`` (e.g. ``service_type``). Using this avoids MySQL 1054
	when falling back to legacy tables.
	"""
	cols = frappe.db.get_table_columns(doctype)
	if not cols:
		return []
	allowed = set(cols)
	return [f for f in fields if f in allowed]


def _is_meaningful_param_value(fieldname: str, val: Any) -> bool:
	if val is None or val == "":
		return False
	if fieldname in _ZERO_LIKE_PARAM_FIELDS and flt(val) == 0:
		return False
	return True


def _param_values_equal(fieldname: str, charge_val: Any, ij_val: Any) -> bool:
	"""Compare routing parameter values (numeric fields use flt, others use trimmed str)."""
	if fieldname in _ZERO_LIKE_PARAM_FIELDS:
		return flt(charge_val) == flt(ij_val)
	return str(charge_val).strip() == str(ij_val).strip()


def parameter_fields_for_service_type(service_type_label: str) -> tuple[str, ...]:
	"""Parameter fieldnames users can set for this charge service type."""
	from logistics.utils.charge_service_type import canonical_charge_service_type_for_storage

	canonical = canonical_charge_service_type_for_storage(service_type_label)
	if not canonical:
		return ()
	return _SERVICE_SCOPED_PARAMETER_FIELDS.get(canonical, ())


def _extract_legacy_row_parameters(row: Any) -> dict[str, Any]:
	"""Read routing parameters stored on the charge row (pre-migration columns)."""
	out: dict[str, Any] = {}
	existing = set(
		filter_fields_existing_in_doctype("Sales Quote Charge", list(SALES_QUOTE_CHARGE_PARAMETER_FIELDS))
	)
	for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS:
		if fn not in existing:
			continue
		val = _row_val(row, fn)
		if not _is_meaningful_param_value(fn, val):
			continue
		out[fn] = val
	return out


def _extract_in_memory_row_parameters(row: Any) -> dict[str, Any]:
	"""Read routing parameters from a synthetic row (e.g. Sales Quote scope / virtual Services line)."""
	out: dict[str, Any] = {}
	for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS:
		val = _row_val(row, fn)
		if not _is_meaningful_param_value(fn, val):
			continue
		out[fn] = val
	return out


def resolve_parameters_for_charge_row(charge_row: Any, quote_doc: Any | None = None) -> dict[str, Any]:
	"""Routing parameters for a Sales Quote Charge from its tagged service (Main or Linked)."""
	from logistics.utils.linked_service_compat import (
		charge_row_linked_service_link,
		is_linked_charge_scope,
		linked_service_doctype,
		normalize_charge_scope,
	)

	service_type = (_row_val(charge_row, "service_type") or "").strip()
	scope = normalize_charge_scope(_row_val(charge_row, "charge_scope"))

	if is_linked_charge_scope(scope):
		ls_name = charge_row_linked_service_link(charge_row)
		dt = linked_service_doctype()
		if ls_name and frappe.db.exists(dt, ls_name):
			try:
				ls_doc = frappe.get_cached_doc(dt, ls_name)
				return extract_service_scoped_quote_parameters(ls_doc, service_type)
			except Exception:
				return {}
		return {}

	if quote_doc:
		return extract_service_scoped_quote_parameters(quote_doc, service_type)
	return {}


def resolve_change_request_charge_parameters(
	charge_row: Any, cr_doc: Any | None = None
) -> dict[str, Any]:
	"""Routing parameters for a Change Request Charge from its tagged service or linked job."""
	from logistics.utils.linked_service_compat import (
		CHARGE_SCOPE_MAIN,
		charge_row_linked_service_link,
		is_linked_charge_scope,
		linked_service_doctype,
		normalize_charge_scope,
	)

	service_type = (_row_val(charge_row, "service_type") or "").strip()
	scope = normalize_charge_scope(_row_val(charge_row, "charge_scope"))
	ls_name = charge_row_linked_service_link(charge_row)
	if not scope and ls_name:
		scope = "Linked"

	if is_linked_charge_scope(scope):
		dt = linked_service_doctype()
		if ls_name and frappe.db.exists(dt, ls_name):
			try:
				ls_doc = frappe.get_cached_doc(dt, ls_name)
				return extract_service_scoped_quote_parameters(ls_doc, service_type)
			except Exception:
				return {}
		return {}

	if scope == CHARGE_SCOPE_MAIN and cr_doc:
		try:
			from logistics.pricing_center.doctype.change_request.change_request import (
				_resolve_main_job_for_change_request,
			)

			main_type, main_name = _resolve_main_job_for_change_request(cr_doc)
			if main_type and main_name and frappe.db.exists(main_type, main_name):
				job_doc = frappe.get_cached_doc(main_type, main_name)
				return extract_service_scoped_quote_parameters(job_doc, service_type)
		except Exception:
			pass

	return _extract_legacy_row_parameters(charge_row)


def refresh_change_request_charge_parameters_display(
	charge_row: Any, cr_doc: Any | None = None
) -> str:
	"""Set and return the read-only ``parameters`` text for one CR charge row."""
	service_type = (_row_val(charge_row, "service_type") or "").strip()
	params = resolve_change_request_charge_parameters(charge_row, cr_doc)
	if not params:
		params = _extract_legacy_row_parameters(charge_row)
	text = format_parameters_display_text(params, service_type)
	if hasattr(charge_row, "parameters"):
		charge_row.parameters = text
	elif isinstance(charge_row, dict):
		charge_row["parameters"] = text
	return text


def effective_change_request_charge_row(charge_row: Any, cr_doc: Any | None = None) -> Any:
	"""Charge row merged with routing parameters resolved from Services / job scope."""
	params = resolve_change_request_charge_parameters(charge_row, cr_doc)
	if not params:
		return charge_row
	if isinstance(charge_row, dict):
		return frappe._dict({**charge_row, **params})
	if hasattr(charge_row, "as_dict"):
		return frappe._dict({**charge_row.as_dict(), **params})
	return frappe._dict({**{fn: getattr(charge_row, fn, None) for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS}, **params})


def extract_sales_quote_charge_parameters(row: Any, quote_doc: Any | None = None) -> dict[str, Any]:
	"""Non-empty routing parameters for a Sales Quote Charge row.

	When *quote_doc* is supplied, parameters are resolved from the tagged service
	(Main = quote scope header, Linked = Linked Service document). Otherwise falls
	back to legacy per-row columns when present.
	"""
	if quote_doc is not None:
		resolved = resolve_parameters_for_charge_row(row, quote_doc)
		if resolved:
			return resolved
	legacy = _extract_legacy_row_parameters(row)
	in_memory = _extract_in_memory_row_parameters(row)
	if in_memory:
		# Synthetic scope rows (Main Service virtual line) carry full parameters in memory while
		# legacy columns on the row may only expose charge_group after the parameter migration.
		if legacy:
			return {**legacy, **in_memory}
		return in_memory
	if legacy:
		return legacy
	if quote_doc is not None:
		return resolve_parameters_for_charge_row(row, quote_doc)
	return {}


# Target field renames when copying Sales Quote scope onto operational documents.
_OPERATIONAL_SCOPE_FIELD_ALIASES: dict[str, dict[str, str]] = {
	"Air Booking": {"air_house_type": "house_type"},
	"Sea Booking": {"sea_house_type": "house_type", "freight_agent_sea": "freight_agent"},
}


def resolve_operational_doc_scope_parameters(
	row: Any, quote_doc: Any | None = None
) -> dict[str, Any]:
	"""Routing parameters for applying a scope / virtual row onto an operational document."""
	params = extract_sales_quote_charge_parameters(row, quote_doc)
	in_memory = _extract_in_memory_row_parameters(row)
	if in_memory:
		params = {**(params or {}), **in_memory}
	return params or {}


def build_main_service_scope_row(
	quote_doc: Any,
	first_charge: Any | None = None,
	parent_overrides: dict[str, Any] | None = None,
) -> frappe._dict:
	"""Synthetic Main Service row from quote scope header (+ optional charge / override values)."""
	row = frappe._dict(resolve_parameters_from_sales_quote_scope(quote_doc))
	ms = (getattr(quote_doc, "main_service", None) or "").strip()
	if ms:
		row.service_type = ms
	if first_charge:
		for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS:
			if fn == "charge_group":
				continue
			val = _row_val(first_charge, fn)
			if _is_meaningful_param_value(fn, val):
				row[fn] = val
	if parent_overrides:
		for k, v in parent_overrides.items():
			if k == "charge_group":
				continue
			if v is not None and str(v).strip() != "":
				row[k] = v
	return row


_DOCTYPE_DEFAULT_SERVICE_TYPE: dict[str, str] = {
	"Air Booking": "Air",
	"Sea Booking": "Sea",
	"Transport Order": "Transport",
	"Declaration Order": "Customs",
	"Inbound Order": "Warehousing",
}


def apply_scope_fields_to_operational_doc(
	doc: Any, row: Any, *, overwrite: bool = False
) -> None:
	"""Copy Sales Quote Main Service scope parameters onto an operational document."""
	if not row or not doc:
		return
	params = resolve_operational_doc_scope_parameters(row)
	if not params:
		return
	meta = frappe.get_meta(doc.doctype)
	aliases = _OPERATIONAL_SCOPE_FIELD_ALIASES.get(doc.doctype, {})
	st = (_row_val(row, "service_type") or "").strip()
	if not st:
		st = _DOCTYPE_DEFAULT_SERVICE_TYPE.get(doc.doctype, "")

	def set_field(dest_fn: str, val: Any) -> None:
		if val is None or val == "":
			return
		if not meta.get_field(dest_fn):
			return
		cur = getattr(doc, dest_fn, None)
		if overwrite or cur is None or cur == "":
			doc.set(dest_fn, val)

	extra_cross_fields: tuple[str, ...] = ()
	if doc.doctype in ("Air Booking", "Sea Booking", "Transport Order"):
		extra_cross_fields = ("transport_mode", "direction")

	for src_fn in list(parameter_fields_for_service_type(st)) + list(extra_cross_fields):
		if src_fn == "charge_group" or src_fn not in params:
			continue
		dest_fn = aliases.get(src_fn, src_fn)
		set_field(dest_fn, params[src_fn])

	if doc.doctype == "Air Booking":
		if params.get("location_from") and not (getattr(doc, "origin_port", None) or "").strip():
			set_field("origin_port", params["location_from"])
		if params.get("location_to") and not (getattr(doc, "destination_port", None) or "").strip():
			set_field("destination_port", params["location_to"])
	elif doc.doctype == "Sea Booking":
		if params.get("location_from") and not (getattr(doc, "origin_port", None) or "").strip():
			set_field("origin_port", params["location_from"])
		if params.get("location_to") and not (getattr(doc, "destination_port", None) or "").strip():
			set_field("destination_port", params["location_to"])
	elif doc.doctype == "Transport Order":
		if params.get("location_from"):
			set_field("location_from", params["location_from"])
		elif params.get("origin_port"):
			set_field("location_from", params["origin_port"])
		if params.get("location_to"):
			set_field("location_to", params["location_to"])
		elif params.get("destination_port"):
			set_field("location_to", params["destination_port"])
		if (
			(getattr(doc, "location_from", None) or getattr(doc, "location_to", None))
			and not (getattr(doc, "location_type", None) or "").strip()
		):
			set_field("location_type", params.get("location_type") or "UNLOCO")
	elif st:
		for fn in parameter_fields_for_service_type(st):
			if fn in params and fn != "charge_group":
				set_field(fn, params[fn])


def merge_charge_row_parameters_onto_dict(
	source_row: Any,
	target: dict[str, Any],
	charge_doctype: str,
) -> None:
	"""Copy non-empty routing parameters onto *target* when the field exists on *charge_doctype*."""
	allowed = set(
		filter_fields_existing_in_doctype(charge_doctype, list(SALES_QUOTE_CHARGE_PARAMETER_FIELDS))
	)
	for fn, val in extract_sales_quote_charge_parameters(source_row).items():
		if fn in allowed:
			target[fn] = val


def extract_service_scoped_quote_parameters(row: Any, service_type_label: str) -> dict[str, Any]:
	"""Non-empty user-visible parameters for one service type (excludes hidden cross-service fields)."""
	out: dict[str, Any] = {}
	for fn in parameter_fields_for_service_type(service_type_label):
		if fn not in SALES_QUOTE_CHARGE_PARAMETER_FIELDS:
			continue
		val = _row_val(row, fn)
		if not _is_meaningful_param_value(fn, val):
			continue
		out[fn] = val
	return out


def normalize_quote_parameter_json(value: Any) -> dict[str, Any]:
	if not value:
		return {}
	if isinstance(value, dict):
		return dict(value)
	if isinstance(value, str):
		try:
			parsed = json.loads(value)
			return dict(parsed) if isinstance(parsed, dict) else {}
		except Exception:
			return {}
	return {}


def sales_quote_charge_row_matches_internal_job_detail_params(
	charge_row: Any, ij_params: dict[str, Any]
) -> bool:
	"""True when every non-empty Internal Job Detail parameter matches the charge row (blank charge field = wildcard)."""
	if not ij_params:
		return True
	charge_params = extract_sales_quote_charge_parameters(charge_row)
	for fieldname, ij_val in ij_params.items():
		if fieldname == "charge_group":
			continue
		if not _is_meaningful_param_value(fieldname, ij_val):
			continue
		charge_val = charge_params.get(fieldname)
		if charge_val is None or charge_val == "":
			continue
		if not _param_values_equal(fieldname, charge_val, ij_val):
			return False
	return True


def coerce_sales_quote_name(sales_quote: Any) -> str:
	"""Return a Sales Quote name from a link string, document, dict, or parent-like object."""
	from frappe.model.document import Document
	from frappe.utils import cstr

	if not sales_quote:
		return ""
	if isinstance(sales_quote, Document):
		return cstr(getattr(sales_quote, "name", None)).strip()
	if isinstance(sales_quote, str):
		return sales_quote.strip()
	if isinstance(sales_quote, dict):
		if cstr(sales_quote.get("doctype")).strip() == "Sales Quote":
			return cstr(sales_quote.get("name")).strip()
		link = sales_quote.get("sales_quote")
		return coerce_sales_quote_name(link) if link else ""
	doctype = cstr(getattr(sales_quote, "doctype", None)).strip()
	if doctype == "Sales Quote":
		return cstr(getattr(sales_quote, "name", None)).strip()
	link = getattr(sales_quote, "sales_quote", None)
	if link:
		return coerce_sales_quote_name(link)
	return ""


def any_sales_quote_charge_matches_internal_job_detail_params(
	sales_quote: str | Any | None,
	ij_row: Any,
	service_type_label: str,
) -> bool:
	"""True when at least one Sales Quote Charge row matches the Internal Job Detail parameters."""
	from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal

	sq_name = coerce_sales_quote_name(sales_quote)
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return True

	ij_params = extract_service_scoped_quote_parameters(ij_row, service_type_label)
	if not ij_params:
		return True

	sq = frappe.get_doc("Sales Quote", sq_name)
	rows = [
		r
		for r in (sq.get("charges") or [])
		if sales_quote_charge_service_types_equal(getattr(r, "service_type", None), service_type_label)
	]
	if not rows:
		return False
	return any(sales_quote_charge_row_matches_internal_job_detail_params(r, ij_params) for r in rows)


def extract_service_scoped_params_dict(
	params: dict[str, Any] | None, service_type_label: str
) -> dict[str, Any]:
	"""Non-empty service-scoped values from a plain parameter dict."""
	out: dict[str, Any] = {}
	for fn in parameter_fields_for_service_type(service_type_label):
		val = (params or {}).get(fn)
		if _is_meaningful_param_value(fn, val):
			out[fn] = val
	return out


def count_meaningful_service_scoped_params(
	params: dict[str, Any] | None, service_type_label: str
) -> int:
	return len(extract_service_scoped_params_dict(params, service_type_label))


def wildcard_fields_for_param_match(charge_row: Any, ij_params: dict[str, Any]) -> list[str]:
	"""Param keys the user set where the charge row field is blank (wildcard match)."""
	if not ij_params:
		return []
	charge_params = extract_sales_quote_charge_parameters(charge_row)
	wildcards: list[str] = []
	for fieldname, ij_val in ij_params.items():
		if fieldname == "charge_group":
			continue
		if not _is_meaningful_param_value(fieldname, ij_val):
			continue
		charge_val = charge_params.get(fieldname)
		if charge_val is None or charge_val == "":
			wildcards.append(fieldname)
	return wildcards


def matching_quote_charge_rows(
	sales_quote: str | None,
	service_type_label: str,
	params: dict[str, Any] | None,
) -> list[Any]:
	"""Sales Quote Charge rows matching service type and parameter dict."""
	from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal

	sq_name = coerce_sales_quote_name(sales_quote)
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return []
	scoped = extract_service_scoped_params_dict(params, service_type_label)
	if not scoped:
		return []
	try:
		sq = frappe.get_doc("Sales Quote", sq_name)
	except Exception:
		return []
	rows = [
		r
		for r in (sq.get("charges") or [])
		if sales_quote_charge_service_types_equal(getattr(r, "service_type", None), service_type_label)
	]
	return [r for r in rows if sales_quote_charge_row_matches_internal_job_detail_params(r, scoped)]


def collect_wildcard_fields_for_param_set(
	sales_quote: str | None,
	service_type_label: str,
	params: dict[str, Any] | None,
) -> list[str]:
	"""Union of wildcard field names across all matching quote charge rows."""
	seen: set[str] = set()
	out: list[str] = []
	for row in matching_quote_charge_rows(sales_quote, service_type_label, params):
		for fn in wildcard_fields_for_param_match(
			row, extract_service_scoped_params_dict(params, service_type_label)
		):
			if fn not in seen:
				seen.add(fn)
				out.append(fn)
	return out


def any_sales_quote_charge_matches_params_dict(
	sales_quote: str | Any | None,
	params: dict[str, Any] | None,
	service_type_label: str,
) -> bool:
	"""True when at least one Sales Quote Charge row matches a parameter dict."""
	sq_name = coerce_sales_quote_name(sales_quote)
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return True
	scoped = extract_service_scoped_params_dict(params, service_type_label)
	if not scoped:
		return True
	return bool(matching_quote_charge_rows(sq_name, service_type_label, scoped))


def _lookup_change_request_charge_parameters(
	charge_row: Any, service_type_label: str | None = None
) -> dict[str, Any]:
	"""Parameters from the linked Change Request Charge row (when programme row omits them)."""
	cr_name = (_row_val(charge_row, "change_request") or "").strip()
	crc_name = (_row_val(charge_row, "change_request_charge") or "").strip()
	if not cr_name or not crc_name or not frappe.db.exists("Change Request", cr_name):
		return {}
	try:
		cr_doc = frappe.get_doc("Change Request", cr_name)
	except Exception:
		return {}
	st = (service_type_label or _row_val(charge_row, "service_type") or "").strip()
	for row in cr_doc.get("charges") or []:
		if (_row_val(row, "name") or "").strip() != crc_name:
			continue
		return resolve_change_request_charge_parameters(row, cr_doc)
	return {}


def resolve_programme_charge_row_parameters(
	charge_row: Any, service_type_label: str | None = None
) -> dict[str, Any]:
	"""Routing parameters for a programme charge row, including linked service / CR / Sales Quote."""
	st = (service_type_label or _row_val(charge_row, "service_type") or "").strip()
	service_line = (_row_val(charge_row, "special_project_service_line") or "").strip()
	if service_line and frappe.db.exists("Special Project Service", service_line):
		try:
			service_doc = frappe.get_cached_doc("Special Project Service", service_line)
			resolved = extract_service_scoped_quote_parameters(service_doc, st)
			if resolved:
				return resolved
		except Exception:
			pass
	direct = (
		extract_service_scoped_quote_parameters(charge_row, st)
		if st
		else extract_sales_quote_charge_parameters(charge_row)
	)
	if direct:
		return direct
	from_cr = _lookup_change_request_charge_parameters(charge_row, st)
	if from_cr:
		return from_cr
	sq_link = (_row_val(charge_row, "sales_quote_link") or "").strip()
	if sq_link:
		sq_params = lookup_quote_parameters_for_operational_charge(sq_link, charge_row)
		if sq_params:
			return extract_service_scoped_quote_parameters(
				frappe._dict(sq_params), st
			) if st else sq_params
	return {}


def _effective_programme_charge_row(charge_row: Any, service_type_label: str | None = None) -> Any:
	"""Programme charge row merged with parameters resolved from CR / Sales Quote links."""
	resolved = resolve_programme_charge_row_parameters(charge_row, service_type_label)
	if not resolved:
		return charge_row
	if isinstance(charge_row, dict):
		return frappe._dict({**charge_row, **resolved})
	if hasattr(charge_row, "as_dict"):
		return frappe._dict({**charge_row.as_dict(), **resolved})
	return frappe._dict({**{k: getattr(charge_row, k, None) for k in SALES_QUOTE_CHARGE_PARAMETER_FIELDS}, **resolved})


def programme_charge_row_parameters(
	charge_row: Any, service_type_label: str | None = None
) -> dict[str, Any]:
	"""Non-empty routing parameters for a programme charge row (incl. linked CR / quote)."""
	return resolve_programme_charge_row_parameters(charge_row, service_type_label)


def matching_programme_charge_rows(
	sp_doc: Any,
	service_type_label: str,
	params: dict[str, Any] | None,
) -> list[Any]:
	"""Programme charge rows on the parent doc matching service type and parameters."""
	from logistics.special_projects.special_project_charge_lifecycle import (
		programme_charges_for_service_type,
	)
	from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal

	scoped = extract_service_scoped_params_dict(params, service_type_label)
	if not scoped:
		return []
	pool = programme_charges_for_service_type(sp_doc, service_type_label)
	return [
		ch
		for ch in pool
		if sales_quote_charge_service_types_equal(getattr(ch, "service_type", None), service_type_label)
		and sales_quote_charge_row_matches_internal_job_detail_params(
			_effective_programme_charge_row(ch, service_type_label), scoped
		)
	]


def any_programme_charge_matches_params_dict(
	sp_doc: Any,
	params: dict[str, Any] | None,
	service_type_label: str,
) -> bool:
	"""True when at least one programme charge row matches a parameter dict."""
	scoped = extract_service_scoped_params_dict(params, service_type_label)
	if not scoped:
		return True
	return bool(matching_programme_charge_rows(sp_doc, service_type_label, scoped))


def collect_wildcard_fields_for_programme_param_set(
	sp_doc: Any,
	service_type_label: str,
	params: dict[str, Any] | None,
) -> list[str]:
	"""Union of wildcard field names across matching programme charge rows."""
	scoped = extract_service_scoped_params_dict(params, service_type_label)
	if not scoped:
		return []
	seen: set[str] = set()
	out: list[str] = []
	for row in matching_programme_charge_rows(sp_doc, service_type_label, scoped):
		for fn in wildcard_fields_for_param_match(
			_effective_programme_charge_row(row, service_type_label), scoped
		):
			if fn not in seen:
				seen.add(fn)
				out.append(fn)
	return out


def programme_charge_matches_creation_parameters(
	charge: Any,
	params: dict[str, Any] | None,
) -> bool:
	"""True when a programme charge row matches the creation parameters (blank charge field = wildcard)."""
	scoped = params or {}
	if not scoped:
		return True
	st = (_row_val(charge, "service_type") or "").strip()
	return sales_quote_charge_row_matches_internal_job_detail_params(
		_effective_programme_charge_row(charge, st), scoped
	)


def lookup_quote_parameters_for_operational_charge(sales_quote: str | None, ch_row: Any) -> dict[str, Any]:
	"""Match Sales Quote Charge by item_code + service_type and return parameter dict."""
	if not sales_quote or not frappe.db.exists("Sales Quote", sales_quote):
		return {}
	item = getattr(ch_row, "item_code", None) or _row_val(ch_row, "item_code")
	st = (getattr(ch_row, "service_type", None) or _row_val(ch_row, "service_type") or "").strip()
	try:
		sq = frappe.get_doc("Sales Quote", sales_quote)
	except Exception:
		return {}
	for r in sq.get("charges") or []:
		if item and r.item_code != item:
			continue
		rst = (r.service_type or "").strip()
		if st and rst != st:
			continue
		return extract_sales_quote_charge_parameters(r)
	return {}


def resolve_parameters_from_sales_quote_scope(quote_doc: Any) -> dict[str, Any]:
	"""Read lane/scope parameters from Sales Quote Service Scope tab header fields."""
	if not quote_doc:
		return {}
	out: dict[str, Any] = {}
	for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS:
		val = getattr(quote_doc, fn, None)
		if val is not None and str(val).strip() != "":
			out[fn] = val
	return out


def _parameter_field_label(fieldname: str) -> str:
	for dt in ("Linked Service", "Sales Quote"):
		try:
			df = frappe.get_meta(dt).get_field(fieldname)
			if df and df.label:
				return str(df.label)
		except Exception:
			pass
	return fieldname.replace("_", " ").title()


def format_parameters_display_text(
	params: dict[str, Any] | None, service_type_label: str | None = None
) -> str:
	"""Human-readable multi-line summary for the charge ``parameters`` display field."""
	if not params:
		return ""
	scoped = (
		extract_service_scoped_params_dict(params, service_type_label or "")
		if service_type_label
		else params
	)
	if not scoped:
		scoped = {
			k: v
			for k, v in (params or {}).items()
			if k != "charge_group" and _is_meaningful_param_value(k, v)
		}
	if not scoped:
		return ""
	lines: list[str] = []
	for fn in sorted(scoped.keys()):
		if fn == "charge_group":
			continue
		val = scoped[fn]
		if not _is_meaningful_param_value(fn, val):
			continue
		lines.append(f"{_parameter_field_label(fn)}: {val}")
	return "\n".join(lines)


def refresh_sales_quote_charge_parameters_display(charge_row: Any, quote_doc: Any | None = None) -> str:
	"""Set and return the read-only ``parameters`` text for one charge row."""
	service_type = (_row_val(charge_row, "service_type") or "").strip()
	params = resolve_parameters_for_charge_row(charge_row, quote_doc)
	if not params:
		params = _extract_legacy_row_parameters(charge_row)
	text = format_parameters_display_text(params, service_type)
	if hasattr(charge_row, "parameters"):
		charge_row.parameters = text
	elif isinstance(charge_row, dict):
		charge_row["parameters"] = text
	return text


@frappe.whitelist()
def format_change_request_charge_parameters_display(
	charge_row=None, change_request_doc=None
) -> str:
	"""Desk helper: format parameters for a CR charge row."""
	if isinstance(charge_row, str):
		charge_row = frappe.parse_json(charge_row)
	if isinstance(change_request_doc, str):
		change_request_doc = frappe.parse_json(change_request_doc)
	if not charge_row:
		return ""
	cr_doc = change_request_doc
	if isinstance(cr_doc, dict) and cr_doc.get("name"):
		try:
			cr_doc = frappe.get_doc("Change Request", cr_doc["name"])
		except Exception:
			cr_doc = frappe._dict(change_request_doc)
	return refresh_change_request_charge_parameters_display(charge_row, cr_doc)


@frappe.whitelist()
def format_charge_parameters_display(charge_row=None, quote_doc=None) -> str:
	"""Desk helper: format parameters for a charge row given optional parent quote snapshot."""
	if isinstance(charge_row, str):
		charge_row = frappe.parse_json(charge_row)
	if isinstance(quote_doc, str):
		quote_doc = frappe.parse_json(quote_doc)
	if not charge_row:
		return ""
	service_type = ""
	if isinstance(charge_row, dict):
		service_type = (charge_row.get("service_type") or "").strip()
	else:
		service_type = (getattr(charge_row, "service_type", None) or "").strip()
	params = resolve_parameters_for_charge_row(charge_row, quote_doc)
	if not params:
		params = _extract_legacy_row_parameters(charge_row)
	return format_parameters_display_text(params, service_type)


def effective_charge_row_parameters(charge_row: Any, quote_doc: Any | None = None) -> dict[str, Any]:
	"""Routing parameters for a charge row (tagged service, with legacy row fallback)."""
	return extract_sales_quote_charge_parameters(charge_row, quote_doc)
