# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

from typing import Any, Dict

import frappe
import requests


def submit_cass_settlement(tx, settings) -> Dict[str, Any]:
	"""Submit CASS settlement request when CASSLink is enabled."""
	if not settings or not settings.cass_enabled:
		return {"success": False, "error": "CASSLink is not enabled"}

	endpoint = settings.cass_api_endpoint
	if not endpoint:
		return {"success": False, "error": "CASS API endpoint is not configured"}

	payload = {
		"participant_code": tx.cass_participant_code or settings.cass_participant_code,
		"air_shipment": tx.air_shipment,
		"billing_reference": tx.cass_billing_reference,
		"settlement_amount": tx.cass_settlement_amount,
		"currency": tx.tact_currency,
	}

	response = requests.post(
		endpoint,
		json=payload,
		timeout=30,
		auth=_cass_auth(settings),
	)
	success = response.status_code in (200, 201, 202)
	result = {"success": success, "status_code": response.status_code, "response": response.text[:1000]}
	if not success:
		result["error"] = response.text[:500]
	return result


def _cass_auth(settings):
	user = getattr(settings, "cass_username", None) or settings.cargo_xml_username
	password = None
	if hasattr(settings, "get_password"):
		password = settings.get_password("cass_password", raise_exception=False)
		password = password or settings.get_password("cargo_xml_password", raise_exception=False)
	if user and password:
		return user, password
	return None
