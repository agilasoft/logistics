import frappe
from frappe import _
from typing import Any, Dict, List, Optional

# ---- helpers ---------------------------------------------------------------

def _coerce_float(v) -> Optional[float]:
    try:
        if v in (None, "", "null"):
            return None
        return float(v)
    except Exception:
        return None

def _get_addr_coords(addrname: str) -> Optional[tuple[float, float]]:
    """(lat, lon) from Address using your site’s conventions."""
    if not addrname:
        return None
    try:
        ad = frappe.get_doc("Address", addrname)
    except Exception:
        return None

    # Prefer JSON geolocation if present
    for geo_f in ("custom_geolocation", "address_map"):
        raw = getattr(ad, geo_f, None)
        if raw and isinstance(raw, str):
            try:
                import json
                obj = json.loads(raw)
                # legacy {lat,lng}
                lat = _coerce_float(obj.get("lat"))
                lon = _coerce_float(obj.get("lng"))
                if lat is not None and lon is not None:
                    return (lat, lon)

                # GeoJSON Point
                if obj.get("type") == "Point" and isinstance(obj.get("coordinates"), list):
                    lon, lat = obj["coordinates"][:2]
                    lat = _coerce_float(lat)
                    lon = _coerce_float(lon)
                    if lat is not None and lon is not None:
                        return (lat, lon)
            except Exception:
                pass

    # Fallback to field pairs if present on this site
    for lat_f, lon_f in (("custom_latitude","custom_longitude"), ("latitude","longitude")):
        lat = _coerce_float(getattr(ad, lat_f, None))
        lon = _coerce_float(getattr(ad, lon_f, None))
        if lat is not None and lon is not None:
            return (lat, lon)

    # If Address links to Location, try that
    for link_f in ("location","custom_location"):
        locname = getattr(ad, link_f, None)
        if locname:
            try:
                loc = frappe.get_doc("Location", locname)
                lat = _coerce_float(getattr(loc, "latitude", None))
                lon = _coerce_float(getattr(loc, "longitude", None))
                if lat is not None and lon is not None:
                    return (lat, lon)
            except Exception:
                pass

    return None

def _google_dir_url(c1: Optional[tuple[float,float]], c2: Optional[tuple[float,float]]) -> str:
    if not c1 or not c2:
        return ""
    return f"https://www.google.com/maps/dir/?api=1&origin={c1[0]},{c1[1]}&destination={c2[0]},{c2[1]}"

def _safe_get(dt: str, name: str) -> Optional[Dict[str, Any]]:
    try:
        d = frappe.get_doc(dt, name)
        return d.as_dict()
    except Exception:
        return None

def _find_legs_link_field() -> str:
    """Detect the link field on Transport Leg that points to Run Sheet. Defaults to 'run_sheet'."""
    meta = frappe.get_meta("Transport Leg")
    if meta.has_field("run_sheet"):
        return "run_sheet"
    # scan other link fields that point to Run Sheet
    for df in meta.fields:
        if df.fieldtype == "Link" and (df.options or "") == "Run Sheet":
            return df.fieldname
    return "run_sheet"

# ---- public: data loader ---------------------------------------------------

