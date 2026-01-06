# apps/logistics/logistics/transport/routing.py
from __future__ import annotations

from math import radians, sin, cos, asin, sqrt
from typing import Any, Dict, Optional, Tuple
import json
import frappe
from frappe.utils.password import get_decrypted_password  # 🔐 for Password fields

try:
    import requests  # only used for OSRM/Mapbox/Google
except Exception:  # pragma: no cover
    requests = None  # type: ignore

__all__ = [
    "compute_leg_distance_time",
    "get_address_coords",
    "haversine_km",
    # compat
    "get_routing_settings",
    "route_leg",
]

# ==================== helpers ====================
def _has_field(doctype: str, fieldname: str) -> bool:
    try:
        meta = frappe.get_meta(doctype)
        return any(df.fieldname == fieldname for df in meta.fields)
    except Exception:
        return False

def _get_password(doctype: str, fieldnames: list[str]) -> Optional[str]:
    """Try to decrypt a Password field from a Single doctype (tries aliases in order)."""
    for fn in fieldnames:
        try:
            val = get_decrypted_password(doctype, doctype, fn, raise_exception=False)
            if val:
                return val
        except Exception:
            pass
    return None

def _get_setting(name: str, default=None):
    """
    Read a value from Transport Settings with tolerant alias lookups and site_config fallbacks.
    Special-cases Password fields to use get_decrypted_password.
    """
    alias_map = {
        "routing_provider": ["route_provider", "distance_time_provider"],
        "osrm_base_url": ["routing_osrm_base_url", "osrm_url", "osrm_server"],
        "default_speed_kmh": [
            "routing_default_speed_kmh",
            "avg_speed_kmh",
            "routing_default_avg_speed_kmh",
        ],
        "routing_timeout_sec": ["route_timeout_sec"],
        "routing_debug": ["route_debug"],

        # 🔐 Password fields (your DocType dump has these names)
        "google_api_key": ["routing_google_api_key", "google_api_key", "google_maps_api_key", "google_key", "maps_api_key"],
        "mapbox_access_token": ["routing_mapbox_api_key", "mapbox_access_token", "mapbox_token", "mapbox_api_key"],

        # plain text (optional)
        "mapbox_profile": ["mapbox_mode", "mapbox_route_profile"],
    }

    # Password-like settings first
    if name in ("google_api_key", "mapbox_access_token"):
        pw = _get_password("Transport Settings", alias_map.get(name, []))
        if pw:
            return pw
        # site_config fallbacks
        if hasattr(frappe, "conf") and hasattr(frappe.conf, "get"):
            if name == "google_api_key":
                for k in ("google_maps_api_key", "google_api_key", "maps_api_key"):
                    v = frappe.conf.get(k)
                    if v:
                        return v
            if name == "mapbox_access_token":
                for k in ("mapbox_access_token", "mapbox_token", "mapbox_api_key"):
                    v = frappe.conf.get(k)
                    if v:
                        return v
        return default

    # Non-password settings
    ts = None
    try:
        ts = frappe.get_single("Transport Settings")
    except Exception:
        ts = None

    if ts and hasattr(ts, name):
        return getattr(ts, name)

    if ts:
        for alias in alias_map.get(name, []):
            if hasattr(ts, alias):
                return getattr(ts, alias)

    # site_config backup for non-passwords
    if hasattr(frappe, "conf") and hasattr(frappe.conf, "get"):
        if name == "mapbox_profile":
            v = frappe.conf.get("mapbox_profile") or frappe.conf.get("mapbox_mode")
            if v:
                return v

    return default

def _coerce_float(val) -> Optional[float]:
    try:
        if val in (None, ""):
            return None
        return float(val)
    except Exception:
        return None

