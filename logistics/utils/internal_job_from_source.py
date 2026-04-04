# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Create Transport Order / Declaration Order / Air Booking / Sea Booking from shipments or transport jobs using Internal Job Detail rows."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from logistics.utils.internal_job_detail_copy import (
	get_declaration_order_job_no_from_shipment_doc,
	persist_internal_job_detail_job_link,
)
from logistics.utils.sales_quote_charge_parameters import extract_sales_quote_charge_parameters


CREATABLE_INTERNAL_JOB_TYPES: frozenset[str] = frozenset(
	{"Transport Order", "Declaration Order", "Air Booking", "Sea Booking"}
)

_SERVICE_LOWER_FOR_JOB_TYPE: dict[str, str] = {
	"Transport Order": "transport",
	"Declaration Order": "customs",
	"Air Booking": "air",
	"Sea Booking": "sea",
}

_ROUTING_LABEL_FOR_JOB_TYPE: dict[str, str] = {
	"Transport Order": "Transport",
	"Declaration Order": "Customs",
	"Air Booking": "Air",
	"Sea Booking": "Sea",
}


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

	Returns (row, 1-based idx) for persisting job_no after create.
	"""
	jt = (job_type or "").strip()
	idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	if idx is not None:
		return resolve_internal_job_detail_row(parent_doc, idx, jt), idx

	rows = list(getattr(parent_doc, "internal_job_details", None) or [])
	for i, r in enumerate(rows, start=1):
		if (getattr(r, "job_type", None) or "").strip() != jt:
			continue
		if (getattr(r, "job_no", None) or "").strip():
			continue
		return r, i

	st_label = _ROUTING_LABEL_FOR_JOB_TYPE.get(jt)
	if not st_label:
		return None, None
	from logistics.utils.routing_quote_context import get_internal_job_detail_by_service_type

	match = get_internal_job_detail_by_service_type(parent_doc, st_label)
	if not match or (getattr(match, "job_no", None) or "").strip():
		return None, None
	for i, r in enumerate(rows, start=1):
		if getattr(r, "name", None) and getattr(match, "name", None) and r.name == match.name:
			return match, i
	return None, None


def resolve_internal_job_detail_row(
	parent_doc: Any, internal_job_detail_idx: int | None, expected_job_type: str
) -> Any | None:
	"""Return the child row at 1-based idx or None. Validates job_type when idx is set."""
	if internal_job_detail_idx is None:
		return None
	rows = list(getattr(parent_doc, "internal_job_details", None) or [])
	if internal_job_detail_idx < 1 or internal_job_detail_idx > len(rows):
		frappe.throw(_("Invalid Internal Job Detail row."))
	row = rows[internal_job_detail_idx - 1]
	jt = (getattr(row, "job_type", None) or "").strip()
	if jt != (expected_job_type or "").strip():
		frappe.throw(_("The selected line is not for {0}.").format(expected_job_type))
	jn = (getattr(row, "job_no", None) or "").strip()
	if jn:
		frappe.throw(
			_("This Internal Job Detail line already references {0} {1}.").format(jt, jn),
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


def _detail_rows_for_creation(parent_doc: Any) -> list[tuple[int, Any]]:
	"""1-based indices of internal_job_details rows that describe a creatable job and have no job_no yet."""
	out: list[tuple[int, Any]] = []
	for i, row in enumerate(getattr(parent_doc, "internal_job_details", None) or [], start=1):
		jt = (getattr(row, "job_type", None) or "").strip()
		if jt not in CREATABLE_INTERNAL_JOB_TYPES:
			continue
		if (getattr(row, "job_no", None) or "").strip():
			continue
		out.append((i, row))
	return out


def _choice_label(job_type: str, row: Any | None, idx: int | None, *, generic: bool = False) -> str:
	"""Dropdown label; detail lines lead with 1-based child row idx."""
	if generic:
		return "{0} — {1}".format(_(job_type), _("default routing"))
	st = (getattr(row, "service_type", None) or "").strip() if row else ""
	parts = []
	if idx is not None:
		parts.append(_("[idx {0}] {1}").format(idx, _(job_type)))
	else:
		parts.append(_(job_type))
	if st:
		parts.append(st)
	return " — ".join(parts)


@frappe.whitelist()
def get_internal_job_creation_choices(
	source_doctype: str,
	source_name: str,
):
	"""Build Create > Internal Job dropdown: Internal Job Detail lines first, then generic eligible types without a matching open line."""
	if not source_name or not frappe.db.exists(source_doctype, source_name):
		frappe.throw(_("Invalid source document."))
	if source_doctype not in ("Air Shipment", "Sea Shipment", "Transport Job"):
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
	detail_by_type: dict[str, list[tuple[int, Any]]] = {}
	for idx, row in _detail_rows_for_creation(doc):
		jt = (getattr(row, "job_type", None) or "").strip()
		detail_by_type.setdefault(jt, []).append((idx, row))
		choices.append(
			{
				"mode": "detail",
				"detail_idx": idx,
				"job_type": jt,
				"label": _choice_label(jt, row, idx, generic=False),
			}
		)

	def add_generic(job_type: str) -> None:
		if job_type in detail_by_type:
			return
		choices.append(
			{
				"mode": "generic",
				"detail_idx": None,
				"job_type": job_type,
				"label": _choice_label(job_type, None, None, generic=True),
			}
		)

	if source_doctype in ("Air Shipment", "Sea Shipment"):
		add_generic("Transport Order")
		sq = getattr(doc, "sales_quote", None)
		if sq and not get_declaration_order_job_no_from_shipment_doc(doc):
			add_generic("Declaration Order")
		if source_doctype == "Air Shipment":
			add_generic("Sea Booking")
		if source_doctype == "Sea Shipment" and _shipment_charge_matches_service(doc, "air"):
			add_generic("Air Booking")
	elif source_doctype == "Transport Job":
		if flags.get("allow_declaration"):
			add_generic("Declaration Order")
		add_generic("Air Booking")
		add_generic("Sea Booking")

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
):
	"""Job-detail parameters and parent charge rows that will be copied into the new internal job."""
	from frappe.utils import cint

	from logistics.utils import module_integration as mi

	jt = (job_type or "").strip()
	if jt not in CREATABLE_INTERNAL_JOB_TYPES:
		frappe.throw(_("Invalid job type."))
	if not source_name or not frappe.db.exists(source_doctype, source_name):
		frappe.throw(_("Invalid source document."))
	if source_doctype not in ("Air Shipment", "Sea Shipment", "Transport Job"):
		frappe.throw(_("Unsupported source type."))

	idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	doc = frappe.get_doc(source_doctype, source_name)
	doc.check_permission("read")

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
			ij, mjt, mj = mi._transport_order_job_context_from_freight_shipment(doc, source_doctype, source_name)
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

	customer = getattr(doc, "local_customer", None) or getattr(doc, "customer", None)
	charges = _charges_preview_list(doc, svc, routing_params)
	preview_params = _job_preview_parameters_for_display(routing_params)
	charges_for_preview = [{**c, "parameters": preview_params} for c in charges]

	return {
		"job_type": jt,
		"detail_idx": res_idx,
		"uses_job_detail_row": ij_row is not None,
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
):
	"""Dispatch create by source + job type; optional 1-based Internal Job Detail row index applies row defaults."""
	jt = (job_type or "").strip()
	if jt not in CREATABLE_INTERNAL_JOB_TYPES:
		frappe.throw(_("Invalid job type."))

	idx = coerce_internal_job_detail_idx(internal_job_detail_idx)

	from logistics.utils import module_integration as mi

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
	if source_doctype == "Sea Shipment":
		if jt == "Transport Order":
			return mi.create_transport_order_from_sea_shipment(
				source_name, internal_job_detail_idx=idx
			)
		if jt == "Declaration Order":
			return mi.create_declaration_order_from_sea_shipment(
				source_name, internal_job_detail_idx=idx
			)
		if jt == "Air Booking":
			return _create_air_booking_from_sea_shipment(source_name, internal_job_detail_idx=idx)
	if source_doctype == "Transport Job":
		if jt == "Transport Order":
			return _create_transport_order_from_transport_job(source_name, internal_job_detail_idx=idx)
		if jt == "Declaration Order":
			return _create_declaration_order_from_transport_job(source_name, internal_job_detail_idx=idx)
		if jt == "Air Booking":
			return _create_air_booking_from_transport_job(source_name, internal_job_detail_idx=idx)
		if jt == "Sea Booking":
			return _create_sea_booking_from_transport_job(source_name, internal_job_detail_idx=idx)

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
