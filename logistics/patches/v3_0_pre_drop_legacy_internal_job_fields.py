# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Pre-model-sync: backfill service_role / main_service_* / linked_service before legacy columns drop.

Runs before DocType sync removes ``is_internal_job``, ``is_main_service``, ``main_job_type``,
``main_job``, and ``internal_job`` from operational headers.
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


def _table(dt: str) -> str:
	return f"tab{dt}"


def _has_column(dt: str, column: str) -> bool:
	return frappe.db.has_column(_table(dt), column)


def _ensure_column(dt: str, column: str, definition: str) -> None:
	if _has_column(dt, column):
		return
	frappe.db.sql_ddl(f"ALTER TABLE `{_table(dt)}` ADD COLUMN `{column}` {definition}")


def execute():
	for dt in _OPERATIONAL_DT:
		if not frappe.db.table_exists(_table(dt)):
			continue

		# Ensure target columns exist before we copy and before model sync drops sources.
		_ensure_column(dt, "service_role", "varchar(140)")
		_ensure_column(dt, "main_service_type", "varchar(140)")
		_ensure_column(dt, "main_service", "varchar(140)")
		_ensure_column(dt, "linked_service", "varchar(140)")

		# service_role from legacy flags
		if _has_column(dt, "is_internal_job"):
			frappe.db.sql(
				f"""
				UPDATE `{_table(dt)}`
				SET service_role = 'Linked'
				WHERE IFNULL(service_role, '') = ''
				  AND IFNULL(is_internal_job, 0) = 1
				"""
			)
		if _has_column(dt, "is_main_service"):
			frappe.db.sql(
				f"""
				UPDATE `{_table(dt)}`
				SET service_role = 'Main'
				WHERE IFNULL(service_role, '') = ''
				  AND IFNULL(is_main_service, 0) = 1
				"""
			)
		frappe.db.sql(
			f"""
			UPDATE `{_table(dt)}`
			SET service_role = 'Standalone'
			WHERE IFNULL(service_role, '') = ''
			"""
		)

		# main_service_* from main_job_*
		if _has_column(dt, "main_job_type"):
			frappe.db.sql(
				f"""
				UPDATE `{_table(dt)}`
				SET main_service_type = main_job_type
				WHERE IFNULL(main_service_type, '') = ''
				  AND IFNULL(main_job_type, '') != ''
				"""
			)
		if _has_column(dt, "main_job"):
			frappe.db.sql(
				f"""
				UPDATE `{_table(dt)}`
				SET main_service = main_job
				WHERE IFNULL(main_service, '') = ''
				  AND IFNULL(main_job, '') != ''
				"""
			)

		# Any row with main refs is Linked
		frappe.db.sql(
			f"""
			UPDATE `{_table(dt)}`
			SET service_role = 'Linked'
			WHERE IFNULL(main_service, '') != ''
			  AND IFNULL(main_service_type, '') != ''
			"""
		)

		# linked_service from internal_job
		if _has_column(dt, "internal_job"):
			frappe.db.sql(
				f"""
				UPDATE `{_table(dt)}`
				SET linked_service = internal_job
				WHERE IFNULL(linked_service, '') = ''
				  AND IFNULL(internal_job, '') != ''
				"""
			)

	frappe.db.commit()
