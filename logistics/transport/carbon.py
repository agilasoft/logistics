# apps/logistics/logistics/transport/carbon.py
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, List
import json

import frappe

try:
    import requests  # only used for external providers if configured
except Exception:
    requests = None  # type: ignore


# -------------------------- Utilities --------------------------
def _doctype_exists(doctype: str) -> bool:
    try:
        frappe.get_meta(doctype)
        return True
    except Exception:
        return False


def _has_field(doctype: str, fieldname: str) -> bool:
    try:
        meta = frappe.get_meta(doctype)
        return any(df.fieldname == fieldname for df in meta.fields)
    except Exception:
        return False


def _coerce_float(v) -> Optional[float]:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except Exception:
        return None


def _get_setting(name: str, default=None):
    """Tolerant getter from Transport Settings with some aliases."""
    try:
        ts = frappe.get_single("Transport Settings")
    except Exception:
        ts = None

    if not ts:
        return default

    if hasattr(ts, name):
        return getattr(ts, name)

    aliases = {
        "carbon_provider": ["emissions_provider", "co2e_provider"],
        "carbon_auto_compute": ["emissions_auto_compute"],
        "carbon_default_factor_g_per_km": ["default_factor_g_per_km", "co2e_default_g_per_km"],
        "carbon_default_factor_g_per_ton_km": ["default_factor_g_per_ton_km", "co2e_default_g_per_ton_km"],
        "carbon_provider_api_key": ["emissions_api_key"],
        "carbon_provider_url": ["emissions_provider_url", "co2e_webhook_url"],
    }
    for a in aliases.get(name, []):
        if hasattr(ts, a):
            return getattr(ts, a)

    return default


def _get_ts_child_rows(child_table_fieldname: str) -> List[Dict[str, Any]]:
    """Return child rows from Transport Settings if both parent and child exist."""
    try:
        ts = frappe.get_single("Transport Settings")
        rows = getattr(ts, child_table_fieldname, None)
        if rows:
            # Return as list of dict (not Document) to keep it simple
            return [r.as_dict() for r in rows]
    except Exception:
        pass
    return []


# --------------------- Factor lookup helpers ---------------------
def _lookup_factor_per_km(vehicle_type: str) -> Optional[Tuple[float, str, str]]:
    """
    Returns (factor_g_per_km, source, scope) using the Transport Emission Factor table.
    """
    rows = _get_ts_child_rows("emission_factors")
    vt = (vehicle_type or "").strip()
    best = None
    for r in rows:
        if (r.get("vehicle_type") or "").strip() == vt and (r.get("scope") or "").upper() == "PER_KM":
            f = _coerce_float(r.get("factor_g_per_km"))
            if f is not None and f > 0:
                best = (f, r.get("source") or "", "PER_KM")
                break
    return best


def _lookup_factor_per_ton_km(vehicle_type: str) -> Optional[Tuple[float, str, str]]:
    """
    Returns (factor_g_per_ton_km, source, scope) using the Transport Emission Factor table.
    """
    rows = _get_ts_child_rows("emission_factors")
    vt = (vehicle_type or "").strip()
    best = None
    for r in rows:
        if (r.get("vehicle_type") or "").strip() == vt and (r.get("scope") or "").upper() == "PER_TON_KM":
            f = _coerce_float(r.get("factor_g_per_ton_km"))
            if f is not None and f > 0:
                best = (f, r.get("source") or "", "PER_TON_KM")
                break
    return best


