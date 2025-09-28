# Copyright (c) 2025, www.agilasoft.com
# logistics/transport/doctype/transport_leg/transport_leg.py

from __future__ import annotations

from typing import Any, Tuple, Optional

import frappe
from frappe.model.document import Document
from frappe.model.meta import get_meta
from frappe.utils import now_datetime


# -----------------------------
# Small helpers
# -----------------------------
def _has_field(doctype: str, fieldname: str) -> bool:
    """Fast, safe check if a field exists on a DocType."""
    try:
        return get_meta(doctype).has_field(fieldname)
    except Exception:
        return False


def _set_if_exists(doc: Document, fieldname: str, value: Any) -> None:
    """Set a value only if the field exists on the document."""
    if _has_field(doc.doctype, fieldname):
        setattr(doc, fieldname, value)


def _get_address_latlng(addr_name: Optional[str]) -> Tuple[Optional[float], Optional[float]]:
    """Probe common Address latitude/longitude fields and coerce to float."""
    if not addr_name:
        return (None, None)
    try:
        addr = frappe.get_doc("Address", addr_name)
    except Exception:
        return (None, None)

    for latf, lngf in (
        ("custom_latitude", "custom_longitude"),
        ("latitude", "longitude"),
        ("custom_gps_latitude", "custom_gps_longitude"),
    ):
        lat = getattr(addr, latf, None)
        lng = getattr(addr, lngf, None)
        if lat is not None and lng is not None:
            try:
                return (float(lat), float(lng))
            except Exception:
                pass
    return (None, None)


def _get_ts(name: str, default=None):
    """Read Transport Settings field safely, with a couple of common aliases."""
    try:
        ts = frappe.get_single("Transport Settings")
    except Exception:
        return default

    # exact first
    if hasattr(ts, name):
        return getattr(ts, name)

    # minimal aliasing
    alias_map = {
        "routing_auto_compute": ["routing_auto_compute", "auto_compute_route"],
        "routing_default_avg_speed_kmh": ["routing_default_avg_speed_kmh", "default_speed_kmh", "avg_speed_kmh"],
        "carbon_auto_compute": ["carbon_auto_compute", "auto_compute_carbon"],
    }
    for alias in alias_map.get(name, []):
        if hasattr(ts, alias):
            return getattr(ts, alias)
    return default


# -----------------------------
# Main controller
# -----------------------------
class TransportLeg(Document):
    def validate(self):
        """
        - Auto-route (if enabled) and we have coordinates.
        - Auto-carbon (if enabled); never block save on error.
        """
        # --- Auto routing ---
        try:
            if bool(_get_ts("routing_auto_compute", 1)) and not frappe.flags.in_import:
                self._auto_route()
        except Exception:
            # Don't break validation if routing has issues
            frappe.clear_last_message()

        # --- Auto carbon ---
        try:
            if bool(_get_ts("carbon_auto_compute", 0)) and not frappe.flags.in_import:
                # Lazy import to avoid circular/reload issues
                try:
                    from logistics.transport.carbon import compute_leg_carbon  # type: ignore
                    if self.name:
                        compute_leg_carbon(self.name)
                except Exception:
                    # never block save for carbon
                    pass
        except Exception:
            pass

    # -------------------------
    # internals
    # -------------------------
    def _auto_route(self) -> None:
        """
        Compute distance/time via routing engine; fallback to Haversine if provider fails.
        No polyline writes.
        """
        pick_lat, pick_lng = _get_address_latlng(getattr(self, "pick_address", None))
        drop_lat, drop_lng = _get_address_latlng(getattr(self, "drop_address", None))
        if None in (pick_lat, pick_lng, drop_lat, drop_lng):
            return  # silently skip if no coords

        # Try full engine first (reads settings, talks to OSRM/Mapbox/etc.; should persist if fields exist)
        try:
            from logistics.transport.routing import compute_leg_distance_time  # type: ignore

            if self.name:
                res = compute_leg_distance_time(self.name) or {}
                if res.get("ok"):
                    # Update in-memory doc so user sees values immediately
                    _set_if_exists(self, "distance_km", round(float(res.get("distance_km") or 0.0), 3))
                    _set_if_exists(self, "duration_min", round(float(res.get("duration_min") or 0.0), 1))
                    _set_if_exists(self, "routing_provider", res.get("provider") or "")
                    # NOTE: No polyline writes here (removed)
                    return
        except Exception:
            # fall through to haversine
            pass

        # Fallback: local Haversine + default speed
        try:
            from logistics.transport.routing import haversine_km  # type: ignore
        except Exception:
            return

        dist_km = haversine_km(pick_lat, pick_lng, drop_lat, drop_lng)
        try:
            speed_kmh = float(_get_ts("routing_default_avg_speed_kmh", 40.0)) or 40.0
        except Exception:
            speed_kmh = 40.0

        dur_min = (dist_km / speed_kmh) * 60.0 if speed_kmh > 0 else 0.0

        _set_if_exists(self, "distance_km", round(dist_km, 3))
        _set_if_exists(self, "duration_min", round(dur_min, 1))
        _set_if_exists(self, "routing_provider", "HAVERSINE")
        # NOTE: No polyline writes here either


