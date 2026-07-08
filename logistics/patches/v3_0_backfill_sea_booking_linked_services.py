# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Backfill booking-owned Linked Service rows for Sea Bookings created before the virtual grid."""

from __future__ import annotations

import frappe

from logistics.utils.linked_service_compat import linked_service_doctype


def execute():
	if not frappe.db.exists("DocType", "Sea Booking"):
		return
	if not frappe.db.exists("DocType", linked_service_doctype()):
		return

	from logistics.pricing_center.doctype.sales_quote.sales_quote import (
		_propagate_linked_services_to_created_booking,
	)

	ls_dt = linked_service_doctype()
	bookings = frappe.get_all(
		"Sea Booking",
		filters={"sales_quote": ["is", "set"], "docstatus": ["<", 2]},
		fields=["name", "sales_quote"],
		limit_page_length=0,
	)
	for row in bookings:
		bk_name = (row.get("name") or "").strip()
		sq_name = (row.get("sales_quote") or "").strip()
		if not bk_name or not sq_name or not frappe.db.exists("Sales Quote", sq_name):
			continue
		if frappe.db.exists(
			ls_dt,
			{"parent_booking_type": "Sea Booking", "parent_booking_name": bk_name},
		):
			continue
		sq_owned = frappe.get_all(
			ls_dt,
			filters={
				"parent_booking_type": "Sales Quote",
				"parent_booking_name": sq_name,
			},
			pluck="name",
			limit_page_length=0,
		)
		if not sq_owned:
			continue
		try:
			sq = frappe.get_doc("Sales Quote", sq_name)
			bk = frappe.get_doc("Sea Booking", bk_name)
			_propagate_linked_services_to_created_booking(sq, bk, blanket_call_off=False)
		except Exception:
			frappe.log_error(
				title=f"Backfill linked services failed for Sea Booking {bk_name}",
				message=frappe.get_traceback(),
			)
	frappe.db.commit()
