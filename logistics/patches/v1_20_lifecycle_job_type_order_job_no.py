# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Lifecycle Job: job_type/order_no for bookings; job_no stores shipment/job name only."""

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
	if not frappe.db.table_exists("tabLifecycle Job"):
		return

	fields = ["name", "job_type", "job_no", "order_no", "lifecycle_job_line"]
	if frappe.db.has_column("Lifecycle Job", "order_type"):
		fields.append("order_type")

	rows = frappe.get_all("Lifecycle Job", fields=fields)
	for row in rows:
		updates: dict[str, str | None] = {}
		jt = (row.job_type or "").strip()
		jn = (row.job_no or "").strip()
		on = (row.order_no or "").strip()
		ot = (getattr(row, "order_type", None) or "").strip()
		is_execution_marker = bool((row.lifecycle_job_line or "").strip())

		if is_execution_marker:
			updates["job_type"] = ""
			updates["job_no"] = ""
			updates["order_no"] = ""
		elif jt in _EXECUTION_JOB_TYPES and jn:
			updates["job_no"] = jn
			updates["job_type"] = ""
		elif ot and on and not jt:
			updates["job_type"] = ot
			updates["order_no"] = on
			updates["job_no"] = jn if jn and jt in _EXECUTION_JOB_TYPES else jn
		elif jt in _PLANNING_ORDER_TYPES and jn and not on:
			updates["order_no"] = jn
			updates["job_no"] = ""
		elif ot and on:
			updates["job_type"] = ot
			updates["order_no"] = on

		if frappe.db.has_column("Lifecycle Job", "order_type"):
			updates["order_type"] = ""

		if updates:
			frappe.db.set_value("Lifecycle Job", row.name, updates, update_modified=False)
