# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Map Sales Quote multimodal routing legs onto Sea / Air Booking routing child tables."""

from __future__ import annotations

import frappe
from frappe.model.document import Document

from frappe.utils import cint

from logistics.utils.service_role_rules import (
	get_main_service_name,
	get_main_service_type,
	is_linked_service_satellite,
)
from logistics.utils.transport_mode_flags import get_air_sea_flags_for_transport_mode

_SEA_ROUTING_OPERATIONAL_FIELDS = ("vessel", "voyage_no", "shipping_line")
_AIR_ROUTING_OPERATIONAL_FIELDS = ("flight_no", "airline")
_MAIN_JOB_ROUTING_OVERLAY_DOCTYPES = frozenset(
	("Sea Shipment", "Air Shipment", "Sea Booking", "Air Booking")
)


def _routing_row_get(row, fieldname: str):
	if row is None:
		return None
	if isinstance(row, dict):
		return row.get(fieldname)
	return getattr(row, fieldname, None)


def _routing_row_ports(leg) -> tuple[str, str]:
	return (
		(_routing_row_get(leg, "load_port") or "").strip(),
		(_routing_row_get(leg, "discharge_port") or "").strip(),
	)


def _find_matching_main_job_routing_leg(booking_leg, main_legs: list) -> object | None:
	if not main_legs:
		return None
	lp, dp = _routing_row_ports(booking_leg)
	b_sea = cint(_routing_row_get(booking_leg, "transport_mode_sea"))
	b_air = cint(_routing_row_get(booking_leg, "transport_mode_air"))

	if lp and dp:
		port_matches = [ml for ml in main_legs if _routing_row_ports(ml) == (lp, dp)]
		if port_matches:
			for ml in port_matches:
				if (
					cint(_routing_row_get(ml, "transport_mode_sea")) == b_sea
					and cint(_routing_row_get(ml, "transport_mode_air")) == b_air
				):
					return ml
			return port_matches[0]

	if b_sea:
		for ml in main_legs:
			if cint(_routing_row_get(ml, "transport_mode_sea")):
				return ml
	if b_air:
		for ml in main_legs:
			if cint(_routing_row_get(ml, "transport_mode_air")):
				return ml

	sorted_legs = sorted(main_legs, key=lambda r: cint(_routing_row_get(r, "idx")))
	for ml in sorted_legs:
		if (_routing_row_get(ml, "type") or "").strip() == "Main":
			return ml
	return sorted_legs[0]


def _copy_routing_operational_fields(target_leg, source_leg, field_names: tuple[str, ...]) -> None:
	for fn in field_names:
		val = _routing_row_get(source_leg, fn)
		if val is not None and val != "":
			target_leg.set(fn, val)


def _main_job_sea_routing_header_fallbacks(main_job_doc: Document) -> dict[str, object | None]:
	"""Header-level sea corridor values when routing child rows omit them."""
	out: dict[str, object | None] = {}
	if hasattr(main_job_doc, "shipping_line"):
		out["shipping_line"] = getattr(main_job_doc, "shipping_line", None)
	vessel = getattr(main_job_doc, "mbl_vessel", None) or getattr(main_job_doc, "vessel", None)
	voyage = getattr(main_job_doc, "mbl_voyage_no", None) or getattr(main_job_doc, "voyage_no", None)
	if vessel:
		out["vessel"] = vessel
	if voyage:
		out["voyage_no"] = voyage
	return out


def _main_job_air_routing_header_fallbacks(main_job_doc: Document) -> dict[str, object | None]:
	out: dict[str, object | None] = {}
	if hasattr(main_job_doc, "airline"):
		out["airline"] = getattr(main_job_doc, "airline", None)
	flight = getattr(main_job_doc, "flight_no", None) or getattr(main_job_doc, "flight_number", None)
	if flight:
		out["flight_no"] = flight
	return out


