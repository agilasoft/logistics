# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Blanket Quotation call-off: preview and create bookings/orders from selected charge rows."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from logistics.pricing_center.doctype.sales_quote.sales_quote import (
	_get_service_params,
	_sq_charge_row_matches_service,
)
from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal
from logistics.utils.sales_quote_validity import throw_if_sales_quote_expired_for_creation

BLANKET_TARGET_DOCTYPES = frozenset(
	{"Sea Booking", "Air Booking", "Transport Order", "Declaration Order"}
)

TARGET_SERVICE_LABEL = {
	"Sea Booking": "Sea",
	"Air Booking": "Air",
	"Transport Order": "Transport",
	"Declaration Order": "Customs",
}

SUMMARY_FIELDS_BY_SERVICE = {
	"Air": ("airline", "origin_port", "destination_port"),
	"Sea": ("shipping_line", "origin_port", "destination_port"),
	"Transport": ("location_type", "location_from", "location_to"),
	"Customs": ("customs_authority", "declaration_type", "customs_broker"),
}

DETAIL_FIELDS = (
	"calculation_method",
	"cost_calculation_method",
	"quantity",
	"cost_quantity",
	"uom",
	"cost_uom",
	"currency",
	"cost_currency",
	"unit_rate",
	"unit_cost",
	"unit_type",
	"cost_unit_type",
	"minimum_charge",
	"maximum_charge",
	"estimated_revenue",
	"estimated_cost",
	"bill_to",
	"pay_to",
	"tariff",
	"revenue_tariff",
	"cost_tariff",
	"charge_type",
	"charge_category",
	"revenue_calc_notes",
	"cost_calc_notes",
)

