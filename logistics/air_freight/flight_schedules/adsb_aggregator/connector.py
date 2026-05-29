# -*- coding: utf-8 -*-
# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""
Free no-auth ADS-B aggregator connectors.

These are community/volunteer-fed ADS-B aggregators with permissive public APIs
and *no* authentication required.  They are used as automatic fallbacks when
the primary live-tracking provider (OpenSky Network) is unreachable from the
host server or has exhausted its quota.

Currently supported providers (try them in order):

- ``adsb.lol``  — https://api.adsb.lol
- ``adsb.fi``   — https://opendata.adsb.fi/api

Both expose the same response shape (the ``readsb-protobuf`` JSON dump format),
so a single connector class handles both with a different base URL.

The normalized output matches the OpenSky connector's ``normalize_state_vector``
output so callers can swap providers transparently:

```
{
    "aircraft_registration": str,        # ICAO24 hex (e.g. "ae5f95")
    "registration":          str | None, # tail number (e.g. "N12345")
    "flight_number":         str | None, # callsign (e.g. "CEB971")
    "country":               str | None, # always None here (not provided)
    "last_position_update":  datetime,
    "last_contact":          datetime,
    "longitude":             float,
    "latitude":              float,
    "altitude_meters":       float | None,
    "is_on_ground":          bool,
    "speed_kmh":             float | None,
    "heading":               float | None,
    "vertical_speed_ms":     float | None,
    "flight_status":         "On Ground" | "Active",
    "aircraft_type":         str | None,
    "data_source":           "adsb.lol" | "adsb.fi",
    "raw_data_json":         str,
}
```
"""

from __future__ import unicode_literals

import json
import time
from datetime import timedelta
from typing import Any, Dict, List, Optional, Tuple

import frappe
import requests
from frappe.utils import now_datetime


# Conversion factors
_KNOTS_TO_KMH = 1.852
_FEET_TO_METERS = 0.3048
_FPM_TO_MPS = 0.00508  # feet/min to m/s

# Providers are tried in this order.  Each entry is (label, base_url).
DEFAULT_PROVIDERS: Tuple[Tuple[str, str], ...] = (
	("adsb.lol", "https://api.adsb.lol/v2"),
	("adsb.fi", "https://opendata.adsb.fi/api/v2"),
)

# adsb.lol/fi ask for max 1 req/sec from free clients.  We sleep between
# per-callsign calls so a single shipment-refresh job doesn't trip rate limits.
_PER_CALL_SLEEP_SEC = 0.4


class AdsbAggregatorConnector:
	"""Free no-auth ADS-B aggregator (adsb.lol / adsb.fi) connector.

	Designed to mirror OpenSkyConnector.get_states_for_callsigns(...) so it can
	be used as a drop-in fallback by ``refresh_air_shipment_flight_position``
	and the bulk ``sync_active_flights`` task.
	"""

	def __init__(self, providers: Optional[Tuple[Tuple[str, str], ...]] = None):
		self.providers: Tuple[Tuple[str, str], ...] = providers or DEFAULT_PROVIDERS
		self.session = requests.Session()
		self.session.headers.update({
			"Accept": "application/json",
			"User-Agent": "Frappe-Logistics/1.0 (+adsb-aggregator-fallback)",
		})
		self.provider_name = "adsb.lol/adsb.fi"
		# Filled in by the last successful provider for the most recent call.
		self.last_provider_used: Optional[str] = None

	# ------------------------------------------------------------------
	# Public API
	# ------------------------------------------------------------------

	def get_states_for_callsigns(
		self,
		callsigns: List[str],
		bbox: Optional[Dict[str, float]] = None,
		timeout: int = 10,
	) -> Dict[str, Dict[str, Any]]:
		"""Return ``{normalized_callsign: normalized_state}`` for the given callsigns.

		Unlike OpenSky, these aggregators don't have a single "give me states
		for these N callsigns" endpoint, but their per-callsign endpoint is
		fast and cheap (<= 50 KB response).  We iterate the providers, and for
		each one iterate the callsigns until we have a hit for every wanted
		callsign or we exhaust providers.

		``bbox`` is ignored (the per-callsign endpoint is already narrow); it
		exists for signature compatibility with the OpenSky connector.
		"""
		out: Dict[str, Dict[str, Any]] = {}
		if not callsigns:
			return out

		wanted: List[str] = []
		seen = set()
		for c in callsigns:
			if not c:
				continue
			cs = str(c).strip().upper()
			if cs and cs not in seen:
				seen.add(cs)
				wanted.append(cs)
		if not wanted:
			return out

		last_error: Optional[Exception] = None
		for label, base in self.providers:
			provider_hit = False
			for idx, cs in enumerate(wanted):
				if cs in out:
					continue
				url = f"{base}/callsign/{cs}"
				try:
					if idx > 0:
						time.sleep(_PER_CALL_SLEEP_SEC)
					resp = self.session.get(url, timeout=timeout)
					if resp.status_code != 200:
						# 404 / 429 / 5xx — try next callsign on same provider.
						continue
					body = resp.json() or {}
				except requests.exceptions.RequestException as e:
					# Network-level failure for this provider — bail and move on.
					last_error = e
					break
				except ValueError as e:
					last_error = e
					continue

				aircraft = body.get("ac") or []
				if not aircraft:
					continue
				# Prefer the entry whose `flight` matches our requested callsign
				# exactly (some endpoints return same-prefix matches too).
				best = None
				for ac in aircraft:
					flight = (ac.get("flight") or "").strip().upper()
					if flight == cs:
						best = ac
						break
				if not best:
					best = aircraft[0]
				normalized = self._normalize_aircraft(best, label)
				if normalized:
					out[cs] = normalized
					out[cs]["_matched_callsign"] = cs
					provider_hit = True
			if provider_hit:
				self.last_provider_used = label
			if len(out) == len(wanted):
				break
		if not self.last_provider_used and last_error is not None:
			raise last_error
		return out

	# ------------------------------------------------------------------
	# Internals
	# ------------------------------------------------------------------

	@staticmethod
	def _normalize_aircraft(ac: Dict[str, Any], provider_label: str) -> Optional[Dict[str, Any]]:
		"""Convert one adsb.lol/adsb.fi aircraft entry to the OpenSky-shaped dict."""
		lat = ac.get("lat")
		lon = ac.get("lon")
		if lat is None or lon is None:
			return None
		# Altitude: prefer geometric, then barometric; both are in feet here.
		alt_ft = ac.get("alt_geom")
		if alt_ft is None:
			alt_ft = ac.get("alt_baro")
		if isinstance(alt_ft, str):  # rare: "ground"
			alt_m: Optional[float] = None
		else:
			alt_m = float(alt_ft) * _FEET_TO_METERS if alt_ft is not None else None

		gs_kn = ac.get("gs")  # ground speed in knots
		speed_kmh = float(gs_kn) * _KNOTS_TO_KMH if gs_kn is not None else None

		# Prefer true heading, then track, then mag heading.
		heading = ac.get("true_heading")
		if heading is None:
			heading = ac.get("track")
		if heading is None:
			heading = ac.get("nav_heading")

		baro_rate_fpm = ac.get("baro_rate")
		geom_rate_fpm = ac.get("geom_rate")
		rate_fpm = geom_rate_fpm if geom_rate_fpm is not None else baro_rate_fpm
		vs_ms = float(rate_fpm) * _FPM_TO_MPS if rate_fpm is not None else None

		on_ground = bool(ac.get("alt_baro") == "ground" or ac.get("airGround") == "G")

		# Anchor "now" to Frappe's clock (respects system_settings.time_zone) so
		# downstream "stale_minutes" math matches the rest of the dashboard.
		seen_pos = ac.get("seen_pos")
		seen = ac.get("seen")
		now_dt = now_datetime()
		last_pos_dt = None
		last_contact_dt = None
		if seen_pos is not None:
			try:
				last_pos_dt = now_dt - timedelta(seconds=float(seen_pos))
			except Exception:
				pass
		if seen is not None:
			try:
				last_contact_dt = now_dt - timedelta(seconds=float(seen))
			except Exception:
				pass

		flight = (ac.get("flight") or "").strip() or None

		return {
			"aircraft_registration": ac.get("hex"),
			"registration": ac.get("r") or None,
			"flight_number": flight,
			"country": None,
			"last_position_update": last_pos_dt,
			"last_contact": last_contact_dt,
			"longitude": float(lon),
			"latitude": float(lat),
			"altitude_meters": alt_m,
			"is_on_ground": on_ground,
			"speed_kmh": speed_kmh,
			"heading": float(heading) if heading is not None else None,
			"vertical_speed_ms": vs_ms,
			"flight_status": "On Ground" if on_ground else "Active",
			"aircraft_type": ac.get("t") or None,
			"data_source": provider_label,
			"raw_data_json": json.dumps(ac),
		}
