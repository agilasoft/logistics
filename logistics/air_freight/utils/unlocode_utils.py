"""
UNLOCO / UNLOCODE auto-population helpers.
Desk API returns {status, message?, data} so logistics/doctype/unloco/unloco.js can apply fields including coordinates.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import frappe
from frappe import _
from frappe.utils import cint

_COORD_RE = re.compile(
	r"^\s*(?P<lat_d>\d{2})(?P<lat_m>\d{2})(?P<lat_h>[NS])\s+(?P<lon_d>\d{3})(?P<lon_m>\d{2})(?P<lon_h>[EW])\s*$",
	re.IGNORECASE,
)


def parse_un_coordinates(coord: str) -> tuple:
	"""
	Parse UN/LOCODE coordinate string to (latitude, longitude) or (None, None).
	Accepts standard form e.g. 4230N 00131E, 3342N 11824W (flexible whitespace, case).
	"""
	if not coord or not isinstance(coord, str):
		return None, None
	s = " ".join(coord.strip().upper().split())
	m = _COORD_RE.match(s)
	if not m:
		return None, None
	lat = int(m.group("lat_d")) + int(m.group("lat_m")) / 60.0
	if m.group("lat_h").upper() == "S":
		lat = -lat
	lon = int(m.group("lon_d")) + int(m.group("lon_m")) / 60.0
	if m.group("lon_h").upper() == "W":
		lon = -lon
	return lat, lon


@frappe.whitelist()
def populate_unlocode_details(unlocode: str, doc: Any = None, refresh_external: bool = False) -> Dict[str, Any]:
	"""
	Return {status, message?, data} for desk; data is a flat field dict for UNLOCO.

	:param refresh_external: If True, merge DataHub (and other external) fields over stored DB
		values so e.g. Function-derived checkboxes update on bulk refresh.
	"""
	try:
		if not unlocode:
			return {"status": "warning", "message": _("No UNLOCO code provided"), "data": {}}

		code = unlocode.strip().upper()
		if len(code) != 5:
			return {"status": "error", "message": _("UNLOCO code must be exactly 5 characters"), "data": {}}

		unlocode_data = get_unlocode_data(code, refresh_external=bool(cint(refresh_external)))

		if unlocode_data:
			unlocode_data.setdefault("unlocode", code)
			populated_fields = populate_fields_from_data(unlocode_data)
			if doc:
				update_document_fields(doc, populated_fields)
			return {"status": "success", "data": populated_fields}

		basic_fields = populate_basic_details_from_code(code)
		if doc:
			update_document_fields(doc, basic_fields)
		if basic_fields:
			return {
				"status": "warning",
				"message": _("Limited details inferred from code; coordinates may be missing."),
				"data": basic_fields,
			}
		return {"status": "warning", "message": _("No UNLOCO data found for this code."), "data": {}}

	except Exception as e:
		frappe.log_error(frappe.get_traceback(), f"UNLOCO populate: {e!s}")
		return {"status": "error", "message": str(e), "data": {}}


def unwrap_populate_result(result: Any) -> Dict[str, Any]:
	"""Normalize populate_unlocode_details return value to a flat field dict for Document setattr."""
	if not result:
		return {}
	if isinstance(result, dict) and "data" in result and isinstance(result["data"], dict):
		return dict(result["data"])
	if isinstance(result, dict) and "status" not in result:
		return dict(result)
	return {}


def _is_blank_str(val: Any) -> bool:
	return val is None or (isinstance(val, str) and not val.strip())


_OVERLAY_FILL_KEYS = (
	"location_name",
	"country",
	"country_code",
	"subdivision",
	"city",
	"location_type",
	"iata_code",
	"icao_code",
	"timezone",
	"currency",
	"language",
	"utc_offset",
	"operating_hours",
	"description",
	"status",
	"data_source",
)

# Keys refreshed from DataHub / ``get_unlocode_from_database`` when forcing an update (Update All).
_EXTERNAL_REFRESH_KEYS = (
	"location_name",
	"country",
	"country_code",
	"subdivision",
	"city",
	"location_type",
	"iata_code",
	"timezone",
	"currency",
	"language",
	"utc_offset",
	"operating_hours",
	"description",
	"status",
	"data_source",
	"latitude",
	"longitude",
	"has_post",
	"has_customs",
	"has_unload",
	"has_airport",
	"has_rail",
	"has_road",
	"has_store",
	"has_terminal",
	"has_discharge",
	"has_seaport",
	"has_outport",
)


def _merge_external_refresh(base: Dict[str, Any], fresh: Dict[str, Any]) -> None:
	"""Overwrite ``base`` fields from ``fresh`` for codelist-driven data (e.g. Function checkboxes)."""
	for key in _EXTERNAL_REFRESH_KEYS:
		if key not in fresh:
			continue
		val = fresh[key]
		if key.startswith("has_"):
			if val is None:
				continue
			base[key] = 1 if val else 0
			continue
		if key in ("latitude", "longitude"):
			base[key] = val
			continue
		if val is None:
			continue
		base[key] = val


def _merge_unlocode_overlay(base: Dict[str, Any], overlay: Optional[Dict[str, Any]]) -> None:
	"""Fill blank string / None scalar fields in base from overlay (e.g. DataHub after a sparse DB row)."""
	if not overlay:
		return
	for key in _OVERLAY_FILL_KEYS:
		if key not in overlay:
			continue
		val = overlay[key]
		if val is None:
			continue
		if isinstance(val, str) and not val.strip():
			continue
		if _is_blank_str(base.get(key)):
			base[key] = val
	if overlay.get("latitude") is not None and base.get("latitude") is None:
		base["latitude"] = overlay["latitude"]
	if overlay.get("longitude") is not None and base.get("longitude") is None:
		base["longitude"] = overlay["longitude"]
	for key in (
		"has_post",
		"has_customs",
		"has_unload",
		"has_airport",
		"has_rail",
		"has_road",
		"has_store",
		"has_terminal",
		"has_discharge",
		"has_seaport",
		"has_outport",
	):
		if key in overlay and overlay[key] is not None and base.get(key) is None:
			base[key] = overlay[key]


def _backfill_country_from_unlocode_prefix(code: str, base: Dict[str, Any]) -> None:
	"""If country or country_code still empty, derive from ISO2 prefix of the 5-letter UN/LOCODE."""
	if not _is_blank_str(base.get("country")) and not _is_blank_str(base.get("country_code")):
		return
	if len(code) != 5:
		return
	info = enrich_country_info(code[:2])
	if _is_blank_str(base.get("country_code")) and info.get("country_code"):
		base["country_code"] = info["country_code"]
	if _is_blank_str(base.get("country")) and info.get("country"):
		base["country"] = info["country"]
	if _is_blank_str(base.get("currency")) and info.get("currency"):
		base["currency"] = info["currency"]
	if _is_blank_str(base.get("language")) and info.get("language"):
		base["language"] = info["language"]


def _unloco_db_row_to_dict(existing: Any) -> Dict[str, Any]:
	return {
		"location_name": existing[1] or "",
		"country": existing[2] or "",
		"country_code": existing[3] or "",
		"subdivision": existing[4] or "",
		"city": existing[5] or "",
		"location_type": existing[6] or "",
		"iata_code": existing[7] or "",
		"icao_code": existing[8] or "",
		"timezone": existing[9] or "",
		"currency": existing[10] or "",
		"language": existing[11] or "",
		"utc_offset": existing[12] or "",
		"operating_hours": existing[13] or "",
		"latitude": existing[14],
		"longitude": existing[15],
		"description": existing[16] or "",
		"has_post": existing[17],
		"has_customs": existing[18],
		"has_unload": existing[19],
		"has_airport": existing[20],
		"has_rail": existing[21],
		"has_road": existing[22],
		"has_store": existing[23],
		"has_terminal": existing[24],
		"has_discharge": existing[25],
		"has_seaport": existing[26],
		"has_outport": existing[27],
	}


def get_unlocode_data(unlocode: str, refresh_external: bool = False) -> Optional[Dict[str, Any]]:
	try:
		code = unlocode.strip().upper()
		existing = frappe.db.get_value(
			"UNLOCO",
			{"unlocode": code},
			[
				"name",
				"location_name",
				"country",
				"country_code",
				"subdivision",
				"city",
				"location_type",
				"iata_code",
				"icao_code",
				"timezone",
				"currency",
				"language",
				"utc_offset",
				"operating_hours",
				"latitude",
				"longitude",
				"description",
				"has_post",
				"has_customs",
				"has_unload",
				"has_airport",
				"has_rail",
				"has_road",
				"has_store",
				"has_terminal",
				"has_discharge",
				"has_seaport",
				"has_outport",
			],
		)

		if existing:
			base = _unloco_db_row_to_dict(existing)
			if refresh_external:
				fresh = get_unlocode_from_database(code)
				if fresh:
					_merge_external_refresh(base, fresh)
				_backfill_country_from_unlocode_prefix(code, base)
				return base
			if _is_blank_str(base.get("country")) or _is_blank_str(base.get("country_code")):
				fresh = get_unlocode_from_database(code)
				_merge_unlocode_overlay(base, fresh)
				_backfill_country_from_unlocode_prefix(code, base)
			return base

		return get_unlocode_from_database(unlocode)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), f"UNLOCO get_unlocode_data: {e!s}")
		return None


def get_unlocode_from_database(unlocode: str) -> Optional[Dict[str, Any]]:
	try:
		try:
			from logistics.air_freight.utils.datahub_unlocode import get_unlocode_from_datahub

			dh = get_unlocode_from_datahub(unlocode)
			if dh:
				dh.setdefault("unlocode", unlocode.upper())
				return dh
		except ImportError:
			pass

		sample_data = _sample_unlocode_rows()
		u = unlocode.upper()
		if u in sample_data:
			return dict(sample_data[u])

		return infer_unlocode_data(u)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), f"UNLOCO get_unlocode_from_database: {e!s}")
		return None


def _sample_unlocode_rows() -> Dict[str, Dict[str, Any]]:
	return {
		"USLAX": {
			"location_name": "Los Angeles International Airport",
			"country": "United States",
			"country_code": "US",
			"subdivision": "California",
			"city": "Los Angeles",
			"location_type": "Airport",
			"iata_code": "LAX",
			"icao_code": "KLAX",
			"timezone": "America/Los_Angeles",
			"currency": "USD",
			"language": "en",
			"utc_offset": "-08:00",
			"operating_hours": "24/7",
			"latitude": 33.9425,
			"longitude": -118.4081,
			"description": "Los Angeles International Airport",
		},
		"USJFK": {
			"location_name": "John F. Kennedy International Airport",
			"country": "United States",
			"country_code": "US",
			"subdivision": "New York",
			"city": "New York",
			"location_type": "Airport",
			"iata_code": "JFK",
			"icao_code": "KJFK",
			"timezone": "America/New_York",
			"currency": "USD",
			"language": "en",
			"latitude": 40.6413,
			"longitude": -73.7781,
			"description": "John F. Kennedy International Airport",
		},
		"GBLHR": {
			"location_name": "London Heathrow Airport",
			"country": "United Kingdom",
			"country_code": "GB",
			"subdivision": "England",
			"city": "London",
			"location_type": "Airport",
			"iata_code": "LHR",
			"icao_code": "EGLL",
			"timezone": "Europe/London",
			"currency": "GBP",
			"language": "en",
			"latitude": 51.47,
			"longitude": -0.4543,
			"description": "London Heathrow Airport",
		},
	}


def infer_unlocode_data(unlocode: str) -> Optional[Dict[str, Any]]:
	if len(unlocode) != 5:
		return None
	country_code = unlocode[:2].upper()
	ci = enrich_country_info(country_code)
	li = infer_location_details(unlocode, country_code, unlocode[2:])
	if not li:
		return None
	out = {**ci, **li}
	out.setdefault("unlocode", unlocode.upper())
	if not out.get("location_name"):
		out["location_name"] = unlocode.upper()
	return out


def get_country_info(country_code: str) -> Dict[str, str]:
	mapping = {
		"US": {"country": "United States", "country_code": "US", "currency": "USD", "language": "en"},
		"GB": {"country": "United Kingdom", "country_code": "GB", "currency": "GBP", "language": "en"},
		"DE": {"country": "Germany", "country_code": "DE", "currency": "EUR", "language": "de"},
		"NL": {"country": "Netherlands", "country_code": "NL", "currency": "EUR", "language": "nl"},
		"SG": {"country": "Singapore", "country_code": "SG", "currency": "SGD", "language": "en"},
	}
	cc = (country_code or "").strip().upper()
	return dict(mapping.get(cc, {}))


def enrich_country_info(country_code: str) -> Dict[str, str]:
	"""
	Resolve ISO-3166 alpha-2 to display fields. Uses built-in map first, then Frappe Country.
	Always returns country_code when input is a valid 2-letter code (even if name is unknown).
	"""
	cc = (country_code or "").strip().upper()
	if len(cc) != 2:
		return {}
	out = dict(get_country_info(cc))
	out.setdefault("country_code", cc)
	if not out.get("country"):
		try:
			name = frappe.db.get_value("Country", {"code": cc}, "country_name")
			if name:
				out["country"] = name
		except Exception:
			pass
	if not out.get("country"):
		out["country"] = ""
	out.setdefault("currency", "")
	out.setdefault("language", "")
	return out


def infer_location_details(unlocode: str, country_code: str, location_code: str) -> Dict[str, Any]:
	air = {
		"LAX",
		"JFK",
		"MIA",
		"ORD",
		"LHR",
		"LGW",
		"CDG",
		"FRA",
		"AMS",
		"SIN",
	}
	if location_code in air:
		return {
			"location_type": "Airport",
			"iata_code": location_code,
			"timezone": _tz_for_country(country_code),
			"description": f"Inferred airport for {unlocode}",
		}
	return {
		"location_type": "Other",
		"timezone": _tz_for_country(country_code),
		"description": f"Inferred location for {unlocode}",
	}


def _tz_for_country(country_code: str) -> str:
	return {
		"US": "America/New_York",
		"GB": "Europe/London",
		"DE": "Europe/Berlin",
		"NL": "Europe/Amsterdam",
		"SG": "Asia/Singapore",
	}.get(country_code, "UTC")


def populate_fields_from_data(unlocode_data: Dict[str, Any]) -> Dict[str, Any]:
	out: Dict[str, Any] = {}
	if unlocode_data.get("location_name") is not None:
		out["location_name"] = unlocode_data["location_name"]
	if unlocode_data.get("country") is not None:
		out["country"] = unlocode_data["country"]
	if unlocode_data.get("country_code") is not None:
		out["country_code"] = unlocode_data["country_code"]
	if unlocode_data.get("subdivision") is not None:
		out["subdivision"] = unlocode_data["subdivision"]
	if unlocode_data.get("city") is not None:
		out["city"] = unlocode_data["city"]
	if unlocode_data.get("location_type") is not None:
		out["location_type"] = unlocode_data["location_type"]
	if unlocode_data.get("iata_code") is not None:
		out["iata_code"] = unlocode_data["iata_code"]
	if unlocode_data.get("icao_code") is not None:
		out["icao_code"] = unlocode_data["icao_code"]
	if unlocode_data.get("timezone") is not None:
		out["timezone"] = unlocode_data["timezone"]
	if unlocode_data.get("currency") is not None:
		out["currency"] = unlocode_data["currency"]
	if unlocode_data.get("language") is not None:
		out["language"] = unlocode_data["language"]
	if unlocode_data.get("utc_offset") is not None:
		out["utc_offset"] = unlocode_data["utc_offset"]
	if unlocode_data.get("operating_hours") is not None:
		out["operating_hours"] = unlocode_data["operating_hours"]
	# Coordinates: use explicit None checks (0.0 is valid latitude)
	if "latitude" in unlocode_data and unlocode_data["latitude"] is not None:
		out["latitude"] = unlocode_data["latitude"]
	if "longitude" in unlocode_data and unlocode_data["longitude"] is not None:
		out["longitude"] = unlocode_data["longitude"]
	if unlocode_data.get("description") is not None:
		out["description"] = unlocode_data["description"]
	if unlocode_data.get("status") is not None:
		out["status"] = unlocode_data["status"]
	if unlocode_data.get("data_source") is not None:
		out["data_source"] = unlocode_data["data_source"]

	for key in (
		"has_post",
		"has_customs",
		"has_unload",
		"has_airport",
		"has_rail",
		"has_road",
		"has_store",
		"has_terminal",
		"has_discharge",
		"has_seaport",
		"has_outport",
	):
		if key in unlocode_data and unlocode_data[key] is not None:
			out[key] = 1 if unlocode_data[key] else 0

	return out


def populate_basic_details_from_code(unlocode: str) -> Dict[str, Any]:
	if len(unlocode) != 5:
		return {}
	cc = unlocode[:2].upper()
	info = enrich_country_info(cc)
	basic = {
		"location_name": unlocode.upper(),
		"country": info.get("country", ""),
		"country_code": info.get("country_code") or cc,
		"currency": info.get("currency", ""),
		"language": info.get("language", ""),
		"timezone": _tz_for_country(cc),
		"description": f"Transport location with UNLOCO code {unlocode}",
	}
	return basic


def update_document_fields(doc: Any, populated_fields: Dict[str, Any]) -> None:
	for field_name, field_value in populated_fields.items():
		if hasattr(doc, field_name):
			setattr(doc, field_name, field_value)
	doc.last_updated = frappe.utils.now()
