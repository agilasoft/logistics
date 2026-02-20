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
	Return default weight_uom, volume_uom, chargeable_uom from Logistics Settings (single source).
	Domain is ignored; all measurement defaults come from Logistics Settings.

	Args:
		domain: One of "transport", "air", "sea", "warehousing" (kept for API compatibility).
		company: Optional company (passed to get_default_uoms for compatibility).

	Returns:
		Dict with keys weight_uom, volume_uom, chargeable_uom.
	"""
	from logistics.utils.measurements import get_default_uoms
	out = {"weight_uom": None, "volume_uom": None, "chargeable_uom": None}
	try:
		uoms = get_default_uoms(company=company)
		out["weight_uom"] = uoms.get("weight")
		out["volume_uom"] = uoms.get("volume")
		out["chargeable_uom"] = uoms.get("chargeable_weight")
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
