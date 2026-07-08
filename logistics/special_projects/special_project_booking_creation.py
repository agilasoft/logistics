# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Create Air/Sea Booking, Transport/Declaration/Inbound Order from Special Project Lifecycle Job rows.

Unlike the operational-job → internal-job flow in ``logistics.utils.internal_job_from_source``, bookings
and orders created from a Special Project are **standalone** (not internal jobs). They link back to the
project via the ``project`` field and reuse the Sales Quote / customer / accounting context from the
Special Project header.

The Lifecycle Job table (``special_project.lifecycle_jobs``) drives this flow: each row seeds a
booking/order; ``job_type`` / ``job_no`` record the linked document. Execution submit appends
child lifecycle rows and programme charge qty/logs.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, today

from logistics.special_projects.project_order_copy import (
	build_project_order_from_special_project,
	suggested_order_title_from_lifecycle_row,
)
from logistics.utils.charge_service_type import (
	effective_internal_job_detail_job_type,
	sales_quote_charge_service_types_equal,
)
from logistics.special_projects.special_project_charge_copy import (
	booking_copy_uses_linked_scope_only,
	programme_charges_for_booking_copy,
	prepare_operational_charges_from_special_project,
)
from logistics.special_projects.special_project_charge_lifecycle import (
	is_planning_lifecycle_row,
	lifecycle_row_order_link_is_cancelled,
	planning_row_is_open,
	programme_charges_for_service_type,
)
from logistics.special_projects.special_project_service_compat import (
	row_special_project_service_link,
	special_project_service_doctype,
	special_project_service_record_exists,
)
from logistics.special_projects.special_project_service_helpers import (
	is_planning_special_project_service_row,
	planning_service_is_open,
	special_project_service_by_name,
)
from logistics.utils.internal_job_from_source import (
	apply_internal_job_detail_row_to_operational_doc,
	coerce_internal_job_detail_idx,
	linked_internal_job_target_is_cancelled,
)
from logistics.utils.sales_quote_charge_parameters import (
	SALES_QUOTE_CHARGE_PARAMETER_FIELDS,
	any_programme_charge_matches_params_dict,
	collect_wildcard_fields_for_programme_param_set,
	extract_service_scoped_params_dict,
	extract_service_scoped_quote_parameters,
	filter_fields_existing_in_doctype,
	normalize_quote_parameter_json,
	parameter_fields_for_service_type,
	programme_charge_matches_creation_parameters,
	programme_charge_row_parameters,
	resolve_programme_charge_row_parameters,
)


SPECIAL_PROJECT_CREATABLE_JOB_TYPES: frozenset[str] = frozenset(
	{
		"Air Booking",
		"Sea Booking",
		"Transport Order",
		"Declaration Order",
		"Inbound Order",
		"Project Order",
	}
)

# Friendly target labels used for the Create dialog header.
_TARGET_DOC_LABELS: dict[str, str] = {
	"Air Booking": "Air Booking",
	"Sea Booking": "Sea Booking",
	"Transport Order": "Transport Order",
	"Declaration Order": "Declaration Order",
	"Inbound Order": "Inbound Order",
	"Project Order": "Project Order",
}

_SERVICE_LABEL_FOR_SP_JOB_TYPE: dict[str, str] = {
	"Transport Order": "Transport",
	"Declaration Order": "Customs",
	"Air Booking": "Air",
	"Sea Booking": "Sea",
	"Inbound Order": "Warehousing",
	"Project Order": "Special Project",
}

LIFECYCLE_JOB_QUOTE_PARAMETER_MISMATCH_MESSAGE = _(
	"No parameters match on your input against project charge lines"
)


def _service_label_for_lifecycle_row(job_type: str, row: Any) -> str | None:
	st = (getattr(row, "service_type", None) or "").strip() if row else ""
	if st:
		return st
	return _SERVICE_LABEL_FOR_SP_JOB_TYPE.get((job_type or "").strip())


def _parse_creation_parameters(value: Any) -> dict[str, Any]:
	return normalize_quote_parameter_json(value)


def _merge_creation_parameters(row: Any, creation_parameters: Any) -> Any:
	"""Overlay dialog parameters onto a lifecycle row for create/validation."""
	base: dict[str, Any] = {}
	if row is not None:
		if isinstance(row, dict):
			base = dict(row)
		elif hasattr(row, "as_dict"):
			base = row.as_dict()
		else:
			base = {k: getattr(row, k, None) for k in _LIFECYCLE_JOB_COPY_FIELDS if hasattr(row, k)}
	merged = frappe._dict(base)
	for k, v in (_parse_creation_parameters(creation_parameters) or {}).items():
		if k in _LIFECYCLE_JOB_COPY_FIELDS or k in parameter_fields_for_service_type(
			(getattr(row, "service_type", None) or "").strip()
		):
			merged[k] = v
	return merged


def _resolve_scoped_creation_params(
	sp_doc: Any,
	job_type: str,
	row: Any | None,
	parsed_params: dict[str, Any] | None = None,
) -> tuple[str, dict[str, Any], Any | None]:
	"""Service label and scoped params for preview/create (dialog params or charge suggestions)."""
	jt = (job_type or "").strip()
	parsed = dict(parsed_params or {})
	merged_row = _merge_creation_parameters(row, parsed) if row else None
	service_label = (
		_service_label_for_lifecycle_row(jt, merged_row)
		if merged_row is not None
		else _service_label_for_lifecycle_row(jt, row)
	) or ""
	scoped = extract_service_scoped_params_dict(parsed, service_label)
	if not scoped and parsed_params is None:
		scoped = suggested_parameters_from_programme_charges(sp_doc, service_label)
	return service_label, scoped, merged_row or row


def _validate_scoped_creation_params(
	parent_doc: Any,
	service_label: str,
	scoped_params: dict[str, Any],
) -> None:
	"""Reject create when set parameters do not match any programme charge row (empty = wildcard)."""
	st = (service_label or "").strip()
	if scoped_params and not any_programme_charge_matches_params_dict(
		parent_doc, scoped_params, st
	):
		frappe.throw(
			LIFECYCLE_JOB_QUOTE_PARAMETER_MISMATCH_MESSAGE,
			title=_("Cannot create booking / order"),
		)


def _parameter_fieldnames_on_programme_charges(sp_doc: Any, service_type_label: str) -> tuple[str, ...]:
	"""Parameter fieldnames that appear on at least one programme charge row for this service."""
	st = (service_type_label or "").strip()
	charge_dt = "Special Project Charges"
	allowed = set(
		filter_fields_existing_in_doctype(charge_dt, list(SALES_QUOTE_CHARGE_PARAMETER_FIELDS))
	)
	service_fields = parameter_fields_for_service_type(st)
	found: set[str] = set()
	for ch in programme_charges_for_booking_copy(sp_doc, st):
		resolved = resolve_programme_charge_row_parameters(ch, st)
		for fn in service_fields:
			val = resolved.get(fn)
			if val is None and fn in allowed:
				val = getattr(ch, fn, None) if not isinstance(ch, dict) else ch.get(fn)
			if val is None or val == "":
				continue
			if fn in {"sp_manpower", "sp_skilled"} and float(val or 0) == 0:
				continue
			found.add(fn)
	return tuple(fn for fn in service_fields if fn in found)


