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