# ---------------------- External providers -----------------------
def _call_climatiq(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Example integration point for Climatiq (you map your own emission factor IDs).
    Not enabled unless carbon_provider='CLIMATIQ' and API key present.
    """
    if _get_setting("carbon_provider", "FACTOR_TABLE") != "CLIMATIQ":
        return None
    api_key = _get_setting("carbon_provider_api_key") or ""
    if not api_key or not requests:
        return None
    try:
        r = requests.post(
            "https://beta3.api.climatiq.io/estimate",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=10,
        )
        r.raise_for_status()
        js = r.json()
        # Expecting { "co2e": value_in_kg, ...}
        val = _coerce_float((js or {}).get("co2e"))
        if val is None:
            return None
        return {"co2e_kg": val, "provider": "CLIMATIQ", "source": "Climatiq"}
    except Exception:
        return None


def _call_carbon_interface(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Example placeholder for Carbon Interface."""
    if _get_setting("carbon_provider", "FACTOR_TABLE") != "CARBON_INTERFACE":
        return None
    # Implement if you decide to use it.
    return None


def _call_custom_webhook(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Generic POST to a custom webhook that returns {"co2e_kg": <float>}."""
    if _get_setting("carbon_provider", "FACTOR_TABLE") != "CUSTOM_WEBHOOK":
        return None
    url = _get_setting("carbon_provider_url") or ""
    if not url or not requests:
        return None
    try:
        r = requests.post(url, data=json.dumps(payload), headers={"Content-Type": "application/json"}, timeout=10)
        r.raise_for_status()
        js = r.json()
        val = _coerce_float((js or {}).get("co2e_kg"))
        if val is None:
            return None
        src = (js or {}).get("source") or "Custom Webhook"
        return {"co2e_kg": val, "provider": "CUSTOM_WEBHOOK", "source": src}
    except Exception:
        return None


# ------------------------- Core compute --------------------------
def _resolve_distance_km(leg) -> Optional[float]:
    # Prefer existing route_distance_km field
    for fn in ["route_distance_km", "distance_km"]:
        if _has_field("Transport Leg", fn):
            val = _coerce_float(getattr(leg, fn, None))
            if val and val > 0:
                return val

    # As a last resort, if routing.py is present & addresses exist, compute haversine
    pick = getattr(leg, "pick_address", None)
    drop = getattr(leg, "drop_address", None)
    if not pick or not drop:
        return None
    try:
        from logistics.transport.routing import get_address_coords, haversine_km  # local import; no circular
        c1 = get_address_coords(pick)
        c2 = get_address_coords(drop)
        if c1 and c2:
            return haversine_km(c1[0], c1[1], c2[0], c2[1])
    except Exception:
        return None
    return None


def _resolve_vehicle_type(leg) -> str:
    for fn in ["vehicle_type"]:
        if _has_field("Transport Leg", fn):
            vt = getattr(leg, fn, None)
            if vt:
                return vt
    # try Transport Job
    tj = getattr(leg, "transport_job", None)
    if tj and _doctype_exists("Transport Job") and _has_field("Transport Job", "vehicle_type"):
        try:
            job = frappe.get_doc("Transport Job", tj)
            if job and getattr(job, "vehicle_type", None):
                return job.vehicle_type
        except Exception:
            pass
    return ""


def _resolve_weight_kg(leg) -> Optional[float]:
    # 1) Direct on leg if you added a field
    for fn in ["cargo_weight_kg", "weight_kg", "gross_weight_kg"]:
        if _has_field("Transport Leg", fn):
            v = _coerce_float(getattr(leg, fn, None))
            if v and v > 0:
                return v

    # 2) From Transport Job aggregate fields
    tj = getattr(leg, "transport_job", None)
    if tj and _doctype_exists("Transport Job"):
        try:
            job = frappe.get_doc("Transport Job", tj)
            for fn in ["total_weight_kg", "weight_kg", "gross_weight", "total_weight"]:
                v = _coerce_float(getattr(job, fn, None))
                if v and v > 0:
                    return v
        except Exception:
            pass

    # 3) If you maintain packages, try common child table fields (best-effort)
    #    Skipped here to avoid DB field surprises; add if you have a stable schema.

    return None


def compute_leg_carbon(leg_name: str) -> Dict[str, Any]:
    """
    Compute CO₂e for a Transport Leg.
    Preference order:
      1) Factor per TON-KM if weight and factor exist.
      2) Factor per KM by vehicle type.
      3) Fallback default factors from settings.
    Writes back (when present): co2e_kg, co2e_method, co2e_factor, co2e_scope,
                                co2e_provider, co2e_source, co2e_last_computed.
    """
    try:
        leg = frappe.get_doc("Transport Leg", leg_name)
    except Exception as e:
        return {"ok": False, "msg": f"Leg not found: {e}"}

    dist_km = _resolve_distance_km(leg)
    if not dist_km or dist_km <= 0:
        return {"ok": False, "msg": "Distance not available on leg and could not be inferred."}

    vehicle_type = _resolve_vehicle_type(leg)
    weight_kg = _resolve_weight_kg(leg)
    provider = str(_get_setting("carbon_provider", "FACTOR_TABLE") or "FACTOR_TABLE").upper()

    result: Dict[str, Any] = {}
    method = ""
    scope = ""
    factor = None  # g per (ton-)km
    source = ""

    # ----- External provider path (optional) -----
    if provider in {"CLIMATIQ", "CARBON_INTERFACE", "CUSTOM_WEBHOOK"}:
        payload = {
            "vehicle_type": vehicle_type or "",
            "distance_km": dist_km,
            "weight_kg": weight_kg or 0,
            "leg_name": leg_name,
            "transport_job": getattr(leg, "transport_job", ""),
        }
        ext: Optional[Dict[str, Any]] = None
        if provider == "CLIMATIQ":
            ext = _call_climatiq(payload)
        elif provider == "CARBON_INTERFACE":
            ext = _call_carbon_interface(payload)
        elif provider == "CUSTOM_WEBHOOK":
            ext = _call_custom_webhook(payload)
        if ext and _coerce_float(ext.get("co2e_kg")) is not None:
            result = {
                "co2e_kg": float(ext["co2e_kg"]),
                "provider": ext.get("provider") or provider,
                "source": ext.get("source") or provider,
                "method": "EXTERNAL",
                "scope": "N/A",
                "factor": 0.0,
            }

    # ----- Factor table path -----
    if not result:
        # Try PER_TON_KM first if weight is present
        if weight_kg and weight_kg > 0:
            cand = _lookup_factor_per_ton_km(vehicle_type)
            if cand:
                factor, source, scope = cand  # g per ton-km
                ton_km = dist_km * (weight_kg / 1000.0)
                co2e_kg = (factor * ton_km) / 1000.0
                result = {
                    "co2e_kg": co2e_kg,
                    "provider": "FACTOR_TABLE",
                    "source": source or "Factor (ton-km)",
                    "method": "PER_TON_KM",
                    "scope": "PER_TON_KM",
                    "factor": factor,
                }

        # Then PER_KM by vehicle type
        if not result:
            cand = _lookup_factor_per_km(vehicle_type)
            if cand:
                factor, source, scope = cand  # g per km
                co2e_kg = (factor * dist_km) / 1000.0
                result = {
                    "co2e_kg": co2e_kg,
                    "provider": "FACTOR_TABLE",
                    "source": source or "Factor (km)",
                    "method": "PER_KM",
                    "scope": "PER_KM",
                    "factor": factor,
                }

        # Fallback default factors from settings
        if not result:
            f_ton = _coerce_float(_get_setting("carbon_default_factor_g_per_ton_km"))
            if f_ton and weight_kg and weight_kg > 0:
                ton_km = dist_km * (weight_kg / 1000.0)
                co2e_kg = (f_ton * ton_km) / 1000.0
                result = {
                    "co2e_kg": co2e_kg,
                    "provider": "DEFAULT",
                    "source": "Default PER_TON_KM",
                    "method": "DEFAULT",
                    "scope": "PER_TON_KM",
                    "factor": f_ton,
                }
            elif (f_km := _coerce_float(_get_setting("carbon_default_factor_g_per_km"))) and f_km > 0:
                co2e_kg = (f_km * dist_km) / 1000.0
                result = {
                    "co2e_kg": co2e_kg,
                    "provider": "DEFAULT",
                    "source": "Default PER_KM",
                    "method": "DEFAULT",
                    "scope": "PER_KM",
                    "factor": f_km,
                }

    if not result:
        return {"ok": False, "msg": "No emission factor found and no defaults configured."}

    # -------------- Persist to leg if fields exist --------------
    dirty = False

    def _set(fn: str, val):
        nonlocal dirty
        if _has_field("Transport Leg", fn):
            setattr(leg, fn, val)
            dirty = True

    _set("co2e_kg", round(float(result["co2e_kg"]), 3))
    _set("co2e_method", result.get("method") or "")
    _set("co2e_factor", round(float(result.get("factor") or 0.0), 3))
    _set("co2e_scope", result.get("scope") or "")
    _set("co2e_provider", result.get("provider") or "")
    _set("co2e_source", result.get("source") or "")
    if _has_field("Transport Leg", "co2e_last_computed"):
        try:
            _set("co2e_last_computed", frappe.utils.now_datetime())
        except Exception:
            pass

    if dirty:
        leg.flags.ignore_permissions = True
        try:
            leg.save()
        except Exception as e:
            # Still return the computation
            result["save_error"] = str(e)

    return {"ok": True, "msg": "OK", **result}