def suggested_parameters_from_programme_charges(
	sp_doc: Any, service_type_label: str
) -> dict[str, Any]:
	"""First non-empty parameter value per field from programme charge rows."""
	out: dict[str, Any] = {}
	for ch in programme_charges_for_booking_copy(sp_doc, service_type_label):
		for k, v in programme_charge_row_parameters(ch, service_type_label).items():
			if k not in out:
				out[k] = v
	return out


def _service_row_doctype_for_meta() -> str:
	"""DocType whose field definitions drive service-line booking parameters."""
	if frappe.db.exists("DocType", "Special Project Service"):
		return "Special Project Service"
	return "Lifecycle Job"


def _legacy_lifecycle_job_meta():
	if not frappe.db.exists("DocType", "Lifecycle Job"):
		return None
	return frappe.get_meta("Lifecycle Job")


def _service_row_meta():
	return frappe.get_meta(_service_row_doctype_for_meta())


def _service_row_doctype_for_name(row_name: str) -> str:
	if row_name and frappe.db.exists("Special Project Service", row_name):
		return "Special Project Service"
	if row_name and frappe.db.exists("Lifecycle Job", row_name):
		return "Lifecycle Job"
	return _service_row_doctype_for_meta()


def _field_def_for_service_parameter(fieldname: str, *fallback_metas: Any) -> Any | None:
	df = _service_row_meta().get_field(fieldname)
	if df:
		return df
	legacy_meta = _legacy_lifecycle_job_meta()
	if legacy_meta:
		df = legacy_meta.get_field(fieldname)
		if df:
			return df
	for meta in fallback_metas:
		if not meta:
			continue
		df = meta.get_field(fieldname)
		if df:
			return df
	return None


def _field_specs_for_fieldnames(
	fieldnames: tuple[str, ...] | list[str], *fallback_metas: Any
) -> list[dict[str, Any]]:
	specs: list[dict[str, Any]] = []
	for fn in fieldnames:
		df = _field_def_for_service_parameter(fn, *fallback_metas)
		if not df:
			continue
		spec: dict[str, Any] = {
			"fieldname": fn,
			"label": _(df.label or fn),
			"fieldtype": df.fieldtype,
			"options": df.options or "",
		}
		if df.fieldtype == "Dynamic Link" and df.options:
			spec["options_fieldname"] = df.options
		specs.append(spec)
	return specs


def get_programme_charge_parameter_field_specs(sp_doc: Any, service_type: str | None = None) -> list[dict[str, Any]]:
	"""Desk field specs for parameters present on Special Project programme charge rows."""
	st = (service_type or "").strip()
	fieldnames = _parameter_fieldnames_on_programme_charges(sp_doc, st)
	if not fieldnames:
		resolved_keys: set[str] = set()
		for ch in programme_charges_for_booking_copy(sp_doc, st):
			resolved_keys.update(resolve_programme_charge_row_parameters(ch, st).keys())
		fieldnames = tuple(
			fn for fn in parameter_fields_for_service_type(st) if fn in resolved_keys
		)
	sp_meta = frappe.get_meta("Special Project Charges")
	sqc_meta = frappe.get_meta("Sales Quote Charge")
	return _field_specs_for_fieldnames(fieldnames, sp_meta, sqc_meta)


@frappe.whitelist()
def get_special_project_service_parameter_field_specs(service_type: str | None = None):
	"""Desk field specs for service-scoped Special Project Service parameters."""
	return get_lifecycle_job_parameter_field_specs(service_type)


def get_lifecycle_job_parameter_field_specs(service_type: str | None = None):
	"""Desk field specs for service-scoped planning row parameters (Special Project Service or legacy Lifecycle Job)."""
	st = (service_type or "").strip()
	fields = parameter_fields_for_service_type(st)
	return _field_specs_for_fieldnames(fields)


def _filter_programme_charges_for_params(
	sp_doc: Any,
	pool: list[Any],
	service_label: str | None,
	params: dict[str, Any] | None,
) -> list[Any]:
	if not params:
		return pool
	return [ch for ch in pool if programme_charge_matches_creation_parameters(ch, params)]


def _programme_charge_pool_for_booking(
	sp_doc: Any,
	lifecycle_row: Any | None,
	job_type: str | None,
	creation_parameters: dict[str, Any] | None = None,
) -> tuple[list[Any], str, dict[str, Any]]:
	"""Matching programme charge rows for a lifecycle line and optional creation parameters."""
	jt = (job_type or "").strip()
	service_label = _service_label_for_lifecycle_row(jt, lifecycle_row) if lifecycle_row else ""
	pool = programme_charges_for_booking_copy(
		sp_doc,
		getattr(lifecycle_row, "service_type", None) if lifecycle_row else None,
		job_type=jt,
	)
	if jt == "Project Order":
		pool = [
			ch
			for ch in pool
			if sales_quote_charge_service_types_equal(
				getattr(ch, "service_type", None), "Special Project"
			)
		]
	scoped = extract_service_scoped_params_dict(creation_parameters or {}, service_label or "")
	if not scoped and creation_parameters is None:
		scoped = suggested_parameters_from_programme_charges(sp_doc, service_label or "")
	if scoped:
		pool = _filter_programme_charges_for_params(sp_doc, pool, service_label, scoped)
	return pool, service_label or "", scoped


def _sales_quote_link_from_programme_charge(charge: Any) -> str | None:
	"""sales_quote_link on the charge row, or the linked Change Request's Sales Quote."""
	sq = (getattr(charge, "sales_quote_link", None) or "").strip()
	if sq:
		return sq
	cr = (getattr(charge, "change_request", None) or "").strip()
	if not cr or not frappe.db.exists("Change Request", cr):
		return None
	cr_sq = (frappe.db.get_value("Change Request", cr, "sales_quote") or "").strip()
	return cr_sq or None


def _primary_sales_quote_link_from_programme_pool(pool: list[Any]) -> str | None:
	"""First sales_quote_link on programme charge rows (not the parent Special Project header)."""
	for ch in pool:
		sq = _sales_quote_link_from_programme_charge(ch)
		if sq:
			return sq
	return None


def _resolve_sales_quote_from_programme_charges(
	sp_doc: Any,
	lifecycle_row: Any | None,
	job_type: str | None = None,
	creation_parameters: dict[str, Any] | None = None,
) -> str | None:
	"""Sales Quote name from matching programme charge rows' sales_quote_link."""
	pool, _, _ = _programme_charge_pool_for_booking(
		sp_doc, lifecycle_row, job_type, creation_parameters
	)
	return _primary_sales_quote_link_from_programme_pool(pool)


