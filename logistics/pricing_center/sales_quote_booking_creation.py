# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Create Air/Sea Booking, Transport/Declaration/Inbound Order from Sales Quote Main Service.

Regular and Project quotes stay reusable: created bookings link to the quote but Services rows and
quote-owned Linked Service documents are **not** updated with ``job_type`` / ``job_no``.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, today

from logistics.utils.charge_service_type import (
	default_job_type_for_internal_job_service_type,
	effective_internal_job_detail_job_type,
	sales_quote_charge_service_types_equal,
)
from logistics.utils.internal_job_from_source import (
	apply_internal_job_detail_row_to_operational_doc,
	coerce_internal_job_detail_idx,
)
from logistics.utils.internal_job_creation_eligibility import (
	charges_exist_for_service,
	evaluate_internal_job_creation_eligibility,
	internal_job_matches_charges,
)
from logistics.utils.linked_service_compat import linked_service_rows
from logistics.utils.sales_quote_charge_parameters import (
	any_sales_quote_charge_matches_internal_job_detail_params,
	extract_service_scoped_quote_parameters,
	normalize_quote_parameter_json,
	parameter_fields_for_service_type,
	resolve_parameters_from_sales_quote_scope,
	SALES_QUOTE_CHARGE_PARAMETER_FIELDS,
)

_LOGISTICS_SQ_CLIENT_LINKED_SERVICES = "_logistics_sq_client_linked_services"

SALES_QUOTE_CREATABLE_JOB_TYPES: frozenset[str] = frozenset(
	{
		"Air Booking",
		"Sea Booking",
		"Transport Order",
		"Declaration Order",
		"Inbound Order",
	}
)

_SERVICE_LABEL_FOR_JOB_TYPE: dict[str, str] = {
	"Transport Order": "Transport",
	"Declaration Order": "Customs",
	"Air Booking": "Air",
	"Sea Booking": "Sea",
	"Inbound Order": "Warehousing",
}

_MAIN_SERVICE_JOB_TYPE: dict[str, str] = {
	"Air": "Air Booking",
	"Sea": "Sea Booking",
	"Transport": "Transport Order",
	"Customs": "Declaration Order",
	"Custom": "Declaration Order",
	"Warehousing": "Inbound Order",
}

_SALES_QUOTE_BOOKING_QUOTATION_TYPES: frozenset[str] = frozenset({"Regular", "Project"})


def quotation_type_supports_booking_creation(sq_doc: Any) -> bool:
	"""Regular quotes always; Project quotes when Main Service maps to a booking/order type."""
	qt = _norm(getattr(sq_doc, "quotation_type", None))
	if qt not in _SALES_QUOTE_BOOKING_QUOTATION_TYPES:
		return False
	if qt == "Project":
		ms = _norm(getattr(sq_doc, "main_service", None))
		return ms in _MAIN_SERVICE_JOB_TYPE
	return True


def _norm(value: Any) -> str:
	if value is None:
		return ""
	return str(value).strip()


def _parse_creation_parameters(value: Any) -> dict[str, Any]:
	return normalize_quote_parameter_json(value)


def _coerce_client_rows(client_value: Any) -> list[Any] | None:
	if client_value is None or client_value == "":
		return None
	if isinstance(client_value, str):
		try:
			client_value = json.loads(client_value)
		except Exception:
			return None
	if isinstance(client_value, list):
		return client_value
	return None


@contextmanager
def _client_linked_services_context(client_value: Any):
	key = _LOGISTICS_SQ_CLIENT_LINKED_SERVICES
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


def _linked_service_rows_list(sq_doc: Any) -> list[Any]:
	ov = getattr(frappe.local, _LOGISTICS_SQ_CLIENT_LINKED_SERVICES, None)
	if ov is not None:
		return list(ov)
	return linked_service_rows(sq_doc)


