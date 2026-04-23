# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Map Sales Quote multimodal routing legs onto Sea / Air Booking routing child tables."""

from __future__ import annotations

import frappe
from frappe.model.document import Document

from logistics.utils.transport_mode_flags import get_air_sea_flags_for_transport_mode


def get_booking_routing_rows_from_sales_quote(
	sales_quote_doc: Document,
	booking_doc: Document | None = None,
) -> list[dict]:
	"""
	Build row dicts for Sea Booking Routing Leg / Air Booking Routing Leg from Sales Quote Routing Leg.

	Sales Quote uses origin/destination (UNLOCO); booking legs use load_port/discharge_port.
	Optional booking_doc enriches Sea legs with shipping_line and Air legs with airline when mode matches.
	"""
	rows: list[dict] = []
	for leg in getattr(sales_quote_doc, "routing_legs", None) or []:
		# Align with Sales Quote Routing Leg default (Road) when missing
		mode = getattr(leg, "mode", None) or "Road"
		air_flag, sea_flag = get_air_sea_flags_for_transport_mode(mode)
		row = {
			"mode": mode,
			"type": getattr(leg, "type", None) or "Main",
			"status": getattr(leg, "status", None) or "Planned",
			"charter_route": 0,
			"notes": getattr(leg, "notes", None),
			"load_port": getattr(leg, "origin", None),
			"discharge_port": getattr(leg, "destination", None),
			"etd": getattr(leg, "etd", None),
			"eta": getattr(leg, "eta", None),
			"transport_mode_air": air_flag,
			"transport_mode_sea": sea_flag,
		}
		if booking_doc and getattr(booking_doc, "doctype", None) == "Sea Booking":
			if sea_flag and getattr(booking_doc, "shipping_line", None):
				row["shipping_line"] = booking_doc.shipping_line
		elif booking_doc and getattr(booking_doc, "doctype", None) == "Air Booking":
			if air_flag and getattr(booking_doc, "airline", None):
				row["airline"] = booking_doc.airline
		rows.append(row)
	return rows


def apply_sales_quote_routing_to_booking(booking_doc: Document, sales_quote_doc: Document) -> None:
	"""Replace booking routing_legs from Sales Quote when the quote defines at least one leg."""
	rows = get_booking_routing_rows_from_sales_quote(sales_quote_doc, booking_doc)
	if not rows:
		return
	booking_doc.set("routing_legs", [])
	for row in rows:
		booking_doc.append("routing_legs", row)


def routing_legs_for_api_response(sales_quote_name: str, booking_doc: Document | None = None) -> list[dict]:
	"""Load Sales Quote by name and return routing rows for whitelisted API responses (unsaved forms)."""
	if not sales_quote_name or not frappe.db.exists("Sales Quote", sales_quote_name):
		return []
	sq = frappe.get_doc("Sales Quote", sales_quote_name)
	return get_booking_routing_rows_from_sales_quote(sq, booking_doc)
