# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Sales Quote Primary Service Type: Cross-Docking → Warehousing; add Time Sensitive option."""

from __future__ import annotations

import frappe


def execute():
	if frappe.db.exists("DocType", "Sales Quote") and frappe.db.has_column("Sales Quote", "main_service"):
		frappe.db.sql(
			"""
			UPDATE `tabSales Quote`
			SET main_service = 'Warehousing'
			WHERE main_service = 'Cross-Docking'
			"""
		)
	if frappe.db.exists("DocType", "Opportunity Service Scope") and frappe.db.has_column(
		"Opportunity Service Scope", "service_type"
	):
		frappe.db.sql(
			"""
			UPDATE `tabOpportunity Service Scope`
			SET service_type = 'Warehousing'
			WHERE service_type = 'Cross-Docking'
			"""
		)
	frappe.clear_cache(doctype="Sales Quote")
	frappe.clear_cache(doctype="Opportunity Service Scope")
	frappe.db.commit()
