# Copyright (c) 2026, AgilaSoft and contributors
"""Copy Air Shipment routing legs onto Air Consolidation routes (issue #945)."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import frappe
from frappe import _
from frappe.utils import add_days, cstr, getdate, today

# Shipment ETD/ETA are dates only; consolidation routes require Time fields.
DEFAULT_ROUTE_DEPARTURE_TIME = "00:00:00"
DEFAULT_ROUTE_ARRIVAL_TIME = "00:00:00"


def _default_route_timing_fields() -> Dict[str, str]:
	return {
		"departure_time": DEFAULT_ROUTE_DEPARTURE_TIME,
		"arrival_time": DEFAULT_ROUTE_ARRIVAL_TIME,
	}


def air_routing_signature(
	origin: Optional[str],
	destination: Optional[str],
	airline: Optional[str],
	flight: Optional[str],
	etd_date: Any,
) -> Tuple[str, str, str, str, str]:
	"""Normalized tuple for comparing shipment vs consolidation main route."""
	return (
		(origin or "").strip().upper(),
		(destination or "").strip().upper(),
		(airline or "").strip(),
		(flight or "").strip().upper(),
		cstr(getdate(etd_date)) if etd_date else "",
	)


def main_routing_leg_from_shipment(job) -> Any:
	legs = list(job.get("routing_legs") or [])
	main_legs = [leg for leg in legs if (getattr(leg, "type", None) or "").strip() == "Main"]
	if main_legs:
		return main_legs[0]
	return legs[0] if legs else None


def routing_signature_from_shipment(shipment_name: str) -> Tuple[str, str, str, str, str]:
	job = frappe.get_doc("Air Shipment", shipment_name)
	leg = main_routing_leg_from_shipment(job)
	if leg:
		return air_routing_signature(
			getattr(leg, "load_port", None) or job.origin_port,
			getattr(leg, "discharge_port", None) or job.destination_port,
			getattr(leg, "airline", None) or job.airline,
			getattr(leg, "flight_no", None),
			getattr(leg, "etd", None) or job.etd,
		)
	return air_routing_signature(
		job.origin_port,
		job.destination_port,
		job.airline,
		None,
		job.etd,
	)


def routing_signature_from_consolidation_route(route) -> Tuple[str, str, str, str, str]:
	return air_routing_signature(
		getattr(route, "origin_airport", None),
		getattr(route, "destination_airport", None),
		getattr(route, "airline", None),
		getattr(route, "flight_number", None),
		getattr(route, "departure_date", None),
	)


def consolidation_route_row_from_shipment_leg(leg, job) -> Dict[str, Any]:
	"""Map one Air Shipment Routing Leg to an Air Consolidation Routes child row dict."""
	leg_type = (getattr(leg, "type", None) or "").strip()
	route_type = "Direct" if leg_type == "Main" else "Transit"
	origin = getattr(leg, "load_port", None) or job.origin_port
	dest = getattr(leg, "discharge_port", None) or job.destination_port
	airline = getattr(leg, "airline", None) or job.airline
	flight = (getattr(leg, "flight_no", None) or "").strip() or "TBA"
	dep = getdate(getattr(leg, "etd", None) or job.etd) or today()
	arr = getdate(getattr(leg, "eta", None) or job.eta) or add_days(dep, 1)
	return {
		"route_type": route_type,
		"origin_airport": origin,
		"destination_airport": dest,
		"airline": airline,
		"flight_number": flight,
		"departure_date": dep,
		"arrival_date": arr,
		"dangerous_goods_allowed": 1,
		**_default_route_timing_fields(),
	}


def consolidation_route_row_from_shipment_header(job) -> Dict[str, Any]:
	"""Single Direct leg when the shipment has no routing_legs rows."""
	dep = getdate(job.etd) or today()
	arr = getdate(job.eta) or add_days(dep, 1)
	return {
		"route_type": "Direct",
		"origin_airport": job.origin_port,
		"destination_airport": job.destination_port,
		"airline": job.airline,
		"flight_number": "TBA",
		"departure_date": dep,
		"arrival_date": arr,
		"dangerous_goods_allowed": 1,
		**_default_route_timing_fields(),
	}


def shipment_legs_for_consolidation_copy(job) -> list:
	"""Legs to copy: prefer rows with flight/port data; Main legs ordered first."""
	legs = list(job.get("routing_legs") or [])
	if not legs:
		return []

	def _has_route_data(leg) -> bool:
		return bool(
			getattr(leg, "load_port", None)
			or getattr(leg, "discharge_port", None)
			or getattr(leg, "flight_no", None)
			or getattr(leg, "airline", None)
		)

	candidates = [leg for leg in legs if _has_route_data(leg)] or legs

	def _sort_key(leg):
		return 0 if (getattr(leg, "type", None) or "").strip() == "Main" else 1

	return sorted(candidates, key=_sort_key)
