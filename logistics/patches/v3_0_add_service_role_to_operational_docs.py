# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Backfill service_role and service_scope on operational headers from legacy MS/IJ flags."""

from __future__ import unicode_literals

import frappe
from frappe.utils import cint

_OPERATIONAL_DT = (
	"Air Booking",
	"Air Shipment",
	"Sea Booking",
	"Sea Shipment",
	"Transport Order",
	"Transport Job",
	"Declaration",
	"Declaration Order",
	"Warehouse Job",
	"Inbound Order",
	"Release Order",
	"Project Job",
	"MICE Job",
	"Exhibit Job",
)


def execute():
	for dt in _OPERATIONAL_DT:
		if not frappe.db.table_exists(f"tab{dt}"):
			continue
		meta = frappe.get_meta(dt)
		if not meta.has_field("service_role"):
			continue
		fields = ["name"]
		if meta.has_field("is_internal_job"):
			fields.append("is_internal_job")
		if meta.has_field("is_main_service"):
			fields.append("is_main_service")
		if meta.has_field("sales_quote"):
			fields.append("sales_quote")
		rows = frappe.get_all(dt, fields=fields, limit_page_length=0)
		for row in rows:
			updates = {}
			if not frappe.db.get_value(dt, row.name, "service_role"):
				if cint(row.get("is_internal_job")):
					updates["service_role"] = "Linked"
				elif cint(row.get("is_main_service")):
					updates["service_role"] = "Main"
				else:
					updates["service_role"] = "Standalone"
			sq = (row.get("sales_quote") or "").strip()
			if sq and meta.has_field("service_scope") and not frappe.db.get_value(dt, row.name, "service_scope"):
				updates["service_scope"] = sq
			if updates:
				frappe.db.set_value(dt, row.name, updates, update_modified=False)
	frappe.db.commit()
