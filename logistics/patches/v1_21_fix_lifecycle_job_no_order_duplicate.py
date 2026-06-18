# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Lifecycle Job: replace job_no when it duplicates order_no with the linked shipment/job."""

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
	if not frappe.db.has_column("Lifecycle Job", "order_no"):
		return

	from logistics.special_projects.special_project_charge_lifecycle import (
		sync_lifecycle_job_execution_no,
	)

	rows = frappe.get_all(
		"Lifecycle Job",
		filters={"parenttype": "Special Project"},
		fields=["name", "parent", "job_type", "order_no", "job_no", "lifecycle_job_line"],
	)
	parents: set[str] = set()
	for row in rows:
		if (row.lifecycle_job_line or "").strip():
			continue
		jt = (row.job_type or "").strip()
		on = (row.order_no or "").strip()
		jn = (row.job_no or "").strip()
		if not jt or jt not in _PLANNING_ORDER_TYPES or not on:
			continue
		if not jn or jn == on or frappe.db.exists(jt, jn):
			row_doc = frappe.get_doc("Lifecycle Job", row.name)
			sync_lifecycle_job_execution_no(row_doc)
			frappe.db.set_value(
				"Lifecycle Job",
				row.name,
				{"job_no": (row_doc.job_no or "").strip() or ""},
				update_modified=False,
			)
			if row.parent:
				parents.add(row.parent)

	for parent in parents:
		try:
			sp = frappe.get_doc("Special Project", parent)
		except Exception:
			continue
		from logistics.special_projects.lifecycle_job_financial_rollup import (
			sync_lifecycle_job_financials,
		)

		sync_lifecycle_job_financials(sp)
