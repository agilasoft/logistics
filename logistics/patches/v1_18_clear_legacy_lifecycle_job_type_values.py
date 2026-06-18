# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Clear legacy execution doctype labels left on Lifecycle Job.job_type after v1_17."""

from __future__ import annotations

import frappe

_PLANNING_ORDER_TYPES = (
	"Air Booking",
	"Sea Booking",
	"Transport Order",
	"Declaration Order",
	"Inbound Order",
	"Project Order",
)


def execute():
	if not frappe.db.table_exists("tabLifecycle Job"):
		return

	frappe.db.sql(
		"""
		UPDATE `tabLifecycle Job`
		SET job_type = '', job_no = ''
		WHERE IFNULL(job_type, '') != ''
		  AND job_type NOT IN %(allowed)s
		""",
		{"allowed": _PLANNING_ORDER_TYPES},
	)
