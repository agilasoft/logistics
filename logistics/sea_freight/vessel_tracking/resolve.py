# -*- coding: utf-8 -*-
# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe


def _row_get(row, key, default=None):
	if row is None:
		return default
	if isinstance(row, dict):
		return row.get(key, default)
	return getattr(row, key, default)


def _leg_is_sea(row):
	mode = _row_get(row, "mode")
	if not mode:
		return False
	return bool(frappe.db.get_value("Transport Mode", mode, "sea"))


def _sort_legs(routing_legs):
	return sorted(routing_legs or [], key=lambda r: int(_row_get(r, "idx") or 0))


def resolve_vessel_name_for_tracking_from_sea_shipment(doc):
	"""
	Return Vessel document name to use for AIS, or None.
	Prefers Main sea leg with vessel_master; else first sea leg with vessel_master.
	"""
	legs = [leg for leg in _sort_legs(_row_get(doc, "routing_legs") or []) if _leg_is_sea(leg)]
	if not legs:
		return None
	for leg in legs:
		if (_row_get(leg, "type") or "") == "Main" and _row_get(leg, "vessel_master"):
			return _row_get(leg, "vessel_master")
	for leg in legs:
		if _row_get(leg, "vessel_master"):
			return _row_get(leg, "vessel_master")
	return None


def get_vessel_ids_for_tracking(vessel_name):
	"""Return (mmsi, imo, vessel_name_label) from Vessel master or (None, None, None)."""
	if not vessel_name or not frappe.db.exists("Vessel", vessel_name):
		return None, None, None
	row = frappe.db.get_value(
		"Vessel",
		vessel_name,
		["mmsi", "imo", "vessel_name", "is_active"],
		as_dict=True,
	)
	if not row or not row.get("is_active"):
		return None, None, None
	mmsi = (row.get("mmsi") or "").strip() or None
	imo = (row.get("imo") or "").strip() or None
	label = row.get("vessel_name") or vessel_name
	return mmsi, imo, label


def sea_freight_settings_allow_tracking(settings_doc):
	"""True if company settings have tracking enabled and a provider + API key configured."""
	if not settings_doc or not getattr(settings_doc, "enable_vessel_tracking", 0):
		return False
	if not (getattr(settings_doc, "vessel_tracking_provider", None) or "").strip():
		return False
	key = None
	try:
		key = settings_doc.get_password("vessel_tracking_api_key")
	except Exception:
		pass
	if key and str(key).strip():
		return True
	from frappe.utils.password import get_decrypted_password

	if getattr(settings_doc, "name", None):
		existing = get_decrypted_password(
			"Sea Freight Settings",
			settings_doc.name,
			"vessel_tracking_api_key",
			raise_exception=False,
		)
		return bool(existing and str(existing).strip())
	return False


def get_vessel_tracking_map_options_for_sea_shipment(doc):
	"""
	Options passed into the dashboard map HTML (no external HTTP).
	"""
	out = {
		"enabled": False,
		"sea_shipment": None,
		"hint": None,
	}
	if not doc or not getattr(doc, "name", None):
		out["hint"] = frappe._("Save the shipment to enable live vessel position.")
		return out
	if getattr(doc, "docstatus", 0) == 2:
		return out
	from logistics.sea_freight.doctype.sea_freight_settings.sea_freight_settings import (
		SeaFreightSettings,
	)

	company = getattr(doc, "company", None)
	settings = SeaFreightSettings.get_settings(company) if company else None
	if not sea_freight_settings_allow_tracking(settings):
		return out
	vessel = resolve_vessel_name_for_tracking_from_sea_shipment(doc)
	if not vessel:
		out["hint"] = frappe._("Set Vessel Master on a sea routing leg (Main leg preferred) with MMSI or IMO on the Vessel record.")
		return out
	mmsi, imo, _label = get_vessel_ids_for_tracking(vessel)
	if not mmsi and not imo:
		out["hint"] = frappe._("Selected Vessel master must have MMSI or IMO for AIS tracking.")
		return out
	return {"enabled": True, "sea_shipment": doc.name, "hint": None}
