# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, see license.txt

"""
Default UOM helpers: return default weight/volume/chargeable UOM from domain-specific Settings.
Used by Sales Quote (per-tab), Transport Job Package, Air/Sea Consolidation Shipments, and other doctypes.
"""

from __future__ import annotations

import frappe
from typing import Optional


def get_default_uoms_for_domain(
	domain: str,
	company: Optional[str] = None,
) -> dict[str, Optional[str]]:
	"""
	Return default weight_uom, volume_uom, chargeable_uom from the Settings for the given domain.

	Args:
		domain: One of "transport", "air", "sea", "warehousing".
		company: Optional company (required for Air Freight Settings and Warehouse Settings, which are company-scoped DocTypes; Transport/Sea use Single doctypes).

	Returns:
		Dict with keys weight_uom, volume_uom, chargeable_uom (values may be None if not set).
	"""
	out = {"weight_uom": None, "volume_uom": None, "chargeable_uom": None}
	domain = (domain or "").strip().lower()

	try:
		if domain == "transport":
			try:
				settings = frappe.get_single("Transport Settings")
			except frappe.DoesNotExistError:
				settings = None
			if settings:
				out["weight_uom"] = getattr(settings, "default_weight_uom", None) or None
				out["volume_uom"] = getattr(settings, "default_volume_uom", None) or None
				out["chargeable_uom"] = getattr(settings, "default_chargeable_uom", None) or None
		elif domain == "air":
			# Air Freight Settings is company-scoped (not Single); use get_settings(company)
			from logistics.air_freight.doctype.air_freight_settings.air_freight_settings import AirFreightSettings
			settings = AirFreightSettings.get_settings(company)
			if settings:
				out["weight_uom"] = getattr(settings, "default_weight_uom", None) or None
				out["volume_uom"] = getattr(settings, "default_volume_uom", None) or None
				out["chargeable_uom"] = getattr(settings, "default_chargeable_uom", None) or None
		elif domain == "sea":
			try:
				settings = frappe.get_single("Sea Freight Settings")
			except frappe.DoesNotExistError:
				settings = None
			if settings:
				out["weight_uom"] = getattr(settings, "default_weight_uom", None) or None
				out["volume_uom"] = getattr(settings, "default_volume_uom", None) or None
				out["chargeable_uom"] = getattr(settings, "default_chargeable_uom", None) or None
		elif domain == "warehousing":
			from logistics.warehousing.doctype.warehouse_settings.warehouse_settings import get_default_uoms
			uoms = get_default_uoms(company=company)
			if uoms:
				out["weight_uom"] = uoms.get("weight")
				out["volume_uom"] = uoms.get("volume")
				out["chargeable_uom"] = uoms.get("chargeable")
	except Exception:
		pass
	return out


@frappe.whitelist()
def get_default_uoms_for_domain_api(domain: str, company: Optional[str] = None):
	"""
	Whitelisted API for client scripts to fetch default UOMs by domain.
	domain: "transport" | "air" | "sea" | "warehousing"
	"""
	return get_default_uoms_for_domain(domain=domain, company=company)
