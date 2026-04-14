# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Create Permit Application / Exemption Certificate from Declaration and link child rows."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cstr, nowdate, random_string, today


def _declaration_summary(doc: Document) -> dict:
	return {
		"declaration": doc.name,
		"customer": getattr(doc, "customer", None),
		"importer_consignee": getattr(doc, "importer_consignee", None),
		"exporter_shipper": getattr(doc, "exporter_shipper", None),
		"company": getattr(doc, "company", None),
		"branch": getattr(doc, "branch", None),
		"customs_authority": getattr(doc, "customs_authority", None),
		"declaration_type": getattr(doc, "declaration_type", None),
		"declaration_date": str(getattr(doc, "declaration_date", None) or ""),
	}


def get_permit_application_create_context(doc: Document) -> dict:
	rows_out = []
	for row in doc.get("permit_requirements") or []:
		rows_out.append(
			{
				"name": row.name,
				"idx": row.idx,
				"planned_permit_type": getattr(row, "planned_permit_type", None),
				"permit_application": getattr(row, "permit_application", None) or None,
			}
		)
	default_type = None
	for r in rows_out:
		if not r.get("permit_application"):
			default_type = r.get("planned_permit_type")
			break
	return {"summary": _declaration_summary(doc), "permit_rows": rows_out, "default_permit_type": default_type}


def create_linked_permit_application(
	doc: Document, permit_type: str, child_row_name: str | None = None
) -> dict:
	if not permit_type:
		frappe.throw(_("Permit Type is required."), title=_("Permit Application"))

	doc.check_permission("write")

	pa = frappe.new_doc("Permit Application")
	pa.permit_type = permit_type
	pa.status = "Draft"
	pa.application_date = today()
	pa.declaration = doc.name
	pa.company = doc.company
	pa.branch = getattr(doc, "branch", None)
	if getattr(doc, "customs_authority", None):
		pa.issuing_authority = doc.customs_authority
	if getattr(doc, "customer", None):
		pa.applicant_type = "Customer"
		pa.applicant = doc.customer
	else:
		frappe.throw(_("Declaration must have a Customer to create a Permit Application."), title=_("Missing Customer"))

	pa.insert()

	decl = frappe.get_doc("Declaration", doc.name)
	target_row = None
	if child_row_name:
		for row in decl.get("permit_requirements") or []:
			if row.name == child_row_name:
				target_row = row
				break
	if not target_row:
		for row in decl.get("permit_requirements") or []:
			if not getattr(row, "permit_application", None):
				if not getattr(row, "planned_permit_type", None) or row.planned_permit_type == permit_type:
					target_row = row
					break
	if not target_row:
		target_row = decl.append("permit_requirements", {})
	target_row.permit_application = pa.name
	if hasattr(target_row, "planned_permit_type"):
		target_row.planned_permit_type = permit_type
	if getattr(target_row, "is_required", None) is None:
		target_row.is_required = 1
	decl.save()

	return {"permit_application": pa.name, "child_row_name": target_row.name}


def get_exemption_certificate_create_context(doc: Document) -> dict:
	rows_out = []
	for row in doc.get("exemptions") or []:
		rows_out.append(
			{
				"name": row.name,
				"idx": row.idx,
				"planned_exemption_type": getattr(row, "planned_exemption_type", None),
				"exemption_certificate": getattr(row, "exemption_certificate", None) or None,
			}
		)
	default_type = None
	for r in rows_out:
		if not r.get("exemption_certificate"):
			default_type = r.get("planned_exemption_type")
			break
	suggested = _suggest_certificate_number(doc.name)
	return {
		"summary": _declaration_summary(doc),
		"exemption_rows": rows_out,
		"default_exemption_type": default_type,
		"suggested_certificate_number": suggested,
	}


def _suggest_certificate_number(declaration_name: str) -> str:
	base = cstr(declaration_name).replace(" ", "")[:24]
	for _ in range(8):
		cand = f"{base}-EX-{random_string(4).upper()}"
		if not frappe.db.exists("Exemption Certificate", cand):
			return cand
	return f"{base}-EX-{random_string(8).upper()}"


def create_linked_exemption_certificate(
	doc: Document, exemption_type: str, certificate_number: str, child_row_name: str | None = None
) -> dict:
	if not exemption_type:
		frappe.throw(_("Exemption Type is required."), title=_("Exemption Certificate"))
	certificate_number = cstr(certificate_number).strip()
	if not certificate_number:
		frappe.throw(_("Certificate Number is required."), title=_("Exemption Certificate"))
	if frappe.db.exists("Exemption Certificate", certificate_number):
		frappe.throw(
			_("Exemption Certificate {0} already exists.").format(certificate_number),
			title=_("Duplicate Certificate Number"),
		)

	doc.check_permission("write")

	# Exemption Certificate issued_to only supports Customer/Supplier (not Consignee).
	if not getattr(doc, "customer", None):
		frappe.throw(
			_("Declaration must have a Customer (certificate is issued to Customer)."),
			title=_("Missing Customer"),
		)

	cert = frappe.new_doc("Exemption Certificate")
	cert.certificate_number = certificate_number
	cert.exemption_type = exemption_type
	cert.status = "Active"
	cert.issue_date = nowdate()
	cert.issued_to_type = "Customer"
	cert.issued_to = doc.customer
	cert.company = doc.company
	if getattr(doc, "customs_authority", None):
		cert.issued_by = doc.customs_authority
	cert.append("declarations", {"declaration": doc.name})
	cert.insert()

	decl = frappe.get_doc("Declaration", doc.name)
	target_row = None
	if child_row_name:
		for row in decl.get("exemptions") or []:
			if row.name == child_row_name:
				target_row = row
				break
	if not target_row:
		for row in decl.get("exemptions") or []:
			if not getattr(row, "exemption_certificate", None):
				if not getattr(row, "planned_exemption_type", None) or row.planned_exemption_type == exemption_type:
					target_row = row
					break
	if not target_row:
		target_row = decl.append("exemptions", {})
	target_row.exemption_certificate = cert.name
	if hasattr(target_row, "planned_exemption_type"):
		target_row.planned_exemption_type = exemption_type
	decl.save()

	return {"exemption_certificate": cert.name, "child_row_name": target_row.name}
