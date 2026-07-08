# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

from typing import Optional, Tuple

import frappe

from .base import BaseCCSConnector, ChampTraxonConnector, GenericCCSConnector, WiseConnector

CONNECTOR_MAP = {
	"champ_traxon": ChampTraxonConnector,
	"generic": GenericCCSConnector,
	"wise": WiseConnector,
	"descartes": GenericCCSConnector,
	"ccnhub": GenericCCSConnector,
}


def get_ccs_provider_doc(provider_name: str):
	if not provider_name:
		return None
	if not frappe.db.exists("CCS Provider", provider_name):
		return None
	return frappe.get_doc("CCS Provider", provider_name)


def get_ccs_connector(settings) -> BaseCCSConnector:
	provider_name = getattr(settings, "ccs_provider", None)
	provider_doc = get_ccs_provider_doc(provider_name)
	if not provider_doc:
		frappe.throw(frappe._("CCS Provider {0} was not found.").format(provider_name or ""))

	connector_type = provider_doc.connector_type or "generic"
	connector_cls = CONNECTOR_MAP.get(connector_type, GenericCCSConnector)
	return connector_cls(settings, provider_doc)


def resolve_ccs_endpoint(settings, test_mode: bool = False) -> Tuple[Optional[str], str]:
	connector = get_ccs_connector(settings)
	return connector.resolve_endpoint(test_mode=test_mode)


def uses_ccs_hub(settings) -> bool:
	return (
		getattr(settings, "connection_mode", None) == "CCS Hub"
		and getattr(settings, "ccs_provider", None)
		and getattr(settings, "cargo_xml_enabled", 0)
	)
