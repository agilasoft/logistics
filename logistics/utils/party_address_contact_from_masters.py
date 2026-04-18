# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Server-side population of address/contact fields from Shipper and Consignee masters.

Mirrors client behaviour (air_booking.js / sea_booking.js) when party links are set.
"""

from __future__ import annotations

import frappe
from frappe.contacts.doctype.address.address import get_address_display


def contact_display_text(contact_name: str | None) -> str:
	"""Multi-line display string for a Contact, aligned with booking form triggers."""
	if not contact_name or not frappe.db.exists("Contact", contact_name):
		return ""
	try:
		c = frappe.get_doc("Contact", contact_name)
		parts = []
		name = " ".join(filter(None, [c.first_name, c.last_name]))
		if name:
			parts.append(name)
		elif c.name:
			parts.append(c.name)
		if c.designation:
			parts.append(c.designation)
		if c.phone:
			parts.append(c.phone)
		if c.mobile_no:
			parts.append(c.mobile_no)
		if c.email_id:
			parts.append(c.email_id)
		return "\n".join(parts)
	except Exception:
		return ""


def populate_air_sea_booking_party_fields_from_masters(doc) -> None:
	"""Set Air/Sea Booking Contacts & Addresses fields from Shipper/Consignee when links are set."""
	if doc.doctype not in ("Air Booking", "Sea Booking"):
		return

	if doc.shipper and frappe.db.exists("Shipper", doc.shipper):
		sd = frappe.get_cached_doc("Shipper", doc.shipper)
		addr = getattr(sd, "pick_address", None) or getattr(sd, "shipper_primary_address", None)
		if addr:
			doc.shipper_address = addr
			doc.shipper_address_display = get_address_display(addr)
		pc = getattr(sd, "shipper_primary_contact", None)
		if pc:
			doc.shipper_contact = pc
			doc.shipper_contact_display = contact_display_text(pc)

	if doc.consignee and frappe.db.exists("Consignee", doc.consignee):
		cd = frappe.get_cached_doc("Consignee", doc.consignee)
		addr = getattr(cd, "delivery_address", None) or getattr(cd, "consignee_primary_address", None)
		if addr:
			doc.consignee_address = addr
			doc.consignee_address_display = get_address_display(addr)
		pc = getattr(cd, "consignee_primary_contact", None)
		if pc:
			doc.consignee_contact = pc
			doc.consignee_contact_display = contact_display_text(pc)


def append_transport_order_door_leg_from_party_masters(order) -> None:
	"""Append one door-to-door leg with pick/drop Address links from Shipper/Consignee masters."""
	if not getattr(order, "shipper", None) or not getattr(order, "consignee", None):
		return

	leg = {
		"facility_type_from": "Shipper",
		"facility_from": order.shipper,
		"facility_type_to": "Consignee",
		"facility_to": order.consignee,
		"scheduled_date": getattr(order, "scheduled_date", None) or getattr(order, "booking_date", None),
		"transport_job_type": getattr(order, "transport_job_type", None) or "Non-Container",
	}

	if frappe.db.exists("Shipper", order.shipper):
		sd = frappe.get_cached_doc("Shipper", order.shipper)
		pick = getattr(sd, "pick_address", None) or getattr(sd, "shipper_primary_address", None)
		if pick:
			leg["pick_address"] = pick

	if frappe.db.exists("Consignee", order.consignee):
		cd = frappe.get_cached_doc("Consignee", order.consignee)
		drop = getattr(cd, "delivery_address", None) or getattr(cd, "consignee_primary_address", None)
		if drop:
			leg["drop_address"] = drop

	order.append("legs", leg)
