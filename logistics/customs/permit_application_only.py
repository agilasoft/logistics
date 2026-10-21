# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Open the permit-application-only job when Declaration Type is Application."""

from __future__ import annotations

import frappe
from frappe.utils import today

from logistics.customs.declaration_types import (
	PERMIT_APPLICATION_ONLY_TASKS,
	PERMIT_APPLICATION_ONLY_TEMPLATE,
	PERMIT_APPLICATION_ONLY_TYPE_CODE,
	PERMIT_APPLICATION_ONLY_TYPE_NAME,
	is_permit_application_only,
)

_PERMIT_CHILD_DOCTYPE = "Permit Requirement"


def permit_application_only_template(doc):
	"""Job-task template for an Application declaration, or None to use the normal checklist.

	An explicit Job Task Template on the document still wins.
	"""
	if not doc or getattr(doc, "doctype", None) != "Declaration":
		return None
	if (getattr(doc, "job_task_template", None) or "").strip():
		return None
	if not is_permit_application_only(getattr(doc, "declaration_type", None)):
		return None
	return PERMIT_APPLICATION_ONLY_TEMPLATE, [dict(task) for task in PERMIT_APPLICATION_ONLY_TASKS]


def ensure_permit_application_only_type() -> str:
	"""Return the Permit Type used when an Application declaration has no planned type."""
	code = PERMIT_APPLICATION_ONLY_TYPE_CODE
	if frappe.db.exists("Permit Type", code):
		return code
	doc = frappe.get_doc(
		{
			"doctype": "Permit Type",
			"permit_code": code,
			"permit_name": PERMIT_APPLICATION_ONLY_TYPE_NAME,
			"applicable_to": "All",
			"is_active": 1,
			"applies_to_importer": 1,
			"applies_to_exporter": 1,
			"applies_to_customer": 1,
			"description": (
				"Default permit for Declaration Type Application. "
				"The job is the permit application only."
			),
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def ensure_permit_application_only_job(doc):
	"""Create and link one Permit Application for an Application declaration.

	Shipper and Consignee are optional. A declaration without a customer cannot
	open the application yet; the next save after a customer is set will.
	"""
	if not doc or getattr(doc, "doctype", None) != "Declaration":
		return None
	if not is_permit_application_only(getattr(doc, "declaration_type", None)):
		return None
	if getattr(getattr(doc, "flags", None), "in_permit_application_only", False):
		return None
	if (
		getattr(frappe.flags, "in_import", False)
		or getattr(frappe.flags, "in_migrate", False)
		or getattr(frappe.flags, "in_patch", False)
	):
		return None
	name = (getattr(doc, "name", None) or "").strip()
	if not name or name.startswith("new-"):
		return None
	customer = (getattr(doc, "customer", None) or "").strip()
	if not customer:
		return None

	linked = _permit_on_doc(doc)
	if linked:
		return linked

	existing = frappe.db.get_value("Permit Application", {"declaration": name}, "name")
	doc.flags.in_permit_application_only = True
	try:
		permit_type = _planned_permit_type(doc) or ensure_permit_application_only_type()
		if existing:
			_link_permit_row(doc, existing, permit_type)
			return existing
		permit_name = _insert_permit_application(doc, permit_type)
		_link_permit_row(doc, permit_name, permit_type)
		return permit_name
	finally:
		doc.flags.in_permit_application_only = False


def _permit_on_doc(doc) -> str | None:
	for row in doc.get("permit_requirements") or []:
		linked = (getattr(row, "permit_application", None) or "").strip()
		if linked:
			return linked
	return None


def _planned_permit_type(doc) -> str | None:
	for row in doc.get("permit_requirements") or []:
		if (getattr(row, "permit_application", None) or "").strip():
			continue
		planned = (getattr(row, "planned_permit_type", None) or "").strip()
		if planned:
			return planned
	return None


def _insert_permit_application(doc, permit_type: str) -> str:
	from logistics.customs.declaration_permit_exemption_create import (
		_issuing_authority_name_from_customs_authority,
	)
	from logistics.customs.permit_matching import append_source_tags

	permit = frappe.new_doc("Permit Application")
	permit.permit_type = permit_type
	permit.status = "Draft"
	permit.application_date = today()
	permit.declaration = doc.name
	permit.company = getattr(doc, "company", None)
	permit.branch = getattr(doc, "branch", None)
	permit.applicant_type = "Customer"
	permit.applicant = doc.customer
	if getattr(doc, "customs_authority", None):
		permit.issuing_authority = _issuing_authority_name_from_customs_authority(doc.customs_authority)
	append_source_tags(permit, doc)
	permit.insert(ignore_permissions=True)
	return permit.name


def _persisted_child_name(row) -> str:
	name = (getattr(row, "name", None) or "").strip()
	if name and not name.startswith("new-"):
		return name
	return ""


def _insert_requirement_row(row) -> None:
	"""Insert one requirement row. Name it first so the child primary key is set."""
	if not _persisted_child_name(row):
		setter = getattr(row, "set_new_name", None)
		if callable(setter):
			setter(force=True)
	if not getattr(row, "parenttype", None):
		row.parenttype = "Declaration"
	if not getattr(row, "parentfield", None):
		row.parentfield = "permit_requirements"
	row.db_insert()


def _link_permit_row(doc, permit_name: str, permit_type: str) -> None:
	"""Attach the application on the declaration without a second full save."""
	for row in doc.get("permit_requirements") or []:
		if (getattr(row, "permit_application", None) or "").strip() == permit_name:
			return
		if not (getattr(row, "permit_application", None) or "").strip():
			row.permit_application = permit_name
			if not (getattr(row, "planned_permit_type", None) or "").strip():
				row.planned_permit_type = permit_type
			row.is_required = 1
			persisted = _persisted_child_name(row)
			if persisted:
				frappe.db.set_value(
					_PERMIT_CHILD_DOCTYPE,
					persisted,
					{
						"permit_application": permit_name,
						"planned_permit_type": row.planned_permit_type,
						"is_required": 1,
					},
					update_modified=False,
				)
			else:
				_insert_requirement_row(row)
			return

	already = frappe.db.get_value(
		_PERMIT_CHILD_DOCTYPE,
		{
			"parent": doc.name,
			"parenttype": "Declaration",
			"parentfield": "permit_requirements",
			"permit_application": permit_name,
		},
		"name",
	)
	if already:
		return

	row = doc.append(
		"permit_requirements",
		{
			"planned_permit_type": permit_type,
			"permit_application": permit_name,
			"is_required": 1,
		},
	)
	_insert_requirement_row(row)
