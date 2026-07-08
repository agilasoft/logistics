# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

from typing import Any, Dict, Optional

import frappe


def resolve_airline_pima(airline: Optional[str]) -> Optional[str]:
	"""Return the CCS PIMA routing code for an airline."""
	if not airline:
		return None

	pima = frappe.db.get_value("Airline", airline, "ccs_pima_code")
	if pima:
		return str(pima).strip().upper()

	# Fall back to IATA 2-letter code when PIMA is not configured.
	return frappe.db.get_value("Airline", airline, "two_character_code") or airline


def build_routing_context(
	*,
	airline: Optional[str] = None,
	reference_doctype: Optional[str] = None,
	reference_name: Optional[str] = None,
	awb_number: Optional[str] = None,
) -> Dict[str, Any]:
	return {
		"airline": airline,
		"airline_pima": resolve_airline_pima(airline),
		"reference_doctype": reference_doctype,
		"reference_name": reference_name,
		"awb_number": awb_number,
	}


def resolve_airline_from_reference(
	reference_doctype: Optional[str],
	reference_name: Optional[str],
) -> Optional[str]:
	if not reference_doctype or not reference_name:
		return None

	if reference_doctype == "Master Air Waybill":
		return frappe.db.get_value("Master Air Waybill", reference_name, "airline")
	if reference_doctype == "Air Shipment":
		return frappe.db.get_value("Air Shipment", reference_name, "airline")
	return None
