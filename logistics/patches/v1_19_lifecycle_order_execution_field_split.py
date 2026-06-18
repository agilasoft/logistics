# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Lifecycle Job: order_type/order_no for bookings; job_type/job_no for shipments/jobs.

Charge Execution Log: drop order_type; job_type holds booking/order type; order_no links via job_type.
"""

from __future__ import annotations

import frappe

_PLANNING_ORDER_TYPES = frozenset(
	{
		"Air Booking",
		"Sea Booking",
		"Transport Order",
		"Declaration Order",
		"Inbound Order",
		"Project Order",
	}
)

_EXECUTION_JOB_TYPES = frozenset(
	{
		"Air Shipment",
		"Sea Shipment",
		"Transport Job",
		"Declaration",
		"Warehouse Job",
		"Project Job",
	}
)


def execute():
	_migrate_lifecycle_jobs()
	_migrate_charge_execution_logs()


def _migrate_lifecycle_jobs():
	if not frappe.db.table_exists("tabLifecycle Job"):
		return

	fields = ["name", "job_type", "job_no", "lifecycle_job_line"]
	if frappe.db.has_column("Lifecycle Job", "order_type"):
		fields.extend(["order_type", "order_no"])

	rows = frappe.get_all("Lifecycle Job", fields=fields)
	for row in rows:
		updates: dict[str, str | None] = {}
		jt = (row.job_type or "").strip()
		jn = (row.job_no or "").strip()
		is_execution_marker = bool((row.lifecycle_job_line or "").strip())

		if is_execution_marker:
			updates["job_type"] = ""
			updates["job_no"] = ""
		elif jt in _PLANNING_ORDER_TYPES and jn:
			updates["order_type"] = jt
			updates["order_no"] = jn
			updates["job_type"] = ""
			updates["job_no"] = ""
		elif jt in _EXECUTION_JOB_TYPES and jn:
			updates.setdefault("job_type", jt)
			updates.setdefault("job_no", jn)

		if updates:
			frappe.db.set_value("Lifecycle Job", row.name, updates, update_modified=False)


def _migrate_charge_execution_logs():
	if not frappe.db.table_exists("tabSpecial Project Charge Execution Log"):
		return
	if not frappe.db.has_column("Special Project Charge Execution Log", "order_type"):
		return

	rows = frappe.get_all(
		"Special Project Charge Execution Log",
		fields=["name", "order_type", "order_no", "job_type", "job_no"],
	)
	for row in rows:
		ot = (row.order_type or "").strip()
		on = (row.order_no or "").strip()
		jt = (row.job_type or "").strip()
		jn = (row.job_no or "").strip()
		updates: dict[str, str | None] = {}
		if ot and on:
			updates["job_type"] = ot
			updates["order_no"] = on
			if jt in _EXECUTION_JOB_TYPES:
				updates["job_no"] = jn
		elif jt in _PLANNING_ORDER_TYPES and on:
			updates["order_no"] = on
			if jn and jt not in _PLANNING_ORDER_TYPES:
				updates["job_no"] = jn
		updates["order_type"] = ""
		if updates:
			frappe.db.set_value(
				"Special Project Charge Execution Log",
				row.name,
				updates,
				update_modified=False,
			)
