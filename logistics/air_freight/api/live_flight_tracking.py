# Copyright (c) 2026, Agilasoft and contributors
"""Live flight tracking endpoint for the Air Freight operations dashboard.

Returns the current position of every operational flight, defined as a Flight
Schedule that is referenced by a Master Air Waybill which is itself referenced
by a non-cancelled Air Shipment.  Draft Air Shipments are included so the
dashboard can preview live positions before submission; the existing status
dropdown on the dashboard is the single source of truth for which rows are
visible.  A single OpenSky `/states/all` call is used to fetch real-time
positions for every requested callsign at once, which is essential to stay
under OpenSky's free anonymous quota (~400 requests/day).
"""

from __future__ import unicode_literals

import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

from logistics.operations_dashboard.heat_map_core import (
	job_status_filter_for_query,
	parse_multi_link_param,
	parse_traffic,
	row_matches_traffic,
	sanitize_link_values,
	session_company_context,
)


AIR_SHIPMENT_VALID_JOB_STATUSES = (
	"Draft",
	"Submitted",
	"In Progress",
	"Completed",
	"Closed",
	"Reopened",
	"Cancelled",
)

# Flight Schedule statuses worth surfacing on the live map.
TRACKABLE_FLIGHT_STATUSES = (
	"Scheduled",
	"Active",
	"EnRoute",
	"Delayed",
	"Diverted",
	"Landed",
)

# Anything older than this is shown as "stale" (no live state and persisted
# fix is old).  Live state always wins regardless of age.
STALE_THRESHOLD_MINUTES = 60


_NON_ALNUM_RE = re.compile(r"[^A-Z0-9]")


def _normalize_callsign(value: Optional[str]) -> str:
	if not value:
		return ""
	return _NON_ALNUM_RE.sub("", str(value).upper())


def _callsign_candidates(flight_number: Optional[str], airline_iata: Optional[str],
                         airline_icao: Optional[str], iata_to_icao: Dict[str, str]) -> List[str]:
	"""Return candidate ADS-B callsigns to try for a given flight identifier.

	ADS-B feeds use ICAO airline designators (e.g. SIA112) while logistics docs
	usually carry IATA flight numbers (e.g. SQ112).  We try both, plus the raw
	value, so the matching tolerates either convention.
	"""
	out: List[str] = []
	seen = set()

	def _add(val: Optional[str]) -> None:
		key = _normalize_callsign(val)
		if not key or key in seen:
			return
		seen.add(key)
		out.append(key)

	_add(flight_number)

	if not flight_number:
		return out

	raw = _normalize_callsign(flight_number)

	# Extract trailing digit portion (the flight number proper).
	m = re.search(r"(\d+)$", raw)
	digits = m.group(1) if m else ""

	# Derive prefix from raw (everything before the digits).
	prefix = raw[: -len(digits)] if digits else ""

	icao = (airline_icao or "").strip().upper()
	iata = (airline_iata or "").strip().upper()

	# If prefix looks like a 2-char IATA airline code, try the ICAO equivalent.
	if digits:
		if iata and iata == prefix:
			ic = (icao or iata_to_icao.get(iata) or "").strip().upper()
			if ic:
				_add(ic + digits)
		elif prefix and len(prefix) == 2:
			ic = (iata_to_icao.get(prefix) or "").strip().upper()
			if ic:
				_add(ic + digits)
		elif not prefix and icao:
			_add(icao + digits)

		# Also try the doc's explicit ICAO prefix even if digits already match.
		if icao:
			_add(icao + digits)
		if iata and icao and prefix == icao:
			_add(iata + digits)

	return out


def _load_iata_to_icao_map() -> Dict[str, str]:
	"""Build IATA -> ICAO airline code lookup.

	Reads from `Airline` (operational doctype) and falls back to `Airline Master`
	(sourced by master_data_sync).  Cached on `frappe.local` for the request.
	"""
	cached = getattr(frappe.local, "_logistics_iata_to_icao", None)
	if cached is not None:
		return cached

	mapping: Dict[str, str] = {}
	try:
		rows = frappe.get_all(
			"Airline",
			fields=["iata_code", "icao_code"],
			filters={"iata_code": ["is", "set"]},
			limit_page_length=0,
		)
		for r in rows:
			iata = (r.get("iata_code") or "").strip().upper()
			icao = (r.get("icao_code") or "").strip().upper()
			if iata and icao:
				mapping.setdefault(iata, icao)
	except Exception:
		pass

	if frappe.db.exists("DocType", "Airline Master"):
		try:
			rows = frappe.get_all(
				"Airline Master",
				fields=["iata_code", "icao_code"],
				filters={"iata_code": ["is", "set"]},
				limit_page_length=0,
			)
			for r in rows:
				iata = (r.get("iata_code") or "").strip().upper()
				icao = (r.get("icao_code") or "").strip().upper()
				if iata and icao:
					mapping.setdefault(iata, icao)
		except Exception:
			pass

	frappe.local._logistics_iata_to_icao = mapping
	return mapping


