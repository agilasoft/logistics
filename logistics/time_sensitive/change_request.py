# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Create Change Request from a Time Sensitive Case (targets the main-service job)."""

from __future__ import annotations

from typing import Optional

import frappe
from frappe import _
from frappe.utils import cint

from logistics.pricing_center.additional_charge_to_job import MAIN_JOB_TYPES_FOR_CHANGE_REQUEST
from logistics.time_sensitive.propagation import _meta_has
from logistics.time_sensitive.service_linking import get_case_linked_services
from logistics.utils.linked_service_usage import get_usages_for_linked_service


SERVICE_TYPE_TO_MAIN_JOB = {
	"Transport": "Transport Job",
	"Air": "Air Shipment",
	"Sea": "Sea Shipment",
	"Customs": "Declaration",
	"Warehousing": "Warehouse Job",
}

COMPLETED_STATUS_BY_JOB = {
	"Transport Job": frozenset({"Completed"}),
	"Warehouse Job": frozenset({"Completed", "Closed"}),
	"Air Shipment": frozenset({"Completed", "Closed", "Delivered"}),
	"Sea Shipment": frozenset({"Completed", "Closed", "Delivered"}),
	"Declaration": frozenset({"Completed", "Submitted", "Closed"}),
	"Special Project": frozenset({"Completed", "Closed"}),
	"Docket": frozenset({"Completed", "Closed"}),
}


def _is_completed_main_job(doctype: str, name: str) -> bool:
	if not doctype or not name:
		return False
	if _meta_has(doctype, "status"):
		try:
			status = (frappe.db.get_value(doctype, name, "status") or "").strip()
		except Exception:
			status = ""
		allowed = COMPLETED_STATUS_BY_JOB.get(doctype)
		if allowed:
			if status in allowed:
				return True
		elif status in ("Completed", "Closed", "Delivered"):
			return True
	if _meta_has(doctype, "docstatus"):
		try:
			return cint(frappe.db.get_value(doctype, name, "docstatus")) == 1
		except Exception:
			return False
	return False


def _preferred_job_doctypes(case) -> list[str]:
	out: list[str] = []
	mst = (getattr(case, "main_service_type", None) or "").strip()
	if mst in MAIN_JOB_TYPES_FOR_CHANGE_REQUEST:
		out.append(mst)
	for linked in get_case_linked_services(case) or []:
		st = getattr(linked, "service_type", None) or (linked.get("service_type") if isinstance(linked, dict) else None)
		job_dt = SERVICE_TYPE_TO_MAIN_JOB.get((st or "").strip())
		if job_dt and job_dt not in out:
			out.append(job_dt)
	return out


def collect_case_main_jobs(case) -> list[tuple[str, str]]:
	"""Main-job (doctype, name) pairs attached to the case via Linked Service usage."""
	seen: set[tuple[str, str]] = set()
	jobs: list[tuple[str, str]] = []
	for linked in get_case_linked_services(case) or []:
		ls_name = getattr(linked, "name", None) or (linked.get("name") if isinstance(linked, dict) else None)
		if not ls_name:
			continue
		for usage in get_usages_for_linked_service(ls_name) or []:
			dt = (usage.get("used_on_doctype") or "").strip()
			nm = (usage.get("used_on_name") or "").strip()
			if not dt or not nm or dt == "Time Sensitive Case":
				continue
			if dt not in MAIN_JOB_TYPES_FOR_CHANGE_REQUEST:
				continue
			key = (dt, nm)
			if key in seen:
				continue
			seen.add(key)
			jobs.append(key)
	return jobs


def resolve_main_job_for_case(case) -> tuple[str, str]:
	"""Return (job_type, job_name) for Create Change Request. Requires a completed main job."""
	explicit_type = (getattr(case, "main_service_type", None) or "").strip()
	explicit_name = (getattr(case, "main_service", None) or "").strip()
	if explicit_type in MAIN_JOB_TYPES_FOR_CHANGE_REQUEST and explicit_name:
		if frappe.db.exists(explicit_type, explicit_name) and _is_completed_main_job(
			explicit_type, explicit_name
		):
			return explicit_type, explicit_name

	jobs = collect_case_main_jobs(case)
	preferred = _preferred_job_doctypes(case)

	def sort_key(item: tuple[str, str]) -> tuple[int, str, str]:
		dt, nm = item
		rank = preferred.index(dt) if dt in preferred else 99
		return (rank, dt, nm)

	completed = [j for j in jobs if _is_completed_main_job(j[0], j[1])]
	completed.sort(key=sort_key)
	if completed:
		return completed[0]
	frappe.throw(
		_(
			"Create and complete the main job for this Time Sensitive Case before creating a Change Request."
		),
		title=_("Main job required"),
	)


def attach_case_linked_services_to_change_request(cr_name: str, case) -> None:
	from logistics.utils.linked_service_usage import record_usages_for_linked_services

	names = []
	for linked in get_case_linked_services(case) or []:
		name = getattr(linked, "name", None) or (linked.get("name") if isinstance(linked, dict) else None)
		if name:
			names.append(name)
	if not names or not cr_name:
		return
	record_usages_for_linked_services(
		names,
		"Change Request",
		cr_name,
		sales_quote=getattr(case, "sales_quote", None),
	)


def create_change_request_from_case(
	case_name: str,
	reason: Optional[str] = None,
	reuse_draft: int | None = None,
) -> str:
	"""Create a Change Request targeting the case's completed main-service job."""
	if not case_name or not frappe.db.exists("Time Sensitive Case", case_name):
		frappe.throw(_("Time Sensitive Case {0} not found.").format(case_name or ""))
	case = frappe.get_doc("Time Sensitive Case", case_name)
	frappe.has_permission("Time Sensitive Case", "write", doc=case, throw=True)
	job_type, job_name = resolve_main_job_for_case(case)
	from logistics.pricing_center.doctype.change_request.change_request import create_change_request

	cr_name = create_change_request(
		job_type,
		job_name,
		reason=reason,
		reuse_draft=reuse_draft,
	)
	attach_case_linked_services_to_change_request(cr_name, case)
	return cr_name
