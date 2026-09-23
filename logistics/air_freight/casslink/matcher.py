# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

"""Match CASS billing lines to MAWB / Air Shipment / Airline."""

from __future__ import unicode_literals

from typing import Any, Dict, Optional

import frappe

from logistics.air_freight.casslink.awb import awb_lookup_candidates, digits_only, normalize_awb


def match_line(line: Dict[str, Any], company: Optional[str] = None) -> Dict[str, Any]:
	"""Return match fields for a parsed CASS line."""
	awb = normalize_awb(line.get("awb_number"), line.get("airline_prefix"))
	prefix = digits_only(line.get("airline_prefix") or "")[:3] or (awb[:3] if len(awb) >= 3 else "")
	mawb = find_mawb(awb, prefix) if awb else None
	shipment = find_air_shipment(awb, mawb) if awb else None
	airline = (
		find_airline(prefix, line.get("airline_code"))
		or (mawb.airline if mawb else None)
		or (frappe.db.get_value("Air Shipment", shipment, "airline") if shipment else None)
	)
	supplier = None
	if airline:
		supplier = frappe.db.get_value("Airline", airline, "supplier")
	statement_line = (not awb) and bool(prefix or line.get("airline_code"))
	matched = bool(mawb or shipment or (statement_line and airline))
	return {
		"awb_number": awb,
		"airline_prefix": prefix,
		"master_awb": mawb.name if mawb else None,
		"air_shipment": shipment,
		"airline": airline,
		"supplier": supplier,
		"match_status": "Matched" if matched else "Unmatched",
	}


def find_mawb(awb: Optional[str], prefix: Optional[str] = None):
	candidates = awb_lookup_candidates(awb, prefix)
	if not candidates:
		return None
	normalized = normalize_awb(awb, prefix)
	for value in candidates:
		name = frappe.db.get_value("Master Air Waybill", {"master_awb_no": value}, "name")
		if name:
			return frappe.get_doc("Master Air Waybill", name)
	if normalized:
		row = frappe.db.sql(
			"""
			select name from `tabMaster Air Waybill`
			where replace(replace(ifnull(master_awb_no, ''), '-', ''), ' ', '') = %s
			limit 1
			""",
			(normalized,),
		)
		if row:
			return frappe.get_doc("Master Air Waybill", row[0][0])
	return None


def find_air_shipment(awb: Optional[str], mawb=None) -> Optional[str]:
	if mawb:
		linked = frappe.db.get_value("Air Shipment", {"master_awb": mawb.name}, "name")
		if linked:
			return linked
	candidates = awb_lookup_candidates(awb)
	normalized = normalize_awb(awb)
	for value in candidates:
		for field in ("master_awb", "house_awb_no", "house_awb", "name"):
			if not frappe.get_meta("Air Shipment").has_field(field) and field != "name":
				continue
			name = frappe.db.get_value("Air Shipment", {field: value}, "name")
			if name:
				return name
	if normalized:
		row = frappe.db.sql(
			"""
			select name from `tabAir Shipment`
			where replace(replace(ifnull(master_awb, ''), '-', ''), ' ', '') = %s
			   or replace(replace(ifnull(house_awb_no, ''), '-', ''), ' ', '') = %s
			limit 1
			""",
			(normalized, normalized),
		)
		if row:
			return row[0][0]
	return None


def find_airline(prefix: Optional[str] = None, iata_code: Optional[str] = None) -> Optional[str]:
	code = (iata_code or "").strip().upper()
	if len(code) == 2:
		meta = frappe.get_meta("Airline")
		for field in ("iata_code", "two_character_code"):
			if not meta.has_field(field):
				continue
			name = frappe.db.get_value("Airline", {field: code}, "name")
			if name:
				return name
	pfx = digits_only(prefix or "")
	if not pfx:
		return None
	padded = pfx.zfill(3)[-3:]
	for field, value in (
		("airline_numeric_code", padded),
		("airline_numeric_code", pfx),
		("three_letter_numeric_code", padded),
		("iata_code", pfx),
	):
		if not frappe.get_meta("Airline").has_field(field):
			continue
		name = frappe.db.get_value("Airline", {field: value}, "name")
		if name:
			return name
	return None
