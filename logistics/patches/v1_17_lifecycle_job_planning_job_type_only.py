# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Lifecycle Job: planning order types only on job_type; clear legacy execution labels."""

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

_LEGACY_EXECUTION_JOB_TYPES = frozenset(
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

	fields = ["name", "job_type", "job_no", "lifecycle_job_line"]
	if frappe.db.has_column("Lifecycle Job", "order_type"):
		fields.extend(["order_type", "order_no"])

	rows = frappe.get_all("Lifecycle Job", fields=fields)
	for row in rows:
		updates: dict[str, str | None] = {}
		jt = (row.job_type or "").strip()
		jn = (row.job_no or "").strip()
		is_execution = bool((row.lifecycle_job_line or "").strip())

		if frappe.db.has_column("Lifecycle Job", "order_type"):
			ot = (row.order_type or "").strip()
			on = (row.order_no or "").strip()
			if ot and on and not jn and not is_execution:
				updates["job_type"] = ot
				updates["job_no"] = on
				jt, jn = ot, on
			updates["order_type"] = ""
			updates["order_no"] = ""

		if is_execution or jt in _LEGACY_EXECUTION_JOB_TYPES or (
			jt and jt not in _PLANNING_ORDER_TYPES
		):
			updates["job_type"] = ""
			updates["job_no"] = ""
		elif jt in _PLANNING_ORDER_TYPES:
			updates.setdefault("job_type", jt)
			if jn:
				updates.setdefault("job_no", jn)

		if updates:
			frappe.db.set_value("Lifecycle Job", row.name, updates, update_modified=False)
