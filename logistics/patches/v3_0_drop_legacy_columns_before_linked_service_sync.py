# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Pre-model-sync: drop legacy Internal Job header columns before adding ``linked_service``.

Sites that already ran ``v3_0_pre_drop_legacy_internal_job_fields`` before ``linked_service``
was added can hit MySQL error 1118 during DocType sync. Drop backfilled legacy columns first,
then rename ``internal_job`` or add ``linked_service``.
"""

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
)


def _table(dt: str) -> str:
	return f"tab{dt}"


def _column_exists(table: str, column: str) -> bool:
	return bool(
		frappe.db.sql(
			"""
			SELECT 1 FROM information_schema.COLUMNS
			WHERE TABLE_SCHEMA = DATABASE()
			  AND TABLE_NAME = %s
			  AND COLUMN_NAME = %s
			LIMIT 1
			""",
			(table, column),
		)
	)


def _drop_column(table: str, column: str) -> None:
	frappe.db.sql(f"ALTER TABLE `{table}` DROP COLUMN `{column}`")


def execute():
	for dt in _OPERATIONAL_DT:
		table = _table(dt)
		if not frappe.db.table_exists(table):
			continue
		if _column_exists(table, "linked_service"):
			continue
		if not _column_exists(table, "service_role"):
			continue

		for col in _LEGACY_COLUMNS:
			if _column_exists(table, col):
				_drop_column(table, col)

		if _column_exists(table, "internal_job"):
			frappe.db.sql_ddl(
				f"ALTER TABLE `{table}` CHANGE COLUMN `internal_job` `linked_service` varchar(140)"
			)
		elif not _column_exists(table, "linked_service"):
			frappe.db.sql_ddl(
				f"ALTER TABLE `{table}` ADD COLUMN `linked_service` varchar(140)"
			)

	frappe.db.commit()
