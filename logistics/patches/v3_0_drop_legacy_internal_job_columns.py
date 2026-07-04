# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Drop legacy Internal Job columns from operational headers after service_role cutover."""

from __future__ import unicode_literals

import frappe

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
	"Warehouse Contract",
)

_LEGACY_COLUMNS = (
	"is_internal_job",
	"is_main_service",
	"main_job_type",
	"main_job",
	"internal_job",
)


def execute():
	for dt in _OPERATIONAL_DT:
		table = f"tab{dt}"
		if not frappe.db.table_exists(table):
			continue
		for col in _LEGACY_COLUMNS:
			# Prefer live information_schema — frappe.db.has_column can be stale mid-migrate.
			exists = frappe.db.sql(
				"""
				SELECT 1 FROM information_schema.COLUMNS
				WHERE TABLE_SCHEMA = DATABASE()
				  AND TABLE_NAME = %s
				  AND COLUMN_NAME = %s
				LIMIT 1
				""",
				(table, col),
			)
			if not exists:
				continue
			frappe.db.sql(f"ALTER TABLE `{table}` DROP COLUMN `{col}`")
	frappe.db.commit()
