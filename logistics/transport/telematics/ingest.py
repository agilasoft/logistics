from __future__ import annotations
from typing import Dict, Any, List
from datetime import timedelta
import frappe
from .providers import make_provider
from .resolve import _provider_conf

def _vehicles_with_mapping() -> List[Dict[str, Any]]:
    rows = frappe.db.get_all("Transport Vehicle",
                             fields=["name","telematics_provider","telematics_external_id"])
    default_provider = frappe.db.get_single_value("Transport Settings", "default_telematics_provider")
    out = []
    for r in rows:
        ext = (r.get("telematics_external_id") or "").strip()
        if not ext:
            continue
        prov = r.get("telematics_provider") or default_provider
        if not prov:
            continue
        out.append({"vehicle": r["name"], "external_id": ext, "provider_doc": prov})
    return out

def _group_by_provider(items: List[Dict[str, Any]]):
    g = {}
    for it in items:
        g.setdefault(it["provider_doc"], []).append(it)
    return g

def run_ingest():
    now = frappe.utils.now_datetime()
    since = now - timedelta(minutes = frappe.db.get_single_value("Transport Settings", "telematics_poll_interval_min") or 5)

    mapping = _vehicles_with_mapping()
    if not mapping: return
    by_provider = _group_by_provider(mapping)

    for provider_doc, vehs in by_provider.items():
        conf = _provider_conf(provider_doc)
        if not conf: continue
        prov = make_provider(conf["provider_type"], conf)
        vindex = {x["external_id"]: x["vehicle"] for x in vehs}

        # Positions
        try:
            for p in prov.fetch_latest_positions(None):
                _store_position(vindex.get(str(p["external_id"])), p)
        except Exception as e:
            frappe.log_error(f"{provider_doc} positions failed: {e}", "Transport/Telematics")

        # Events
        try:
            for ev in prov.fetch_events(since, now):
                _store_event(vindex.get(str(ev["external_id"])), ev)
        except Exception as e:
            frappe.log_error(f"{provider_doc} events failed: {e}", "Transport/Telematics")

        # Temps
        try:
            for t in prov.fetch_temperatures(since, now):
                _store_temp(vindex.get(str(t["external_id"])), t)
        except Exception:
            pass

        # CAN
        try:
            for c in prov.fetch_can(since, now):
                _store_can(vindex.get(str(c["external_id"])), c)
        except Exception:
            pass

def _store_position(vehicle: str, p: Dict[str, Any]):
    if not vehicle: return
    doc = frappe.get_doc({
        "doctype": "Telematics Position",
        "vehicle": vehicle,
        "ts": p["ts"],
        "lat": p["lat"], "lon": p["lon"],
        "speed_kph": p.get("speed_kph"),
        "ignition": 1 if p.get("ignition") else 0,
        "odometer_km": p.get("odometer_km"),
        "raw_json": frappe.as_json(p.get("raw")),
    })
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)

def _store_event(vehicle: str, ev: Dict[str, Any]):
    if not vehicle: return
    doc = frappe.get_doc({
        "doctype": "Telematics Event",
        "vehicle": vehicle,
        "ts": ev["ts"],
        "kind": ev["kind"],
        "meta_json": frappe.as_json(ev.get("meta")),
    })
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)

def _store_temp(vehicle: str, t: Dict[str, Any]):
    if not vehicle: return
    doc = frappe.get_doc({
        "doctype": "Telematics Temperature",
        "vehicle": vehicle,
        "ts": t["ts"], "sensor": t["sensor"], "temperature_c": t["temperature_c"],
    })
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)

def _store_can(vehicle: str, c: Dict[str, Any]):
    if not vehicle: return
    doc = frappe.get_doc({
        "doctype": "Telematics CAN Snapshot",
        "vehicle": vehicle,
        "ts": c["ts"],
        "fuel_l": c.get("fuel_l"), "rpm": c.get("rpm"),
        "engine_hours": c.get("engine_hours"),
        "coolant_c": c.get("coolant_c"), "ambient_c": c.get("ambient_c"),
        "raw_json": frappe.as_json(c.get("raw")),
    })
    doc.flags.ignore_permissions = True
    doc.insert(ignore_permissions=True)
