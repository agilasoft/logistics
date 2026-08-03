# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

"""Migrate legacy Time Sensitive service legs to canonical Linked Services."""

import frappe

from logistics.time_sensitive.service_linking import (
	CANONICAL_SERVICE_TYPES,
	record_case_usage,
	record_operational_usage,
)


def execute():
	# Table may remain after DocType delete; prefer SQL so Meta is not required.
	if not frappe.db.table_exists("Time Sensitive Case Service Leg"):
		return

	columns = {
		row[0]
		for row in frappe.db.sql("DESC `tabTime Sensitive Case Service Leg`")
	}
	fields = [
		field
		for field in (
			"parent",
			"service_type",
			"linked_service",
			"linked_doctype",
			"linked_name",
			"idx",
		)
		if field in columns
	]
	if "parent" not in fields or "service_type" not in fields:
		return

	select_cols = ", ".join(f"`{f}`" for f in fields)
	order_by = "`parent` asc, `idx` asc" if "idx" in fields else "`parent` asc"
	rows = frappe.db.sql(
		f"SELECT {select_cols} FROM `tabTime Sensitive Case Service Leg` ORDER BY {order_by}",
		as_dict=True,
	)
	for row in rows:
		if not row.parent or not frappe.db.exists("Time Sensitive Case", row.parent):
			continue
		if row.service_type not in CANONICAL_SERVICE_TYPES:
			frappe.log_error(
				f"Skipped legacy service type {row.service_type} on {row.parent}",
				"Time Sensitive service leg migration",
			)
			continue

		case = frappe._dict(
			doctype="Time Sensitive Case",
			name=row.parent,
			sales_quote=frappe.db.get_value(
				"Time Sensitive Case", row.parent, "sales_quote"
			),
		)
		linked_service = row.get("linked_service")
		if not linked_service or not frappe.db.exists("Linked Service", linked_service):
			linked = frappe.get_doc(
				{
					"doctype": "Linked Service",
					"service_type": row.service_type,
					"parent_booking_type": case.doctype,
					"parent_booking_name": case.name,
				}
			)
			linked.insert(ignore_permissions=True)
			linked_service = linked.name
			record_case_usage(case, linked_service)
		else:
			record_case_usage(case, linked_service)

		if row.get("linked_doctype") and row.get("linked_name"):
			if frappe.db.exists(row.linked_doctype, row.linked_name):
				record_operational_usage(
					case,
					linked_service,
					row.linked_doctype,
					row.linked_name,
				)

