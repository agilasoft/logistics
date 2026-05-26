from __future__ import annotations
from typing import Optional, Dict, Any
import frappe
from frappe.utils.password import get_decrypted_password

def _provider_conf(provider_docname: str) -> Optional[Dict[str, Any]]:
    doc = frappe.get_doc("Telematics Provider", provider_docname)
    if not doc.enabled:
        return None

    conf: Dict[str, Any] = {
        "name": doc.name,
        "provider_docname": doc.name,
        "provider_type": doc.provider_type,
        "base_url": doc.base_url,
        "api_key": get_decrypted_password("Telematics Provider", provider_docname, "api_key", raise_exception=False),
        "username": getattr(doc, "username", None),
        "password": get_decrypted_password("Telematics Provider", provider_docname, "password", raise_exception=False),
        "timeout": getattr(doc, "request_timeout_sec", None) or 20,
    }

    # Go Transport tab fields (passed through unconditionally; the provider
    # class will only use them when provider_type == "GOTRANSPORT").
    position_method = getattr(doc, "gotransport_position_method", None)
    if position_method:
        conf["position_method"] = position_method
        conf["gotransport_position_method"] = position_method
    if getattr(doc, "gotransport_api_secret", None):
        try:
            api_secret = get_decrypted_password(
                "Telematics Provider", provider_docname,
                "gotransport_api_secret", raise_exception=False,
            )
        except Exception:
            api_secret = None
        if api_secret:
            conf["api_secret"] = api_secret
            conf["gotransport_api_secret"] = api_secret

    return conf

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
