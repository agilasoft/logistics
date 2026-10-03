# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Backfill Permit Application tags from the customer applicant and declaration job.

Supplier applicants stay on the applicant field. A declaration with no Job Number
keeps the declaration link and does not get a shipment tag.
"""

import frappe


_TARGET_FLAGS = (
	"applies_to_importer",
	"applies_to_exporter",
	"applies_to_freight_agent",
	"applies_to_customer",
	"applies_to_company",
	"applies_to_commodity",
	"applies_to_shipment",
)


def execute():
	if not frappe.db.table_exists("Permit Application Tag"):
		return
	if not frappe.db.table_exists("Permit Type"):
		return
	_default_shipment_target()
	_backfill_application_tags()


def _default_shipment_target():
	"""Existing types were shipment-oriented. Give them a target so the next save validates."""
	zero = " and ".join(f"ifnull(`{field}`, 0) = 0" for field in _TARGET_FLAGS)
	frappe.db.sql(
		f"""
		update `tabPermit Type`
		set applies_to_shipment = 1
		where {zero}
		"""
	)


def _backfill_application_tags():
	applications = frappe.get_all(
		"Permit Application",
		fields=["name", "applicant_type", "applicant", "declaration", "permit_type"],
		limit=10000,
	)
	for application in applications:
		if application.applicant_type == "Customer" and application.applicant:
			if frappe.db.exists("Customer", application.applicant):
				_ensure_tag(application.name, "Customer", application.applicant)
				if application.permit_type and frappe.db.exists("Permit Type", application.permit_type):
					frappe.db.set_value(
						"Permit Type",
						application.permit_type,
						"applies_to_customer",
						1,
						update_modified=False,
					)
		if not application.declaration or not frappe.db.exists("Declaration", application.declaration):
			continue
		job_number = frappe.db.get_value("Declaration", application.declaration, "job_number")
		if not job_number or not frappe.db.exists("Job Number", job_number):
			continue
		_ensure_tag(application.name, "Job Number", job_number)
		if application.permit_type and frappe.db.exists("Permit Type", application.permit_type):
			frappe.db.set_value(
				"Permit Type",
				application.permit_type,
				"applies_to_shipment",
				1,
				update_modified=False,
			)


def _ensure_tag(parent, entity_type, entity_name):
	if frappe.db.exists(
		"Permit Application Tag",
		{"parent": parent, "entity_type": entity_type, "entity_name": entity_name},
	):
		return
	idx = frappe.db.count("Permit Application Tag", {"parent": parent}) + 1
	row = frappe.new_doc("Permit Application Tag")
	row.parent = parent
	row.parenttype = "Permit Application"
	row.parentfield = "tags"
	row.idx = idx
	row.entity_type = entity_type
	row.entity_name = entity_name
	row.db_insert()
