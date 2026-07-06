# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

from typing import Any, Dict

import frappe
import requests
from frappe.utils import flt


def lookup_tact_rate(air_shipment: str, settings) -> Dict[str, Any]:
	if not settings or not settings.tact_subscription:
		return {"success": False, "error": "TACT subscription is not enabled"}

	endpoint = settings.tact_endpoint
	api_key = settings.get_password("tact_api_key", raise_exception=False) if hasattr(settings, "get_password") else None
	if not endpoint or not api_key:
		return {"success": False, "error": "TACT endpoint or API key is not configured"}

	ship = frappe.get_doc("Air Shipment", air_shipment)
	payload = {
		"origin": ship.origin_port,
		"destination": ship.destination_port,
		"chargeable_weight": flt(ship.chargeable or ship.weight),
		"airline": ship.airline,
	}

	response = requests.post(
		endpoint,
		json=payload,
		headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
		timeout=30,
	)
	if response.status_code != 200:
		return {"success": False, "error": response.text[:500], "status_code": response.status_code}

	data = response.json() if response.text else {}
	return {
		"success": True,
		"tact_rate_reference": data.get("reference") or data.get("rate_id"),
		"tact_rate_amount": flt(data.get("amount") or data.get("rate")),
		"tact_currency": data.get("currency"),
		"tact_rate_validity": data.get("valid_until"),
		"raw": data,
	}
