# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Create / import Time Sensitive Cases and operational service documents."""

from __future__ import annotations

from typing import Optional

import frappe
from frappe import _
from frappe.utils import add_to_date, now_datetime


SERVICE_TYPE_DEFAULT_DOCTYPE = {
	"Air": "Air Booking",
	"Sea": "Sea Booking",
	"Transport": "Transport Order",
	"Customs": "Declaration Order",
	"Warehousing": "VAS Order",
	"Cross-Docking": "Cross-Docking Order",
	"On-Demand Last Mile": "ODDS Order",
}


def build_case_from_sales_quote(
	sq,
	*,
	case_type: Optional[str] = None,
	critical_deadline: Optional[str] = None,
):
	"""Build (unsaved) Time Sensitive Case from Sales Quote + Linked Services."""
	if not case_type:
		case_type = frappe.db.get_value(
			"Time Sensitive Case Type", {"enabled": 1, "code": "OTHER"}, "name"
		) or frappe.db.get_value("Time Sensitive Case Type", {"enabled": 1}, "name")
	if not case_type:
		frappe.throw(_("Seed Time Sensitive Case Types before creating a case."))

	deadline = critical_deadline or getattr(sq, "critical_deadline", None)
	if not deadline:
		deadline = add_to_date(now_datetime(), hours=24)

	case = frappe.new_doc("Time Sensitive Case")
	case.case_title = _("Urgent: {0}").format(sq.name)
	case.case_type = case_type
	case.customer = getattr(sq, "customer", None)
	case.sales_quote = sq.name
	case.critical_deadline = deadline
	case.status = "Triage"
	case.severity = "Urgent"
	case.priority = getattr(sq, "priority", None) or "Urgent"
	case.company = getattr(sq, "company", None)
	case.branch = getattr(sq, "branch", None)
	case.cost_center = getattr(sq, "cost_center", None)
	case.profit_center = getattr(sq, "profit_center", None)
	case.origin = getattr(sq, "origin_port", None)
	case.destination = getattr(sq, "destination_port", None)
	case.coordinator = frappe.session.user

	main_service = getattr(sq, "main_service", None)
	pending_service_types = []

	# Import Linked Service docs owned by this quote
	linked = frappe.get_all(
		"Linked Service",
		filters={
			"parent_booking_type": "Sales Quote",
			"parent_booking_name": sq.name,
		},
		fields=["name", "service_type"],
		ignore_permissions=True,
	)

	pending_linked_services = []
	linked_types = set()
	for row in linked or []:
		st = row.get("service_type")
		if not st or st not in SERVICE_TYPE_DEFAULT_DOCTYPE:
			continue
		linked_types.add(st)
		pending_linked_services.append(row.get("name"))
	if main_service in SERVICE_TYPE_DEFAULT_DOCTYPE and main_service not in linked_types:
		pending_service_types.append(main_service)

	# Pull charge service types as soft hints when the quote has no service records.
	if not pending_linked_services and not pending_service_types and hasattr(sq, "charges"):
		seen = set()
		for ch in sq.get("charges") or []:
			st = getattr(ch, "service_type", None)
			if st in SERVICE_TYPE_DEFAULT_DOCTYPE and st not in seen:
				seen.add(st)
				pending_service_types.append(st)

	case.flags.pending_linked_services = pending_linked_services
	case.flags.pending_service_types = pending_service_types
	return case


def _scope_row_for_ts_service(sq, service_type: str, case) -> frappe._dict:
	"""Build a parameter scope row from the linked Sales Quote for one service leg."""
	from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal
	from logistics.utils.sales_quote_charge_parameters import (
		SALES_QUOTE_CHARGE_PARAMETER_FIELDS,
		build_main_service_scope_row,
	)

	st = (service_type or "").strip()
	row = build_main_service_scope_row(sq)
	if st:
		row.service_type = st

	for ch in sq.get("charges") or []:
		ch_st = getattr(ch, "service_type", None)
		if not sales_quote_charge_service_types_equal(ch_st, st):
			continue
		for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS:
			if fn == "charge_group":
				continue
			val = getattr(ch, fn, None)
			if val is not None and str(val).strip() != "":
				row[fn] = val
		break

	if getattr(case, "origin", None) and not (row.get("origin_port") or row.get("location_from")):
		row.origin_port = case.origin
	if getattr(case, "destination", None) and not (
		row.get("destination_port") or row.get("location_to")
	):
		row.destination_port = case.destination
	return row


def _populate_ts_operational_charges(sq, doc) -> None:
	from logistics.pricing_center.sales_quote_booking_creation import _populate_charges_on_target

	_populate_charges_on_target(sq, doc)


