# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Resolve air/sea UI flags from linked Load Type or Transport Mode (checkboxes)."""

from __future__ import annotations

import json

import frappe


def get_air_sea_flags_for_transport_mode(mode: str | None) -> tuple[int, int]:
	"""Return (transport_mode_air, transport_mode_sea) as 0/1 from Load Type or Transport Mode checkboxes."""
	if not mode:
		return (0, 0)
	if frappe.db.exists("Load Type", mode):
		row = frappe.db.get_value("Load Type", mode, ("air", "sea"), as_dict=True) or {}
		return (1 if row.get("air") else 0, 1 if row.get("sea") else 0)
	if frappe.db.exists("Transport Mode", mode):
		row = frappe.db.get_value("Transport Mode", mode, ("air", "sea"), as_dict=True) or {}
		return (1 if row.get("air") else 0, 1 if row.get("sea") else 0)
	return (0, 0)


def sync_flags_to_routing_leg(doc) -> None:
	"""Set transport_mode_air / transport_mode_sea on a booking/shipment routing leg row."""
	air, sea = get_air_sea_flags_for_transport_mode(getattr(doc, "mode", None))
	doc.transport_mode_air = air
	doc.transport_mode_sea = sea


@frappe.whitelist()
def get_transport_mode_flags_bulk(modes):
	"""Return {mode_name: {"air": 0|1, "sea": 0|1}} for desk forms (child routing legs)."""
	if isinstance(modes, str):
		modes = json.loads(modes)
	result = {}
	for mode in modes or []:
		if not mode:
			continue
		air, sea = get_air_sea_flags_for_transport_mode(mode)
		result[mode] = {"air": air, "sea": sea}
	return result
