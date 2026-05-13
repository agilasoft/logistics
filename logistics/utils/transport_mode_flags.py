# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Resolve air/sea UI flags from linked Load Type or Transport Mode (checkboxes)."""

from __future__ import annotations

import json

import frappe


def get_air_sea_flags_for_transport_mode(mode: str | None) -> tuple[int, int]:
	"""Return (transport_mode_air, transport_mode_sea) as 0/1 from master checkboxes.

	Routing-leg **Mode** links to **Transport Mode**, so resolve that first when the name exists.
	Fallback to **Load Type** for values that exist only there (legacy / non-TM codes).
	"""
	if not mode:
		return (0, 0)
	if frappe.db.exists("Transport Mode", mode):
		row = frappe.db.get_value("Transport Mode", mode, ("air", "sea"), as_dict=True) or {}
		return (1 if row.get("air") else 0, 1 if row.get("sea") else 0)
	if frappe.db.exists("Load Type", mode):
		row = frappe.db.get_value("Load Type", mode, ("air", "sea"), as_dict=True) or {}
		return (1 if row.get("air") else 0, 1 if row.get("sea") else 0)
	return (0, 0)


def sync_flags_to_routing_leg(doc) -> None:
	"""Set transport_mode_air / transport_mode_sea on a booking/shipment routing leg row."""
	air, sea = get_air_sea_flags_for_transport_mode(getattr(doc, "mode", None))
	doc.transport_mode_air = air
	doc.transport_mode_sea = sea


def sync_transport_mode_flags_on_parent_routing_legs(parent) -> None:
	"""Set air/sea flags on every ``routing_legs`` row from each row's **Mode**.

	When saving a parent (Sea/Air Booking or Shipment), Frappe updates child table rows with
	``db_update`` and does **not** run the child DocType's ``validate``. Call this from the
	parent's ``validate`` so ``transport_mode_air`` / ``transport_mode_sea`` stay in sync with
	**Transport Mode** / **Load Type** (desk ``depends_on`` and reports).
	"""
	for leg in getattr(parent, "routing_legs", None) or []:
		sync_flags_to_routing_leg(leg)


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


def _doc_as_json_string(doc) -> str:
	"""Desk sends ``doc`` JSON-stringified; some paths may pass a dict."""
	if isinstance(doc, str):
		return doc
	return json.dumps(doc)


@frappe.whitelist(methods=["POST"])
def save_parent_with_routing_quiet(doc, action="Save"):
	"""Persist parent + routing legs like **Save** on the form, without the green *Saved* toast.

	``frappe.client.save`` skips ``savedocs`` child handling (e.g. ``__temporary_name``). Routing-leg
	**Mode** autosave uses this so rows persist reliably while avoiding ``frm.save()`` (which closes
	the grid row).
	"""
	from frappe.desk.form.save import savedocs

	doc_s = _doc_as_json_string(doc)
	prev = bool(frappe.flags.get("mute_messages"))
	frappe.flags.mute_messages = True
	try:
		savedocs(doc_s, action or "Save")
	finally:
		frappe.flags.mute_messages = prev
