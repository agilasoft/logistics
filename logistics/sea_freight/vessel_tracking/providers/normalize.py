# -*- coding: utf-8 -*-
from __future__ import unicode_literals


def normalized_position(
	lat, lon, label=None, sog=None, cog=None, recorded_at=None, source=None, raw=None
):
	return {
		"lat": lat,
		"lon": lon,
		"label": label,
		"sog": sog,
		"cog": cog,
		"recorded_at": recorded_at,
		"source": source,
		"raw": raw,
	}


def pick_coords(payload):
	"""Extract lat/lon from dict-like AIS payloads."""
	if not isinstance(payload, dict):
		return None, None
	lat = payload.get("latitude")
	if lat is None:
		lat = payload.get("lat")
	lon = payload.get("longitude")
	if lon is None:
		lon = payload.get("lng")
	if lon is None:
		lon = payload.get("lon")
	try:
		if lat is not None:
			lat = float(lat)
		if lon is not None:
			lon = float(lon)
	except (TypeError, ValueError):
		return None, None
	if lat is None or lon is None:
		return None, None
	if not (-90 <= lat <= 90 and -180 <= lon <= 180):
		return None, None
	return lat, lon