def _rows_for_form(sq_doc: Any, client_rows: Any) -> list[tuple[int, Any]]:
	with _client_linked_services_context(client_rows):
		rows = _linked_service_rows_list(sq_doc)
	return [(int(getattr(row, "idx", None) or i), row) for i, row in enumerate(rows, start=1)]


def _row_by_idx(sq_doc: Any, idx: int | None) -> Any | None:
	if idx is None:
		return None
	for row_idx, row in _rows_for_form(sq_doc, None):
		if row_idx == idx:
			return row
	return None


def _main_service_job_type(sq_doc: Any) -> str:
	ms = _norm(getattr(sq_doc, "main_service", None))
	return _MAIN_SERVICE_JOB_TYPE.get(ms, "")


def _main_service_virtual_row(sq_doc: Any) -> frappe._dict:
	"""Synthetic Services row from quote scope / header for standalone main-service shipments."""
	from logistics.utils.sales_quote_charge_parameters import build_main_service_scope_row

	ms = _norm(getattr(sq_doc, "main_service", None))
	jt = _main_service_job_type(sq_doc)
	row = build_main_service_scope_row(sq_doc)
	row.job_type = jt or default_job_type_for_internal_job_service_type(ms)
	return row


def _parse_quote_context(value: Any) -> dict[str, Any] | None:
	if value is None or value == "":
		return None
	if isinstance(value, str):
		try:
			value = json.loads(value)
		except Exception:
			return None
	if isinstance(value, dict):
		return value
	return None


def _apply_client_quote_context(sq_doc: Any, quote_context: Any) -> None:
	"""Overlay Primary Service Type / Scope tab fields from the desk form (unsaved edits)."""
	ctx = _parse_quote_context(quote_context)
	if not ctx:
		return
	ms = _norm(ctx.get("main_service"))
	if ms:
		sq_doc.main_service = ms
	for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS:
		if fn not in ctx:
			continue
		val = ctx.get(fn)
		if val is not None and str(val).strip() != "":
			sq_doc.set(fn, val)


def _load_sales_quote_for_booking(sales_quote: str, quote_context: Any = None) -> Any:
	sq_doc = frappe.get_doc("Sales Quote", sales_quote)
	_apply_client_quote_context(sq_doc, quote_context)
	return sq_doc


def _linked_service_rows_nonempty(sq_doc: Any, client_rows: Any = None) -> bool:
	return bool(_rows_for_form(sq_doc, client_rows))


def _use_main_service_mode(
	use_main_service: int | None,
	detail_idx: int | None,
) -> bool:
	"""Default to Main Service scope; per-line create only when use_main_service=0."""
	if use_main_service is not None:
		return bool(cint(use_main_service))
	return True


def _preview_main_service_creatability(sq_doc: Any) -> dict[str, Any]:
	"""Standalone main-service quote: no Services tab rows; scope header + main-service charges suffice."""
	ms = _norm(getattr(sq_doc, "main_service", None))
	jt = _main_service_job_type(sq_doc)
	if not ms or not jt or jt not in SALES_QUOTE_CREATABLE_JOB_TYPES:
		return {
			"creatable": False,
			"has_params": False,
			"has_quote_match": False,
			"not_creatable_message": _(
				"Main Service must be Air, Sea, Transport, Customs, or Warehousing to create a booking/order."
			),
		}
	if not charges_exist_for_service(sq_doc.name, sq_doc, ms):
		return {
			"creatable": False,
			"has_params": False,
			"has_quote_match": False,
			"not_creatable_message": _(
				"Add at least one charge line for {0} (Main Service) before creating."
			).format(ms),
		}
	virtual_row = _main_service_virtual_row(sq_doc)
	has_match = internal_job_matches_charges(sq_doc.name, sq_doc, virtual_row, ms)
	return {
		"creatable": has_match,
		"has_params": bool(resolve_parameters_from_sales_quote_scope(sq_doc)),
		"has_quote_match": has_match,
		"not_creatable_message": (
			None
			if has_match
			else _(
				"Main Service scope parameters do not match any {0} charge line on this quote."
			).format(ms)
		),
	}


