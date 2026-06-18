# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Charge Execution Log: job_type must be a planning order type for order_no Dynamic Link."""

from __future__ import annotations

import frappe

from logistics.special_projects.special_project_charge_execution import (
	_normalize_one_charge_execution_log_link,
)


def execute():
	if not frappe.db.table_exists("tabSpecial Project Charge Execution Log"):
		return

	rows = frappe.get_all(
		"Special Project Charge Execution Log",
		fields=["name", "job_type", "order_no", "job_no"],
	)
	for row in rows:
		log = frappe._dict(row)
		_normalize_one_charge_execution_log_link(log)
		updates = {
			"job_type": (log.job_type or "").strip() or "",
			"order_no": (log.order_no or "").strip() or "",
		}
		if updates["job_type"] != (row.job_type or "").strip() or updates[
			"order_no"
		] != (row.order_no or "").strip():
			frappe.db.set_value(
				"Special Project Charge Execution Log",
				row.name,
				updates,
				update_modified=False,
			)

	frappe.db.commit()
