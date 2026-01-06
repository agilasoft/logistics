from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

import frappe

try:
    import requests
except Exception:
    requests = None  # type: ignore


def _compose_address_text(doc) -> str:
    parts = []
    for fn in (
        "address_line1",
        "address_line2",
        "city",
        "county",
        "state",
        "pincode",
        "country",
    ):
        v = getattr(doc, fn, None)
        if v:
            parts.append(str(v).strip())
    return ", ".join(parts)


@frappe.whitelist()
def geocode_address(address_name: str) -> Dict[str, object]:
    """Forward-geocode Address → set custom_latitude/custom_longitude.
       Uses OSM Nominatim (no key). You can later switch to Google/Mapbox if desired."""
    if not requests:
        return {"ok": False, "error": "requests not available"}

    try:
        doc = frappe.get_doc("Address", address_name)
    except Exception:
        return {"ok": False, "error": "Address not found"}

    q = _compose_address_text(doc).strip()
    if not q:
        return {"ok": False, "error": "Address text is empty"}

    # Respect Nominatim policies: add a descriptive UA and optionally email in settings if you want
    headers = {"User-Agent": f"Frappe-Logistics-Geocoder/1.0 ({frappe.utils.get_url()})"}
    params = {"format": "json", "q": q, "limit": 1}

    try:
        r = requests.get("https://nominatim.openstreetmap.org/search", params=params, headers=headers, timeout=8)
        r.raise_for_status()
        arr = r.json() or []
        if not arr:
            return {"ok": False, "error": "No result from geocoder"}
        hit = arr[0]
        lat = float(hit.get("lat"))
        lon = float(hit.get("lon"))

        # Save back to Address.custom_latitude/custom_longitude
        doc.flags.ignore_permissions = True
        if hasattr(doc, "custom_latitude"):
            doc.custom_latitude = lat
        if hasattr(doc, "custom_longitude"):
            doc.custom_longitude = lon
        if hasattr(doc, "custom_geocode_status"):
            doc.custom_geocode_status = hit.get("display_name", "")[:140]
        if hasattr(doc, "custom_geocoded_at"):
            doc.custom_geocoded_at = frappe.utils.now_datetime()
        doc.save()

        return {
            "ok": True,
            "lat": lat,
            "lng": lon,
            "status": hit.get("display_name"),
            "geocoded_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