def _fetch_operational_rows(
	job_status_filter: Optional[str],
	filter_user: Optional[str],
	company: Optional[str],
	airlines: Optional[List[str]],
) -> List[Dict[str, Any]]:
	"""Run the SQL join to pull Air Shipment -> Master AWB -> Flight Schedule rows.

	Draft (``docstatus = 0``) shipments are included; the existing status
	dropdown on the dashboard ("Ongoing (no draft)" / "Ongoing (incl. draft)" /
	"Draft" / "Submitted" / ...) is the single source of truth for which rows
	are surfaced.  Only Cancelled (``docstatus = 2``) shipments are always
	excluded.
	"""
	mode, val = job_status_filter_for_query(job_status_filter, AIR_SHIPMENT_VALID_JOB_STATUSES)
	conditions: List[str] = ["fs.name IS NOT NULL", "ash.docstatus < 2"]
	params: Dict[str, Any] = {}

	if mode == "not_in":
		conditions.append("ash.job_status NOT IN %(job_status_vals)s")
		params["job_status_vals"] = tuple(val)
	else:
		conditions.append("ash.job_status = %(job_status_val)s")
		params["job_status_val"] = val

	if company:
		conditions.append("ash.company = %(company)s")
		params["company"] = company

	fu = (filter_user or "").strip()
	if fu and frappe.db.exists("User", fu):
		conditions.append("ash.owner = %(filter_user)s")
		params["filter_user"] = fu

	if airlines:
		conditions.append("ash.airline IN %(airlines)s")
		params["airlines"] = tuple(airlines)

	if TRACKABLE_FLIGHT_STATUSES:
		conditions.append("(fs.flight_status IS NULL OR fs.flight_status IN %(flight_statuses)s)")
		params["flight_statuses"] = tuple(TRACKABLE_FLIGHT_STATUSES)

	where_sql = " AND ".join(conditions)

	sql = """
		SELECT
			fs.name              AS flight_schedule,
			fs.flight_number     AS flight_number,
			fs.airline_iata      AS airline_iata,
			fs.airline_icao      AS airline_icao,
			fs.flight_status     AS flight_status,
			fs.departure_iata    AS departure_iata,
			fs.departure_icao    AS departure_icao,
			fs.arrival_iata      AS arrival_iata,
			fs.arrival_icao      AS arrival_icao,
			fs.departure_time_scheduled AS etd,
			fs.arrival_time_scheduled   AS eta,
			fs.departure_time_actual    AS atd,
			fs.arrival_time_actual      AS ata,
			fs.latitude         AS last_lat,
			fs.longitude        AS last_lon,
			fs.altitude_meters  AS last_alt,
			fs.speed_kmh        AS last_speed,
			fs.heading          AS last_heading,
			fs.is_on_ground     AS last_on_ground,
			fs.last_position_update AS last_pos_at,
			fs.aircraft_type    AS aircraft_type,
			fs.registration     AS registration,
			mawb.name            AS master_awb,
			mawb.master_awb_no   AS master_awb_no,
			ash.name             AS air_shipment,
			ash.airline          AS shipment_airline,
			ash.origin_port      AS origin_port,
			ash.destination_port AS destination_port,
			ash.job_status       AS job_status,
			ash.owner            AS shipment_owner
		FROM `tabAir Shipment` ash
		INNER JOIN `tabMaster Air Waybill` mawb ON mawb.name = ash.master_awb
		INNER JOIN `tabFlight Schedule` fs ON fs.name = mawb.flight_schedule
		WHERE {where}
	""".format(where=where_sql)

	return frappe.db.sql(sql, params, as_dict=True) or []


