# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

from typing import Any, Dict, List

import frappe
import requests


def validate_dangerous_goods(air_shipment: str, settings) -> Dict[str, Any]:
	if not settings or not settings.dg_autocheck_enabled:
		return {"success": False, "error": "DG AutoCheck is not enabled"}

	api_key = settings.get_password("dg_autocheck_api_key", raise_exception=False) if hasattr(settings, "get_password") else None
	if not api_key:
		return {"success": False, "error": "DG AutoCheck API key is not configured"}

	ship = frappe.get_doc("Air Shipment", air_shipment)
	dg_lines: List[Dict[str, str]] = []
	for pkg in ship.get("packages") or []:
		if not pkg.dg_substance and not getattr(pkg, "un_number", None):
			continue
		dg_lines.append(
			{
				"un_number": getattr(pkg, "un_number", None) or pkg.dg_substance,
				"dg_class": pkg.dg_class,
				"packing_group": getattr(pkg, "packing_group", None),
				"proper_shipping_name": getattr(pkg, "proper_shipping_name", None),
			}
		)

	if not dg_lines:
		return {"success": True, "message": "No dangerous goods on shipment", "validated": []}

	endpoint = frappe.conf.get("iata_dg_autocheck_url") or "https://www.iata.org/api/dg-autocheck/validate"
	response = requests.post(
		endpoint,
		json={"shipment": air_shipment, "items": dg_lines},
		headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
		timeout=30,
	)
	success = response.status_code == 200
	return {
		"success": success,
		"validated": dg_lines,
		"response": response.text[:1000],
		"error": None if success else response.text[:500],
	}
