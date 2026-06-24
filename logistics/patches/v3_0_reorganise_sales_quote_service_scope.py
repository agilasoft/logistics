# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Rename Sales Quote linked-services child field; stamp service_scope on charge/Services rows."""

from __future__ import unicode_literals

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	_rename_sq_child_field()
	_stamp_service_scope_on_sales_quote_children()
	frappe.db.commit()


def _rename_sq_child_field():
	if not frappe.db.exists("DocType", "Sales Quote"):
		return
	meta = frappe.get_meta("Sales Quote")
	if meta.has_field("internal_job_details") and not meta.has_field("linked_services"):
		rename_field("Sales Quote", "internal_job_details", "linked_services")
		frappe.clear_cache(doctype="Sales Quote")


def _stamp_service_scope_on_sales_quote_children():
	if not frappe.db.table_exists("tabSales Quote"):
		return
	quotes = frappe.get_all("Sales Quote", pluck="name", limit_page_length=0)
	detail_dt = "Linked Service Detail"
	if not frappe.db.table_exists(f"tab{detail_dt}"):
		detail_dt = "Internal Job Detail"
	for sq in quotes:
		if frappe.db.table_exists("tabSales Quote Charge"):
			frappe.db.sql(
				"""
				UPDATE `tabSales Quote Charge`
				SET service_scope = %s
				WHERE parent = %s AND parenttype = 'Sales Quote'
				  AND (service_scope IS NULL OR service_scope = '')
				""",
				(sq, sq),
			)
		if frappe.db.table_exists(f"tab{detail_dt}"):
			frappe.db.sql(
				f"""
				UPDATE `tab{detail_dt}`
				SET service_scope = %s
				WHERE parent = %s AND parenttype = 'Sales Quote'
				  AND (service_scope IS NULL OR service_scope = '')
				""",
				(sq, sq),
			)