# -----------------------------
# Actions (buttons / API)
# -----------------------------
@frappe.whitelist()
def regenerate_routing(leg_name: str):
    """
    Button handler: Action → Regenerate Routing
    Uses robust engine; raises a frappe error if it fails so UI shows a red message.
    No polyline returned or written here.
    """
    if not leg_name:
        frappe.throw("Missing leg name")

    try:
        from logistics.transport.routing import compute_leg_distance_time  # type: ignore
    except Exception as e:
        frappe.throw(f"Routing engine import failed: {frappe.safe_decode(str(e))}")

    res = compute_leg_distance_time(leg_name) or {}
    if not res.get("ok"):
        frappe.throw(res.get("msg") or "Routing failed")

    # Return a small payload (document fields already saved inside the engine if they exist)
    return {
        "ok": True,
        "provider": res.get("provider") or "",
        "distance_km": float(res.get("distance_km") or 0.0),
        "duration_min": float(res.get("duration_min") or 0.0),
    }


@frappe.whitelist()
def regenerate_carbon(leg_name: str):
    """
    Button handler: Action → Regenerate CO₂e
    """
    if not leg_name:
        frappe.throw("Missing leg name")

    try:
        from logistics.transport.carbon import compute_leg_carbon  # type: ignore
    except Exception as e:
        frappe.throw(f"Carbon engine import failed: {frappe.safe_decode(str(e))}")

    res = compute_leg_carbon(leg_name) or {}
    if not res.get("ok"):
        frappe.throw(res.get("msg") or "Carbon compute failed")

    return {
        "ok": True,
        "co2e_kg": float(res.get("co2e_kg") or 0.0),
        "method": res.get("method") or "",
        "scope": res.get("scope") or "",
        "provider": res.get("provider") or "",
        "factor": float(res.get("factor") or 0.0),
        "source": res.get("source") or "",
    }


# -----------------------------
# Operational helpers (used by mobile/scan UI)
# -----------------------------
@frappe.whitelist()
def start_leg(leg_name: str):
    if not leg_name:
        frappe.throw("Missing leg name")
    leg = frappe.get_doc("Transport Leg", leg_name)
    if not getattr(leg, "start_date", None):
        leg.set("start_date", now_datetime())
        leg.flags.ignore_permissions = True
        leg.save()
    return {"ok": True, "start_date": leg.start_date}


@frappe.whitelist()
def end_leg(leg_name: str):
    if not leg_name:
        frappe.throw("Missing leg name")
    leg = frappe.get_doc("Transport Leg", leg_name)
    if not getattr(leg, "end_date", None):
        leg.set("end_date", now_datetime())
        # Derive actual duration if both timestamps exist
        try:
            if getattr(leg, "start_date", None) and hasattr(leg, "actual_duration_min"):
                td = leg.end_date - leg.start_date
                minutes = round(td.total_seconds() / 60.0, 1)
                leg.set("actual_duration_min", minutes)
        except Exception:
            pass
        # Default actual distance to planned distance if field exists & empty
        try:
            if hasattr(leg, "actual_distance_km") and not getattr(leg, "actual_distance_km", None):
                if hasattr(leg, "distance_km") and leg.distance_km:
                    leg.set("actual_distance_km", float(leg.distance_km))
        except Exception:
            pass
        leg.flags.ignore_permissions = True
        leg.save()
    return {
        "ok": True,
        "end_date": leg.end_date,
        "actual_duration_min": getattr(leg, "actual_duration_min", None),
        "actual_distance_km": getattr(leg, "actual_distance_km", None),
    }
