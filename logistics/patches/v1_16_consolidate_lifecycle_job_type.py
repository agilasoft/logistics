# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Move planning refs from order_type/order_no back to job_type/job_no on Lifecycle Job."""

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
		if (row.lifecycle_job_line or "").strip():
			continue
		updates: dict[str, str | None] = {}
		ot = (row.order_type or "").strip()
		on = (row.order_no or "").strip()
		jt = (row.job_type or "").strip()
		jn = (row.job_no or "").strip()
		if ot and on and not jn:
			updates["job_type"] = ot
			updates["job_no"] = on
		elif ot and on and jt in _PLANNING_ORDER_TYPES and jn:
			pass
		elif ot and on and jt and jt not in _PLANNING_ORDER_TYPES:
			pass
		if updates:
			frappe.db.set_value("Lifecycle Job", row.name, updates, update_modified=False)