def _main_service_choice(sq_doc: Any) -> dict[str, Any] | None:
	jt = _main_service_job_type(sq_doc)
	if not jt:
		return None
	ms = _norm(getattr(sq_doc, "main_service", None))
	flags = _preview_main_service_creatability(sq_doc)
	creatable = bool(flags.get("creatable"))
	title = _(ms) if ms else (_(jt) if jt else _("Main Service"))
	return {
		"mode": "main",
		"detail_idx": None,
		"job_type": jt,
		"service_type": ms or None,
		"creatable": creatable,
		"header_title": title,
		"header_badge": _("Main Service"),
		"header_subtitle": _(
			"Creates {0} from Main Service scope. Regular and Project quotes stay reusable — Services lines are not updated with Job No."
		).format(_(jt)),
		**{k: flags.get(k) for k in ("not_creatable_message",)},
	}


def _service_label_for_row(job_type: str, row: Any) -> str | None:
	st = (_norm(getattr(row, "service_type", None)) if row else "") or ""
	if st:
		return st
	return _SERVICE_LABEL_FOR_JOB_TYPE.get(_norm(job_type))


def _dialog_creatable_job_type(row: Any) -> str:
	return effective_internal_job_detail_job_type(row)


def _merge_creation_parameters(row: Any, creation_parameters: Any) -> Any:
	base: dict[str, Any] = {}
	if row is not None:
		if isinstance(row, dict):
			base = dict(row)
		elif hasattr(row, "as_dict"):
			base = row.as_dict()
		else:
			base = {k: getattr(row, k, None) for k in dir(row) if not k.startswith("_")}
	merged = frappe._dict(base)
	for k, v in (_parse_creation_parameters(creation_parameters) or {}).items():
		merged[k] = v
	return merged


def _resolve_scoped_params(
	sq_doc: Any,
	job_type: str,
	row: Any | None,
	parsed_params: dict[str, Any] | None,
) -> tuple[str, dict[str, Any], Any | None]:
	jt = _norm(job_type)
	merged_row = _merge_creation_parameters(row, parsed_params) if row else None
	service_label = _service_label_for_row(jt, merged_row) or ""
	scoped = (
		extract_service_scoped_quote_parameters(merged_row, service_label)
		if merged_row and service_label
		else {}
	)
	if parsed_params:
		for k, v in parsed_params.items():
			if k in parameter_fields_for_service_type(service_label):
				scoped[k] = v
	return service_label, scoped, merged_row


def _row_matches_charges(sq_doc: Any, row: Any, service_label: str) -> bool:
	if not row or not service_label:
		return False
	return any_sales_quote_charge_matches_internal_job_detail_params(
		sq_doc, row, service_label
	)


def _preview_creatability(
	sq_doc: Any,
	job_type: str,
	row: Any | None,
	scoped_params: dict[str, Any],
) -> dict[str, Any]:
	service_label = _service_label_for_row(job_type, row) or ""
	elig = evaluate_internal_job_creation_eligibility(
		sales_quote=sq_doc.name,
		parent_doc=sq_doc,
		ij_row=row,
		service_type_label=service_label,
	)
	creatable = bool(elig.get("eligible"))
	not_creatable_message = elig.get("message")
	if creatable and scoped_params and not _row_matches_charges(sq_doc, row, service_label):
		creatable = False
		not_creatable_message = _("No charge lines match the parameters on this service line.")
	return {
		"creatable": creatable,
		"has_params": bool(scoped_params),
		"has_quote_match": _row_matches_charges(sq_doc, row, service_label),
		"not_creatable_message": not_creatable_message,
	}


