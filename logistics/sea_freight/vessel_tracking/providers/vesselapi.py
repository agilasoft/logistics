# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

import frappe
import requests

from logistics.sea_freight.vessel_tracking.providers.normalize import normalized_position, pick_coords


VESSELAPI_POSITION_URL = "https://api.vesselapi.com/v1/vessel/{vessel_id}/position"


def fetch_position(api_key, mmsi=None, imo=None, timeout=15):
	"""Return normalized dict or None."""
	if not api_key or (not mmsi and not imo):
		return None
	id_type = "mmsi" if mmsi else "imo"
	vid = mmsi or imo
	url = VESSELAPI_POSITION_URL.format(vessel_id=str(vid))
	try:
		resp = requests.get(
			url,
			headers={"Authorization": "Bearer {0}".format(api_key.strip())},
			params={"filter.idType": id_type},
			timeout=timeout,
		)
	except requests.RequestException as e:
		frappe.log_error(json.dumps({"error": str(e), "provider": "VesselAPI"}), "VesselAPI request error")
		return None
	if resp.status_code != 200:
		frappe.log_error(
			json.dumps(
				{
					"provider": "VesselAPI",
					"status": resp.status_code,
					"body": (resp.text or "")[:2000],
				}
			),
			"VesselAPI HTTP error",
		)
		return None
	try:
		body = resp.json()
	except ValueError:
		return None
	block = body.get("data") if isinstance(body.get("data"), dict) else body
	lat, lon = pick_coords(block or {})
	if lat is None:
		return None
	name = None
	if isinstance(block, dict):
		name = block.get("vessel_name") or block.get("name")
	return normalized_position(
		lat,
		lon,
		label=name,
		sog=block.get("sog") if isinstance(block, dict) else None,
		cog=block.get("cog") if isinstance(block, dict) else None,
		recorded_at=(block.get("timestamp") if isinstance(block, dict) else None),
		source="VesselAPI",
		raw=body,
	)
