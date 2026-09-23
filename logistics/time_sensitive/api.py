# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Whitelisted APIs for Time Sensitive module."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import add_to_date, now_datetime

from logistics.time_sensitive.doctype.time_sensitive_case.time_sensitive_case import (
	_infer_service_type,
)
from logistics.time_sensitive.propagation import stamp_document_from_case


@frappe.whitelist()
def create_case_from_document(
	doctype: str,
	docname: str,
	case_type: str,
	critical_deadline: str | None = None,
):
	"""Create a Time Sensitive Case linked to an operational document."""
	src = frappe.get_doc(doctype, docname)
	frappe.has_permission(doctype, "write", doc=src, throw=True)
	from logistics.utils.menu_permission import assert_perm

	assert_perm("Time Sensitive Case", "create")

	deadline = critical_deadline or getattr(src, "critical_deadline", None)
	if not deadline:
		deadline = add_to_date(now_datetime(), hours=24)

	case = frappe.new_doc("Time Sensitive Case")
	case.case_title = _("Urgent: {0} {1}").format(doctype, docname)
	case.case_type = case_type
	case.customer = getattr(src, "customer", None) or getattr(src, "local_customer", None)
	case.sales_quote = getattr(src, "sales_quote", None)
	case.critical_deadline = deadline
	case.status = "Triage"
	case.severity = "Urgent"
	case.coordinator = frappe.session.user
	case.company = getattr(src, "company", None)
	case.branch = getattr(src, "branch", None)
	case.insert()
	from logistics.time_sensitive.service_linking import (
		create_linked_service_for_case,
		record_operational_usage,
	)

	linked = create_linked_service_for_case(case, _infer_service_type(doctype))
	record_operational_usage(case, linked.name, doctype, docname)
	stamp_document_from_case(doctype, docname, case)
	return {"name": case.name, "linked_service": linked.name}


@frappe.whitelist()
def get_timer_payload(doctype: str | None = None, name: str | None = None):
	"""Return deadline + at-risk hours for client timer sync. Always includes server_now."""
	payload = {
		"critical_deadline": None,
		"is_time_sensitive": 0,
		"time_sensitive_case": None,
		"sla_status": None,
		"at_risk_hours": 4,
		"server_now": now_datetime(),
	}
	if not doctype or not name or doctype == "User":
		return payload
	if not frappe.db.exists(doctype, name):
		return payload
	meta = frappe.get_meta(doctype)
	fields = ["name"]
	for fn in ("critical_deadline", "is_time_sensitive", "time_sensitive_case", "sla_status", "at_risk_hours"):
		if meta.get_field(fn):
			fields.append(fn)
	row = frappe.db.get_value(doctype, name, fields, as_dict=True) or {}
	at_risk = row.get("at_risk_hours") or 4
	if row.get("time_sensitive_case"):
		case_hours = frappe.db.get_value(
			"Time Sensitive Case", row.time_sensitive_case, "at_risk_hours"
		)
		if case_hours:
			at_risk = case_hours
	payload.update(
		{
			"critical_deadline": row.get("critical_deadline"),
			"is_time_sensitive": row.get("is_time_sensitive"),
			"time_sensitive_case": row.get("time_sensitive_case"),
			"sla_status": row.get("sla_status"),
			"at_risk_hours": at_risk,
		}
	)
	return payload
