# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Backfill service_role + main_service_* from legacy Internal Job fields.

Keeps ``main_job_*`` / ``is_internal_job`` populated for backend compatibility while
the desk shows only Service Role / Main Service Type / Main Service.
"""

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
	"VAS Order",
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
		for fn in (
			"service_role",
			"is_internal_job",
			"is_main_service",
			"main_job_type",
			"main_job",
			"main_service_type",
			"main_service",
			"internal_job",
		):
			if meta.has_field(fn):
				fields.append(fn)

		rows = frappe.get_all(dt, fields=fields, limit_page_length=0)
		for row in rows:
			updates = {}

			role = (row.get("service_role") or "").strip()
			if not role:
				if cint(row.get("is_internal_job")):
					role = "Linked"
				elif cint(row.get("is_main_service")):
					role = "Main"
				else:
					role = "Standalone"
				updates["service_role"] = role

			if role == "Linked" or cint(row.get("is_internal_job")):
				mt = (row.get("main_service_type") or row.get("main_job_type") or "").strip()
				mn = (row.get("main_service") or row.get("main_job") or "").strip()
				if meta.has_field("main_service_type") and not (row.get("main_service_type") or "").strip() and mt:
					updates["main_service_type"] = mt
				if meta.has_field("main_service") and not (row.get("main_service") or "").strip() and mn:
					updates["main_service"] = mn
				if meta.has_field("main_job_type") and not (row.get("main_job_type") or "").strip() and mt:
					updates["main_job_type"] = mt
				if meta.has_field("main_job") and not (row.get("main_job") or "").strip() and mn:
					updates["main_job"] = mn
				if meta.has_field("is_internal_job") and not cint(row.get("is_internal_job")):
					updates["is_internal_job"] = 1
				if meta.has_field("is_main_service") and cint(row.get("is_main_service")):
					updates["is_main_service"] = 0
				if meta.has_field("service_role") and role != "Linked":
					updates["service_role"] = "Linked"
			elif role == "Main" or cint(row.get("is_main_service")):
				if meta.has_field("is_main_service") and not cint(row.get("is_main_service")):
					updates["is_main_service"] = 1
				if meta.has_field("is_internal_job") and cint(row.get("is_internal_job")):
					updates["is_internal_job"] = 0

			if updates:
				frappe.db.set_value(dt, row.name, updates, update_modified=False)

	frappe.db.commit()