def _extract_lat_lon_from_geo(geo) -> Optional[Tuple[float, float]]:
    """Return (lat, lon) from GeoJSON or legacy dicts."""
    if not geo:
        return None

    # Legacy: {lat, lng}
    if isinstance(geo, dict) and "lat" in geo and "lng" in geo:
        lat = _coerce_float(geo.get("lat"))
        lon = _coerce_float(geo.get("lng"))
        return (lat, lon) if lat is not None and lon is not None else None

    # Parse JSON string
    if isinstance(geo, str):
        try:
            geo = json.loads(geo)
        except Exception:
            return None

    # FeatureCollection
    if isinstance(geo, dict) and geo.get("type") == "FeatureCollection":
        for f in (geo.get("features") or []):
            r = _extract_lat_lon_from_geo(f)
            if r:
                return r
        return None

    # Feature
    if isinstance(geo, dict) and geo.get("type") == "Feature" and geo.get("geometry"):
        return _extract_lat_lon_from_geo(geo.get("geometry"))

    # Geometry Point
    if isinstance(geo, dict) and geo.get("type") == "Point":
        coords = geo.get("coordinates") or []
        if isinstance(coords, (list, tuple)) and len(coords) >= 2:
            lon = _coerce_float(coords[0])
            lat = _coerce_float(coords[1])
            if lat is not None and lon is not None:
                return (lat, lon)

    return None

def get_address_coords(addr_name: str) -> Optional[Tuple[float, float]]:
    """
    STRICT: Use ONLY Address.custom_latitude / Address.custom_longitude.
    Ignore any geolocation (GeoJSON) or standard latitude/longitude fields.
    """
    if not addr_name:
        return None
    try:
        ad = frappe.get_doc("Address", addr_name)
    except Exception:
        return None

    lat = ad.get("custom_latitude")
    lon = ad.get("custom_longitude")

    try:
        if lat is None or lon is None:
            return None
        lat = float(lat)
        lon = float(lon)
    except Exception:
        return None

    # Basic validity checks (optional)
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    if lat == 0.0 and lon == 0.0:
        return None

    return (lat, lon)

# ==================== haversine ====================
def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0088
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2) ** 2
    c = 2 * asin(sqrt(a))
    return R * c

