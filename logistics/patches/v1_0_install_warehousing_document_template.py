# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Add Warehousing Order document template (for sites that ran v1_0_install_document_types before this was added)."""

from __future__ import unicode_literals

import frappe


def execute():
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
		frappe.db.commit()
