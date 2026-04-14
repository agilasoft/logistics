# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Create Transport Order / Declaration Order / Air Booking / Sea Booking from shipments or transport jobs using Internal Job Detail rows."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import frappe
from frappe import _

from logistics.utils.charge_service_type import effective_internal_job_detail_job_type
from logistics.utils.internal_job_detail_copy import (
	get_declaration_order_job_no_from_shipment_doc,
	persist_internal_job_detail_job_link,
)
from logistics.utils.sales_quote_charge_parameters import extract_sales_quote_charge_parameters


CREATABLE_INTERNAL_JOB_TYPES: frozenset[str] = frozenset(
	{"Transport Order", "Declaration Order", "Air Booking", "Sea Booking", "Inbound Order"}
)

_SERVICE_LOWER_FOR_JOB_TYPE: dict[str, str] = {
	"Transport Order": "transport",
	"Declaration Order": "customs",
	"Air Booking": "air",
	"Sea Booking": "sea",
	"Inbound Order": "warehousing",
}

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
	"""Resolve the Internal Job Detail row used for create: explicit idx, else first open line for this job type.

	Does not match rows using sales quote routing; only explicit index or open lines in ``internal_job_details``.

	Returns (row, 1-based idx) for persisting job_no after create.
	"""
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
	params = extract_sales_quote_charge_parameters(row)
	if not params:
		return
	meta = frappe.get_meta(doc.doctype)
	dt = doc.doctype

	def set_field(fieldname: str, val: Any) -> None:
		if val is None or val == "":
			return
		if not meta.get_field(fieldname):
			return
		cur = getattr(doc, fieldname, None)
		if overwrite or cur is None or cur == "":
			doc.set(fieldname, val)

	if dt == "Air Booking":
		if "air_house_type" in params:
			set_field("house_type", params["air_house_type"])
		for fn in (
			"airline",
			"freight_agent",
			"direction",
			"origin_port",
			"destination_port",
			"transport_mode",
			"load_type",
		):
			if fn in params:
				set_field(fn, params[fn])
		return

	if dt == "Sea Booking":
		if "sea_house_type" in params:
			set_field("house_type", params["sea_house_type"])
		if "freight_agent_sea" in params:
			set_field("freight_agent", params["freight_agent_sea"])
		for fn in ("shipping_line", "direction", "origin_port", "destination_port", "transport_mode"):
			if fn in params:
				set_field(fn, params[fn])
		return

	for fn, val in params.items():
		set_field(fn, val)


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
			return source_doctype == "Air Shipment"
		if jt == "Air Booking":
			return source_doctype == "Sea Shipment" and _shipment_charge_matches_service(parent_doc, "air")
		if jt == "Inbound Order":
			return bool(flags.get("allow_inbound"))
		return False
	if source_doctype == "Transport Job":
		if jt == "Transport Order":
			return True
		if jt == "Declaration Order":
			return bool(flags.get("allow_declaration"))
		if jt in ("Air Booking", "Sea Booking"):
			return True
		if jt == "Inbound Order":
			return bool(flags.get("allow_inbound"))
		return False
	if source_doctype == "Declaration":
		from frappe.utils import cint

		sq = getattr(parent_doc, "sales_quote", None)
		if jt == "Transport Order":
			if not sq:
				return False
			if (getattr(parent_doc, "transport_order", None) or "").strip():
				return False
			is_ij = cint(getattr(parent_doc, "is_internal_job", 0))
			is_main = cint(getattr(parent_doc, "is_main_service", 0))
			return bool((is_main and not is_ij) or is_ij)
		if jt == "Inbound Order":
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
	"""Structured card header (title, pill, subtitle) for Create Internal Job UI."""
	jt_label = (job_type or "").strip()
	st = (getattr(row, "service_type", None) or "").strip() if row else ""
	jn = (getattr(row, "job_no", None) or "").strip() if row else ""
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
	return {
		"header_title": title,
		"header_badge": badge,
		"header_subtitle": subtitle,
	}


