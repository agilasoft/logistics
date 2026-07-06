# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

from typing import Any, Dict, Optional

import frappe
import requests


def validate_before_submit(
	content: str,
	message_type: str,
	settings=None,
	connector=None,
) -> Dict[str, Any]:
	"""Local schema checks plus optional remote IATA Cargo-XML AutoCheck validation."""
	from logistics.air_freight.iata_cargo_xml.base_connector import IATAConnector

	connector = connector or IATAConnector()
	local = connector.validate_message(content, message_type)
	if not local.get("valid"):
		return local

	autocheck_url = None
	if settings:
		autocheck_url = getattr(settings, "cargo_xml_autocheck_url", None)

	if not autocheck_url:
		return local

	try:
		response = requests.post(
			autocheck_url,
			data=content,
			headers={"Content-Type": "application/xml", "Accept": "application/json"},
			timeout=30,
		)
		if response.status_code != 200:
			local.setdefault("warnings", []).append(
				f"AutoCheck HTTP {response.status_code}: {response.text[:200]}"
			)
			return local

		payload = response.json() if "json" in (response.headers.get("Content-Type") or "") else {}
		if payload.get("valid") is False:
			errors = payload.get("errors") or [payload.get("message") or "AutoCheck rejected message"]
			return {"valid": False, "errors": errors, "warnings": local.get("warnings", [])}

		local.setdefault("warnings", []).append("Passed remote Cargo-XML AutoCheck")
		return local
	except Exception as exc:
		frappe.log_error(f"Cargo-XML AutoCheck error: {exc}")
		local.setdefault("warnings", []).append(f"AutoCheck unavailable: {exc}")
		return local