def _choice_header(job_type: str, row: Any | None, idx: int | None) -> dict[str, str]:
	jt_label = _norm(job_type)
	st = _norm(getattr(row, "service_type", None)) if row else ""
	title = _(st) if st else (_(jt_label) if jt_label else _("(no service type)"))
	badge = _("Service {0}").format(idx) if idx is not None else _("Service")
	if not st:
		subtitle = _("Set Service Type on this line before creating.")
	elif not jt_label:
		subtitle = _("Could not resolve target document type for this service.")
	else:
		subtitle = _(
			"Creates {0}. Regular and Project quotes stay reusable — this service line is not updated with Job No."
		).format(_(jt_label))
	return {"header_title": title, "header_badge": badge, "header_subtitle": subtitle}


@frappe.whitelist()
def get_sales_quote_booking_choices(
	sales_quote: str, linked_services: Any = None, quote_context: Any = None
):
	"""Return Create > Booking/Order option from Main Service on a Regular or Project Sales Quote."""
	if not sales_quote or not frappe.db.exists("Sales Quote", sales_quote):
		frappe.throw(_("Invalid Sales Quote."))
	sq_doc = _load_sales_quote_for_booking(sales_quote, quote_context)
	sq_doc.check_permission("read")
	if not quotation_type_supports_booking_creation(sq_doc):
		frappe.throw(
			_(
				"Create Booking/Order is only available for Regular Sales Quotes, or Project quotes with Main Service Air, Sea, Transport, Customs, or Warehousing."
			)
		)
	if cint(sq_doc.docstatus) != 1:
		frappe.throw(_("Submit the Sales Quote before creating bookings or orders."))

	choices: list[dict[str, Any]] = []
	main_choice = _main_service_choice(sq_doc)
	if main_choice:
		choices.append(main_choice)
	service_type_filters = sorted(
		{
			(c.get("service_type") or "").strip()
			for c in choices
			if c.get("creatable") and (c.get("service_type") or "").strip()
		}
	)
	return {"choices": choices, "service_type_filters": service_type_filters}


@frappe.whitelist()
def get_sales_quote_booking_preview(
	sales_quote: str,
	job_type: str,
	detail_idx: int | None = None,
	linked_services: Any = None,
	creation_parameters: Any = None,
	use_main_service: int | None = None,
	quote_context: Any = None,
):
	"""Preview parameters and matching charges for one Services row or standalone main service."""
	if not sales_quote or not frappe.db.exists("Sales Quote", sales_quote):
		frappe.throw(_("Invalid Sales Quote."))
	sq_doc = _load_sales_quote_for_booking(sales_quote, quote_context)
	sq_doc.check_permission("read")
	jt = _norm(job_type)
	idx = coerce_internal_job_detail_idx(detail_idx)
	parsed_params = (
		_parse_creation_parameters(creation_parameters)
		if creation_parameters is not None
		else None
	)
	main_mode = _use_main_service_mode(use_main_service, idx)
	if main_mode:
		expected_jt = _main_service_job_type(sq_doc)
		if expected_jt:
			jt = expected_jt
		row = _main_service_virtual_row(sq_doc)
		idx = None
	else:
		with _client_linked_services_context(linked_services):
			row = _row_by_idx(sq_doc, idx)
	service_label, scoped_params, merged_row = _resolve_scoped_params(
		sq_doc, jt, row, parsed_params
	)
	if main_mode:
		flags = _preview_main_service_creatability(sq_doc)
	else:
		flags = _preview_creatability(sq_doc, jt, merged_row or row, scoped_params)
	charges = []
	if main_mode and flags.get("creatable"):
		ms = _norm(getattr(sq_doc, "main_service", None))
		for ch in sq_doc.get("charges") or []:
			st = _norm(getattr(ch, "service_type", None))
			if not sales_quote_charge_service_types_equal(st, ms):
				continue
			charges.append(
				{
					"service_type": st,
					"item_code": getattr(ch, "item_code", None),
					"item_name": getattr(ch, "item_name", None),
					"unit_rate": getattr(ch, "unit_rate", None),
					"currency": getattr(ch, "currency", None),
				}
			)
	elif service_label and _row_matches_charges(sq_doc, merged_row or row, service_label):
		for ch in sq_doc.get("charges") or []:
			st = _norm(getattr(ch, "service_type", None))
			if not sales_quote_charge_service_types_equal(st, service_label):
				continue
			charges.append(
				{
					"service_type": st,
					"item_code": getattr(ch, "item_code", None),
					"item_name": getattr(ch, "item_name", None),
					"unit_rate": getattr(ch, "unit_rate", None),
					"currency": getattr(ch, "currency", None),
				}
			)
	return {
		"job_type": jt,
		"detail_idx": idx,
		"use_main_service": bool(main_mode),
		"creatable": flags.get("creatable") and jt in SALES_QUOTE_CREATABLE_JOB_TYPES,
		"job_detail_parameters": scoped_params,
		"charges": charges[:50],
		"source_context": {
			"source_doctype": "Sales Quote",
			"source_name": sq_doc.name,
			"customer": sq_doc.customer,
			"company": sq_doc.company,
			"sales_quote": sq_doc.name,
		},
		**flags,
	}