@frappe.whitelist()
def get_internal_job_creation_choices(
	source_doctype: str,
	source_name: str,
	internal_job_details: Any = None,
):
	"""Build Create > Internal Job options: all Internal Job Detail rows; lines with Job No stay visible (not creatable)."""
	if not source_name or not frappe.db.exists(source_doctype, source_name):
		frappe.throw(_("Invalid source document."))
	if source_doctype not in ("Air Shipment", "Sea Shipment", "Transport Job", "Declaration"):
		frappe.throw(_("Unsupported source type."))

	doc = frappe.get_doc(source_doctype, source_name)
	doc.check_permission("read")

	from logistics.utils.sales_quote_service_eligibility import get_quote_module_flags

	flags = get_quote_module_flags(
		getattr(doc, "sales_quote", None),
		source_doctype=source_doctype,
		source_name=source_name,
	)

	choices: list[dict[str, Any]] = []
	for idx, row in _all_internal_job_detail_rows_for_form(doc, internal_job_details):
		st = (getattr(row, "service_type", None) or "").strip()
		jt = effective_internal_job_detail_job_type(row)
		jn = (getattr(row, "job_no", None) or "").strip()
		if jn:
			creatable = False
		else:
			creatable = bool(st) and bool(jt) and _job_type_allowed_for_source(source_doctype, doc, jt, flags)
		label = _choice_label(jt, row, idx)
		if jt and not creatable and not jn:
			label = "{0} — {1}".format(label, _("cannot create from here"))
		choices.append(
			{
				"mode": "detail",
				"detail_idx": idx,
				"job_type": jt,
				"service_type": st or None,
				"job_no": jn or None,
				"label": label,
				"creatable": creatable,
				**_choice_header_fields(jt, row, idx),
			}
		)

	return {"choices": choices}


def _job_preview_parameters_for_display(params: dict[str, Any] | None) -> dict[str, Any]:
	"""Strip charge_group from Create Internal Job preview (not part of Internal Job Detail anymore)."""
	if not params:
		return {}
	return {k: v for k, v in params.items() if k != "charge_group"}


