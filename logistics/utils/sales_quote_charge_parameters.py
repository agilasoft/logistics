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
		"transport_template",
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


def extract_sales_quote_charge_parameters(row: Any) -> dict[str, Any]:
	"""Non-empty parameter values from a Sales Quote Charge row (dict or document)."""
	out: dict[str, Any] = {}
	for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS:
		val = _row_val(row, fn)
		if not _is_meaningful_param_value(fn, val):
			continue
		out[fn] = val
	return out


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


def any_sales_quote_charge_matches_internal_job_detail_params(
	sales_quote: str | None,
	ij_row: Any,
	service_type_label: str,
) -> bool:
	"""True when at least one Sales Quote Charge row matches the Internal Job Detail parameters."""
	from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal

	sq_name = (sales_quote or "").strip()
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

	sq_name = (sales_quote or "").strip()
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
	sales_quote: str | None,
	params: dict[str, Any] | None,
	service_type_label: str,
) -> bool:
	"""True when at least one Sales Quote Charge row matches a parameter dict."""
	sq_name = (sales_quote or "").strip()
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
		row_st = (_row_val(row, "service_type") or st or "").strip()
		return extract_service_scoped_quote_parameters(row, row_st)
	return {}


def resolve_programme_charge_row_parameters(
	charge_row: Any, service_type_label: str | None = None
) -> dict[str, Any]:
	"""Routing parameters for a programme charge row, including linked CR / Sales Quote sources."""
	st = (service_type_label or _row_val(charge_row, "service_type") or "").strip()
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