def _apply_sq_booking_context(sq_doc: Any, target_doc: Any, row: Any | None, job_type: str) -> None:
	from logistics.special_projects.special_project_booking_creation import (
		_apply_sales_quote_parties_to_target,
		_set_main_service_for_one_off_quote_target,
	)
	from logistics.utils.module_integration import copy_sales_quote_fields_to_target

	meta = frappe.get_meta(target_doc.doctype)
	target_doc.sales_quote = sq_doc.name
	if meta.get_field("quote_type"):
		target_doc.quote_type = "Sales Quote"
	if meta.get_field("quote"):
		target_doc.quote = sq_doc.name
	if meta.get_field("local_customer"):
		target_doc.local_customer = sq_doc.customer
	if meta.get_field("customer"):
		target_doc.customer = sq_doc.customer
	for fn in ("company", "branch", "cost_center", "profit_center"):
		if meta.get_field(fn) and getattr(sq_doc, fn, None):
			target_doc.set(fn, getattr(sq_doc, fn))
	copy_sales_quote_fields_to_target(sq_doc, target_doc)
	_set_main_service_for_one_off_quote_target(target_doc, sq_doc.name)
	service_label = _service_label_for_row(job_type, row) or ""
	main_st = _norm(getattr(sq_doc, "main_service", None))
	from logistics.utils.service_role_rules import (
		SERVICE_ROLE_LINKED,
		apply_main_service_flags,
		get_service_role,
	)

	if (
		(hasattr(target_doc, "service_role") or hasattr(target_doc, "is_main_service"))
		and service_label
		and main_st
		and sales_quote_charge_service_types_equal(service_label, main_st)
		and get_service_role(target_doc) != SERVICE_ROLE_LINKED
	):
		apply_main_service_flags(target_doc)
	_apply_sales_quote_parties_to_target(target_doc, sq_doc.name)


def _populate_charges_on_target(sq_doc: Any, target_doc: Any) -> None:
	dt = target_doc.doctype
	if dt == "Air Booking" and hasattr(target_doc, "_populate_charges_from_sales_quote"):
		from logistics.air_freight.doctype.air_booking.air_booking import _sync_quote_and_sales_quote

		_sync_quote_and_sales_quote(target_doc)
		target_doc._populate_charges_from_sales_quote(sq_doc.name)
	elif dt == "Sea Booking" and hasattr(target_doc, "_populate_charges_from_sales_quote"):
		from logistics.sea_freight.doctype.sea_booking.sea_booking import _sync_quote_and_sales_quote

		_sync_quote_and_sales_quote(target_doc)
		target_doc._populate_charges_from_sales_quote(sq_doc)
	elif dt == "Transport Order" and hasattr(target_doc, "_populate_charges_from_sales_quote"):
		from logistics.transport.doctype.transport_order.transport_order import (
			_sync_quote_and_sales_quote,
		)

		_sync_quote_and_sales_quote(target_doc)
		target_doc._populate_charges_from_sales_quote()
	elif dt == "Declaration Order" and hasattr(target_doc, "_populate_charges_from_sales_quote"):
		target_doc._populate_charges_from_sales_quote()
	elif dt == "Inbound Order" and hasattr(target_doc, "populate_charges_from_sales_quote"):
		target_doc.populate_charges_from_sales_quote(sq_doc.name)


