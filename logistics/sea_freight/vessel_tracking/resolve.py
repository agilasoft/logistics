# -*- coding: utf-8 -*-
# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Sea Shipment ⇄ Vessel resolution helpers.

The actual live-AIS plumbing (providers, API keys, cache TTL, fallback order)
now lives in the **GoConnect** app under ``GoConnect Settings ▸ Vessel``.

This module keeps a small surface that the logistics dashboard still needs:

  * ``resolve_vessel_name_for_tracking_from_sea_shipment(doc)`` — given an
	in-memory Sea Shipment doc, return the Vessel master name from the most
	relevant sea leg. Used by tests and by code that doesn't want to hit
	GoConnect's SQL path.
  * ``get_vessel_ids_for_tracking(vessel_name)`` — look up MMSI/IMO from the
	Vessel master.
  * ``get_vessel_tracking_map_options_for_sea_shipment(doc)`` — feeds the
	Sea Shipment dashboard's map block. Tells the front-end whether to wire
	up the AIS overlay, and surfaces a hint when something is missing.
"""

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
	"""Return the Vessel master name for AIS lookup, or ``None``.

	Prefers the **Main** sea leg with ``vessel_master`` set; falls back to the
	first sea leg that has any ``vessel_master``.
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
	"""Return ``(mmsi, imo, vessel_name_label)`` or ``(None, None, None)``."""
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


def _goconnect_vessel_tracking_available():
	"""True iff goConnect is installed and at least one vessel provider is enabled."""
	try:
		if "goconnect" not in frappe.get_installed_apps():
			return False
	except Exception:
		return False
	try:
		from goconnect.sea.aggregator import get_aggregator

		return bool(get_aggregator().providers())
	except Exception:
		return False


def _resolve_via_goconnect(sea_shipment_name):
	"""Return ``{mmsi, imo, source, ...}`` from goConnect, or None.

	goConnect's resolver also walks the Master Bill → Vessel Schedule path,
	so it covers cases where the Sea Shipment routing leg has no
	``vessel_master`` but the linked Master Bill points to a curated
	Vessel Schedule.
	"""
	try:
		from goconnect.sea.resolve import get_or_resolve_ids_for_sea_shipment

		return get_or_resolve_ids_for_sea_shipment(sea_shipment_name)
	except Exception:
		return None


def get_vessel_tracking_map_options_for_sea_shipment(doc):
	"""Options passed into the dashboard map HTML (no external HTTP).

	When ``enabled`` is True the front-end will call goConnect's
	``goconnect.api.sea.get_vessel_position_for_map`` to fetch the live dot.
	When False, ``hint`` (if set) is shown to the user.
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

	if not _goconnect_vessel_tracking_available():
		out["hint"] = frappe._(
			"Vessel tracking is not configured. Enable a provider in "
			"GoConnect Settings ▸ Vessel."
		)
		return out

	# Mirror goConnect's resolution chain so the hint matches what the
	# fetch endpoint will actually do (Master Bill → Vessel Schedule first,
	# then Sea Shipment routing leg).
	resolved = _resolve_via_goconnect(doc.name)
	if resolved and (resolved.get("mmsi") or resolved.get("imo")):
		return {"enabled": True, "sea_shipment": doc.name, "hint": None}

	# Fall back to the in-memory leg walk so unsaved/local edits still get
	# a useful hint before the doc round-trips.
	vessel = resolve_vessel_name_for_tracking_from_sea_shipment(doc)
	if not vessel:
		out["hint"] = frappe._(
			"Set Vessel Master on a sea routing leg (Main leg preferred) with "
			"MMSI or IMO on the Vessel record."
		)
		return out

	mmsi, imo, _label = get_vessel_ids_for_tracking(vessel)
	if not mmsi and not imo:
		out["hint"] = frappe._(
			"Selected Vessel master must have MMSI or IMO for AIS tracking."
		)
		return out

	# Vessel master exists with ids but goConnect's resolver didn't pick it up
	# (rare — usually a stale cache). Still enable; the API call will retry.
	return {"enabled": True, "sea_shipment": doc.name, "hint": None}
