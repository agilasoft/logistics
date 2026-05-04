# -*- coding: utf-8 -*-
# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json

import frappe
from frappe import _

from logistics.sea_freight.doctype.sea_freight_settings.sea_freight_settings import SeaFreightSettings
from logistics.sea_freight.vessel_tracking.providers.marinesia import fetch_position as marinesia_fetch
from logistics.sea_freight.vessel_tracking.providers.vesselapi import fetch_position as vesselapi_fetch
from logistics.sea_freight.vessel_tracking.providers.vesselfinder import fetch_position as vesselfinder_fetch
from logistics.sea_freight.vessel_tracking.resolve import (
	get_vessel_ids_for_tracking,
	resolve_vessel_name_for_tracking_from_sea_shipment,
	sea_freight_settings_allow_tracking,
)


def _cache_key(provider, mmsi, imo):
	return "logistics:ais_position:{0}:{1}".format(provider, mmsi or imo)


def _run_provider(settings, mmsi, imo):
	provider = (settings.vessel_tracking_provider or "").strip()
	api_key = settings.get_password("vessel_tracking_api_key")
	api_user = (settings.vessel_tracking_api_user or "").strip() or None
	api_secret = None
	try:
		api_secret = settings.get_password("vessel_tracking_api_secret")
	except Exception:
		pass
	if api_secret is not None and not str(api_secret).strip():
		api_secret = None
	if provider == "VesselAPI":
		return vesselapi_fetch(api_key, mmsi=mmsi, imo=imo)
	if provider == "Marinesia":
		return marinesia_fetch(api_key, mmsi=mmsi, imo=imo)
	if provider == "VesselFinder":
		return vesselfinder_fetch(
			api_key, mmsi=mmsi, imo=imo, api_user=api_user, api_secret=api_secret
		)
	return None


@frappe.whitelist()
def get_vessel_position_for_map(sea_shipment):
	"""Return latest AIS position for the vessel linked on the Sea Shipment's routing (cached ~90s)."""
	doc = frappe.get_doc("Sea Shipment", sea_shipment)
	if not frappe.has_permission("Sea Shipment", "read", doc):
		frappe.throw(_("Not permitted to read this Sea Shipment."), frappe.PermissionError)

	settings = SeaFreightSettings.get_settings(doc.company)
	if not sea_freight_settings_allow_tracking(settings):
		return {"success": False, "message": _("Vessel tracking is not configured for this company.")}

	vessel_link = resolve_vessel_name_for_tracking_from_sea_shipment(doc)
	if not vessel_link:
		return {"success": False, "message": _("No Vessel Master linked on a sea routing leg.")}

	mmsi, imo, vessel_label = get_vessel_ids_for_tracking(vessel_link)
	if not mmsi and not imo:
		return {"success": False, "message": _("Vessel master has no MMSI or IMO.")}

	provider = (settings.vessel_tracking_provider or "").strip()
	cache_key = _cache_key(provider, mmsi, imo)
	cached = frappe.cache().get_value(cache_key)
	if cached:
		try:
			return json.loads(cached)
		except Exception:
			pass

	pos = _run_provider(settings, mmsi, imo)
	if not pos:
		out = {
			"success": False,
			"message": _("Could not fetch vessel position from the provider."),
		}
		return out

	label = pos.get("label") or vessel_label
	out = {
		"success": True,
		"lat": pos["lat"],
		"lon": pos["lon"],
		"label": label,
		"sog": pos.get("sog"),
		"cog": pos.get("cog"),
		"recorded_at": pos.get("recorded_at"),
		"provider": provider,
	}
	frappe.cache().set_value(cache_key, json.dumps(out), expires_in_sec=90)
	return out
