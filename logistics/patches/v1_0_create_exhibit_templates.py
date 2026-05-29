# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Seed Exhibits milestone/document templates and default Exhibit Settings."""

from __future__ import annotations

import frappe

EXHIBIT_MILESTONES = [
	"Asset Retrieved",
	"Staging Complete",
	"Refurbishment Complete",
	"Freight Booked",
	"In Transit",
	"Delivered to Venue",
	"Installation Complete",
	"QC Passed",
	"Event Documentation Complete",
	"Dismantle Complete",
	"Return Shipped",
	"Returned to Storage",
]


def execute():
	_ensure_exhibit_settings()
	_ensure_milestone_template()
	_ensure_document_template()


def _ensure_exhibit_settings():
	if frappe.db.exists("Exhibit Settings", "Exhibit Settings"):
		return
	doc = frappe.new_doc("Exhibit Settings")
	doc.name = "Exhibit Settings"
	doc.strict_lifecycle_mode = 1
	doc.auto_create_phase_orders = 1
	doc.insert(ignore_permissions=True)


def _ensure_milestone_template():
	name = "Exhibits Standard Lifecycle"
	if frappe.db.exists("Milestone Template", name):
		frappe.db.set_single_value("Exhibit Settings", "default_milestone_template", name)
		return
	if not frappe.db.exists("DocType", "Milestone Template"):
		return
	try:
		tpl = frappe.new_doc("Milestone Template")
		tpl.template_name = name
		tpl.product_type = "Exhibits"
		tpl.applies_to = "Shipment/Job"
		if hasattr(tpl, "is_active"):
			tpl.is_active = 1
		child_field = "milestones" if tpl.meta.get_field("milestones") else None
		if child_field:
			for idx, label in enumerate(EXHIBIT_MILESTONES, start=1):
				row = {"milestone": _get_or_create_logistics_milestone(label)}
				if tpl.meta.get_field("milestones", "fields", {"fieldname": "sequence"}):
					row["sequence"] = idx
				tpl.append(child_field, row)
		tpl.insert(ignore_permissions=True)
		frappe.db.set_single_value("Exhibit Settings", "default_milestone_template", tpl.name)
	except Exception:
		frappe.log_error(title="Exhibits: milestone template seed skipped")


def _ensure_document_template():
	name = "Exhibits Standard Documents"
	if frappe.db.exists("Document List Template", name):
		frappe.db.set_single_value("Exhibit Settings", "default_document_template", name)
		return
	if not frappe.db.exists("DocType", "Document List Template"):
		return
	try:
		tpl = frappe.new_doc("Document List Template")
		tpl.template_name = name
		tpl.product_type = "Exhibits"
		tpl.applies_to = "Shipment/Job"
		if hasattr(tpl, "is_active"):
			tpl.is_active = 1
		if tpl.meta.get_field("documents"):
			for label in ("Booth Photos", "QC Checklist", "Delivery Receipt", "Return Receipt"):
				doc_type = _get_or_create_logistics_document_type(label)
				tpl.append("documents", {"document_type": doc_type, "is_mandatory": 0})
		tpl.insert(ignore_permissions=True)
		frappe.db.set_single_value("Exhibit Settings", "default_document_template", tpl.name)
	except Exception:
		frappe.log_error(title="Exhibits: document template seed skipped")


def _get_or_create_logistics_document_type(label):
	if not label or not frappe.db.exists("DocType", "Logistics Document Type"):
		return label
	existing = frappe.db.get_value("Logistics Document Type", {"document_name": label})
	if existing:
		return existing
	code = frappe.scrub(label).upper().replace("-", "_")[:140]
	if frappe.db.exists("Logistics Document Type", code):
		return code
	row = frappe.new_doc("Logistics Document Type")
	row.document_code = code
	row.document_name = label
	row.insert(ignore_permissions=True)
	return row.name


def _get_or_create_logistics_milestone(label):
	if frappe.db.exists("Logistics Milestone", label):
		return label
	if not frappe.db.exists("DocType", "Logistics Milestone"):
		return label
	m = frappe.new_doc("Logistics Milestone")
	m.milestone_name = label
	m.is_active = 1
	m.insert(ignore_permissions=True)
	return m.name