def _propagate_subsidiary_linked_services(sq_doc: Any, booking_doc: Any) -> None:
	from logistics.pricing_center.doctype.sales_quote.sales_quote import (
		_propagate_linked_services_to_created_booking,
	)

	_propagate_linked_services_to_created_booking(sq_doc, booking_doc)


def _create_air_booking(
	sq_doc: Any, row: Any, creation_parameters: dict[str, Any] | None = None
) -> dict[str, Any]:
	from logistics.pricing_center.doctype.sales_quote.sales_quote import (
		throw_if_additional_charge_sales_quote_blocks_booking_order_creation,
		throw_if_sales_quote_expired_for_creation,
	)
	from logistics.special_projects.special_project_booking_creation import (
		_apply_air_sea_corridor_ports_from_context,
		_apply_air_sea_settings_defaults_before_insert,
		_booking_date_field,
		_validate_air_sea_corridor_ports_before_insert,
	)
	from logistics.utils.party_address_contact_from_masters import (
		apply_party_address_contact_from_source_or_masters,
	)
	from logistics.utils.shipper_consignee_defaults import apply_shipper_consignee_defaults

	throw_if_sales_quote_expired_for_creation(sq_doc)
	throw_if_additional_charge_sales_quote_blocks_booking_order_creation(sq_doc)
	merged = _merge_creation_parameters(row, creation_parameters)
	doc = frappe.new_doc("Air Booking")
	_apply_sq_booking_context(sq_doc, doc, merged, "Air Booking")
	bd = _booking_date_field(doc)
	if bd:
		doc.set(bd, today())
	apply_internal_job_detail_row_to_operational_doc(doc, merged, overwrite=True)
	_apply_air_sea_corridor_ports_from_context(doc, sq_doc, merged)
	_apply_air_sea_settings_defaults_before_insert(doc)
	apply_party_address_contact_from_source_or_masters(doc, sq_doc)
	apply_shipper_consignee_defaults(doc)
	_validate_air_sea_corridor_ports_before_insert(doc)
	# Charges populate also copies Sales Quote routing_legs onto the booking (#1135)
	doc.flags.skip_sales_quote_on_change = True
	try:
		_populate_charges_on_target(sq_doc, doc)
		if hasattr(doc, "_normalize_charges_before_save"):
			doc._normalize_charges_before_save()
		doc.insert(ignore_permissions=True)
	finally:
		doc.flags.skip_sales_quote_on_change = False
	_propagate_subsidiary_linked_services(sq_doc, doc)
	frappe.db.commit()
	return {"air_booking": doc.name, "message": _("Air Booking {0} created.").format(doc.name)}


