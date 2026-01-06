from __future__ import annotations
from typing import Optional, Dict, Any
import frappe
from frappe.utils.password import get_decrypted_password

def _provider_conf(provider_docname: str) -> Optional[Dict[str, Any]]:
    doc = frappe.get_doc("Telematics Provider", provider_docname)
    if not doc.enabled:
        return None
    return {
        "name": doc.name,
        "provider_type": doc.provider_type,
        "base_url": doc.base_url,
        "api_key": get_decrypted_password("Telematics Provider", provider_docname, "api_key", raise_exception=False),
        "username": getattr(doc, "username", None),
        "password": get_decrypted_password("Telematics Provider", provider_docname, "password", raise_exception=False),
        "timeout": 20,
    }

def resolve_vehicle_provider(vehicle_name: str) -> Optional[Dict[str, Any]]:
    v = frappe.get_doc("Transport Vehicle", vehicle_name)
    ext = (getattr(v, "telematics_external_id", "") or "").strip()
    if not ext:
        return None

    prov_link = getattr(v, "telematics_provider", None)
    if not prov_link:
        prov_link = frappe.db.get_single_value("Transport Settings", "default_telematics_provider")
    if not prov_link:
        return None

    conf = _provider_conf(prov_link)
    if not conf:
        return None

    conf["external_id"] = ext
    conf["vehicle_name"] = vehicle_name
    conf["provider_docname"] = prov_link
    return conf