PARENT_FIELD_SPECS = {
	"Sea Booking": [
		{"fieldname": "local_customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "reqd": 1},
		{"fieldname": "service_type", "label": _("Service Type"), "fieldtype": "Data", "read_only": 1},
		{"fieldname": "shipping_line", "label": _("Shipping Line"), "fieldtype": "Link", "options": "Shipping Line"},
		{"fieldname": "reference_no", "label": _("Reference No."), "fieldtype": "Data", "filter_only": 1},
		{"fieldname": "origin_port", "label": _("Origin Port"), "fieldtype": "Link", "options": "UNLOCO"},
		{"fieldname": "destination_port", "label": _("Destination Port"), "fieldtype": "Link", "options": "UNLOCO"},
		{"fieldname": "vessel", "label": _("Vessel / Voyage"), "fieldtype": "Data", "filter_only": 1},
		{"fieldname": "etd", "label": _("ETD (Origin)"), "fieldtype": "Date"},
		{"fieldname": "eta", "label": _("ETA (Destination)"), "fieldtype": "Date"},
		{"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company"},
		{"fieldname": "branch", "label": _("Branch"), "fieldtype": "Link", "options": "Branch"},
		{"fieldname": "cost_center", "label": _("Cost Center"), "fieldtype": "Link", "options": "Cost Center"},
		{"fieldname": "profit_center", "label": _("Profit Center"), "fieldtype": "Link", "options": "Profit Center"},
	],
	"Air Booking": [
		{"fieldname": "local_customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "reqd": 1},
		{"fieldname": "service_type", "label": _("Service Type"), "fieldtype": "Data", "read_only": 1},
		{"fieldname": "airline", "label": _("Airline"), "fieldtype": "Link", "options": "Airline"},
		{"fieldname": "reference_no", "label": _("Reference No."), "fieldtype": "Data", "filter_only": 1},
		{"fieldname": "origin_port", "label": _("Origin Port"), "fieldtype": "Link", "options": "UNLOCO"},
		{"fieldname": "destination_port", "label": _("Destination Port"), "fieldtype": "Link", "options": "UNLOCO"},
		{"fieldname": "etd", "label": _("ETD (Origin)"), "fieldtype": "Date"},
		{"fieldname": "eta", "label": _("ETA (Destination)"), "fieldtype": "Date"},
		{"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company"},
		{"fieldname": "branch", "label": _("Branch"), "fieldtype": "Link", "options": "Branch"},
		{"fieldname": "cost_center", "label": _("Cost Center"), "fieldtype": "Link", "options": "Cost Center"},
		{"fieldname": "profit_center", "label": _("Profit Center"), "fieldtype": "Link", "options": "Profit Center"},
	],
	"Transport Order": [
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "reqd": 1},
		{"fieldname": "service_type", "label": _("Service Type"), "fieldtype": "Data", "read_only": 1},
		{"fieldname": "reference_no", "label": _("Reference No."), "fieldtype": "Data", "filter_only": 1},
		{"fieldname": "location_type", "label": _("Location Type"), "fieldtype": "Select", "options": "\nUNLOCO\nAddress\nEconomic Zone"},
		{"fieldname": "location_from", "label": _("Location From"), "fieldtype": "Dynamic Link", "options": "location_type"},
		{"fieldname": "location_to", "label": _("Location To"), "fieldtype": "Dynamic Link", "options": "location_type"},
		{"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company"},
		{"fieldname": "branch", "label": _("Branch"), "fieldtype": "Link", "options": "Branch"},
		{"fieldname": "cost_center", "label": _("Cost Center"), "fieldtype": "Link", "options": "Cost Center"},
		{"fieldname": "profit_center", "label": _("Profit Center"), "fieldtype": "Link", "options": "Profit Center"},
	],
	"Declaration Order": [
		{"fieldname": "customer", "label": _("Customer"), "fieldtype": "Link", "options": "Customer", "reqd": 1},
		{"fieldname": "service_type", "label": _("Service Type"), "fieldtype": "Data", "read_only": 1},
		{"fieldname": "reference_no", "label": _("Reference No."), "fieldtype": "Data", "filter_only": 1},
		{"fieldname": "customs_authority", "label": _("Customs Authority"), "fieldtype": "Link", "options": "Customs Authority"},
		{"fieldname": "declaration_type", "label": _("Declaration Type"), "fieldtype": "Select", "options": "Import\nExport\nTransit\nBonded"},
		{"fieldname": "customs_broker", "label": _("Customs Broker"), "fieldtype": "Link", "options": "Broker"},
		{"fieldname": "port_of_loading", "label": _("Port of Loading"), "fieldtype": "Link", "options": "UNLOCO"},
		{"fieldname": "port_of_discharge", "label": _("Port of Discharge"), "fieldtype": "Link", "options": "UNLOCO"},
		{"fieldname": "transport_mode", "label": _("Transport Mode"), "fieldtype": "Link", "options": "Transport Mode"},
		{"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company"},
		{"fieldname": "branch", "label": _("Branch"), "fieldtype": "Link", "options": "Branch"},
		{"fieldname": "cost_center", "label": _("Cost Center"), "fieldtype": "Link", "options": "Cost Center"},
		{"fieldname": "profit_center", "label": _("Profit Center"), "fieldtype": "Link", "options": "Profit Center"},
	],
}


def is_blanket_sales_quote(doc) -> bool:
	return cint(getattr(doc, "blanket_quotation", 0)) == 1 and (
		getattr(doc, "quotation_type", None) or ""
	).strip() == "Regular"


def _parse_json_list(value) -> list[str]:
	if not value:
		return []
	if isinstance(value, str):
		value = frappe.parse_json(value)
	if not isinstance(value, (list, tuple)):
		return []
	return [str(x).strip() for x in value if x and str(x).strip()]


def _parse_parent_fields(value) -> dict:
	if not value:
		return {}
	if isinstance(value, str):
		value = frappe.parse_json(value)
	return value if isinstance(value, dict) else {}


def _load_blanket_sales_quote(sales_quote_name: str):
	if not sales_quote_name or not frappe.db.exists("Sales Quote", sales_quote_name):
		frappe.throw(_("Sales Quote {0} not found.").format(sales_quote_name))
	sq = frappe.get_doc("Sales Quote", sales_quote_name)
	if sq.docstatus != 1:
		frappe.throw(_("Sales Quote must be submitted before creating a call-off."))
	if not is_blanket_sales_quote(sq):
		frappe.throw(_("This Sales Quote is not a submitted Blanket Quotation."))
	throw_if_sales_quote_expired_for_creation(sq)
	return sq


def _service_label_for_row(row) -> str | None:
	st = getattr(row, "service_type", None) or ""
	for label in ("Air", "Sea", "Transport", "Customs", "Warehousing"):
		if sales_quote_charge_service_types_equal(st, label):
			return label
	return (st or "").strip() or None


def _row_matches_target_service(row, target_doctype: str) -> bool:
	service = TARGET_SERVICE_LABEL.get(target_doctype)
	if not service:
		return False
	return _sq_charge_row_matches_service(row, service)


def _service_type_label(main_service: str | None) -> str:
	ms = (main_service or "").strip()
	labels = {
		"Sea": _("Sea Freight"),
		"Air": _("Air Freight"),
		"Transport": _("Transport"),
		"Customs": _("Customs"),
		"Warehousing": _("Warehousing"),
	}
	return labels.get(ms, ms or "")


def _routing_summary_for_row(row, service: str | None) -> str:
	parts = []
	if service in ("Air", "Sea"):
		origin = getattr(row, "origin_port", None)
		dest = getattr(row, "destination_port", None)
		if origin or dest:
			parts.append(f"{origin or '—'} → {dest or '—'}")
		carrier = getattr(row, "shipping_line", None) if service == "Sea" else getattr(row, "airline", None)
		if carrier:
			parts.append(str(carrier))
		load_type = getattr(row, "load_type", None)
		if load_type:
			parts.append(str(load_type))
	elif service == "Transport":
		loc_from = getattr(row, "location_from", None)
		loc_to = getattr(row, "location_to", None)
		if loc_from or loc_to:
			parts.append(f"{loc_from or '—'} → {loc_to or '—'}")
	elif service == "Customs":
		for fn in ("customs_authority", "declaration_type", "customs_broker"):
			val = getattr(row, fn, None)
			if val:
				parts.append(str(val))
	return " | ".join(parts) if parts else "—"


def _cost_side_label(row) -> str:
	charge_type = (getattr(row, "charge_type", None) or "").strip()
	if charge_type == "Revenue":
		method = getattr(row, "revenue_calculation_method", None) or getattr(row, "calculation_method", None)
		return method or charge_type or "—"
	if charge_type in ("Cost", "Disbursement"):
		method = getattr(row, "cost_calculation_method", None)
		return method or charge_type or "—"
	method = getattr(row, "revenue_calculation_method", None) or getattr(row, "cost_calculation_method", None)
	return method or charge_type or "—"


def _calculation_method_label(row) -> str:
	charge_type = (getattr(row, "charge_type", None) or "").strip()
	if charge_type in ("Cost", "Disbursement"):
		return getattr(row, "cost_calculation_method", None) or getattr(row, "cost_unit_type", None) or "—"
	return (
		getattr(row, "revenue_calculation_method", None)
		or getattr(row, "unit_type", None)
		or getattr(row, "calculation_method", None)
		or "—"
	)


def _rate_display(row) -> str:
	currency = getattr(row, "currency", None) or getattr(row, "cost_currency", None) or ""
	rate = getattr(row, "unit_rate", None)
	if rate in (None, ""):
		rate = getattr(row, "unit_cost", None)
	if rate in (None, ""):
		return "—"
	parts = [str(currency).strip()] if currency else []
	parts.append(str(rate))
	return " ".join(parts)


def _quote_meta(sq) -> dict:
	valid_until = getattr(sq, "valid_until", None)
	valid_from = getattr(sq, "date", None) or getattr(sq, "creation", None)
	if valid_from and hasattr(valid_from, "date"):
		valid_from = valid_from.date()
	return {
		"name": sq.name,
		"status": _("Submitted") if sq.docstatus == 1 else sq.status,
		"valid_from": valid_from,
		"valid_until": valid_until,
		"customer": sq.customer,
		"main_service": getattr(sq, "main_service", None),
		"service_type_label": _service_type_label(getattr(sq, "main_service", None)),
	}


def _filter_only_parent_fields(target_doctype: str) -> frozenset[str]:
	specs = PARENT_FIELD_SPECS.get(target_doctype, [])
	return frozenset(s["fieldname"] for s in specs if s.get("filter_only"))


def _strip_filter_only_parent_fields(target_doctype: str, parent_overrides: dict) -> dict:
	filter_only = _filter_only_parent_fields(target_doctype)
	if not filter_only:
		return parent_overrides
	return {k: v for k, v in (parent_overrides or {}).items() if k not in filter_only}


def _serialize_charge_row(row, target_doctype: str, main_service: str | None = None) -> dict:
	service = _service_label_for_row(row)
	matches_target = _row_matches_target_service(row, target_doctype)
	matches_main = (
		_sq_charge_row_matches_service(row, main_service) if main_service else False
	)
	summary = {
		"service_type": service or getattr(row, "service_type", None),
		"charge_group": getattr(row, "charge_group", None),
		"item_code": getattr(row, "item_code", None),
		"item_name": getattr(row, "item_name", None),
		"description": getattr(row, "description", None) or getattr(row, "item_name", None),
	}
	for fn in SUMMARY_FIELDS_BY_SERVICE.get(service or "", ()):
		summary[fn] = getattr(row, fn, None)
	detail = {fn: getattr(row, fn, None) for fn in DETAIL_FIELDS if getattr(row, fn, None) not in (None, "")}
	return {
		"name": row.name,
		"idx": row.idx,
		"selectable": True,
		"matches_target": matches_target,
		"matches_main_service": matches_main,
		"summary": summary,
		"detail": detail,
		"routing_summary": _routing_summary_for_row(row, service),
		"calculation_method": _calculation_method_label(row),
		"cost_side": _cost_side_label(row),
		"bill_to": getattr(row, "bill_to", None),
		"pay_to": getattr(row, "pay_to", None),
		"rate_display": _rate_display(row),
	}


def _parent_defaults_for_target(sq, target_doctype: str, service_label: str) -> dict:
	first = _get_service_params(sq, service_label)
	defaults = {
		"company": sq.company,
		"branch": sq.branch,
		"cost_center": sq.cost_center,
		"profit_center": sq.profit_center,
		"service_type": _service_type_label(getattr(sq, "main_service", None)),
	}
	if target_doctype in ("Sea Booking", "Air Booking"):
		defaults["local_customer"] = sq.customer
		defaults["origin_port"] = getattr(first, "origin_port", None) or sq.origin_port
		defaults["destination_port"] = getattr(first, "destination_port", None) or sq.destination_port
		if target_doctype == "Sea Booking":
			defaults["shipping_line"] = getattr(first, "shipping_line", None) or sq.shipping_line
		else:
			defaults["airline"] = getattr(first, "airline", None) or sq.airline
	elif target_doctype == "Transport Order":
		defaults["customer"] = sq.customer
		defaults["location_type"] = getattr(first, "location_type", None) or sq.location_type or "UNLOCO"
		defaults["location_from"] = (
			getattr(first, "location_from", None) or sq.location_from or sq.origin_port
		)
		defaults["location_to"] = (
			getattr(first, "location_to", None) or sq.location_to or sq.destination_port
		)
	elif target_doctype == "Declaration Order":
		defaults["customer"] = sq.customer
		defaults["customs_authority"] = getattr(first, "customs_authority", None)
		defaults["declaration_type"] = getattr(first, "declaration_type", None) or sq.direction
		defaults["customs_broker"] = getattr(first, "customs_broker", None)
		defaults["port_of_loading"] = getattr(first, "origin_port", None) or sq.origin_port
		defaults["port_of_discharge"] = getattr(first, "destination_port", None) or sq.destination_port
		defaults["transport_mode"] = getattr(first, "transport_mode", None) or sq.transport_mode
	return {k: v for k, v in defaults.items() if v not in (None, "")}


def get_blanket_call_off_targets(sales_quote_name: str) -> list[str]:
	"""Target doctypes that have at least one matching charge line on the quote."""
	sq = _load_blanket_sales_quote(sales_quote_name)
	targets = []
	for dt, svc in TARGET_SERVICE_LABEL.items():
		if any(_sq_charge_row_matches_service(c, svc) for c in (sq.charges or [])):
			targets.append(dt)
	return targets


@frappe.whitelist()
def get_blanket_call_off_target_options(sales_quote: str) -> dict:
	"""Return target doctypes available for call-off on this blanket quote."""
	targets = get_blanket_call_off_targets(sales_quote)
	return {"targets": targets}


@frappe.whitelist()
def preview_blanket_call_off(sales_quote: str, target_doctype: str) -> dict:
	target_doctype = (target_doctype or "").strip()
	if target_doctype not in BLANKET_TARGET_DOCTYPES:
		frappe.throw(_("Unsupported target document type: {0}").format(target_doctype))

	sq = _load_blanket_sales_quote(sales_quote)
	service_label = TARGET_SERVICE_LABEL[target_doctype]
	main_service = getattr(sq, "main_service", None)
	charge_rows = [
		_serialize_charge_row(row, target_doctype, main_service) for row in (sq.charges or [])
	]
	targets = get_blanket_call_off_targets(sales_quote)

	return {
		"target_doctype": target_doctype,
		"available_targets": targets,
		"quote_meta": _quote_meta(sq),
		"parent_field_specs": PARENT_FIELD_SPECS.get(target_doctype, []),
		"parent_defaults": _parent_defaults_for_target(sq, target_doctype, service_label),
		"charge_rows": charge_rows,
	}


def _validate_selected_charge_rows(sq, target_doctype: str, selected_names: list[str]) -> list:
	if not selected_names:
		frappe.throw(_("Select at least one charge line for this call-off."))
	by_name = {c.name: c for c in (sq.charges or [])}
	selected = []
	for nm in selected_names:
		row = by_name.get(nm)
		if not row:
			frappe.throw(_("Charge row {0} does not belong to this Sales Quote.").format(nm))
		selected.append(row)
	return selected


@frappe.whitelist()
def create_blanket_call_off(
	sales_quote: str,
	target_doctype: str,
	parent_fields=None,
	selected_charge_row_names=None,
) -> dict:
	target_doctype = (target_doctype or "").strip()
	if target_doctype not in BLANKET_TARGET_DOCTYPES:
		frappe.throw(_("Unsupported target document type: {0}").format(target_doctype))

	sq = _load_blanket_sales_quote(sales_quote)
	parent_overrides = _strip_filter_only_parent_fields(
		target_doctype, _parse_parent_fields(parent_fields)
	)
	selected_names = _parse_json_list(selected_charge_row_names)
	_validate_selected_charge_rows(sq, target_doctype, selected_names)

	if target_doctype == "Sea Booking":
		from logistics.pricing_center.doctype.sales_quote.sales_quote import _create_sea_booking_from_sales_quote

		result = _create_sea_booking_from_sales_quote(
			sq,
			parent_overrides=parent_overrides,
			selected_charge_row_names=selected_names,
			blanket_call_off=True,
		)
		docname = result.get("sea_booking")
	elif target_doctype == "Air Booking":
		from logistics.pricing_center.doctype.sales_quote.sales_quote import _create_air_booking_from_sales_quote

		result = _create_air_booking_from_sales_quote(
			sq,
			parent_overrides=parent_overrides,
			selected_charge_row_names=selected_names,
			blanket_call_off=True,
		)
		docname = result.get("air_booking")
	elif target_doctype == "Transport Order":
		from logistics.pricing_center.doctype.sales_quote.sales_quote import _create_transport_order_from_sales_quote

		result = _create_transport_order_from_sales_quote(
			sq,
			parent_overrides=parent_overrides,
			selected_charge_row_names=selected_names,
			blanket_call_off=True,
		)
		docname = result.get("transport_order")
	else:
		from logistics.customs.doctype.declaration_order.declaration_order import (
			create_declaration_order_from_sales_quote,
		)

		result = create_declaration_order_from_sales_quote(
			sq.name,
			customs_authority=parent_overrides.get("customs_authority"),
			declaration_type=parent_overrides.get("declaration_type"),
			parent_overrides=parent_overrides,
			selected_charge_row_names=selected_names,
			blanket_call_off=True,
		)
		docname = result.get("declaration_order")

	return {
		"success": True,
		"doctype": target_doctype,
		"name": docname,
		"message": result.get("message"),
	}