def _apply_ts_service_scope(doc, case, sq, linked, scope_row) -> None:
	from logistics.utils.internal_job_from_source import apply_internal_job_detail_row_to_operational_doc
	from logistics.utils.party_address_contact_from_masters import (
		apply_party_address_contact_from_source_or_masters,
	)
	from logistics.utils.shipper_consignee_defaults import apply_shipper_consignee_defaults

	apply_internal_job_detail_row_to_operational_doc(doc, scope_row, overwrite=True)

	if doc.doctype in ("Air Booking", "Sea Booking"):
		from logistics.special_projects.special_project_booking_creation import (
			_apply_air_sea_corridor_ports_from_context,
			_apply_air_sea_settings_defaults_before_insert,
			_booking_date_field,
			_validate_air_sea_corridor_ports_before_insert,
		)
		from frappe.utils import today

		sp_ctx = frappe._dict(sales_quote=sq.name)
		bd = _booking_date_field(doc)
		if bd and not getattr(doc, bd, None):
			doc.set(bd, today())
		_apply_air_sea_corridor_ports_from_context(doc, sp_ctx, scope_row)
		apply_party_address_contact_from_source_or_masters(doc, sq)
		apply_shipper_consignee_defaults(doc)
		_apply_air_sea_settings_defaults_before_insert(doc)
		_validate_air_sea_corridor_ports_before_insert(doc)
	elif doc.doctype == "Transport Order":
		from frappe.utils import today

		if hasattr(doc, "booking_date") and not doc.booking_date:
			doc.booking_date = today()
		if hasattr(doc, "scheduled_date") and not doc.scheduled_date:
			doc.scheduled_date = today()
	elif doc.doctype == "Declaration Order":
		from frappe.utils import today

		if hasattr(doc, "order_date") and not doc.order_date:
			doc.order_date = today()

	if hasattr(doc, "linked_service"):
		doc.linked_service = linked.name


def create_operational_doc_for_service(case, linked_service: str) -> dict:
	"""Create a draft operational document for a canonical Linked Service."""
	from logistics.time_sensitive.service_linking import record_operational_usage

	linked = frappe.get_doc("Linked Service", linked_service)
	doctype = SERVICE_TYPE_DEFAULT_DOCTYPE.get(linked.service_type)
	if not doctype:
		frappe.throw(_("No default document for service type {0}").format(linked.service_type))
	if not frappe.db.exists("DocType", doctype):
		frappe.throw(_("DocType {0} is not installed").format(doctype))

	doc = frappe.new_doc(doctype)
	_apply_common_headers(doc, case)

	# DocType-specific minimal fields
	if doctype in ("Air Booking", "Sea Booking"):
		if hasattr(doc, "local_customer") and case.customer:
			doc.local_customer = case.customer
		elif hasattr(doc, "customer") and case.customer:
			doc.customer = case.customer
	elif doctype == "Transport Order":
		if hasattr(doc, "customer") and case.customer:
			doc.customer = case.customer
	elif doctype == "Declaration Order":
		if hasattr(doc, "customer") and case.customer:
			doc.customer = case.customer
	elif doctype in ("VAS Order", "Cross-Docking Order", "Inbound Order", "Release Order"):
		if hasattr(doc, "customer") and case.customer:
			doc.customer = case.customer

	if hasattr(doc, "is_time_sensitive"):
		doc.is_time_sensitive = 1
	if hasattr(doc, "time_sensitive_case"):
		doc.time_sensitive_case = case.name
	if hasattr(doc, "ts_case_type"):
		doc.ts_case_type = case.case_type
	if hasattr(doc, "critical_deadline"):
		doc.critical_deadline = case.critical_deadline

	sq_name = getattr(case, "sales_quote", None)
	if sq_name and frappe.db.exists("Sales Quote", sq_name):
		sq = frappe.get_doc("Sales Quote", sq_name)
		scope_row = _scope_row_for_ts_service(sq, linked.service_type, case)
		_apply_ts_service_scope(doc, case, sq, linked, scope_row)
		_populate_ts_operational_charges(sq, doc)
		if doc.doctype == "Air Booking" and hasattr(doc, "_normalize_charges_before_save"):
			doc._normalize_charges_before_save()
		elif doc.doctype == "Sea Booking" and hasattr(doc, "_normalize_charges_before_save"):
			doc._normalize_charges_before_save()

	doc.insert(ignore_permissions=False)
	record_operational_usage(case, linked.name, doctype, doc.name)
	return {
		"doctype": doctype,
		"name": doc.name,
		"linked_service": linked.name,
	}


def _apply_common_headers(doc, case):
	for fn in ("sales_quote", "company", "branch", "cost_center", "profit_center", "customer"):
		if hasattr(doc, fn) and getattr(case, fn, None):
			setattr(doc, fn, getattr(case, fn))
	if hasattr(doc, "customer") and case.customer and not doc.customer:
		doc.customer = case.customer