def _create_sea_booking(
	sq_doc: Any, row: Any, creation_parameters: dict[str, Any] | None = None
) -> dict[str, Any]:
	from logistics.pricing_center.doctype.sales_quote.sales_quote import (
		throw_if_additional_charge_sales_quote_blocks_booking_order_creation,
		throw_if_sales_quote_expired_for_creation,
	)
	from logistics.special_projects.special_project_booking_creation import (
		_apply_air_sea_corridor_ports_from_context,
		_apply_air_sea_settings_defaults_before_insert,
		_booking_date_field,
		_validate_air_sea_corridor_ports_before_insert,
	)
	from logistics.utils.party_address_contact_from_masters import (
		apply_party_address_contact_from_source_or_masters,
	)
	from logistics.utils.shipper_consignee_defaults import apply_shipper_consignee_defaults

	throw_if_sales_quote_expired_for_creation(sq_doc)
	throw_if_additional_charge_sales_quote_blocks_booking_order_creation(sq_doc)
	merged = _merge_creation_parameters(row, creation_parameters)
	doc = frappe.new_doc("Sea Booking")
	_apply_sq_booking_context(sq_doc, doc, merged, "Sea Booking")
	bd = _booking_date_field(doc)
	if bd:
		doc.set(bd, today())
	apply_internal_job_detail_row_to_operational_doc(doc, merged, overwrite=True)
	_apply_air_sea_corridor_ports_from_context(doc, sq_doc, merged)
	_apply_air_sea_settings_defaults_before_insert(doc)
	apply_party_address_contact_from_source_or_masters(doc, sq_doc)
	apply_shipper_consignee_defaults(doc)
	_validate_air_sea_corridor_ports_before_insert(doc)
	_populate_charges_on_target(sq_doc, doc)
	if hasattr(doc, "_normalize_charges_before_save"):
		doc._normalize_charges_before_save()
	doc.insert(ignore_permissions=True)
	_propagate_subsidiary_linked_services(sq_doc, doc)
	frappe.db.commit()
	return {"sea_booking": doc.name, "message": _("Sea Booking {0} created.").format(doc.name)}


def _create_transport_order(
	sq_doc: Any, row: Any, creation_parameters: dict[str, Any] | None = None
) -> dict[str, Any]:
	"""Create Transport Order using the full Sales Quote scope + charge mapping path."""
	from logistics.pricing_center.doctype.sales_quote.sales_quote import (
		_create_transport_order_from_sales_quote,
	)

	# Overlay Main Service scope / virtual row parameters onto the quote before create.
	if row:
		for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS:
			val = getattr(row, fn, None)
			if val is not None and str(val).strip() != "":
				sq_doc.set(fn, val)
	if creation_parameters:
		for k, v in (_parse_creation_parameters(creation_parameters) or {}).items():
			if v is not None and str(v).strip() != "":
				sq_doc.set(k, v)

	result = _create_transport_order_from_sales_quote(sq_doc)
	return {
		"transport_order": result.get("transport_order"),
		"message": result.get("message")
		or _("Transport Order {0} created.").format(result.get("transport_order")),
	}


def _create_declaration_order(
	sq_doc: Any, row: Any, creation_parameters: dict[str, Any] | None = None
) -> dict[str, Any]:
	from logistics.pricing_center.doctype.sales_quote.sales_quote import (
		throw_if_additional_charge_sales_quote_blocks_booking_order_creation,
		throw_if_sales_quote_expired_for_creation,
	)

	throw_if_sales_quote_expired_for_creation(sq_doc)
	throw_if_additional_charge_sales_quote_blocks_booking_order_creation(sq_doc)
	merged = _merge_creation_parameters(row, creation_parameters)
	order = frappe.new_doc("Declaration Order")
	_apply_sq_booking_context(sq_doc, order, merged, "Declaration Order")
	if frappe.get_meta("Declaration Order").get_field("order_date"):
		order.order_date = today()
	apply_internal_job_detail_row_to_operational_doc(order, merged, overwrite=True)
	from logistics.utils.service_role_rules import apply_standalone_service_flags

	apply_standalone_service_flags(order)
	_populate_charges_on_target(sq_doc, order)
	order.insert(ignore_permissions=True)
	_propagate_subsidiary_linked_services(sq_doc, order)
	frappe.db.commit()
	return {
		"declaration_order": order.name,
		"message": _("Declaration Order {0} created.").format(order.name),
	}


