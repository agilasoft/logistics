# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Move booking/order ids from Internal Job Detail.job_no → order_no.

Convention: ``order_no`` = booking/order; ``job_no`` = job/shipment (execution) only.
Linked Service Detail is virtual (Usage-backed); no row table migrate needed.
"""

from __future__ import annotations

import frappe

_ORDER_TYPES = (
	"Air Booking",
	"Sea Booking",
	"Transport Order",
	"Declaration Order",
	"VAS Order",
	"Inbound Order",
	"Release Order",
	"Transfer Order",
	"Cross-Docking Order",
	"Project Order",
	"MICE Order",
)


def execute():
	if not frappe.db.has_table("tabInternal Job Detail"):
		return
	if not frappe.db.has_column("tabInternal Job Detail", "order_no"):
		# Schema sync may run after this patch; re-run safely after migrate.
		return
	placeholders = ", ".join(["%s"] * len(_ORDER_TYPES))
	frappe.db.sql(
		f"""
		UPDATE `tabInternal Job Detail`
		SET order_no = job_no, job_no = NULL
		WHERE IFNULL(job_no, '') != ''
			AND IFNULL(order_no, '') = ''
			AND job_type IN ({placeholders})
		""",
		_ORDER_TYPES,
	)