# ==================== providers (return (result, error)) ====================
def _route_osrm(start: Tuple[float, float], end: Tuple[float, float]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    base = (_get_setting("osrm_base_url") or "").strip().rstrip("/")
    if not base:
        return None, "OSRM base URL not set"
    if not requests:
        return None, "requests library unavailable"
    if "map.project-osrm.org" in base:
        base = "https://router.project-osrm.org"

    t = _get_setting("routing_timeout_sec", 10)
    try:
        t = float(t)
        if t <= 0:
            t = 10.0
    except Exception:
        t = 10.0

    s = f"{start[1]},{start[0]}"  # lon,lat
    e = f"{end[1]},{end[0]}"
    url = f"{base}/route/v1/driving/{s};{e}"
    params = {"overview": "full", "geometries": "polyline6"}

    try:
        r = requests.get(url, params=params, timeout=t)
        r.raise_for_status()
        js = r.json()
    except Exception as e:
        return None, f"OSRM request failed: {e}"

    routes = (js or {}).get("routes") or []
    if not routes:
        return None, "OSRM returned no routes"
    rt = routes[0]
    try:
        return {
            "distance_km": float(rt.get("distance", 0)) / 1000.0,
            "duration_min": float(rt.get("duration", 0)) / 60.0,
            "polyline": rt.get("geometry") or "",
            "provider": "OSRM",
            "raw": rt,
        }, None
    except Exception:
        return None, "OSRM parse error"

def _route_mapbox(start: Tuple[float, float], end: Tuple[float, float]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Mapbox Directions (metric)."""
    if not requests:
        return None, "requests library unavailable"

    token = _get_setting("mapbox_access_token")
    if not token:
        return None, "Mapbox token not set"

    profile = (_get_setting("mapbox_profile") or "driving").strip() or "driving"
    if profile not in ("driving", "driving-traffic", "walking", "cycling"):
        profile = "driving"

    t = _get_setting("routing_timeout_sec", 10)
    try:
        t = float(t)
        if t <= 0:
            t = 10.0
    except Exception:
        t = 10.0

    s = f"{start[1]},{start[0]}"  # lon,lat
    e = f"{end[1]},{end[0]}"
    url = f"https://api.mapbox.com/directions/v5/mapbox/{profile}/{s};{e}"
    params = {
        "alternatives": "false",
        "geometries": "polyline6",
        "overview": "false",
        "steps": "false",
        "access_token": token,
    }

    try:
        r = requests.get(url, params=params, timeout=t)
        js = r.json() if r.content else {}
    except Exception as e:
        return None, f"Mapbox request failed: {e}"

    code = (js or {}).get("code")
    if code != "Ok":
        msg = js.get("message") or "Mapbox error"
        return None, f"Mapbox code={code}: {msg}"

    routes = js.get("routes") or []
    if not routes:
        return None, "Mapbox returned no routes"

    rt = routes[0]
    try:
        distance_m = float(rt.get("distance", 0.0))
        duration_s = float(rt.get("duration", 0.0))
        return {
            "distance_km": distance_m / 1000.0,
            "duration_min": duration_s / 60.0,
            "provider": "MAPBOX",
            "raw": rt,
        }, None
    except Exception:
        return None, "Mapbox parse error"

def _route_google(start: Tuple[float, float], end: Tuple[float, float]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Google Distance Matrix (metric, driving)."""
    if not requests:
        return None, "requests library unavailable"

    key = _get_setting("google_api_key")
    if not key:
        return None, "Google API key not set"

    t = _get_setting("routing_timeout_sec", 10)
    try:
        t = float(t)
        if t <= 0:
            t = 10.0
    except Exception:
        t = 10.0

    origins = f"{start[0]},{start[1]}"  # lat,lon
    dests   = f"{end[0]},{end[1]}"

    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": origins,
        "destinations": dests,
        "mode": "driving",
        "units": "metric",
        "key": key,
    }

    try:
        r = requests.get(url, params=params, timeout=t)
        js = r.json() if r.content else {}
    except Exception as e:
        return None, f"Google request failed: {e}"

    status = (js or {}).get("status")
    if status != "OK":
        err_msg = js.get("error_message") or status or "Google error"
        return None, f"Google status={status}: {err_msg}"

    rows = js.get("rows") or []
    if not rows or not rows[0].get("elements"):
        return None, "Google returned empty rows/elements"

    el = rows[0]["elements"][0]
    if el.get("status") != "OK":
        return None, f"Google element status={el.get('status')}"

    try:
        distance_m = float(el["distance"]["value"])
        duration_s = float(el["duration"]["value"])
    except Exception:
        return None, "Google parse error"

    return {
        "distance_km": distance_m / 1000.0,
        "duration_min": duration_s / 60.0,
        "provider": "GOOGLE",
        "raw": el,
    }, None

# ==================== main API ====================
def _msg_fallback(provider: str, reason: str):
    """Show a concise warning and optionally log details."""
    try:
        frappe.msgprint(
            msg=f"Routing provider {provider} failed: {frappe.utils.escape_html(reason)}. Falling back to Haversine.",
            title="Routing Warning",
            indicator="orange",
            alert=True,
        )
    except Exception:
        pass

def _store_failure_reason(leg, reason: str):
    if _has_field("Transport Leg", "route_failure_reason"):
        try:
            setattr(leg, "route_failure_reason", reason)
        except Exception:
            pass

def compute_leg_distance_time(leg_name: str) -> Dict[str, Any]:
    """
    Compute & save distance/time on Transport Leg.
    Emits a user-visible warning if the chosen provider fails, with the reason.
    Stores reason in route_failure_reason (if field exists).
    """
    try:
        leg = frappe.get_doc("Transport Leg", leg_name)
    except Exception as e:
        return {"ok": False, "msg": f"Leg not found: {e}"}

    pick = getattr(leg, "pick_address", None)
    drop = getattr(leg, "drop_address", None)
    if not pick or not drop:
        return {"ok": False, "msg": "Pick or Drop Address not set."}

    c1 = get_address_coords(pick)
    c2 = get_address_coords(drop)
    if not c1 or not c2:
        return {"ok": False, "msg": "Missing coordinates on Pick/Drop Address."}

    provider = (_get_setting("routing_provider", "HAVERSINE") or "HAVERSINE").upper()
    result: Optional[Dict[str, Any]] = None
    failure_reason: Optional[str] = None
    failed_provider: Optional[str] = None

    if provider == "OSRM":
        result, err = _route_osrm(c1, c2)
        if err:
            failure_reason, failed_provider = err, "OSRM"
    elif provider == "MAPBOX":
        result, err = _route_mapbox(c1, c2)
        if err:
            failure_reason, failed_provider = err, "MAPBOX"
    elif provider == "GOOGLE":
        result, err = _route_google(c1, c2)
        if err:
            failure_reason, failed_provider = err, "GOOGLE"
    elif provider in ("DISABLED", "NONE"):
        failure_reason, failed_provider = "Provider disabled", provider
        result = None
    else:
        failure_reason, failed_provider = f"Unknown provider '{provider}'", provider
        result = None

    if not result:
        if failed_provider and failure_reason:
            _store_failure_reason(leg, f"{failed_provider}: {failure_reason}")
            if _get_setting("routing_debug", 0):
                try:
                    frappe.log_error(f"{failed_provider} failed: {failure_reason}", "Routing")
                except Exception:
                    pass
            _msg_fallback(failed_provider, failure_reason)

        dist_km = haversine_km(c1[0], c1[1], c2[0], c2[1])
        speed_kmh = _coerce_float(_get_setting("default_speed_kmh", 40.0)) or 40.0
        dur_min = (dist_km / speed_kmh) * 60.0 if speed_kmh > 0 else 0.0
        result = {"distance_km": dist_km, "duration_min": dur_min, "provider": "HAVERSINE"}

    # Persist ONLY distance/duration/provider (with alias support)
    dirty = False

    def _set(field: str, value):
        nonlocal dirty
        if _has_field("Transport Leg", field):
            setattr(leg, field, value)
            dirty = True

    def _set_any(field_names: list[str], value):
        for f in field_names:
            _set(f, value)

    _set_any(["route_distance_km", "distance_km"], round(float(result.get("distance_km") or 0.0), 3))
    _set_any(["route_duration_min", "duration_min"], round(float(result.get("duration_min") or 0.0), 1))
    _set_any(["route_provider", "routing_provider"], result.get("provider") or "")

    if _has_field("Transport Leg", "route_last_computed"):
        try:
            _set("route_last_computed", frappe.utils.now_datetime())
        except Exception:
            pass

    if dirty:
        leg.flags.ignore_permissions = True
        try:
            leg.save()
        except Exception as e:
            if _get_setting("routing_debug", 0):
                try:
                    frappe.log_error(f"Computed but save failed: {e}", "Routing")
                except Exception:
                    pass
            payload = {
                "ok": False,
                "msg": f"Computed but save failed: {e}",
                "distance_km": result["distance_km"],
                "duration_min": result["duration_min"],
                "provider": result["provider"],
            }
            if failed_provider and failure_reason:
                payload.update({
                    "failed_provider": failed_provider,
                    "failure_reason": failure_reason,
                    "fallback": "HAVERSINE",
                })
            return payload

    payload = {
        "ok": True,
        "msg": "OK",
        "distance_km": result["distance_km"],
        "duration_min": result["duration_min"],
        "provider": result["provider"],
    }
    if failed_provider and failure_reason:
        payload.update({
            "failed_provider": failed_provider,
            "failure_reason": failure_reason,
            "fallback": "HAVERSINE",
        })
    return payload

# ==================== compat API ====================
def get_routing_settings() -> Dict[str, Any]:
    """Compatibility shim for legacy imports."""
    return {
        "provider": (_get_setting("routing_provider", "HAVERSINE") or "HAVERSINE").upper(),
        "osrm_base_url": _get_setting("osrm_base_url") or "",
        "default_speed_kmh": _get_setting("default_speed_kmh", 40.0),
        "timeout": _get_setting("routing_timeout_sec", 10),
    }

def route_leg(leg_name: str) -> Dict[str, Any]:
    """Compatibility shim for legacy imports."""
    return compute_leg_distance_time(leg_name)