def _booking_source_context(
	sp_doc: Any,
	lifecycle_row: Any | None = None,
	job_type: str | None = None,
	creation_parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
	pool, _, _ = _programme_charge_pool_for_booking(
		sp_doc, lifecycle_row, job_type, creation_parameters
	)
	return {
		"source_doctype": "Special Project",
		"source_name": sp_doc.name,
		"customer": getattr(sp_doc, "customer", None),
		"company": getattr(sp_doc, "company", None),
		"sales_quote": _primary_sales_quote_link_from_programme_pool(pool),
		"source_is_internal_job": False,
		"source_main_job_type": None,
		"source_main_job": None,
		"from_main_service_shipment": False,
	}


def _programme_charge_source_label(charge: Any) -> str:
	"""Human-readable source for a programme charge row (quotation vs change request)."""
	cr = (getattr(charge, "change_request", None) or "").strip() if charge else ""
	if cr:
		return _("Change Request")
	sq = (getattr(charge, "sales_quote_link", None) or "").strip() if charge else ""
	if sq:
		return _("Sales Quote")
	return _("Project")


def _charges_preview_rows(
	sp_doc: Any,
	pool: list[Any],
	params: dict[str, Any] | None,
	service_label: str | None = None,
) -> list[dict[str, Any]]:
	from frappe.utils import flt as _flt

	out: list[dict[str, Any]] = []
	for ch in pool:
		ch_params = programme_charge_row_parameters(ch, service_label or "")
		out.append(
			{
				"service_type": getattr(ch, "service_type", None),
				"item_code": getattr(ch, "item_code", None),
				"item_name": getattr(ch, "item_name", None),
				"unit_rate": _flt(getattr(ch, "unit_rate", None)) or None,
				"per_unit_rate": _flt(getattr(ch, "per_unit_rate", None)) or None,
				"currency": getattr(ch, "currency", None) or getattr(ch, "selling_currency", None),
				"selling_currency": getattr(ch, "selling_currency", None),
				"estimated_revenue": _flt(getattr(ch, "estimated_revenue", None)) or None,
				"parameters": ch_params or params or {},
				"charge_source": _programme_charge_source_label(ch),
				"change_request": getattr(ch, "change_request", None),
				"sales_quote_link": _sales_quote_link_from_programme_charge(ch),
			}
		)
	return out


def _preview_creatability_flags(
	sp_doc: Any,
	jt: str,
	row: Any | None,
	params: dict[str, Any] | None,
	*,
	base_creatable: bool,
) -> dict[str, Any]:
	service_label = _service_label_for_lifecycle_row(jt, row) if row else ""
	scoped = params or {}
	has_charge_match = True
	wildcard_fields: list[str] = []
	if scoped:
		has_charge_match = any_programme_charge_matches_params_dict(
			sp_doc,
			scoped,
			service_label or "",
		)
		if has_charge_match:
			wildcard_fields = collect_wildcard_fields_for_programme_param_set(
				sp_doc,
				service_label or "",
				scoped,
			)
	creatable = base_creatable and has_charge_match
	not_creatable_message: str | None = None
	if base_creatable and scoped and not has_charge_match:
		not_creatable_message = LIFECYCLE_JOB_QUOTE_PARAMETER_MISMATCH_MESSAGE
	if creatable and row is not None:
		from logistics.utils.internal_job_creation_eligibility import (
			evaluate_internal_job_creation_eligibility,
		)

		sq_link = getattr(sp_doc, "sales_quote", None) or _resolve_sales_quote_from_programme_charges(
			sp_doc, row, jt, scoped or None
		)
		elig = evaluate_internal_job_creation_eligibility(
			sales_quote=sq_link,
			parent_doc=sp_doc,
			ij_row=row,
			service_type_label=service_label,
		)
		if not elig.get("eligible"):
			creatable = False
			not_creatable_message = elig.get("message") or not_creatable_message
	return {
		"creatable": creatable,
		"has_params": True,
		"has_charge_match": has_charge_match,
		"has_quote_match": has_charge_match,
		"wildcard_fields": wildcard_fields,
		"not_creatable_message": not_creatable_message,
		"parameter_field_specs": get_programme_charge_parameter_field_specs(sp_doc, service_label),
		"suggested_parameters": suggested_parameters_from_programme_charges(sp_doc, service_label or ""),
	}


def lifecycle_job_params_match_quotation(
	parent_doc: Any,
	job_type: str,
	row: Any,
) -> bool:
	"""True when Lifecycle Job parameters match at least one programme charge row (or no check needed)."""
	if not row:
		return True
	service_label = _service_label_for_lifecycle_row(job_type, row)
	if not service_label:
		return True
	return any_programme_charge_matches_params_dict(
		parent_doc,
		extract_service_scoped_quote_parameters(row, service_label),
		service_label,
	)


def validate_lifecycle_job_params_match_quotation(
	parent_doc: Any,
	job_type: str,
	lifecycle_job_idx: int | None = None,
	creation_parameters: Any = None,
) -> None:
	"""Reject create when parameters do not match any programme charge row."""
	jt = (job_type or "").strip()
	row, _resolved_idx = _resolve_row_for_create(parent_doc, jt, coerce_internal_job_detail_idx(lifecycle_job_idx))
	params_explicit = creation_parameters is not None
	parsed_params = (
		_parse_creation_parameters(creation_parameters) if params_explicit else None
	)
	service_label, scoped_params, _merged_row = _resolve_scoped_creation_params(
		parent_doc,
		jt,
		row,
		parsed_params,
	)
	_validate_scoped_creation_params(parent_doc, service_label, scoped_params)
	from logistics.utils.internal_job_creation_eligibility import (
		require_internal_job_creation_eligible,
	)

	sq_link = getattr(parent_doc, "sales_quote", None) or _resolve_sales_quote_from_programme_charges(
		parent_doc,
		row,
		jt,
		parsed_params if params_explicit else None,
	)
	require_internal_job_creation_eligible(
		sales_quote=sq_link,
		parent_doc=parent_doc,
		ij_row=row,
		service_type_label=service_label,
	)

_LIFECYCLE_JOB_COPY_FIELDS = (
	"lifecycle_stage",
	"activity_code",
	"activity_name",
	"lifecycle_activity_status",
	"service_type",
	"job_description",
	"transport_template",
	"vehicle_type",
	"load_type",
	"direction",
	"air_house_type",
	"sea_house_type",
	"origin_port",
	"destination_port",
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
	"airline",
	"freight_agent",
	"freight_agent_sea",
	"shipping_line",
	"transport_mode",
)


def _norm(value: Any) -> str:
	return (value or "").strip()


def _planning_row_idx(row: Any, fallback: int | None = None) -> int | None:
	idx = cint(getattr(row, "idx", 0) or 0)
	if idx:
		return idx
	return fallback


def _linked_order_for_planning(parent_doc: Any, planning_row: Any) -> tuple[str, str]:
	"""Return (order_type, order_no) for the planning booking/order on a lifecycle line."""
	from logistics.special_projects.special_project_charge_lifecycle import (
		_PLANNING_ORDER_TYPES,
	)

	planning_name = _norm(getattr(planning_row, "name", None))
	if not planning_name:
		return "", ""
	check = _service_row_by_name(parent_doc, planning_name) or planning_row
	jt = _norm(getattr(check, "job_type", None))
	on = _norm(getattr(check, "order_no", None))
	if jt in _PLANNING_ORDER_TYPES and on:
		return jt, on
	ot = _norm(getattr(check, "order_type", None))
	if ot in _PLANNING_ORDER_TYPES and on:
		return ot, on
	return "", ""


def _linked_execution_for_planning(parent_doc: Any, planning_row: Any) -> tuple[str, str]:
	"""Return (job_type, job_no) for the submitted execution doc on a planning line."""
	from logistics.utils.special_project_internal_jobs import (
		resolve_lifecycle_job_row_to_operational_ref,
	)

	planning_name = _norm(getattr(planning_row, "name", None))
	if not planning_name:
		return "", ""
	check = _service_row_by_name(parent_doc, planning_name) or planning_row
	ref = resolve_lifecycle_job_row_to_operational_ref(check)
	return ref if ref else ("", "")


def _linked_job_for_planning(parent_doc: Any, planning_row: Any) -> tuple[str, str]:
	"""Backward-compatible alias: returns planning order (job_type, job_no)."""
	return _linked_order_for_planning(parent_doc, planning_row)


def _planning_rows_for_form(parent_doc: Any, client_lifecycle_jobs: Any) -> list[tuple[int, Any]]:
	"""Planning lifecycle rows for the Create dialog (``detail_idx`` = child row ``idx``)."""
	with _client_rows_context(client_lifecycle_jobs):
		rows = _lifecycle_rows_list(parent_doc)
	planning = [r for r in rows if _is_planning_service_row(r)]
	out: list[tuple[int, Any]] = []
	for i, row in enumerate(planning, start=1):
		out.append((_planning_row_idx(row, i), row))
	return out


def _planning_row_by_idx(parent_doc: Any, idx: int | None) -> Any | None:
	if idx is None:
		return None
	for row in _lifecycle_rows_list(parent_doc):
		if not _is_planning_service_row(row):
			continue
		if cint(getattr(row, "idx", 0) or 0) == cint(idx):
			return row
	return None


def _dialog_creatable_job_type(row: Any) -> str:
	"""Job type used in Create > Booking/Order (Special Project service → Project Order, not Project Job)."""
	if not row:
		return ""
	st = (getattr(row, "service_type", None) or "").strip()
	if sales_quote_charge_service_types_equal(st, "Special Project"):
		return "Project Order"
	return effective_internal_job_detail_job_type(row)

_LOGISTICS_SP_CLIENT_ROWS = "_logistics_sp_ij_client_rows"


def _coerce_client_rows(client_value: Any) -> list | None:
	"""List of Special Project Service / legacy Lifecycle Job row dicts from the desk form."""
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
def _client_rows_context(client_value: Any):
	key = _LOGISTICS_SP_CLIENT_ROWS
	parsed = _coerce_client_rows(client_value)
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


def _service_rows_list(parent_doc: Any) -> list[Any]:
	"""Planning service rows for Create; falls back to legacy lifecycle rows when no services exist."""
	ov = getattr(frappe.local, _LOGISTICS_SP_CLIENT_ROWS, None)
	if ov is not None:
		return list(ov)
	services = list(getattr(parent_doc, "special_project_services", None) or [])
	if services:
		return services
	return list(getattr(parent_doc, "lifecycle_jobs", None) or [])


def _uses_special_project_services(parent_doc: Any) -> bool:
	ov = getattr(frappe.local, _LOGISTICS_SP_CLIENT_ROWS, None)
	if ov is not None:
		return True
	return bool(getattr(parent_doc, "special_project_services", None))


def _uses_special_project_services_from_row(row: Any) -> bool:
	return hasattr(row, "special_project_service_line")


def _is_planning_service_row(row: Any) -> bool:
	if _uses_special_project_services_from_row(row):
		return is_planning_special_project_service_row(row)
	return is_planning_lifecycle_row(row)


def _planning_row_is_open(sp_doc: Any, row: Any) -> bool:
	if _uses_special_project_services(sp_doc) or _uses_special_project_services_from_row(row):
		return planning_service_is_open(sp_doc, row)
	return planning_row_is_open(sp_doc, row)


def _legacy_lifecycle_job_row_by_name(parent_doc: Any, row_name: str) -> Any | None:
	row_name = _norm(row_name)
	if not row_name:
		return None
	for row in getattr(parent_doc, "lifecycle_jobs", None) or []:
		if _norm(getattr(row, "name", None)) == row_name:
			return row
	return None


def _service_row_by_name(parent_doc: Any, row_name: str) -> Any | None:
	row_name = _norm(row_name)
	if not row_name:
		return None
	if _uses_special_project_services(parent_doc):
		return special_project_service_by_name(parent_doc, row_name)
	return _legacy_lifecycle_job_row_by_name(parent_doc, row_name)


def _lifecycle_rows_list(parent_doc: Any) -> list[Any]:
	return _service_rows_list(parent_doc)


def _all_rows_for_form(parent_doc: Any, client_lifecycle_jobs: Any) -> list[tuple[int, Any]]:
	return _planning_rows_for_form(parent_doc, client_lifecycle_jobs)


def _resolve_row_for_create(
	parent_doc: Any, job_type: str, idx: int | None
) -> tuple[Any | None, int | None]:
	"""Resolve the planning Lifecycle Job row used for create."""
	jt = (job_type or "").strip()
	if idx is not None:
		row = _planning_row_by_idx(parent_doc, idx)
		if not row:
			frappe.throw(_("Invalid Lifecycle Job row."))
		row_jt = _dialog_creatable_job_type(row)
		if row_jt != jt:
			frappe.throw(_("The selected line is not for {0}.").format(jt))
		if not _planning_row_is_open(parent_doc, row):
			linked_jt, linked_jn = _linked_job_for_planning(parent_doc, row)
			frappe.throw(
				_("This Lifecycle Job line already references {0} {1}.").format(
					linked_jt or row_jt, linked_jn
				),
				title=_("Already linked"),
			)
		return row, _planning_row_idx(row, idx)
	for row in _lifecycle_rows_list(parent_doc):
		if not _is_planning_service_row(row):
			continue
		if _dialog_creatable_job_type(row) != jt:
			continue
		if not _planning_row_is_open(parent_doc, row):
			continue
		return row, _planning_row_idx(row)
	return None, None


def _choice_header(
	job_type: str,
	row: Any | None,
	idx: int | None,
	order_no: str,
	execution_no: str = "",
) -> dict[str, Any]:
	jt_label = (job_type or "").strip()
	st = (getattr(row, "service_type", None) or "").strip() if row else ""
	title = _(st) if st else (_(jt_label) if jt_label else _("(no service type)"))
	if execution_no:
		badge = execution_no
	elif order_no:
		badge = order_no
	elif idx is not None:
		badge = _("Pending")
	else:
		badge = _("Job Details")
	if execution_no:
		subtitle = _("Executed — open the job/shipment from Job No above.")
	elif order_no:
		subtitle = _("Planned — open the booking/order from Order No above.")
	elif not st:
		subtitle = _("Select a service type on this line to set the target document type.")
	elif not jt_label:
		subtitle = _("Could not resolve target document type for this service.")
	else:
		subtitle = _("Creates {0} linked to this Special Project.").format(_(_TARGET_DOC_LABELS.get(jt_label, jt_label)))
	return {"header_title": title, "header_badge": badge, "header_subtitle": subtitle}


@frappe.whitelist()
def get_special_project_booking_choices(
	special_project: str, lifecycle_jobs: Any = None, special_project_services: Any = None
):
	"""Return Create > Booking/Order options for each Special Project Service row on a Special Project."""
	if not special_project or not frappe.db.exists("Special Project", special_project):
		frappe.throw(_("Invalid Special Project."))
	doc = frappe.get_doc("Special Project", special_project)
	doc.check_permission("read")

	client_rows = special_project_services if special_project_services is not None else lifecycle_jobs
	choices: list[dict[str, Any]] = []
	for idx, row in _all_rows_for_form(doc, client_rows):
		st = (getattr(row, "service_type", None) or "").strip()
		jt = _dialog_creatable_job_type(row)
		linked_ot, order_no = _linked_order_for_planning(doc, row)
		exec_jt, exec_no = _linked_execution_for_planning(doc, row)
		if not jt and linked_ot:
			jt = linked_ot
		creatable = (
			bool(jt)
			and jt in SPECIAL_PROJECT_CREATABLE_JOB_TYPES
			and _planning_row_is_open(doc, row)
		)
		header = _choice_header(jt, row, idx, order_no, exec_no)
		cancelled = bool(order_no and lifecycle_row_order_link_is_cancelled(row))
		if cancelled:
			header = {
				**header,
				"header_subtitle": _("Linked to {0} (cancelled).").format(order_no),
				"linked_job_cancelled": True,
			}
		choice = {
			"mode": "detail",
			"detail_idx": idx,
			"job_type": jt,
			"service_type": st or None,
			"job_no": exec_no or None,
			"execution_job_type": exec_jt or None,
			"creatable": creatable,
			**header,
		}
		if creatable and jt == "Project Order":
			choice["suggested_order_title"] = suggested_order_title_from_lifecycle_row(doc, row)
		if st and creatable:
			choice["parameter_field_specs"] = get_programme_charge_parameter_field_specs(doc, st)
			choice["suggested_parameters"] = suggested_parameters_from_programme_charges(doc, st)
		choices.append(choice)
	service_type_filters = sorted(
		{
			(c.get("service_type") or "").strip()
			for c in choices
			if c.get("creatable") and (c.get("service_type") or "").strip()
		}
	)
	return {"choices": choices, "service_type_filters": service_type_filters}


@frappe.whitelist()
def get_special_project_booking_preview(
	special_project: str,
	job_type: str,
	lifecycle_job_idx: int | None = None,
	lifecycle_jobs: Any = None,
	special_project_services: Any = None,
	creation_parameters: Any = None,
):
	"""Special Project Service parameters and matching charge rows that will inform the new operational document."""
	if not special_project or not frappe.db.exists("Special Project", special_project):
		frappe.throw(_("Invalid Special Project."))
	doc = frappe.get_doc("Special Project", special_project)
	doc.check_permission("read")

	jt = (job_type or "").strip()
	idx = coerce_internal_job_detail_idx(lifecycle_job_idx)
	params_explicit = creation_parameters is not None
	parsed_params = (
		_parse_creation_parameters(creation_parameters) if params_explicit else None
	)
	client_rows = special_project_services if special_project_services is not None else lifecycle_jobs

	with _client_rows_context(client_rows):
		planning_row = _planning_row_by_idx(doc, idx) if idx is not None else None

		if planning_row is not None:
			linked_jt, jn_linked = _linked_order_for_planning(doc, planning_row)
			if jn_linked:
				row_jt = linked_jt or _dialog_creatable_job_type(planning_row)
				cancelled = linked_internal_job_target_is_cancelled(row_jt, jn_linked)
				if (
					not cancelled
					and row_jt == "Project Order"
					and frappe.db.exists("Project Order", jn_linked)
				):
					cancelled = (frappe.db.get_value("Project Order", jn_linked, "docstatus") or 0) == 2
				msg = _("This line is already linked to {0}.").format(jn_linked)
				if cancelled:
					msg = _(
						"This line still references {0}, which is cancelled. Reload the project if the link should have been removed."
					).format(jn_linked)
				return {
					"job_type": jt or row_jt,
					"detail_idx": idx,
					"uses_job_detail_row": True,
					"creatable": False,
					"has_params": False,
					"has_quote_match": False,
					"wildcard_fields": [],
					"not_creatable_message": msg,
					"linked_job_cancelled": cancelled,
					"source_context": _booking_source_context(
						doc, planning_row, jt or row_jt, parsed_params or None
					),
					"target_internal_job": None,
					"job_detail_parameters": {},
					"charges": [],
					"parameter_field_specs": get_programme_charge_parameter_field_specs(
						doc, getattr(planning_row, "service_type", None)
					),
				}

		if not jt:
			if idx is None:
				frappe.throw(_("Invalid selection."))
			row = _planning_row_by_idx(doc, idx)
			return {
				"job_type": "",
				"detail_idx": idx,
				"uses_job_detail_row": True,
				"creatable": False,
				"has_params": False,
				"has_quote_match": False,
				"wildcard_fields": [],
				"not_creatable_message": _("Set Service Type on this line before creating."),
				"source_context": _booking_source_context(doc, row, "", parsed_params or None),
				"target_internal_job": None,
				"job_detail_parameters": {},
				"charges": [],
				"parameter_field_specs": get_programme_charge_parameter_field_specs(
					doc, getattr(row, "service_type", None) if row else None
				),
			}

		if jt not in SPECIAL_PROJECT_CREATABLE_JOB_TYPES:
			return {
				"job_type": jt,
				"detail_idx": idx,
				"uses_job_detail_row": True,
				"creatable": False,
				"has_params": False,
				"has_quote_match": False,
				"wildcard_fields": [],
				"not_creatable_message": _(
					"This job type cannot be created from this screen. Choose a supported booking/order."
				),
				"source_context": _booking_source_context(doc, None, jt, parsed_params or None),
				"target_internal_job": None,
				"job_detail_parameters": {},
				"charges": [],
				"parameter_field_specs": [],
			}

		row, res_idx = _resolve_row_for_create(doc, jt, idx)
		service_label, scoped_params, merged_row = _resolve_scoped_creation_params(
			doc,
			jt,
			row,
			parsed_params,
		)

		base_creatable = row is not None and _planning_row_is_open(doc, row)
		flags = _preview_creatability_flags(
			doc, jt, merged_row, scoped_params, base_creatable=base_creatable
		)

		pool_params = parsed_params if params_explicit else None
		pool, *_rest = _programme_charge_pool_for_booking(doc, merged_row, jt, pool_params)
		source_context = _booking_source_context(doc, merged_row, jt, pool_params)

		out = {
			"job_type": jt,
			"detail_idx": res_idx,
			"uses_job_detail_row": row is not None,
			"source_context": source_context,
			"target_internal_job": None,
			"job_detail_parameters": scoped_params,
			"charges": _charges_preview_rows(doc, pool, scoped_params, service_label),
			**flags,
		}
		if jt == "Project Order" and row is not None:
			out["suggested_order_title"] = suggested_order_title_from_lifecycle_row(doc, row)
		if flags.get("creatable") and scoped_params and not pool:
			out["creatable"] = False
			out["not_creatable_message"] = _("No charge lines match the parameters you set.")
		return out


def _apply_sales_quote_parties_to_target(target_doc: Any, sq_name: str | None = None) -> None:
	"""Copy shipper/consignee from the linked Sales Quote (same as quote → booking creation)."""
	sq_name = (sq_name or getattr(target_doc, "sales_quote", None) or "").strip()
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return
	sq = frappe.get_cached_doc("Sales Quote", sq_name)
	meta = frappe.get_meta(target_doc.doctype)
	for party_fn in ("shipper", "consignee"):
		if not meta.get_field(party_fn):
			continue
		if not (getattr(target_doc, party_fn, None) or "").strip() and getattr(sq, party_fn, None):
			target_doc.set(party_fn, sq.get(party_fn))
	if target_doc.doctype in ("Air Booking", "Sea Booking"):
		from logistics.utils.party_address_contact_from_masters import (
			populate_air_sea_booking_party_fields_from_masters,
		)
		from logistics.utils.shipper_consignee_defaults import apply_shipper_consignee_defaults

		populate_air_sea_booking_party_fields_from_masters(target_doc)
		apply_shipper_consignee_defaults(target_doc)


def _set_main_service_for_one_off_quote_target(target_doc: Any, sq_name: str | None = None) -> None:
	"""Primary legs from One-off Sales Quotes are main service (Project quotes leave flags unset)."""
	from logistics.utils.service_role_rules import (
		apply_main_service_flags,
		get_service_role,
		SERVICE_ROLE_LINKED,
	)

	if not (hasattr(target_doc, "service_role") or hasattr(target_doc, "is_main_service")):
		return
	if get_service_role(target_doc) == SERVICE_ROLE_LINKED:
		return
	sq_name = (sq_name or getattr(target_doc, "sales_quote", None) or "").strip()
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return
	if frappe.db.get_value("Sales Quote", sq_name, "quotation_type") == "One-off":
		apply_main_service_flags(target_doc)


def _apply_special_project_context(
	target_doc: Any,
	sp_doc: Any,
	*,
	lifecycle_row: Any | None = None,
	job_type: str | None = None,
	creation_parameters: dict[str, Any] | None = None,
) -> None:
	"""Populate accounting and reference fields from the Special Project onto the new booking/order."""
	meta = frappe.get_meta(target_doc.doctype)
	sq_name = _resolve_sales_quote_from_programme_charges(
		sp_doc, lifecycle_row, job_type, creation_parameters
	)

	def _set_if_field(fieldname: str, value: Any) -> None:
		if value in (None, ""):
			return
		if not meta.get_field(fieldname):
			return
		target_doc.set(fieldname, value)

	_set_if_field("company", getattr(sp_doc, "company", None))
	_set_if_field("branch", getattr(sp_doc, "branch", None))
	_set_if_field("cost_center", getattr(sp_doc, "cost_center", None))
	_set_if_field("profit_center", getattr(sp_doc, "profit_center", None))
	_set_if_field("project", getattr(sp_doc, "project", None) or sp_doc.name)
	_set_if_field("sales_quote", sq_name)
	_set_main_service_for_one_off_quote_target(target_doc, sq_name)
	# Customer fields differ by doctype.
	cust = getattr(sp_doc, "customer", None)
	if cust:
		if meta.get_field("local_customer"):
			target_doc.local_customer = cust
		if meta.get_field("customer"):
			target_doc.customer = cust
	_apply_sales_quote_parties_to_target(target_doc, sq_name)


def _apply_air_sea_corridor_ports_from_context(
	target_doc: Any, sp_doc: Any, row: Any | None
) -> None:
	"""Fill mandatory origin/destination ports from the lifecycle row or linked Sales Quote."""
	if target_doc.doctype not in ("Air Booking", "Sea Booking"):
		return
	meta = frappe.get_meta(target_doc.doctype)
	if not meta.get_field("origin_port"):
		return

	service = "Air" if target_doc.doctype == "Air Booking" else "Sea"

	def _set_if_empty(fieldname: str, value: Any) -> None:
		if value in (None, ""):
			return
		if not meta.get_field(fieldname):
			return
		if not (getattr(target_doc, fieldname, None) or "").strip():
			target_doc.set(fieldname, value)

	if row:
		for fn in ("origin_port", "destination_port", "direction"):
			_set_if_empty(fn, getattr(row, fn, None))
		# Lifecycle rows may store UNLOCO corridor as location_from / location_to.
		_set_if_empty("origin_port", getattr(row, "location_from", None))
		_set_if_empty("destination_port", getattr(row, "location_to", None))

	if (getattr(target_doc, "origin_port", None) or "").strip() and (
		getattr(target_doc, "destination_port", None) or ""
	).strip():
		return

	sq_name = (getattr(target_doc, "sales_quote", None) or "").strip()
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return

	from logistics.pricing_center.doctype.sales_quote.sales_quote import (
		_get_service_params,
		_sq_charge_row_matches_service,
	)

	try:
		sq = frappe.get_doc("Sales Quote", sq_name)
	except Exception:
		return

	first = _get_service_params(sq, service)
	legacy_table = "air_freight" if service == "Air" else "sea_freight"
	legacy_rows = getattr(sq, legacy_table, None) or []
	if not first and legacy_rows:
		first = legacy_rows[0]

	origin = (getattr(target_doc, "origin_port", None) or "").strip() or None
	dest = (getattr(target_doc, "destination_port", None) or "").strip() or None

	if not origin:
		if service == "Air":
			origin = (
				(getattr(first, "origin_port", None) if first else None)
				or getattr(sq, "origin_port", None)
				or (getattr(first, "location_from", None) if first else None)
				or getattr(sq, "location_from", None)
			)
		else:
			origin = (
				(getattr(first, "origin_port", None) if first else None)
				or getattr(sq, "origin_port_sea", None)
				or getattr(sq, "origin_port", None)
				or getattr(sq, "location_from", None)
			)
	if not dest:
		if service == "Air":
			dest = (
				(getattr(first, "destination_port", None) if first else None)
				or getattr(sq, "destination_port", None)
				or (getattr(first, "location_to", None) if first else None)
				or getattr(sq, "location_to", None)
			)
		else:
			dest = (
				(getattr(first, "destination_port", None) if first else None)
				or getattr(sq, "destination_port_sea", None)
				or getattr(sq, "destination_port", None)
				or getattr(sq, "location_to", None)
			)

	charges = [c for c in (sq.get("charges") or []) if _sq_charge_row_matches_service(c, service)]
	if not origin or not dest:
		for ch in charges:
			if not origin and getattr(ch, "origin_port", None):
				origin = ch.origin_port
			if not dest and getattr(ch, "destination_port", None):
				dest = ch.destination_port
			if not origin and getattr(ch, "location_from", None):
				origin = ch.location_from
			if not dest and getattr(ch, "location_to", None):
				dest = ch.location_to
			if origin and dest:
				break

	if (not origin or not dest) and getattr(sq, "routing_legs", None):
		for leg in sq.routing_legs:
			if getattr(leg, "mode", None) != service:
				continue
			if not origin and getattr(leg, "origin", None):
				origin = leg.origin
			if not dest and getattr(leg, "destination", None):
				dest = leg.destination
			if origin and dest:
				break

	_set_if_empty("origin_port", origin)
	_set_if_empty("destination_port", dest)
	if first or getattr(sq, "direction", None):
		_set_if_empty(
			"direction",
			(getattr(first, "direction", None) if first else None) or getattr(sq, "direction", None),
		)


def _apply_air_sea_settings_defaults_before_insert(target_doc: Any) -> None:
	"""Apply module settings defaults before mandatory port validation on programmatic create."""
	if hasattr(target_doc, "apply_settings_defaults"):
		target_doc.apply_settings_defaults()


def _validate_air_sea_corridor_ports_before_insert(target_doc: Any) -> None:
	"""Fail with a clear message when corridor ports could not be resolved from context."""
	if target_doc.doctype not in ("Air Booking", "Sea Booking"):
		return
	if not (getattr(target_doc, "origin_port", None) or "").strip():
		frappe.throw(
			_(
				"Origin Port is required. Set Origin Port (or Location From) on the Special Project "
				"Service line, on the linked Sales Quote, or in Air Freight Settings defaults."
			),
			title=_("Origin Port Required"),
		)
	if not (getattr(target_doc, "destination_port", None) or "").strip():
		frappe.throw(
			_(
				"Destination Port is required. Set Destination Port (or Location To) on the "
				"Special Project Service line, on the linked Sales Quote, or in Air Freight "
				"Settings defaults."
			),
			title=_("Destination Port Required"),
		)


def _prepare_charges_before_insert(
	sp_doc: Any,
	target_doc: Any,
	row: Any | None,
	creation_parameters: dict[str, Any] | None = None,
) -> None:
	"""Copy matching programme charges (or Sales Quote lines) before the first save."""
	prepare_operational_charges_from_special_project(
		sp_doc, target_doc, row, creation_parameters=creation_parameters
	)


def _booking_date_field(target_doc: Any) -> str | None:
	meta = frappe.get_meta(target_doc.doctype)
	for fn in ("booking_date", "order_date", "scheduled_date"):
		if meta.get_field(fn):
			return fn
	return None


def _propagate_linked_services_after_insert(sp_doc: Any, operational_doc: Any) -> None:
	"""Clone subsidiary Sales Quote Linked Services onto a Special Project booking/order."""
	from logistics.utils.sales_quote_one_off_internal_jobs import (
		propagate_linked_services_for_special_project_booking,
	)

	propagate_linked_services_for_special_project_booking(sp_doc, operational_doc)


def _row_field(row: Any, field: str) -> Any:
	if isinstance(row, dict):
		return row.get(field)
	return getattr(row, field, None)


def _special_project_service_name_from_row(row: Any) -> str:
	return _norm(row_special_project_service_link(row) or _row_field(row, "name"))


def _link_special_project_service_order(
	service_name: str,
	order_type: str,
	order_no: str,
) -> str:
	service_name = _norm(service_name)
	if not service_name or not special_project_service_record_exists(service_name):
		frappe.throw(_("Planning service row not found on this Special Project."))
	service_doc = frappe.get_doc(special_project_service_doctype(), service_name)
	service_doc.job_type = order_type
	service_doc.order_no = order_no
	service_doc.job_no = None
	service_doc.flags.ignore_permissions = True
	service_doc.flags.skip_special_project_service_detail_sync = True
	service_doc.save(ignore_permissions=True)
	return service_name


def _link_planning_service_row(
	sp_name: str,
	planning_row: Any,
	order_type: str,
	order_no: str,
	operational_doc: Any | None = None,
) -> str:
	"""Set job_type/order_no on the planning service (or legacy lifecycle) row."""
	if not (order_type and order_no and planning_row):
		return ""
	planning_name = _norm(_row_field(planning_row, "name"))
	if not planning_name:
		frappe.throw(_("Planning service row must be saved before creating a booking/order."))

	sp = frappe.get_doc("Special Project", sp_name)
	if _uses_special_project_services(sp):
		linked_row = special_project_service_by_name(sp, planning_name)
		if not linked_row:
			frappe.throw(_("Planning service row not found on this Special Project."))
		service_name = _special_project_service_name_from_row(planning_row)
		if not service_name:
			service_name = _special_project_service_name_from_row(linked_row)
		return _link_special_project_service_order(service_name, order_type, order_no)

	linked_row = _legacy_lifecycle_job_row_by_name(sp, planning_name)
	if not linked_row:
		frappe.throw(_("Planning service row not found on this Special Project."))

	linked_row.job_type = order_type
	linked_row.order_no = order_no
	linked_row.job_no = None

	sp.flags.ignore_validate = True
	sp.save(ignore_permissions=True)
	return _norm(_row_field(linked_row, "name"))


def _link_planning_lifecycle_row(
	sp_name: str,
	planning_row: Any,
	order_type: str,
	order_no: str,
	operational_doc: Any | None = None,
) -> str:
	return _link_planning_service_row(
		sp_name, planning_row, order_type, order_no, operational_doc
	)


def _update_lifecycle_job_row_financials(
	row_name: str, order_type: str, order_no: str
) -> None:
	"""Refresh planned/actual columns on one planning service row after linking an operational job."""
	from logistics.special_projects.lifecycle_job_financial_rollup import (
		calculate_linked_job_stack_totals,
	)

	doctype = _service_row_doctype_for_name(row_name)
	row_doc = frappe.get_doc(doctype, row_name)
	pc, pr, ac, ar = calculate_linked_job_stack_totals(
		order_type, order_no, lifecycle_row=row_doc
	)
	frappe.db.set_value(
		doctype,
		row_name,
		{
			"planned_cost": pc,
			"planned_revenue": pr,
			"actual_cost": ac,
			"actual_revenue": ar,
		},
		update_modified=False,
	)


def _create_air_booking(
	sp_doc: Any,
	row: Any,
	detail_idx: int,
	shipment_lines: Any = None,
	creation_parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
	doc = frappe.new_doc("Air Booking")
	_apply_special_project_context(
		doc, sp_doc, lifecycle_row=row, job_type="Air Booking", creation_parameters=creation_parameters
	)
	bd = _booking_date_field(doc)
	if bd:
		doc.set(bd, today())
	apply_internal_job_detail_row_to_operational_doc(doc, row, overwrite=True)
	_apply_air_sea_corridor_ports_from_context(doc, sp_doc, row)
	_apply_cargo_and_shipment_lines(sp_doc, doc, shipment_lines)
	_prepare_charges_before_insert(sp_doc, doc, row, creation_parameters)
	_apply_air_sea_settings_defaults_before_insert(doc)
	_validate_air_sea_corridor_ports_before_insert(doc)
	doc.insert(ignore_permissions=True)
	_propagate_linked_services_after_insert(sp_doc, doc)
	_link_planning_lifecycle_row(sp_doc.name, row, "Air Booking", doc.name, doc)
	frappe.db.commit()
	return {"air_booking": doc.name, "message": _("Air Booking {0} created.").format(doc.name)}


def _create_sea_booking(
	sp_doc: Any,
	row: Any,
	detail_idx: int,
	shipment_lines: Any = None,
	creation_parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
	doc = frappe.new_doc("Sea Booking")
	_apply_special_project_context(
		doc, sp_doc, lifecycle_row=row, job_type="Sea Booking", creation_parameters=creation_parameters
	)
	bd = _booking_date_field(doc)
	if bd:
		doc.set(bd, today())
	apply_internal_job_detail_row_to_operational_doc(doc, row, overwrite=True)
	_apply_air_sea_corridor_ports_from_context(doc, sp_doc, row)
	_apply_cargo_and_shipment_lines(sp_doc, doc, shipment_lines)
	_prepare_charges_before_insert(sp_doc, doc, row, creation_parameters)
	_apply_air_sea_settings_defaults_before_insert(doc)
	_validate_air_sea_corridor_ports_before_insert(doc)
	doc.insert(ignore_permissions=True)
	_propagate_linked_services_after_insert(sp_doc, doc)
	_link_planning_lifecycle_row(sp_doc.name, row, "Sea Booking", doc.name, doc)
	frappe.db.commit()
	return {"sea_booking": doc.name, "message": _("Sea Booking {0} created.").format(doc.name)}


def _create_transport_order(
	sp_doc: Any,
	row: Any,
	detail_idx: int,
	shipment_lines: Any = None,
	creation_parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
	from logistics.utils.transport_job_type import (
		apply_container_transport_context_to_order,
		set_internal_transport_order_draft_insert_flags,
	)

	order = frappe.new_doc("Transport Order")
	_apply_special_project_context(
		order,
		sp_doc,
		lifecycle_row=row,
		job_type="Transport Order",
		creation_parameters=creation_parameters,
	)
	order.booking_date = today()
	if frappe.get_meta("Transport Order").get_field("transport_job_type"):
		order.transport_job_type = "Non-Container"
	if frappe.get_meta("Transport Order").get_field("scheduled_date"):
		order.scheduled_date = today()
	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	apply_container_transport_context_to_order(order, row)
	set_internal_transport_order_draft_insert_flags(order)
	# Special Project orders are standalone, not linked satellites.
	from logistics.utils.service_role_rules import apply_standalone_service_flags

	apply_standalone_service_flags(order)
	_apply_cargo_and_shipment_lines(sp_doc, order, shipment_lines)
	_prepare_charges_before_insert(sp_doc, order, row, creation_parameters)
	order.insert(ignore_permissions=True)
	_propagate_linked_services_after_insert(sp_doc, order)
	_link_planning_lifecycle_row(sp_doc.name, row, "Transport Order", order.name, order)
	frappe.db.commit()
	return {"transport_order": order.name, "message": _("Transport Order {0} created.").format(order.name)}


def _create_declaration_order(
	sp_doc: Any,
	row: Any,
	detail_idx: int,
	shipment_lines: Any = None,
	creation_parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
	order = frappe.new_doc("Declaration Order")
	_apply_special_project_context(
		order,
		sp_doc,
		lifecycle_row=row,
		job_type="Declaration Order",
		creation_parameters=creation_parameters,
	)
	if frappe.get_meta("Declaration Order").get_field("order_date"):
		order.order_date = today()
	if frappe.get_meta("Declaration Order").get_field("transport_mode") and not order.get("transport_mode"):
		order.transport_mode = getattr(row, "transport_mode", None) or order.get("transport_mode")
	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	from logistics.utils.service_role_rules import apply_standalone_service_flags

	apply_standalone_service_flags(order)
	_prepare_charges_before_insert(sp_doc, order, row, creation_parameters)
	order.insert(ignore_permissions=True)
	_propagate_linked_services_after_insert(sp_doc, order)
	_link_planning_lifecycle_row(sp_doc.name, row, "Declaration Order", order.name, order)
	frappe.db.commit()
	return {
		"declaration_order": order.name,
		"message": _("Declaration Order {0} created.").format(order.name),
	}


def _create_inbound_order(
	sp_doc: Any,
	row: Any,
	detail_idx: int,
	shipment_lines: Any = None,
	creation_parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
	order = frappe.new_doc("Inbound Order")
	_apply_special_project_context(
		order,
		sp_doc,
		lifecycle_row=row,
		job_type="Inbound Order",
		creation_parameters=creation_parameters,
	)
	if frappe.get_meta("Inbound Order").get_field("order_date"):
		order.order_date = today()
	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	_apply_cargo_and_shipment_lines(sp_doc, order, shipment_lines)
	_prepare_charges_before_insert(sp_doc, order, row, creation_parameters)
	order.insert(ignore_permissions=True)
	_propagate_linked_services_after_insert(sp_doc, order)
	_link_planning_lifecycle_row(sp_doc.name, row, "Inbound Order", order.name, order)
	frappe.db.commit()
	return {"inbound_order": order.name, "message": _("Inbound Order {0} created.").format(order.name)}


def _create_project_order(
	sp_doc: Any,
	row: Any,
	detail_idx: int,
	order_title: str | None = None,
	shipment_lines: Any = None,
	creation_parameters: dict[str, Any] | None = None,
) -> dict[str, Any]:
	title = (order_title or "").strip()
	if not title:
		frappe.throw(_("Order Title is required to create a Project Order."))
	order = build_project_order_from_special_project(sp_doc, title, lifecycle_row=row)
	_apply_cargo_and_shipment_lines(sp_doc, order, shipment_lines)
	order.insert(ignore_permissions=True)
	_propagate_linked_services_after_insert(sp_doc, order)
	_link_planning_lifecycle_row(sp_doc.name, row, "Project Order", order.name, order)
	frappe.db.commit()
	return {
		"project_order": order.name,
		"message": _("Project Order {0} created.").format(order.name),
	}


_CREATE_DISPATCH = {
	"Air Booking": _create_air_booking,
	"Sea Booking": _create_sea_booking,
	"Transport Order": _create_transport_order,
	"Declaration Order": _create_declaration_order,
	"Inbound Order": _create_inbound_order,
	"Project Order": _create_project_order,
}


def _apply_cargo_and_shipment_lines(
	sp_doc: Any, target_doc: Any, shipment_lines: Any = None
) -> None:
	from logistics.special_projects.special_project_packages import (
		apply_shipment_lines_to_target,
		copy_always_along_packages_to_target,
	)

	if shipment_lines:
		apply_shipment_lines_to_target(sp_doc, target_doc, shipment_lines)
	if target_doc.doctype in (
		"Air Booking",
		"Sea Booking",
		"Transport Order",
		"Inbound Order",
		"Project Order",
	):
		copy_always_along_packages_to_target(sp_doc, target_doc)


@frappe.whitelist()
def create_booking_or_order_from_special_project(
	special_project: str,
	job_type: str,
	lifecycle_job_idx: int | None = None,
	lifecycle_jobs: Any = None,
	special_project_services: Any = None,
	order_title: str | None = None,
	shipment_lines: Any = None,
	creation_parameters: Any = None,
):
	"""Create the chosen booking/order from the matching Special Project Service row on the Special Project."""
	if not special_project or not frappe.db.exists("Special Project", special_project):
		frappe.throw(_("Invalid Special Project."))
	jt = (job_type or "").strip()
	if jt not in SPECIAL_PROJECT_CREATABLE_JOB_TYPES:
		frappe.throw(_("Invalid job type."))

	sp_doc = frappe.get_doc("Special Project", special_project)
	sp_doc.check_permission("write")

	idx = coerce_internal_job_detail_idx(lifecycle_job_idx)
	params_explicit = creation_parameters is not None
	parsed_params = (
		_parse_creation_parameters(creation_parameters) if params_explicit else None
	)
	client_rows = special_project_services if special_project_services is not None else lifecycle_jobs

	with _client_rows_context(client_rows):
		validate_lifecycle_job_params_match_quotation(
			sp_doc,
			jt,
			idx,
			creation_parameters=creation_parameters,
		)
		row, resolved_idx = _resolve_row_for_create(sp_doc, jt, idx)
		if row is None:
			frappe.throw(
				_(
					"Add a Service line with service type matching {0}, or select an existing open line."
				).format(jt)
			)
		if resolved_idx is None:
			frappe.throw(_("Could not resolve the Service row to update after creation."))
		service_label, scoped_params, merged_row = _resolve_scoped_creation_params(
			sp_doc,
			jt,
			row,
			parsed_params,
		)
		handler = _CREATE_DISPATCH[jt]
		kwargs: dict[str, Any] = {
			"shipment_lines": shipment_lines,
			"creation_parameters": (
				parsed_params if params_explicit else (scoped_params or None)
			),
		}
		if jt == "Project Order":
			return handler(
				sp_doc,
				merged_row,
				resolved_idx,
				order_title=order_title,
				**kwargs,
			)
		return handler(sp_doc, merged_row, resolved_idx, **kwargs)
