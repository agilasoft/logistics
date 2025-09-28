# logistics/transport/telematics/tests/remora_smoketest.py

import datetime as dt
import frappe
from logistics.transport.telematics.providers.remora import RemoraProvider

VEHICLE_NAME   = "NAG 1873 (ZF9745)"
LOOKBACK_HOURS = 6
FORCE_DEBUG    = 1

def get_val(obj, *names):
    for n in names:
        if hasattr(obj, n):
            v = getattr(obj, n)
            if v not in (None, ""):
                return v
        if isinstance(obj, dict) and n in obj and obj[n] not in (None, ""):
            return obj[n]
    return None

def get_provider_doc_from_vehicle(tv):
    pv = get_val(tv, "telematics_provider", "provider")
    if pv:
        return frappe.get_doc("Telematics Provider", pv)
    ts = frappe.get_single("Transport Settings")
    dp = get_val(ts, "telematics_default_provider", "default_telematics_provider")
    if dp:
        return frappe.get_doc("Telematics Provider", dp)
    raise Exception("No Telematics Provider found")

def build_remora_conf(provider_doc, debug_flag):
    return {
        "username": get_val(provider_doc, "username"),
        "password": get_val(provider_doc, "password"),
        "soap_endpoint_override": get_val(provider_doc, "soap_endpoint_override")
            or "https://api.evogps.com/Services/Data/ExportApiDataService.svc/basicHttp",
        "soap_version": (get_val(provider_doc, "soap_version") or "SOAP11").upper(),
        "request_timeout_sec": float(get_val(provider_doc, "request_timeout_sec") or 20),
        "base_url": get_val(provider_doc, "base_url"),
        "debug": debug_flag,
    }

def detect_device_id(tv):
    return get_val(tv, "telematics_device_id", "device_id", "imei",
                   "sim_imei", "plate_no", "license_plate", "vin", "vin_no")

def _to_float(v):
    try:
        if v in (None, "", "null"): return None
        return float(v)
    except Exception:
        return None

def _parse_ts(v):
    if not v:
        return None
    if isinstance(v, dt.datetime):
        return v if v.tzinfo is None else v.astimezone(dt.timezone.utc).replace(tzinfo=None)
    s = str(v).strip()
    try:
        x = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        return x if x.tzinfo is None else x.astimezone(dt.timezone.utc).replace(tzinfo=None)
    except Exception:
        return None

def set_vehicle_fields(tv_doc, lat, lon, ts, provider="REMORA"):
    meta = frappe.get_meta("Transport Vehicle")
    fields = {df.fieldname for df in meta.fields}

    updates = {}
    for f in ["last_latitude", "current_latitude", "latitude"]:
        if f in fields: updates[f] = lat; break
    for f in ["last_longitude", "current_longitude", "longitude"]:
        if f in fields: updates[f] = lon; break
    for f in ["last_gps_timestamp", "last_position_at", "gps_timestamp"]:
        if f in fields: updates[f] = ts; break
    for f in ["last_position_provider", "gps_provider"]:
        if f in fields: updates[f] = provider; break

    if not updates:
        print("⚠️ No matching lat/lon/timestamp fields to update.")
        return False

    for k, v in updates.items():
        tv_doc.set(k, v)

    tv_doc.flags.ignore_permissions = True
    tv_doc.save()
    frappe.db.commit()
    print(f"✅ Updated vehicle {tv_doc.name} with {updates}")
    return True

def run():
    tv = frappe.get_doc("Transport Vehicle", VEHICLE_NAME)
    prov = get_provider_doc_from_vehicle(tv)
    conf = build_remora_conf(prov, FORCE_DEBUG)
    p = RemoraProvider(conf)

    print("\n=== REMORA Version Info ===")
    print(p.GetVersionInfo())

    dev_id = detect_device_id(tv)
    latest = None

    if dev_id:
        end = dt.datetime.utcnow()
        start = end - dt.timedelta(hours=LOOKBACK_HOURS)
        rows = p.GetPositionsByInterval(dev_id, start, end)
        print(f"Got {len(rows)} rows for {dev_id}")
        if rows:
            r = rows[-1]
            coord = r.get("coordinate") or r.get("Coordinate") or {}
            lat = _to_float(coord.get("latitude") or coord.get("lat"))
            lon = _to_float(coord.get("longitude") or coord.get("lon"))
            ts  = _parse_ts(r.get("dateTime") or r.get("DateTime"))
            latest = {"lat": lat, "lon": lon, "ts": ts}
    else:
        first = next(iter(p.fetch_latest_positions()), None)
        if first:
            latest = {
                "lat": _to_float(first.get("latitude")),
                "lon": _to_float(first.get("longitude")),
                "ts":  _parse_ts(first.get("timestamp")),
            }

    if latest and latest["lat"] and latest["lon"]:
        set_vehicle_fields(tv, latest["lat"], latest["lon"], latest["ts"])
    else:
        print("⚠️ No usable position found.")
