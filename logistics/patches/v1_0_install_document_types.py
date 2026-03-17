# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Install default Document Type records and sample Document List Templates."""

from __future__ import unicode_literals

import frappe


def execute():
	install_document_types()
	install_document_list_templates()


def install_document_types():
	"""Create standard Document Type records if they don't exist."""
	types = [
		{"document_code": "CI", "document_name": "Commercial Invoice", "category": "Trade"},
		{"document_code": "PL", "document_name": "Packing List", "category": "Trade"},
		{"document_code": "BL", "document_name": "Bill of Lading", "category": "Transport"},
		{"document_code": "AWB", "document_name": "Air Waybill", "category": "Transport"},
		{"document_code": "COO", "document_name": "Certificate of Origin", "category": "Trade"},
		{"document_code": "EXL", "document_name": "Export License", "category": "Customs"},
		{"document_code": "IML", "document_name": "Import License", "category": "Customs"},
		{"document_code": "IMP", "document_name": "Import Permit", "category": "Customs"},
		{"document_code": "INS", "document_name": "Insurance Certificate", "category": "Insurance"},
		{"document_code": "PHY", "document_name": "Phytosanitary Certificate", "category": "Other"},
		{"document_code": "FUM", "document_name": "Fumigation Certificate", "category": "Other"},
		{"document_code": "DGD", "document_name": "Dangerous Goods Declaration", "category": "Dangerous Goods"},
		{"document_code": "DO", "document_name": "Delivery Order", "category": "Transport"},
		{"document_code": "POD", "document_name": "Proof of Delivery", "category": "Transport"},
		{"document_code": "OTH", "document_name": "Other", "category": "Other"},
	]

	for dt in types:
		if not frappe.db.exists("Logistics Document Type", dt["document_code"]):
			frappe.get_doc({
				"doctype": "Logistics Document Type",
				**dt,
			}).insert(ignore_permissions=True)

	frappe.db.commit()


def install_document_list_templates():
	"""Create sample Document List Templates for Air and Sea."""
	# Air Export - Booking
	if not frappe.db.exists("Document List Template", "Air Export Standard"):
		template = frappe.get_doc({
			"doctype": "Document List Template",
			"template_name": "Air Export Standard",
			"product_type": "Air Freight",
			"applies_to": "Both",
			"direction": "Export",
			"is_default": 1,
			"description": "Standard documents for air export shipments",
			"documents": [
				{"document_type": "CI", "sequence": 1, "is_mandatory": 1, "date_required_basis": "ETD", "days_offset": -3},
				{"document_type": "PL", "sequence": 2, "is_mandatory": 1, "date_required_basis": "ETD", "days_offset": -3},
				{"document_type": "COO", "sequence": 3, "is_mandatory": 0, "date_required_basis": "ETD", "days_offset": -2},
				{"document_type": "AWB", "sequence": 4, "is_mandatory": 1, "date_required_basis": "ETD", "days_offset": 0},
			],
		})
		template.insert(ignore_permissions=True)

	# Sea Import - Shipment/Job
	if not frappe.db.exists("Document List Template", "Sea Import Standard"):
		template = frappe.get_doc({
			"doctype": "Document List Template",
			"template_name": "Sea Import Standard",
			"product_type": "Sea Freight",
			"applies_to": "Both",
			"direction": "Import",
			"is_default": 1,
			"description": "Standard documents for sea import shipments",
			"documents": [
				{"document_type": "BL", "sequence": 1, "is_mandatory": 1, "date_required_basis": "ETA", "days_offset": -1},
				{"document_type": "CI", "sequence": 2, "is_mandatory": 1, "date_required_basis": "ETA", "days_offset": -2},
				{"document_type": "PL", "sequence": 3, "is_mandatory": 1, "date_required_basis": "ETA", "days_offset": -2},
				{"document_type": "IMP", "sequence": 4, "is_mandatory": 0, "date_required_basis": "ETA", "days_offset": -5},
			],
		})
		template.insert(ignore_permissions=True)

	# Transport - Job
	if not frappe.db.exists("Document List Template", "Transport Job Standard"):
		template = frappe.get_doc({
			"doctype": "Document List Template",
			"template_name": "Transport Job Standard",
			"product_type": "Transport",
			"applies_to": "Shipment/Job",
			"is_default": 1,
			"description": "Standard documents for transport jobs",
			"documents": [
				{"document_type": "DO", "sequence": 1, "is_mandatory": 1, "date_required_basis": "Job Date", "days_offset": 0},
				{"document_type": "POD", "sequence": 2, "is_mandatory": 1, "date_required_basis": "Job Date", "days_offset": 1},
			],
		})
		template.insert(ignore_permissions=True)

	# Warehousing - Inbound/Release/Transfer Order
	if not frappe.db.exists("Document List Template", "Warehousing Order Standard"):
		template = frappe.get_doc({
			"doctype": "Document List Template",
			"template_name": "Warehousing Order Standard",
			"product_type": "Warehousing",
			"applies_to": "Booking",
			"is_default": 1,
			"description": "Standard documents for warehousing orders (Inbound, Release, Transfer)",
			"documents": [
				{"document_type": "CI", "sequence": 1, "is_mandatory": 0, "date_required_basis": "Booking Date", "days_offset": 0},
				{"document_type": "PL", "sequence": 2, "is_mandatory": 0, "date_required_basis": "Booking Date", "days_offset": 0},
				{"document_type": "DO", "sequence": 3, "is_mandatory": 1, "date_required_basis": "Booking Date", "days_offset": 0},
				{"document_type": "POD", "sequence": 4, "is_mandatory": 0, "date_required_basis": "Booking Date", "days_offset": 1},
			],
		})
		template.insert(ignore_permissions=True)

	# Customs Declaration Order
	if not frappe.db.exists("Document List Template", "Customs Declaration Order Standard"):
		template = frappe.get_doc({
			"doctype": "Document List Template",
			"template_name": "Customs Declaration Order Standard",
			"product_type": "Customs",
			"applies_to": "Booking",
			"is_default": 1,
			"description": "Standard documents for customs declaration orders",
			"documents": [
				{"document_type": "CI", "sequence": 1, "is_mandatory": 1, "date_required_basis": "Booking Date", "days_offset": 0},
				{"document_type": "PL", "sequence": 2, "is_mandatory": 1, "date_required_basis": "Booking Date", "days_offset": 0},
				{"document_type": "BL", "sequence": 3, "is_mandatory": 0, "date_required_basis": "Booking Date", "days_offset": 0},
				{"document_type": "AWB", "sequence": 4, "is_mandatory": 0, "date_required_basis": "Booking Date", "days_offset": 0},
				{"document_type": "COO", "sequence": 5, "is_mandatory": 0, "date_required_basis": "Booking Date", "days_offset": 0},
			],
		})
		template.insert(ignore_permissions=True)

	frappe.db.commit()
