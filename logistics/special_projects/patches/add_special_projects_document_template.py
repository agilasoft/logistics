# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Add Special Projects document template for project-level document tracking."""

from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.exists("Document List Template", "Special Projects Standard"):
		template = frappe.get_doc({
			"doctype": "Document List Template",
			"template_name": "Special Projects Standard",
			"product_type": "Special Projects",
			"applies_to": "Shipment/Job",
			"is_default": 1,
			"description": "Standard documents for special projects (contracts, permits, DG certs)",
			"documents": [
				{"document_type": "CI", "sequence": 1, "is_mandatory": 0, "date_required_basis": "Job Date", "days_offset": 0},
				{"document_type": "PL", "sequence": 2, "is_mandatory": 0, "date_required_basis": "Job Date", "days_offset": 0},
				{"document_type": "DO", "sequence": 3, "is_mandatory": 0, "date_required_basis": "Job Date", "days_offset": 0},
				{"document_type": "POD", "sequence": 4, "is_mandatory": 0, "date_required_basis": "Job Date", "days_offset": 1},
			],
		})
		template.insert(ignore_permissions=True)
		frappe.db.commit()
