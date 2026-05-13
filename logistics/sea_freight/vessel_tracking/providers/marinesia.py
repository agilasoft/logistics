# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

import frappe
import requests

from logistics.sea_freight.vessel_tracking.providers.normalize import normalized_position, pick_coords


MARINESIA_LATEST_V1 = "https://api.marinesia.com/api/v1/vessel/{mmsi}/location/latest"
MARINESIA_LATEST_V2 = "https://api.marinesia.com/api/v2/vessel/location/latest"


def fetch_position(api_key, mmsi=None, imo=None, timeout=15):
	if not api_key or (not mmsi and not imo):
		return None
	key = api_key.strip()
	try:
		if mmsi:
			url = MARINESIA_LATEST_V1.format(mmsi=requests.utils.quote(str(mmsi), safe=""))
			resp = requests.get(url, params={"key": key}, timeout=timeout)
		else:
			resp = requests.get(
				MARINESIA_LATEST_V2, params={"imo": str(imo), "key": key}, timeout=timeout
			)
	except requests.RequestException as e:
		frappe.log_error(json.dumps({"error": str(e), "provider": "Marinesia"}), "Marinesia request error")
		return None
	if resp.status_code != 200:
		frappe.log_error(
			json.dumps(
				{
					"provider": "Marinesia",
					"status": resp.status_code,
					"body": (resp.text or "")[:2000],
				}
			),
			"Marinesia HTTP error",
		)
		return None
	try:
		body = resp.json()
	except ValueError:
		return None
	if body.get("error"):
		return None
	data = body.get("data")
	if not isinstance(data, dict):
		return None
	lat, lon = pick_coords(data)
	if lat is None:
		return None
	return normalized_position(
		lat,
		lon,
		label=None,
		sog=data.get("sog"),
		cog=data.get("cog"),
		recorded_at=data.get("ts"),
		source="Marinesia",
		raw=body,
	)
