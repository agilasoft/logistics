# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Canonical Linked Service integration for Time Sensitive Cases."""

from __future__ import annotations

import frappe
from frappe import _
from logistics.utils.linked_service_usage import (
	USAGE_ROLE_PARENT_BOOKING,
	USAGE_ROLE_SATELLITE_JOB,
	record_linked_service_usage,
)


CANONICAL_SERVICE_TYPES = frozenset(
	{
		"Air",
		"Sea",
		"Transport",
		"Customs",
		"Warehousing",
		"Cross-Docking",
		"On-Demand Last Mile",
		"Special Project",
		"MICE",
	}
)


def validate_linked_service_type(service_type: str) -> str:
	value = (service_type or "").strip()
	if value not in CANONICAL_SERVICE_TYPES:
		frappe.throw(
			_("{0} is not a standard Linked Service type.").format(value or _("Service Type")),
			title=_("Linked Service"),
		)
	return value


def create_linked_service_for_case(case, service_type: str):
	"""Create a canonical service owned by the case."""
	service_type = validate_linked_service_type(service_type)
	if not case.name or case.is_new():
		frappe.throw(_("Save the Time Sensitive Case before adding a linked service."))

	linked = frappe.new_doc("Linked Service")
	linked.service_type = service_type
	linked.parent_booking_type = case.doctype
	linked.parent_booking_name = case.name
	linked.insert()
	record_case_usage(case, linked.name)
	return linked


def record_case_usage(case, linked_service: str) -> None:
	"""Register the case as a consumer without changing Linked Service ownership."""
	record_linked_service_usage(
		linked_service,
		case.doctype,
		case.name,
		usage_role=USAGE_ROLE_PARENT_BOOKING,
		sales_quote=getattr(case, "sales_quote", None),
	)


def record_operational_usage(
	case,
	linked_service: str,
	linked_doctype: str,
	linked_name: str,
) -> None:
	"""Register the operational booking/order/job as the service's satellite."""
	record_case_usage(case, linked_service)
	record_linked_service_usage(
		linked_service,
		linked_doctype,
		linked_name,
		usage_role=USAGE_ROLE_SATELLITE_JOB,
		sales_quote=getattr(case, "sales_quote", None),
	)


def get_case_linked_services(case):
	"""Return canonical services owned by or shared with this case."""
	from logistics.logistics.doctype.linked_service.linked_service import (
		get_linked_services_for_booking,
	)

	return get_linked_services_for_booking(case.doctype, case.name)