def _charges_preview_list(parent_doc: Any, service_lower: str, routing_params: dict[str, Any]) -> list[dict[str, Any]]:
	"""Mirror module_integration freight preview: charge rows × routing parameters shown per line."""
	from frappe.utils import flt

	out: list[dict[str, Any]] = []
	params = dict(routing_params or {})
	for ch in getattr(parent_doc, "charges", None) or []:
		st = (getattr(ch, "service_type", None) or "").strip().lower()
		if st != service_lower:
			continue
		out.append(
			{
				"service_type": getattr(ch, "service_type", None),
				"item_code": getattr(ch, "item_code", None),
				"item_name": getattr(ch, "item_name", None),
				"rate": flt(getattr(ch, "rate", None)) or None,
				"unit_rate": flt(getattr(ch, "unit_rate", None)) or None,
				"per_unit_rate": flt(getattr(ch, "per_unit_rate", None)) or None,
				"currency": getattr(ch, "currency", None),
				"selling_currency": getattr(ch, "selling_currency", None),
				"estimated_revenue": flt(getattr(ch, "estimated_revenue", None)) or None,
				"parameters": params,
			}
		)
	return out


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
	from frappe.utils import cint

	from logistics.utils import module_integration as mi

	def _line_only_preview(
		row: Any, res_idx: int, *, message: str, job_type_label: str | None = None
	) -> dict[str, Any]:
		params = extract_sales_quote_charge_parameters(row) if row else {}
		preview_params = _job_preview_parameters_for_display(params)
		customer = getattr(doc, "local_customer", None) or getattr(doc, "customer", None)
		jtl = (job_type_label if job_type_label is not None else jt) or ""
		if not jtl and row is not None:
			jtl = effective_internal_job_detail_job_type(row)
		return {
			"job_type": jtl,
			"detail_idx": res_idx,
			"uses_job_detail_row": True,
			"creatable": False,
			"not_creatable_message": message,
			"source_context": {
				"source_doctype": source_doctype,
				"source_name": source_name,
				"customer": customer,
				"company": getattr(doc, "company", None),
				"sales_quote": getattr(doc, "sales_quote", None),
				"source_is_internal_job": bool(cint(getattr(doc, "is_internal_job", 0))),
				"source_main_job_type": getattr(doc, "main_job_type", None),
				"source_main_job": getattr(doc, "main_job", None),
				"from_main_service_shipment": False,
			},
			"target_internal_job": None,
			"job_detail_parameters": preview_params,
			"charges": [],
		}

	if idx is not None:
		rows_ij = _ij_rows_list(doc)
		if 1 <= idx <= len(rows_ij):
			row_linked = rows_ij[idx - 1]
			jn_linked = (getattr(row_linked, "job_no", None) or "").strip()
			if jn_linked:
				row_jt = effective_internal_job_detail_job_type(row_linked)
				jtl = (jt or "").strip() or row_jt
				return _line_only_preview(
					row_linked,
					idx,
					message=_("This line is already linked to {0}.").format(jn_linked),
					job_type_label=jtl or row_jt,
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
	ij, mjt, mj = (
		cint(getattr(doc, "is_internal_job", 0)),
		getattr(doc, "main_job_type", None),
		getattr(doc, "main_job", None),
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
		else:
			target_internal = None
	elif source_doctype == "Transport Job":
		if jt in ("Declaration Order", "Transport Order"):
			target_internal = {
				"is_internal_job": True,
				"main_job_type": "Transport Job",
				"main_job": doc.name,
			}
	elif source_doctype == "Declaration":
		if jt == "Transport Order" and cint(getattr(doc, "is_internal_job", 0)):
			target_internal = {
				"is_internal_job": True,
				"main_job_type": "Declaration",
				"main_job": doc.name,
			}
		elif jt == "Inbound Order":
			target_internal = {
				"is_internal_job": True,
				"main_job_type": "Declaration",
				"main_job": doc.name,
			}

	customer = getattr(doc, "local_customer", None) or getattr(doc, "customer", None)
	charges = _charges_preview_list(doc, svc, routing_params)
	preview_params = _job_preview_parameters_for_display(routing_params)
	charges_for_preview = [{**c, "parameters": preview_params} for c in charges]

	return {
		"job_type": jt,
		"detail_idx": res_idx,
		"uses_job_detail_row": ij_row is not None,
		"creatable": True,
		"source_context": {
			"source_doctype": source_doctype,
			"source_name": source_name,
			"customer": customer,
			"company": getattr(doc, "company", None),
			"sales_quote": getattr(doc, "sales_quote", None),
			"source_is_internal_job": bool(cint(getattr(doc, "is_internal_job", 0))),
			"source_main_job_type": getattr(doc, "main_job_type", None),
			"source_main_job": getattr(doc, "main_job", None),
			"from_main_service_shipment": from_main,
		},
		"target_internal_job": target_internal,
		"job_detail_parameters": preview_params,
		"charges": charges_for_preview,
	}


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

	idx = coerce_internal_job_detail_idx(internal_job_detail_idx)

	from logistics.utils import module_integration as mi

	with internal_job_details_client_rows(internal_job_details):
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
			if jt == "Inbound Order":
				return mi.create_inbound_order_from_air_shipment(
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
			if jt == "Inbound Order":
				return mi.create_inbound_order_from_sea_shipment(
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
			if jt == "Inbound Order":
				return mi.create_inbound_order_from_transport_job(
					source_name, internal_job_detail_idx=idx
				)
		if source_doctype == "Declaration":
			if jt == "Transport Order":
				return mi.create_transport_order_from_declaration(
					source_name, internal_job_detail_idx=idx
				)
			if jt == "Inbound Order":
				return mi.create_inbound_order_from_declaration(
					source_name, internal_job_detail_idx=idx
				)

	frappe.throw(_("Unsupported source type."))


def _create_air_booking_from_sea_shipment(sea_shipment_name: str, internal_job_detail_idx: int | None):
	shipment = frappe.get_doc("Sea Shipment", sea_shipment_name)
	idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	row, resolved_idx = resolve_internal_job_detail_row_for_create(shipment, "Air Booking", idx)
	if row is None and not _shipment_charge_matches_service(shipment, "air"):
		frappe.throw(
			_("Air Booking is only available when this shipment has Air-related charges or an Internal Job Detail line for Air Booking.")
		)
	doc = frappe.new_doc("Air Booking")
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
	doc.is_internal_job = 1
	doc.main_job_type = "Sea Shipment"
	doc.main_job = sea_shipment_name
	if row:
		apply_internal_job_detail_row_to_operational_doc(doc, row, overwrite=True)
	doc.insert(ignore_permissions=True)
	persist_internal_job_detail_job_link(
		"Sea Shipment", sea_shipment_name, "Air Booking", doc.name, detail_idx=resolved_idx
	)
	frappe.db.commit()
	return {"air_booking": doc.name, "message": _("Air Booking {0} created.").format(doc.name)}


def _create_sea_booking_from_air_shipment(air_shipment_name: str, internal_job_detail_idx: int | None):
	shipment = frappe.get_doc("Air Shipment", air_shipment_name)
	idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	row, resolved_idx = resolve_internal_job_detail_row_for_create(shipment, "Sea Booking", idx)
	doc = frappe.new_doc("Sea Booking")
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
	doc.is_internal_job = 1
	doc.main_job_type = "Air Shipment"
	doc.main_job = air_shipment_name
	if row:
		apply_internal_job_detail_row_to_operational_doc(doc, row, overwrite=True)
	doc.insert(ignore_permissions=True)
	persist_internal_job_detail_job_link(
		"Air Shipment", air_shipment_name, "Sea Booking", doc.name, detail_idx=resolved_idx
	)
	frappe.db.commit()
	return {"sea_booking": doc.name, "message": _("Sea Booking {0} created.").format(doc.name)}


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
	doc.is_internal_job = 1
	doc.main_job_type = "Transport Job"
	doc.main_job = job.name
	if row:
		apply_internal_job_detail_row_to_operational_doc(doc, row, overwrite=True)
	doc.insert(ignore_permissions=True)
	persist_internal_job_detail_job_link(
		"Transport Job", transport_job_name, "Air Booking", doc.name, detail_idx=resolved_idx
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
	doc.is_internal_job = 1
	doc.main_job_type = "Transport Job"
	doc.main_job = job.name
	if row:
		apply_internal_job_detail_row_to_operational_doc(doc, row, overwrite=True)
	doc.insert(ignore_permissions=True)
	persist_internal_job_detail_job_link(
		"Transport Job", transport_job_name, "Sea Booking", doc.name, detail_idx=resolved_idx
	)
	frappe.db.commit()
	return {"sea_booking": doc.name, "message": _("Sea Booking {0} created.").format(doc.name)}


def _create_declaration_order_from_transport_job(transport_job_name: str, internal_job_detail_idx: int | None):
	from frappe.utils import today

	job = frappe.get_doc("Transport Job", transport_job_name)
	idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	row, resolved_idx = resolve_internal_job_detail_row_for_create(job, "Declaration Order", idx)
	order = frappe.new_doc("Declaration Order")
	order.is_internal_job = 1
	order.main_job_type = "Transport Job"
	order.main_job = job.name
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
	persist_internal_job_detail_job_link(
		"Transport Job", transport_job_name, "Declaration Order", order.name, detail_idx=resolved_idx
	)
	frappe.db.commit()
	return {"declaration_order": order.name, "message": _("Declaration Order {0} created.").format(order.name)}


def _create_transport_order_from_transport_job(transport_job_name: str, internal_job_detail_idx: int | None):
	job = frappe.get_doc("Transport Job", transport_job_name)
	idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	row, resolved_idx = resolve_internal_job_detail_row_for_create(job, "Transport Order", idx)
	if row is None:
		frappe.throw(
			_("Add an Internal Job Detail line with Job Type {0} or pick that line when creating a Transport Order from a Transport Job.").format(
				_("Transport Order")
			)
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
	order.transport_job_type = getattr(job, "transport_job_type", None) or "Non-Container"
	if getattr(job, "transport_mode", None):
		order.transport_mode = job.transport_mode
	if getattr(job, "load_type", None):
		order.load_type = job.load_type
	order.is_internal_job = 1
	order.main_job_type = "Transport Job"
	order.main_job = job.name
	from logistics.utils.module_integration import copy_sales_quote_fields_to_target

	copy_sales_quote_fields_to_target(job, order)
	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	order.insert(ignore_permissions=True)
	persist_internal_job_detail_job_link(
		"Transport Job", transport_job_name, "Transport Order", order.name, detail_idx=resolved_idx
	)
	frappe.db.commit()
	return {"transport_order": order.name, "message": _("Transport Order {0} created.").format(order.name)}