def _create_inbound_order(
	sq_doc: Any, row: Any, creation_parameters: dict[str, Any] | None = None
) -> dict[str, Any]:
	from logistics.pricing_center.doctype.sales_quote.sales_quote import (
		throw_if_additional_charge_sales_quote_blocks_booking_order_creation,
		throw_if_sales_quote_expired_for_creation,
	)

	throw_if_sales_quote_expired_for_creation(sq_doc)
	throw_if_additional_charge_sales_quote_blocks_booking_order_creation(sq_doc)
	merged = _merge_creation_parameters(row, creation_parameters)
	order = frappe.new_doc("Inbound Order")
	_apply_sq_booking_context(sq_doc, order, merged, "Inbound Order")
	if frappe.get_meta("Inbound Order").get_field("order_date"):
		order.order_date = today()
	apply_internal_job_detail_row_to_operational_doc(order, merged, overwrite=True)
	_populate_charges_on_target(sq_doc, order)
	order.insert(ignore_permissions=True)
	_propagate_subsidiary_linked_services(sq_doc, order)
	frappe.db.commit()
	return {"inbound_order": order.name, "message": _("Inbound Order {0} created.").format(order.name)}


_CREATE_DISPATCH = {
	"Air Booking": _create_air_booking,
	"Sea Booking": _create_sea_booking,
	"Transport Order": _create_transport_order,
	"Declaration Order": _create_declaration_order,
	"Inbound Order": _create_inbound_order,
}


@frappe.whitelist()
def create_booking_or_order_from_sales_quote(
	sales_quote: str,
	job_type: str,
	detail_idx: int | None = None,
	linked_services: Any = None,
	creation_parameters: Any = None,
	use_main_service: int | None = None,
	quote_context: Any = None,
):
	"""Create a booking/order from a Regular or Project Sales Quote Main Service scope."""
	if not sales_quote or not frappe.db.exists("Sales Quote", sales_quote):
		frappe.throw(_("Invalid Sales Quote."))
	jt = _norm(job_type)
	if jt not in SALES_QUOTE_CREATABLE_JOB_TYPES:
		frappe.throw(_("Invalid job type."))
	sq_doc = _load_sales_quote_for_booking(sales_quote, quote_context)
	sq_doc.check_permission("write")
	if not quotation_type_supports_booking_creation(sq_doc):
		frappe.throw(
			_(
				"Create Booking/Order is only available for Regular Sales Quotes, or Project quotes with Main Service Air, Sea, Transport, Customs, or Warehousing."
			)
		)
	idx = coerce_internal_job_detail_idx(detail_idx)
	parsed_params = (
		_parse_creation_parameters(creation_parameters)
		if creation_parameters is not None
		else None
	)
	main_mode = _use_main_service_mode(use_main_service, idx)
	if main_mode:
		expected_jt = _main_service_job_type(sq_doc)
		if expected_jt:
			jt = expected_jt
		if not jt or jt not in SALES_QUOTE_CREATABLE_JOB_TYPES:
			frappe.throw(_("The selected target does not match quote Primary Service Type."))
		row = _main_service_virtual_row(sq_doc)
		flags = _preview_main_service_creatability(sq_doc)
		if not flags.get("creatable"):
			frappe.throw(
				flags.get("not_creatable_message")
				or _("Cannot create {0} from Main Service.").format(jt),
				title=_("Cannot create booking/order"),
			)
		merged_row = _merge_creation_parameters(row, parsed_params)
		handler = _CREATE_DISPATCH[jt]
		return handler(sq_doc, merged_row, parsed_params)

	with _client_linked_services_context(linked_services):
		row = _row_by_idx(sq_doc, idx)
	if row is None:
		frappe.throw(_("Could not find the selected Services line on this Sales Quote."))
	row_jt = _dialog_creatable_job_type(row)
	if row_jt != jt:
		frappe.throw(_("The selected line is not for {0}.").format(jt))
	service_label, scoped_params, merged_row = _resolve_scoped_params(
		sq_doc, jt, row, parsed_params
	)
	flags = _preview_creatability(sq_doc, jt, merged_row, scoped_params)
	if not flags.get("creatable"):
		frappe.throw(
			flags.get("not_creatable_message")
			or _("Cannot create {0} from this service line.").format(jt),
			title=_("Cannot create booking/order"),
		)
	handler = _CREATE_DISPATCH[jt]
	return handler(sq_doc, merged_row, parsed_params)
