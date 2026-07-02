# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Rename Opportunity Service Scope ``main_service`` to ``service_type`` (desk grid Select fix)."""

from __future__ import unicode_literals

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	if not frappe.db.exists("DocType", "Opportunity Service Scope"):
		return
	meta = frappe.get_meta("Opportunity Service Scope")
	if meta.has_field("main_service") and not meta.has_field("service_type"):
		rename_field("Opportunity Service Scope", "main_service", "service_type")
	elif frappe.db.has_column("Opportunity Service Scope", "main_service"):
		frappe.db.sql(
			"""
			UPDATE `tabOpportunity Service Scope`
			SET service_type = main_service
			WHERE (service_type IS NULL OR service_type = '')
			  AND main_service IS NOT NULL AND main_service != ''
			"""
		)
		frappe.db.sql_ddl(
			"ALTER TABLE `tabOpportunity Service Scope` DROP COLUMN `main_service`"
		)
	frappe.clear_cache(doctype="Opportunity Service Scope")
	frappe.db.commit()
