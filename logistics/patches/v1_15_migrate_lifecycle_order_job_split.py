# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Move planning booking/order refs from job_type/job_no to order_type/order_no on Lifecycle Job."""

from __future__ import annotations

import frappe

_PLANNING_ORDER_TYPES = frozenset(
	{
		"Air Booking",
		"Sea Booking",
		"Transport Order",
		"Declaration Order",
		"Inbound Order",
		"Release Order",
		"Transfer Order",
		"Project Order",
	}
)

_EXECUTION_DOCTYPES = frozenset(
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
	if not frappe.db.has_column("Lifecycle Job", "order_type"):
		return

	rows = frappe.get_all(
		"Lifecycle Job",
		filters={"parenttype": "Special Project"},
		fields=["name", "job_type", "job_no", "order_type", "order_no", "lifecycle_job_line"],
	)
	for row in rows:
		updates: dict[str, str | None] = {}
		jt = (row.job_type or "").strip()
		jn = (row.job_no or "").strip()
		ot = (row.order_type or "").strip()
		on = (row.order_no or "").strip()

		if jt in _PLANNING_ORDER_TYPES and jn and not on:
			updates["order_type"] = jt
			updates["order_no"] = jn
			updates["job_type"] = None
			updates["job_no"] = None
		elif jt in _EXECUTION_DOCTYPES and jn and not on:
			# Already execution on job_type/job_no — leave as-is.
			pass
		elif jt in _PLANNING_ORDER_TYPES and jn and on:
			updates["job_type"] = None
			updates["job_no"] = None

		if updates:
			frappe.db.set_value("Lifecycle Job", row.name, updates, update_modified=False)
