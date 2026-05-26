# apps/logistics/logistics/transport/api.py
from typing import List, Dict
import frappe
from frappe import _
from logistics.transport.routing import get_address_coords

def _safe_meta_fieldnames(doctype: str) -> set:
    meta = frappe.get_meta(doctype)
    fns = set()
    for df in meta.get("fields", []) or []:
        fn = getattr(df, "fieldname", None) or (df.get("fieldname") if isinstance(df, dict) else None)
        if fn: fns.add(fn)
    return fns

def _first_present(src: Dict, candidates: List[str]):
    for c in candidates:
        if c in src and src[c] not in (None, "", []):
            return src[c]
    return None

@frappe.whitelist()
def build_operations_from_template(template: str) -> List[Dict]:
    """Return rows compatible with 'Transport Order Operation' from the selected template."""
    if not template:
        return []

    tpl = frappe.get_doc("Transport Operations Template", template)

    dest_child_doctype = "Transport Order Operation"
    dest_fields = _safe_meta_fieldnames(dest_child_doctype)

    # Destination → candidate source field names (ordered)
    FIELD_MAP = {
        "operation":     ["operation", "transport_operation", "operation_code", "op", "op_code"],
        "facility_type": ["facility_type", "facilitydoctype", "facility_doctype"],
        "facility":      ["facility", "facility_name", "facility_link"],
        "address":       ["address", "address_name", "address_link"],
        "notes":         ["notes", "instruction", "instructions", "remarks", "description"],
    }

    rows: List[Dict] = []
    for src in (tpl.get("operations") or []):   # child: Transport Job Template Operations
        srcd = src.as_dict()

        # Safe intersection copy (ignores parent/name/idx)
        row = {k: v for k, v in srcd.items()
               if k in dest_fields and k not in {"parent", "parenttype", "parentfield", "name", "idx"}}

        # Fill mapped fields (handles different source fieldnames)
        for dest_key, candidates in FIELD_MAP.items():
            if dest_key in dest_fields:
                val = _first_present(srcd, candidates)
                if val is not None:
                    row[dest_key] = val

        rows.append(row)

    return rows

@frappe.whitelist()
def get_address_latlon(addr_name: str):
    c = get_address_coords(addr_name)
    return {"lat": c[0], "lon": c[1]} if c else None

# Fields exposed to driver mobile app (agilasoft/driver) via get_run_sheet_bundle
RUN_SHEET_BUNDLE_LEG_FIELDS = [
    "name", "date", "transport_job", "vehicle_type", "leg_type", "priority", "order",
    "facility_type_from", "facility_from", "pick_address", "pick_address_format",
    "facility_type_to", "facility_to", "drop_address", "drop_address_html",
    "pick_window_start", "pick_window_end", "drop_window_start", "drop_window_end",
    "pick_consolidated", "drop_consolidated",
    "contains_dangerous_goods", "refrigeration",
    "start_date", "end_date", "distance_km", "duration_min",
    "pick_signature", "pick_signed_by", "pick_signed_at",
    "drop_signature", "drop_signed_by", "drop_signed_at", "date_signed",
    "pick_latitude", "pick_longitude", "drop_latitude", "drop_longitude",
    "pick_notes", "drop_notes", "pick_photo", "drop_photo",
    "status", "actual_distance_km", "actual_duration_min",
]

# Allowlisted keys for apply_leg_driver_updates (native app + run sheet scan)
DRIVER_LEG_UPDATE_FIELDS = frozenset({
    "start_date", "end_date",
    "pick_signature", "pick_signed_by", "pick_signed_at",
    "drop_signature", "drop_signed_by", "drop_signed_at", "date_signed",
    "pick_latitude", "pick_longitude", "drop_latitude", "drop_longitude",
    "pick_notes", "drop_notes", "pick_photo", "drop_photo",
})


def _enrich_leg_for_mobile(leg: Dict) -> None:
    """Add aliases and navigation coordinates for driver clients."""
    leg["signature"] = leg.get("drop_signature")
    leg["signed_by"] = leg.get("drop_signed_by")
    leg["route_distance_km"] = leg.get("actual_distance_km") or leg.get("distance_km")
    leg["route_duration_min"] = leg.get("actual_duration_min") or leg.get("duration_min")

    pick_lat = leg.get("pick_latitude")
    pick_lon = leg.get("pick_longitude")
    if pick_lat is not None and pick_lon is not None:
        leg["_pick_coord"] = {"lat": pick_lat, "lon": pick_lon}
    elif leg.get("pick_address"):
        c = get_address_coords(leg["pick_address"])
        if c:
            leg["_pick_coord"] = {"lat": c[0], "lon": c[1]}

    drop_lat = leg.get("drop_latitude")
    drop_lon = leg.get("drop_longitude")
    if drop_lat is not None and drop_lon is not None:
        leg["_drop_coord"] = {"lat": drop_lat, "lon": drop_lon}
    elif leg.get("drop_address"):
        c = get_address_coords(leg["drop_address"])
        if c:
            leg["_drop_coord"] = {"lat": c[0], "lon": c[1]}


def resolve_driver_for_user(user: str | None = None) -> str | None:
    """Resolve Driver name for a Frappe user (matches agilasoft/driver login strategies)."""
    user = user or frappe.session.user
    if not user or user == "Guest":
        return None

    strategies = (
        ("user", user),
        ("user_id", user),
    )
    for field, value in strategies:
        if frappe.get_meta("Driver").has_field(field):
            name = frappe.db.get_value("Driver", {field: value}, "name")
            if name:
                return name

    employee = frappe.db.get_value("Employee", {"user_id": user}, "name")
    if employee and frappe.get_meta("Driver").has_field("employee"):
        name = frappe.db.get_value("Driver", {"employee": employee}, "name")
        if name:
            return name

    full_name = frappe.db.get_value("User", user, "full_name")
    if full_name:
        name = frappe.db.get_value("Driver", {"full_name": full_name}, "name")
        if name:
            return name

    return None