def apply_main_job_routing_operational_overlay(booking_doc: Document) -> bool:
	"""Copy vessel/voyage/shipping line (and air flight fields) from Main Job routing onto booking legs.

	Used after Sales Quote routing is applied on internal Air/Sea Booking create (#936).
	"""
	if not is_linked_service_satellite(booking_doc):
		return False
	mjt = get_main_service_type(booking_doc)
	mj = get_main_service_name(booking_doc)
	if not mjt or not mj or mjt not in _MAIN_JOB_ROUTING_OVERLAY_DOCTYPES:
		return False
	if not frappe.db.exists(mjt, mj):
		return False
	booking_legs = list(getattr(booking_doc, "routing_legs", None) or [])
	if not booking_legs:
		return False

	try:
		main_job_doc = frappe.get_doc(mjt, mj)
	except Exception:
		return False
	main_legs = list(getattr(main_job_doc, "routing_legs", None) or [])
	if not main_legs:
		return False

	sea_header = _main_job_sea_routing_header_fallbacks(main_job_doc)
	air_header = _main_job_air_routing_header_fallbacks(main_job_doc)
	applied = False

	for booking_leg in booking_legs:
		source_leg = _find_matching_main_job_routing_leg(booking_leg, main_legs)
		if source_leg:
			if cint(_routing_row_get(booking_leg, "transport_mode_sea")):
				_copy_routing_operational_fields(
					booking_leg, source_leg, _SEA_ROUTING_OPERATIONAL_FIELDS
				)
				applied = True
			if cint(_routing_row_get(booking_leg, "transport_mode_air")):
				_copy_routing_operational_fields(
					booking_leg, source_leg, _AIR_ROUTING_OPERATIONAL_FIELDS
				)
				applied = True

		if cint(_routing_row_get(booking_leg, "transport_mode_sea")):
			for fn, val in sea_header.items():
				if val and not _routing_row_get(booking_leg, fn):
					booking_leg.set(fn, val)
					applied = True
		if cint(_routing_row_get(booking_leg, "transport_mode_air")):
			for fn, val in air_header.items():
				if val and not _routing_row_get(booking_leg, fn):
					booking_leg.set(fn, val)
					applied = True

	return applied


def get_booking_routing_rows_from_sales_quote(
	sales_quote_doc: Document,
	booking_doc: Document | None = None,
) -> list[dict]:
	"""
	Build row dicts for Sea Booking Routing Leg / Air Booking Routing Leg from Sales Quote Routing Leg.

	Sales Quote uses origin/destination (UNLOCO); booking legs use load_port/discharge_port.
	Optional booking_doc enriches Sea legs with shipping_line and Air legs with airline when mode matches.
	"""
	rows: list[dict] = []
	for leg in getattr(sales_quote_doc, "routing_legs", None) or []:
		# Align with Sales Quote Routing Leg default (Road) when missing
		mode = getattr(leg, "mode", None) or "Road"
		air_flag, sea_flag = get_air_sea_flags_for_transport_mode(mode)
		row = {
			"mode": mode,
			"type": getattr(leg, "type", None) or "Main",
			"status": getattr(leg, "status", None) or "Planned",
			"charter_route": 0,
			"notes": getattr(leg, "notes", None),
			"load_port": getattr(leg, "origin", None),
			"discharge_port": getattr(leg, "destination", None),
			"etd": getattr(leg, "etd", None),
			"eta": getattr(leg, "eta", None),
			"transport_mode_air": air_flag,
			"transport_mode_sea": sea_flag,
		}
		if booking_doc and getattr(booking_doc, "doctype", None) == "Sea Booking":
			if sea_flag and getattr(booking_doc, "shipping_line", None):
				row["shipping_line"] = booking_doc.shipping_line
		elif booking_doc and getattr(booking_doc, "doctype", None) == "Air Booking":
			if air_flag and getattr(booking_doc, "airline", None):
				row["airline"] = booking_doc.airline
		rows.append(row)
	return rows


def apply_sales_quote_routing_to_booking(booking_doc: Document, sales_quote_doc: Document) -> None:
	"""Replace booking routing_legs from Sales Quote when the quote defines at least one leg."""
	rows = get_booking_routing_rows_from_sales_quote(sales_quote_doc, booking_doc)
	if not rows:
		return
	booking_doc.set("routing_legs", [])
	for row in rows:
		booking_doc.append("routing_legs", row)


def apply_linked_sales_quote_routing_to_booking(booking_doc: Document) -> bool:
	"""Apply routing_legs from ``booking_doc.sales_quote`` when set (internal job create / charge refresh)."""
	sq_name = getattr(booking_doc, "sales_quote", None)
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return False
	try:
		sq = frappe.get_doc("Sales Quote", sq_name)
	except Exception:
		return False
	if not get_booking_routing_rows_from_sales_quote(sq, booking_doc):
		return False
	apply_sales_quote_routing_to_booking(booking_doc, sq)
	return True


def routing_legs_for_api_response(sales_quote_name: str, booking_doc: Document | None = None) -> list[dict]:
	"""Load Sales Quote by name and return routing rows for whitelisted API responses (unsaved forms)."""
	if not sales_quote_name or not frappe.db.exists("Sales Quote", sales_quote_name):
		return []
	sq = frappe.get_doc("Sales Quote", sales_quote_name)
	return get_booking_routing_rows_from_sales_quote(sq, booking_doc)