@frappe.whitelist()
def get_run_sheet_summary(run_sheet: str):
    """Load a Run Sheet (by name or scanned code) and return header + legs + maps URLs."""
    try:
        if not run_sheet:
            return {"ok": False, "message": _("No Run Sheet provided.")}

        # Accept full links or raw names; extract the trailing ID if a URL is pasted
        rs = str(run_sheet).strip()
        if "/Form/Run%20Sheet/" in rs or "/Form/Run Sheet/" in rs or "/app/Run%20Sheet/" in rs or "/app/Run Sheet/" in rs:
            rs = rs.split("/")[-1]

        # Try direct fetch
        doc = _safe_get("Run Sheet", rs)

        # If not found, try interpreting the string as a barcode value
        if not doc:
            if frappe.get_meta("Run Sheet").has_field("barcode"):
                name = frappe.db.get_value("Run Sheet", {"barcode": rs}, "name")
                if name:
                    doc = _safe_get("Run Sheet", name)

        if not doc:
            return {"ok": False, "message": _("Run Sheet not found: {0}").format(run_sheet)}

        # Header we care about (only if fields exist)
        header = {"name": doc.get("name")}
        for f in ("run_date","vehicle","driver"):
            if f in doc:
                header[f] = doc.get(f)

        # Legs
        link_field = _find_legs_link_field()
        fields = [
            "name", "pick_address", "drop_address",
            "facility_from", "facility_to",
            "routing_provider", "route_distance_km", "distance_km",
            "route_duration_min", "duration_min",
            "start_date", "end_date", "actual_duration_min",
        ]
        # keep only existing fields
        tl_meta = frappe.get_meta("Transport Leg")
        fields = [f for f in fields if tl_meta.has_field(f) or f in ("name",)]

        legs = frappe.get_all(
            "Transport Leg",
            filters={link_field: header["name"]},
            fields=fields,
            order_by="idx asc, modified asc"
        ) or []

        # decorate legs: distance/duration resolution + maps URL
        out_legs: List[Dict[str, Any]] = []
        for r in legs:
            d = dict(r)
            # choose route_* over plain if present
            dist = d.get("route_distance_km", None)
            if dist in (None, "", 0):
                dist = d.get("distance_km", None)
            dur = d.get("route_duration_min", None)
            if dur in (None, "", 0):
                dur = d.get("duration_min", None)
            d["distance_km"] = dist
            d["duration_min"] = dur

            c1 = _get_addr_coords(d.get("pick_address"))
            c2 = _get_addr_coords(d.get("drop_address"))
            d["maps_url_google"] = _google_dir_url(c1, c2)

            out_legs.append(d)

        return {"ok": True, "run_sheet": header, "legs": out_legs}

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Run Sheet Scan: get_run_sheet_summary")
        return {"ok": False, "message": _("Unexpected error while loading. Check server logs for details.")}

# ---- public: start/end ops -------------------------------------------------

@frappe.whitelist()
def set_leg_times(leg_name: str, op: str):
    """
    Set start/end timestamps on Transport Leg from the server (authoritative time).
    - op = "start" → set start_date if empty
    - op = "end"   → set end_date (always) and recompute actual_duration_min if start exists
    Returns updated fields for the UI.
    Ensures status is properly updated by explicitly calling update_status().
    """
    try:
        if not leg_name or not op:
            return {"ok": False, "message": "Missing arguments."}

        leg = frappe.get_doc("Transport Leg", leg_name)
        now = frappe.utils.now_datetime()
        changed = False

        if op == "start":
            if not getattr(leg, "start_date", None):
                leg.set("start_date", now)
                changed = True
        elif op == "end":
            leg.set("end_date", now)
            changed = True
        else:
            return {"ok": False, "message": "Invalid operation."}

        # compute actual minutes if both present
        start_dt = getattr(leg, "start_date", None)
        end_dt   = getattr(leg, "end_date", None)
        actual_minutes = None
        if start_dt and end_dt:
            diff_sec = max(0, (end_dt - start_dt).total_seconds())
            actual_minutes = round(diff_sec / 60.0, 1)
            if frappe.get_meta("Transport Leg").has_field("actual_duration_min"):
                leg.set("actual_duration_min", actual_minutes)
                changed = True

        if changed:
            # Explicitly call update_status to ensure status is updated
            leg.update_status()
            leg.save(ignore_permissions=False)

        return {"ok": True, "data": {
            "start_date": leg.get("start_date"),
            "end_date": leg.get("end_date"),
            "actual_duration_min": actual_minutes if actual_minutes is not None else leg.get("actual_duration_min"),
            "status": leg.get("status")  # Include status in response
        }}

    except frappe.PermissionError:
        return {"ok": False, "message": _("No permission to update this Transport Leg.")}
    except Exception:
        frappe.log_error(frappe.get_traceback(), "Run Sheet Scan: set_leg_times")
        return {"ok": False, "message": _("Unexpected server error while updating the leg.")}