def _verify_driver_may_update_leg(leg_doc, driver_id: str | None) -> None:
    """When a Driver is linked to the session user, restrict updates to their run sheets."""
    if not driver_id or not leg_doc.run_sheet:
        return
    rs_driver = frappe.db.get_value("Run Sheet", leg_doc.run_sheet, "driver")
    if rs_driver and rs_driver != driver_id:
        frappe.throw(
            _("You are not assigned to Run Sheet {0}.").format(leg_doc.run_sheet),
            frappe.PermissionError,
        )


@frappe.whitelist()
def get_run_sheet_bundle(name: str):
    """Return a Run Sheet header + its legs (safe fields for driver mobile app)."""
    if not name:
        frappe.throw(_("Run Sheet name required."))

    doc = frappe.get_doc("Run Sheet", name)
    doc.check_permission("read")

    meta = frappe.get_meta("Transport Leg")
    fields = [f for f in RUN_SHEET_BUNDLE_LEG_FIELDS if meta.has_field(f)]

    legs = frappe.get_all(
        "Transport Leg",
        filters={"run_sheet": name, "docstatus": ["<", 2]},
        fields=fields,
        order_by="order asc, date asc, modified asc",
        limit_page_length=1000,
    )

    for leg in legs:
        _enrich_leg_for_mobile(leg)

    return {"doc": doc.as_dict(no_nulls=True), "legs": legs}


@frappe.whitelist()
def apply_leg_driver_updates(leg_name: str, updates: str | Dict | None = None):
    """
    Apply driver/mobile field updates on a Transport Leg using doc.save()
    so status cascades to Run Sheet and Transport Job.
    """
    if isinstance(updates, str):
        updates = frappe.parse_json(updates) if updates else {}
    updates = updates or {}

    if not leg_name:
        frappe.throw(_("Transport Leg name required."))

    leg_doc = frappe.get_doc("Transport Leg", leg_name)
    leg_doc.check_permission("write")

    driver_id = resolve_driver_for_user()
    _verify_driver_may_update_leg(leg_doc, driver_id)

    meta = frappe.get_meta("Transport Leg")
    applied = {}
    for key, value in updates.items():
        if key not in DRIVER_LEG_UPDATE_FIELDS or not meta.has_field(key):
            continue
        leg_doc.set(key, value)
        applied[key] = value

    if not applied:
        return {"ok": True, "name": leg_name, "message": _("No valid fields to update.")}

    leg_doc.save(ignore_permissions=True)

    return {
        "ok": True,
        "name": leg_name,
        "status": leg_doc.status,
        "start_date": leg_doc.start_date,
        "end_date": leg_doc.end_date,
        "pick_signed_at": leg_doc.get("pick_signed_at"),
        "drop_signed_at": leg_doc.get("drop_signed_at"),
        "date_signed": leg_doc.date_signed,
    }


@frappe.whitelist()
def update_driver_location(
    driver: str,
    latitude: float,
    longitude: float,
    accuracy: float | None = None,
    speed: float | None = None,
    heading: float | None = None,
    timestamp: str | None = None,
):
    """Update last-known GPS for a Driver (agilasoft/driver live location)."""
    if not driver:
        frappe.throw(_("Driver is required."))
    if not frappe.db.exists("Driver", driver):
        frappe.throw(_("Driver {0} does not exist.").format(driver))

    session_driver = resolve_driver_for_user()
    if session_driver and session_driver != driver:
        frappe.throw(_("Cannot update location for another driver."), frappe.PermissionError)

    lat, lon = float(latitude), float(longitude)
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        frappe.throw(_("Invalid latitude or longitude."))

    ts = timestamp or frappe.utils.now_datetime()
    values = {
        "custom_last_known_latitude": lat,
        "custom_last_known_longitude": lon,
        "custom_last_location_time": ts,
    }
    if accuracy is not None and frappe.get_meta("Driver").has_field("custom_last_location_accuracy"):
        values["custom_last_location_accuracy"] = float(accuracy)
    if speed is not None and frappe.get_meta("Driver").has_field("custom_last_speed"):
        values["custom_last_speed"] = float(speed)
    if heading is not None and frappe.get_meta("Driver").has_field("custom_last_heading"):
        values["custom_last_heading"] = float(heading)

    driver_meta = frappe.get_meta("Driver")
    for fieldname, value in values.items():
        if driver_meta.has_field(fieldname):
            frappe.db.set_value("Driver", driver, fieldname, value, update_modified=False)

    # Fallback field names used by driver app REST PUT
    legacy = {
        "last_known_latitude": lat,
        "last_known_longitude": lon,
        "last_location_time": ts,
    }
    for fieldname, value in legacy.items():
        if driver_meta.has_field(fieldname):
            frappe.db.set_value("Driver", driver, fieldname, value, update_modified=False)

    vehicle = frappe.db.get_value("Driver", driver, "custom_default_vehicle")
    if vehicle and frappe.get_meta("Transport Vehicle").has_field("last_telematics_lat"):
        frappe.db.set_value(
            "Transport Vehicle",
            vehicle,
            {
                "last_telematics_lat": lat,
                "last_telematics_lon": lon,
                "last_telematics_ts": ts,
            },
            update_modified=False,
        )

    frappe.db.commit()
    return {"ok": True, "driver": driver, "latitude": lat, "longitude": lon, "timestamp": ts}