def _aggregate_by_flight_schedule(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
	"""Group joined rows by Flight Schedule, collecting the linked shipments/MAWBs."""
	flights: Dict[str, Dict[str, Any]] = {}
	for r in rows:
		fs = r.get("flight_schedule")
		if not fs:
			continue
		entry = flights.get(fs)
		if not entry:
			entry = {
				"flight_schedule": fs,
				"flight_number": r.get("flight_number"),
				"airline_iata": r.get("airline_iata"),
				"airline_icao": r.get("airline_icao"),
				"flight_status": r.get("flight_status"),
				"departure_iata": r.get("departure_iata"),
				"departure_icao": r.get("departure_icao"),
				"arrival_iata": r.get("arrival_iata"),
				"arrival_icao": r.get("arrival_icao"),
				"etd": r.get("etd"),
				"eta": r.get("eta"),
				"atd": r.get("atd"),
				"ata": r.get("ata"),
				"aircraft_type": r.get("aircraft_type"),
				"registration": r.get("registration"),
				"last_lat": r.get("last_lat"),
				"last_lon": r.get("last_lon"),
				"last_alt": r.get("last_alt"),
				"last_speed": r.get("last_speed"),
				"last_heading": r.get("last_heading"),
				"last_on_ground": bool(r.get("last_on_ground")),
				"last_pos_at": r.get("last_pos_at"),
				"shipments": [],
				"master_awbs": set(),
				"owners": set(),
			}
			flights[fs] = entry
		entry["shipments"].append({
			"name": r.get("air_shipment"),
			"master_awb": r.get("master_awb"),
			"master_awb_no": r.get("master_awb_no"),
			"origin": r.get("origin_port"),
			"destination": r.get("destination_port"),
			"job_status": r.get("job_status"),
		})
		if r.get("master_awb"):
			entry["master_awbs"].add(r["master_awb"])
		if r.get("shipment_owner"):
			entry["owners"].add(r["shipment_owner"])
	return flights


def _filter_by_traffic(flights: Dict[str, Dict[str, Any]], traffic: str) -> Dict[str, Dict[str, Any]]:
	"""Apply the dashboard's traffic filter (import/export/domestic/all)."""
	if traffic == "all":
		return flights

	unloco_keys = set()
	for f in flights.values():
		for s in f.get("shipments", []):
			if s.get("origin"):
				unloco_keys.add(s["origin"])
			if s.get("destination"):
				unloco_keys.add(s["destination"])
	if not unloco_keys:
		return flights

	cc_by_unloco: Dict[str, str] = {}
	try:
		rows = frappe.get_all(
			"UNLOCO",
			filters={"name": ["in", list(unloco_keys)]},
			fields=["name", "country"],
			limit_page_length=0,
		)
		country_map: Dict[str, str] = {}
		country_names = {r["country"] for r in rows if r.get("country")}
		if country_names:
			country_rows = frappe.get_all(
				"Country",
				filters={"name": ["in", list(country_names)]},
				fields=["name", "code"],
				limit_page_length=0,
			)
			country_map = {c["name"]: (c.get("code") or "").upper() for c in country_rows}
		for r in rows:
			cc = country_map.get(r.get("country"), "")
			cc_by_unloco[r["name"]] = cc
	except Exception:
		cc_by_unloco = {}

	out: Dict[str, Dict[str, Any]] = {}
	for fs, f in flights.items():
		# A flight matches the traffic filter if ANY linked shipment matches.
		matched = False
		for s in f.get("shipments", []):
			if row_matches_traffic(traffic, s.get("origin"), s.get("destination"), cc_by_unloco):
				matched = True
				break
		if matched:
			out[fs] = f
	return out


def _try_fetch_live_states(flights: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
	"""Call OpenSky once for every callsign candidate across all flights.

	Returns: { "states": {callsign -> normalized_state}, "provider": str,
	           "provider_status": "live" | "stale" | "disabled" | "error",
	           "error": Optional[str] }
	"""
	result: Dict[str, Any] = {
		"states": {},
		"provider": "OpenSky Network",
		"provider_status": "live",
		"error": None,
	}

	try:
		settings = frappe.get_cached_doc("GoConnect Settings")
	except Exception:
		settings = None

	if not settings or not getattr(settings, "flight_enable_realtime_tracking", 0):
		result["provider_status"] = "disabled"
		return result

	if not getattr(settings, "opensky_enabled", 0):
		result["provider_status"] = "disabled"
		result["error"] = "OpenSky Network is not enabled in GoConnect Settings"
		return result

	# Collect every callsign candidate we want to look up.
	iata_to_icao = _load_iata_to_icao_map()
	wanted: List[str] = []
	for f in flights.values():
		cands = _callsign_candidates(
			f.get("flight_number"),
			f.get("airline_iata"),
			f.get("airline_icao"),
			iata_to_icao,
		)
		f["_callsign_candidates"] = cands
		wanted.extend(cands)
	wanted = list({w for w in wanted if w})

	if not wanted:
		return result

	try:
		from logistics.air_freight.flight_schedules.opensky.connector import OpenSkyConnector
		connector = OpenSkyConnector()
		result["states"] = connector.get_states_for_callsigns(wanted) or {}
	except Exception as e:
		result["provider_status"] = "error"
		result["error"] = str(e)
		frappe.log_error(
			title="Live Flight Tracking - OpenSky fetch failed",
			message=frappe.get_traceback(),
		)
	return result


def _serialize_flight(f: Dict[str, Any], states_by_callsign: Dict[str, Dict[str, Any]],
                      now: datetime) -> Dict[str, Any]:
	"""Build the dashboard payload for a single flight."""
	live = None
	matched_callsign = None
	for cs in f.get("_callsign_candidates", []) or []:
		state = states_by_callsign.get(cs)
		if not state:
			continue
		live = state
		matched_callsign = cs
		break

	# Decide which position to surface: live if we have it, else the persisted
	# last-known fix.
	stale = False
	stale_minutes: Optional[int] = None
	if live and live.get("latitude") is not None and live.get("longitude") is not None:
		lat = live.get("latitude")
		lon = live.get("longitude")
		alt = live.get("altitude_meters")
		speed = live.get("speed_kmh")
		heading = live.get("heading")
		on_ground = bool(live.get("is_on_ground"))
		pos_at = live.get("last_position_update")
		source = "live"
	else:
		lat = f.get("last_lat")
		lon = f.get("last_lon")
		alt = f.get("last_alt")
		speed = f.get("last_speed")
		heading = f.get("last_heading")
		on_ground = bool(f.get("last_on_ground"))
		pos_at = f.get("last_pos_at")
		source = "stale" if pos_at else "none"
		if pos_at:
			try:
				dt = get_datetime(pos_at)
				delta = (now - dt).total_seconds() / 60.0
				stale_minutes = int(max(0, delta))
				stale = stale_minutes >= STALE_THRESHOLD_MINUTES
			except Exception:
				stale = True

	def _iso(v: Any) -> Optional[str]:
		if not v:
			return None
		try:
			return get_datetime(v).isoformat()
		except Exception:
			try:
				return str(v)
			except Exception:
				return None

	return {
		"flight_schedule": f.get("flight_schedule"),
		"flight_number": f.get("flight_number"),
		"airline_iata": f.get("airline_iata"),
		"airline_icao": f.get("airline_icao"),
		"matched_callsign": matched_callsign,
		"flight_status": f.get("flight_status"),
		"departure_iata": f.get("departure_iata") or f.get("departure_icao"),
		"arrival_iata": f.get("arrival_iata") or f.get("arrival_icao"),
		"etd": _iso(f.get("etd")),
		"eta": _iso(f.get("eta")),
		"atd": _iso(f.get("atd")),
		"ata": _iso(f.get("ata")),
		"aircraft_type": f.get("aircraft_type"),
		"registration": f.get("registration"),
		"position": {
			"lat": float(lat) if lat is not None else None,
			"lon": float(lon) if lon is not None else None,
			"altitude_m": float(alt) if alt is not None else None,
			"speed_kmh": float(speed) if speed is not None else None,
			"heading": float(heading) if heading is not None else None,
			"on_ground": on_ground,
			"position_at": _iso(pos_at),
			"source": source,
			"stale": stale,
			"stale_minutes": stale_minutes,
		},
		"shipments": f.get("shipments") or [],
		"master_awbs": sorted(list(f.get("master_awbs") or [])),
	}


def _airport_or_unloco_coords(code: Optional[str]) -> Optional[Tuple[float, float]]:
	"""Resolve a port/airport identifier to (lat, lon) by checking UNLOCO then Airport Master."""
	if not code:
		return None
	for doctype, lat_field, lon_field in (
		("UNLOCO", "latitude", "longitude"),
		("Airport Master", "latitude", "longitude"),
	):
		try:
			row = frappe.db.get_value(doctype, code, [lat_field, lon_field], as_dict=True)
		except Exception:
			row = None
		if row and row.get(lat_field) is not None and row.get(lon_field) is not None:
			try:
				lat = float(row[lat_field])
				lon = float(row[lon_field])
			except Exception:
				continue
			if lat == 0.0 and lon == 0.0:
				continue
			return (lat, lon)
	return None


def _bbox_for_air_shipment(doc, fs: Dict[str, Any], padding_deg: float = 5.0) -> Optional[Dict[str, float]]:
	"""Compute an OpenSky bounding box (lamin/lomin/lamax/lomax) around the shipment's corridor.

	We try the Air Shipment's origin/destination ports first, falling back to
	the Flight Schedule's IATA codes via Airport Master.  Padding is generous
	(~500 km at 5°) so the in-flight aircraft sits well inside the bbox even if
	winds push it off the great-circle.  Returns ``None`` if no usable coords
	are available so the caller can fall back to the global query.
	"""
	candidates: List[Tuple[float, float]] = []
	for code in (
		getattr(doc, "origin_port", None),
		getattr(doc, "destination_port", None),
		fs.get("departure_iata"),
		fs.get("arrival_iata"),
	):
		c = _airport_or_unloco_coords(code)
		if c:
			candidates.append(c)
	if not candidates:
		return None
	lats = [c[0] for c in candidates]
	lons = [c[1] for c in candidates]
	lamin = max(-90.0, min(lats) - padding_deg)
	lamax = min(90.0, max(lats) + padding_deg)
	lomin = max(-180.0, min(lons) - padding_deg)
	lomax = min(180.0, max(lons) + padding_deg)
	# OpenSky rejects boxes that wrap the antimeridian; clamp width to <180°.
	if (lomax - lomin) > 350.0:
		return None
	return {"lamin": lamin, "lomin": lomin, "lamax": lamax, "lomax": lomax}


def _resolve_air_shipment_flight(doc) -> Optional[Dict[str, Any]]:
	"""Resolve the Flight Schedule + airline metadata for a single Air Shipment.

	Returns ``None`` when the Air Shipment is not linked to a Master AWB or the
	Master AWB has no Flight Schedule attached.
	"""
	if not doc:
		return None
	master_awb = getattr(doc, "master_awb", None)
	if not master_awb:
		return None
	mawb = frappe.db.get_value(
		"Master Air Waybill",
		master_awb,
		["name", "master_awb_no", "airline", "flight_no", "flight_schedule"],
		as_dict=True,
	)
	if not mawb or not mawb.get("flight_schedule"):
		return None
	fs = frappe.db.get_value(
		"Flight Schedule",
		mawb["flight_schedule"],
		[
			"name", "flight_number", "airline_iata", "airline_icao",
			"flight_status", "departure_iata", "arrival_iata",
			"departure_time_scheduled", "arrival_time_scheduled",
			"latitude", "longitude", "altitude_meters", "speed_kmh",
			"heading", "is_on_ground", "last_position_update",
			"aircraft_type", "registration", "data_source",
		],
		as_dict=True,
	)
	if not fs:
		return None
	return {"mawb": mawb, "fs": fs}


@frappe.whitelist()
def get_aircraft_position_for_map(air_shipment: str) -> Dict[str, Any]:
	"""Return the latest position for the flight linked to ``air_shipment``.

	Shape mirrors ``goconnect.api.sea.get_vessel_position_for_map``
	so the dashboard route map can drop a marker the same way.  Server-side
	cache is 60 seconds keyed by the resolved callsign so multiple users open
	on the same shipment don't multiply OpenSky calls.
	"""
	if not air_shipment:
		return {"success": False, "message": _("Air Shipment is required.")}
	if not frappe.db.exists("Air Shipment", air_shipment):
		return {"success": False, "message": _("Air Shipment not found.")}
	if not frappe.has_permission("Air Shipment", "read", doc=air_shipment):
		frappe.throw(_("Not permitted to read this Air Shipment."), frappe.PermissionError)

	doc = frappe.get_doc("Air Shipment", air_shipment)
	resolved = _resolve_air_shipment_flight(doc)
	if not resolved:
		return {
			"success": False,
			"message": _("This Air Shipment is not linked to a Flight Schedule via its Master AWB."),
		}
	fs = resolved["fs"]
	mawb = resolved["mawb"]

	try:
		settings = frappe.get_cached_doc("GoConnect Settings")
	except Exception:
		settings = None

	provider_status = "live"
	provider_error: Optional[str] = None

	if not settings or not getattr(settings, "flight_enable_realtime_tracking", 0):
		provider_status = "disabled"
	else:
		# Non-blocking: enqueue a background refresh that hits OpenSky.  The
		# foreground response always reads the persisted Flight Schedule row, so
		# the dashboard never waits on a slow third-party API call.  The 60s
		# auto-refresh on the badge picks up the new position on the next tick.
		recorded_at = fs.get("last_position_update")
		needs_refresh = True
		if recorded_at:
			try:
				age = (now_datetime() - get_datetime(recorded_at)).total_seconds()
				# Don't bother re-queuing if we have a position from the last 45s.
				if age < 45:
					needs_refresh = False
			except Exception:
				needs_refresh = True
		if needs_refresh:
			# Cache-key throttle: only enqueue once per minute per FS so back-to-back
			# page loads / 60s polls don't queue a flood of jobs.
			enqueue_lock_key = "logistics:af_live_enqueue:" + str(fs.get("name") or "")
			if not frappe.cache().get_value(enqueue_lock_key):
				try:
					frappe.cache().set_value(enqueue_lock_key, "1", expires_in_sec=60)
					frappe.enqueue(
						"logistics.air_freight.api.live_flight_tracking.refresh_air_shipment_flight_position",
						queue="short",
						timeout=120,
						air_shipment=air_shipment,
						now=False,
						enqueue_after_commit=False,
					)
					provider_status = "queued"
				except Exception:
					# Enqueue failure is non-fatal — we still serve persisted data.
					pass

	now = now_datetime()

	# Always read persisted Flight Schedule data for the foreground response.
	lat = fs.get("latitude")
	lon = fs.get("longitude")
	alt = fs.get("altitude_meters")
	speed = fs.get("speed_kmh")
	heading = fs.get("heading")
	on_ground = bool(fs.get("is_on_ground"))
	recorded_at = fs.get("last_position_update")
	source = "stale" if recorded_at else "none"
	stale_minutes: Optional[int] = None
	if recorded_at:
		try:
			stale_minutes = int(max(0, (now - get_datetime(recorded_at)).total_seconds() / 60.0))
			# Treat very fresh data (<2 min) as live for the UI.
			if stale_minutes is not None and stale_minutes < 2:
				source = "live"
		except Exception:
			stale_minutes = None

	# Lat/lon may be 0/0 placeholders from the Flight Schedule seed — treat as no fix.
	if lat is None or lon is None or (float(lat) == 0.0 and float(lon) == 0.0 and source != "live"):
		# Surface the most recent background refresh outcome so the badge can
		# explain *why* there's no fix (unreachable / no_match / disabled / ...).
		refresh = _read_refresh_status(air_shipment) or {}
		rstatus = refresh.get("status")
		rmsg = refresh.get("message") or ""
		if rstatus == "unreachable":
			provider_status = "unreachable"
			msg = rmsg or _("OpenSky is unreachable from this server.")
		elif rstatus == "no_match":
			provider_status = "no_match"
			msg = rmsg or _("No ADS-B fix for this flight right now.")
		elif rstatus == "no_callsign":
			provider_status = "no_callsign"
			msg = rmsg or _("Could not derive an ADS-B callsign.")
		elif rstatus == "disabled":
			provider_status = "disabled"
			msg = rmsg or _("Real-time tracking is disabled.")
		elif rstatus in ("provider_error", "db_error", "error"):
			provider_status = "error"
			msg = rmsg or _("Background refresh failed.")
		elif provider_status == "queued":
			msg = _("Fetching live position in the background — retrying in 60s.")
		else:
			msg = _("No position fix available yet.")
		out_no_fix: Dict[str, Any] = {
			"success": False,
			"message": msg,
			"provider": "OpenSky Network",
			"provider_status": provider_status,
			"provider_error": provider_error or rmsg or None,
			"refresh_status": rstatus,
			"flight_schedule": fs.get("name"),
			"flight_number": fs.get("flight_number"),
			"flight_status": fs.get("flight_status"),
			"departure_iata": fs.get("departure_iata"),
			"arrival_iata": fs.get("arrival_iata"),
			"master_awb": mawb.get("name"),
			"master_awb_no": mawb.get("master_awb_no"),
		}
		return out_no_fix

	def _iso(v: Any) -> Optional[str]:
		if not v:
			return None
		try:
			return get_datetime(v).isoformat()
		except Exception:
			return str(v)

	flight_number = fs.get("flight_number") or mawb.get("flight_no") or ""
	label_bits = []
	if flight_number:
		label_bits.append(str(flight_number))
	if fs.get("departure_iata") and fs.get("arrival_iata"):
		label_bits.append("{0}→{1}".format(fs["departure_iata"], fs["arrival_iata"]))
	label = " · ".join(label_bits) or "Aircraft"

	out: Dict[str, Any] = {
		"success": True,
		"lat": float(lat),
		"lon": float(lon),
		"label": label,
		"flight_number": flight_number,
		"flight_schedule": fs.get("name"),
		"flight_status": fs.get("flight_status"),
		"departure_iata": fs.get("departure_iata"),
		"arrival_iata": fs.get("arrival_iata"),
		"etd": _iso(fs.get("departure_time_scheduled")),
		"eta": _iso(fs.get("arrival_time_scheduled")),
		"altitude_m": float(alt) if alt is not None else None,
		"speed_kmh": float(speed) if speed is not None else None,
		"heading": float(heading) if heading is not None else None,
		"on_ground": on_ground,
		"recorded_at": _iso(recorded_at),
		"stale_minutes": stale_minutes,
		"source": source,
		"provider": fs.get("data_source") or "OpenSky Network",
		"provider_status": provider_status,
		"provider_error": provider_error,
		"master_awb": mawb.get("name"),
		"master_awb_no": mawb.get("master_awb_no"),
		"aircraft_type": fs.get("aircraft_type"),
		"registration": fs.get("registration"),
	}

	return out


def _refresh_status_cache_key(air_shipment: str) -> str:
	return "logistics:af_refresh_status:" + str(air_shipment or "")


def _set_refresh_status(air_shipment: str, status: str, message: str = "") -> None:
	"""Cache the last background-refresh outcome so the foreground endpoint can surface it."""
	try:
		frappe.cache().set_value(
			_refresh_status_cache_key(air_shipment),
			json.dumps({"status": status, "message": message[:240]}),
			expires_in_sec=900,
		)
	except Exception:
		pass


def _read_refresh_status(air_shipment: str) -> Dict[str, Any]:
	try:
		raw = frappe.cache().get_value(_refresh_status_cache_key(air_shipment))
		if raw:
			return json.loads(raw)
	except Exception:
		pass
	return {}


def _fetch_states_with_fallback(
	candidates: List[str],
	bbox: Optional[Dict[str, float]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], Optional[str], Optional[str], bool]:
	"""Try every configured live-tracking provider in order and return the first hit.

	Provider order:
	  1. OpenSky Network (if enabled in GoConnect Settings ▸ Flight tab)
	  2. adsb.lol  (no-auth public ADS-B aggregator)
	  3. adsb.fi   (no-auth public ADS-B aggregator)

	Returns ``(states_by_callsign, provider_label_used, last_error_message, any_responded)``.
	``any_responded`` is True if at least one provider answered HTTP 200 even
	with an empty list — this lets callers tell "no ADS-B fix" (no_match) from
	"all providers unreachable" (unreachable).
	"""
	if not candidates:
		return {}, None, None, False

	last_err: Optional[str] = None
	provider_attempted: Optional[str] = None
	any_responded = False

	# --- 1. OpenSky --------------------------------------------------------
	try:
		settings = frappe.get_cached_doc("GoConnect Settings")
	except Exception:
		settings = None
	opensky_enabled = bool(settings and getattr(settings, "opensky_enabled", 0))

	if opensky_enabled:
		provider_attempted = "OpenSky Network"
		try:
			from logistics.air_freight.flight_schedules.opensky.connector import OpenSkyConnector
			connector = OpenSkyConnector()
			states = connector.get_states_for_callsigns(
				candidates, bbox=bbox, timeout=20
			) or {}
			any_responded = True  # call succeeded (even if no match)
			if states:
				return states, "OpenSky Network", None, True
		except Exception as e_open:
			last_err = str(e_open)
			frappe.log_error(
				title="live-flight-tracking - OpenSky fetch failed",
				message=frappe.get_traceback(),
			)

	# --- 2. Free no-auth ADS-B aggregators (adsb.lol → adsb.fi) -----------
	try:
		from logistics.air_freight.flight_schedules.adsb_aggregator.connector import (
			AdsbAggregatorConnector,
		)
		connector = AdsbAggregatorConnector()
		states = connector.get_states_for_callsigns(candidates, timeout=10) or {}
		# If at least one provider answered (even with no `ac`), treat that as
		# a successful network response.  The connector only raises when *every*
		# provider failed at the network layer.
		any_responded = True
		if states:
			return states, connector.last_provider_used or "adsb.lol", None, True
		provider_attempted = connector.last_provider_used or "adsb.lol / adsb.fi"
	except Exception as e_adsb:
		last_err = str(e_adsb)
		frappe.log_error(
			title="live-flight-tracking - adsb.lol/fi fetch failed",
			message=frappe.get_traceback(),
		)

	return {}, provider_attempted, last_err, any_responded


def refresh_air_shipment_flight_position(air_shipment: str) -> Dict[str, Any]:
	"""Background job: hit OpenSky for one Air Shipment and persist the fix.

	Designed to be enqueued from ``get_aircraft_position_for_map`` so the user-
	facing endpoint never waits on OpenSky.  Failures are logged but never
	raised — this job runs on a best-effort basis.  The outcome is cached so
	the next foreground poll can surface a useful message in the badge.
	"""
	result: Dict[str, Any] = {"air_shipment": air_shipment, "updated": 0}
	try:
		if not air_shipment or not frappe.db.exists("Air Shipment", air_shipment):
			_set_refresh_status(air_shipment, "not_found", "Air Shipment not found.")
			return result
		doc = frappe.get_doc("Air Shipment", air_shipment)
		resolved = _resolve_air_shipment_flight(doc)
		if not resolved:
			_set_refresh_status(
				air_shipment, "no_link",
				"This Air Shipment is not linked to a Flight Schedule via its Master AWB."
			)
			return result
		fs = resolved["fs"]
		try:
			settings = frappe.get_cached_doc("GoConnect Settings")
		except Exception:
			settings = None
		if not settings or not getattr(settings, "flight_enable_realtime_tracking", 0):
			_set_refresh_status(air_shipment, "disabled", "Real-time tracking is disabled.")
			return result
		if not getattr(settings, "opensky_enabled", 0):
			_set_refresh_status(air_shipment, "disabled", "OpenSky provider is disabled.")
			return result

		iata_to_icao = _load_iata_to_icao_map()
		candidates = _callsign_candidates(
			fs.get("flight_number"),
			fs.get("airline_iata"),
			fs.get("airline_icao"),
			iata_to_icao,
		)
		if not candidates:
			_set_refresh_status(
				air_shipment, "no_callsign",
				"Could not derive an ADS-B callsign for {0}.".format(fs.get("flight_number") or "this flight"),
			)
			return result

		bbox = _bbox_for_air_shipment(doc, fs)

		states, provider_used, fetch_err_msg, any_responded = _fetch_states_with_fallback(
			candidates, bbox=bbox
		)

		if not states and not any_responded:
			# Every provider failed at the network layer.
			low = (fetch_err_msg or "").lower()
			if "timeout" in low or "timed out" in low or "unreachable" in low or not fetch_err_msg:
				_set_refresh_status(
					air_shipment, "unreachable",
					"All live-tracking providers are unreachable from this server. "
					"Check outbound firewall for opensky-network.org / api.adsb.lol / opendata.adsb.fi.",
				)
			else:
				_set_refresh_status(air_shipment, "provider_error", fetch_err_msg)
			return result

		state = None
		matched = None
		for cs in candidates:
			if cs in states:
				state = states[cs]
				matched = cs
				break
		if not state:
			_set_refresh_status(
				air_shipment, "no_match",
				"Tried {0} but no ADS-B fix for {1} right now (callsigns: {2}). The aircraft may be on the ground or out of receiver coverage.".format(
					provider_used or "providers",
					fs.get("flight_number") or "this flight",
					", ".join(candidates[:3]),
				),
			)
			return result

		updates: Dict[str, Any] = {}
		if state.get("latitude") is not None:
			updates["latitude"] = state["latitude"]
		if state.get("longitude") is not None:
			updates["longitude"] = state["longitude"]
		if state.get("altitude_meters") is not None:
			updates["altitude_meters"] = state["altitude_meters"]
		if state.get("speed_kmh") is not None:
			updates["speed_kmh"] = state["speed_kmh"]
		if state.get("heading") is not None:
			updates["heading"] = state["heading"]
		if state.get("vertical_speed_ms") is not None:
			updates["vertical_speed_ms"] = state["vertical_speed_ms"]
		if state.get("is_on_ground") is not None:
			updates["is_on_ground"] = 1 if state["is_on_ground"] else 0
		pos_at = state.get("last_position_update") or state.get("last_contact")
		if pos_at:
			updates["last_position_update"] = pos_at
		updates["last_updated"] = now_datetime()
		updates["sync_status"] = "Synced"
		updates["data_source"] = state.get("data_source") or provider_used or "OpenSky Network"
		try:
			frappe.db.set_value("Flight Schedule", fs.get("name"), updates, update_modified=False)
			frappe.db.commit()
			result["updated"] = 1
			result["matched_callsign"] = matched
			result["provider"] = provider_used
			_set_refresh_status(
				air_shipment, "ok",
				"Updated from {0} via callsign {1}.".format(provider_used or "provider", matched),
			)
		except Exception:
			frappe.log_error(
				title="refresh_air_shipment_flight_position - DB write failed",
				message=frappe.get_traceback(),
			)
			_set_refresh_status(air_shipment, "db_error", "Failed to persist position.")
	except Exception as e_top:
		frappe.log_error(
			title="refresh_air_shipment_flight_position - top-level",
			message=frappe.get_traceback(),
		)
		_set_refresh_status(air_shipment, "error", str(e_top))
	return result


@frappe.whitelist()
def get_live_operational_flights(
	job_status_filter: Optional[str] = None,
	filter_user: Optional[str] = None,
	traffic: Optional[str] = None,
	airlines: Optional[Any] = None,
) -> Dict[str, Any]:
	"""Return live + persisted positions of every operational flight.

	"Operational" means: a Flight Schedule that is referenced by a Master AWB
	which is itself referenced by an Air Shipment matching the same filters as
	the rest of the Air Freight Operations Dashboard.  Draft Air Shipments
	(``docstatus = 0``) are included; only Cancelled shipments are excluded.
	"""
	company = (session_company_context().get("company") or "").strip() or None
	traffic_val = parse_traffic(traffic)

	airline_codes = parse_multi_link_param(airlines)
	if airline_codes:
		airline_codes = sanitize_link_values(airline_codes, "Airline")

	rows = _fetch_operational_rows(job_status_filter, filter_user, company, airline_codes)
	flights = _aggregate_by_flight_schedule(rows)
	flights = _filter_by_traffic(flights, traffic_val)

	live_result = _try_fetch_live_states(flights)
	states = live_result.get("states") or {}

	now = now_datetime()
	payload_flights: List[Dict[str, Any]] = []
	live_count = 0
	stale_count = 0
	no_pos_count = 0
	for f in flights.values():
		p = _serialize_flight(f, states, now)
		src = (p.get("position") or {}).get("source") or "none"
		if src == "live":
			live_count += 1
		elif src == "stale":
			stale_count += 1
		else:
			no_pos_count += 1
		payload_flights.append(p)

	payload_flights.sort(key=lambda x: (
		0 if (x.get("position") or {}).get("source") == "live" else
		1 if (x.get("position") or {}).get("source") == "stale" else 2,
		(x.get("flight_number") or "").upper(),
	))

	return {
		"refreshed_at": now.isoformat(),
		"provider": live_result.get("provider"),
		"provider_status": live_result.get("provider_status"),
		"provider_error": live_result.get("error"),
		"total_flights": len(payload_flights),
		"live_count": live_count,
		"stale_count": stale_count,
		"no_position_count": no_pos_count,
		"stale_threshold_minutes": STALE_THRESHOLD_MINUTES,
		"flights": payload_flights,
	}
