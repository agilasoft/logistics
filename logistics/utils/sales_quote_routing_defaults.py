# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Default Sales Quote routing legs from Shipper, Consignee, and corridor ports (#1120)."""

from __future__ import annotations

import frappe
from frappe.model.document import Document

_ROUTING_QUOTE_TYPES = frozenset({"Regular", "One-off"})
_ROUTING_MAIN_SERVICES = frozenset({"Air", "Sea", "Transport"})


def _strip(value) -> str | None:
	if value is None:
		return None
	s = str(value).strip()
	return s or None


def _party_default_port(party_name: str | None, party_doctype: str, main_service: str) -> str | None:
	if not party_name:
		return None
	row = (
		frappe.db.get_value(
			party_doctype,
			party_name,
			("default_unloco", "default_airport", "default_seaport"),
			as_dict=True,
		)
		or {}
	)
	if main_service == "Air":
		return _strip(row.get("default_airport")) or _strip(row.get("default_unloco"))
	if main_service == "Sea":
		return _strip(row.get("default_seaport")) or _strip(row.get("default_unloco"))
	return (
		_strip(row.get("default_unloco"))
		or _strip(row.get("default_seaport"))
		or _strip(row.get("default_airport"))
	)


def _default_transport_mode(*, main_service: str | None = None, flag: str | None = None) -> str | None:
	service_flag = flag
	if not service_flag and main_service:
		service_flag = {"Air": "air", "Sea": "sea", "Transport": "transport"}.get(main_service)
	filters = {"is_active": 1}
	if service_flag:
		filters[service_flag] = 1
	names = frappe.get_all("Transport Mode", filters=filters, pluck="name", limit=1)
	if names:
		return names[0]
	if main_service and frappe.db.exists("Transport Mode", main_service):
		return main_service
	return None


def _routing_leg_row(
	*,
	mode: str | None,
	leg_type: str,
	origin: str | None,
	destination: str | None,
	is_main_job: int = 0,
	status: str = "Planned",
	etd=None,
	eta=None,
	notes: str | None = None,
) -> dict:
	return {
		"mode": mode,
		"type": leg_type,
		"is_main_job": is_main_job,
		"status": status or "Planned",
		"origin": origin,
		"destination": destination,
		"etd": etd,
		"eta": eta,
		"notes": notes,
	}


def _normalize_main_job_flags(legs: list[dict]) -> list[dict]:
	main_assigned = False
	for leg in legs:
		if leg.get("type") == "Main" and not main_assigned:
			leg["is_main_job"] = 1
			main_assigned = True
		else:
			leg["is_main_job"] = 0
	if legs and not main_assigned:
		legs[0]["is_main_job"] = 1
	return legs


def _legs_from_freight_routing(origin_port: str, destination_port: str) -> list[dict] | None:
	routing_name = frappe.db.get_value(
		"Freight Routing",
		{"origin": origin_port, "destination": destination_port, "docstatus": 1},
		"name",
		order_by="modified desc",
	)
	if not routing_name:
		return None
	routing_doc = frappe.get_doc("Freight Routing", routing_name)
	rows: list[dict] = []
	for item in routing_doc.get("routes") or []:
		rows.append(
			_routing_leg_row(
				mode=_strip(getattr(item, "mode", None)),
				leg_type=_strip(getattr(item, "type", None)) or "Main",
				origin=_strip(getattr(item, "loading_port", None)),
				destination=_strip(getattr(item, "discharge_port", None)),
				status=_strip(getattr(item, "status", None)) or "Planned",
				etd=getattr(item, "etd", None),
				eta=getattr(item, "eta", None),
				notes=_strip(getattr(item, "notes", None)),
			)
		)
	return _normalize_main_job_flags(rows) if rows else None


def _legs_from_parties_and_ports(
	*,
	shipper: str,
	consignee: str,
	origin_port: str,
	destination_port: str,
	main_service: str,
	transport_mode: str | None = None,
) -> list[dict]:
	road_mode = _default_transport_mode(flag="transport")
	main_mode = _strip(transport_mode) or _default_transport_mode(main_service=main_service)
	shipper_port = _party_default_port(shipper, "Shipper", main_service)
	consignee_port = _party_default_port(consignee, "Consignee", main_service)

	legs: list[dict] = []
	if shipper_port and shipper_port != origin_port:
		legs.append(
			_routing_leg_row(
				mode=road_mode,
				leg_type="Pre-carriage",
				origin=shipper_port,
				destination=origin_port,
			)
		)
	legs.append(
		_routing_leg_row(
			mode=main_mode,
			leg_type="Main",
			origin=origin_port,
			destination=destination_port,
		)
	)
	if consignee_port and consignee_port != destination_port:
		legs.append(
			_routing_leg_row(
				mode=road_mode,
				leg_type="On-forwarding",
				origin=destination_port,
				destination=consignee_port,
			)
		)
	return _normalize_main_job_flags(legs)


def can_suggest_sales_quote_routing_legs(doc) -> bool:
	if getattr(doc, "additional_charge", 0):
		return False
	if getattr(doc, "quotation_type", None) not in _ROUTING_QUOTE_TYPES:
		return False
	if getattr(doc, "main_service", None) not in _ROUTING_MAIN_SERVICES:
		return False
	return bool(
		_strip(getattr(doc, "shipper", None))
		and _strip(getattr(doc, "consignee", None))
		and _strip(getattr(doc, "origin_port", None))
		and _strip(getattr(doc, "destination_port", None))
	)


def suggest_sales_quote_routing_legs(
	*,
	shipper: str | None = None,
	consignee: str | None = None,
	origin_port: str | None = None,
	destination_port: str | None = None,
	main_service: str | None = None,
	transport_mode: str | None = None,
) -> list[dict]:
	"""Return routing leg row dicts for Sales Quote Routing Leg child table."""
	shipper = _strip(shipper)
	consignee = _strip(consignee)
	origin_port = _strip(origin_port)
	destination_port = _strip(destination_port)
	main_service = _strip(main_service)

	if not (shipper and consignee and origin_port and destination_port and main_service):
		return []
	if main_service not in _ROUTING_MAIN_SERVICES:
		return []

	from_master = _legs_from_freight_routing(origin_port, destination_port)
	if from_master:
		return from_master

	return _legs_from_parties_and_ports(
		shipper=shipper,
		consignee=consignee,
		origin_port=origin_port,
		destination_port=destination_port,
		main_service=main_service,
		transport_mode=transport_mode,
	)


def apply_sales_quote_routing_defaults(doc: Document, *, force: bool = False) -> bool:
	"""Populate ``routing_legs`` when empty (or when ``force``) and corridor inputs are complete."""
	if not force and (getattr(doc, "routing_legs", None) or []):
		return False
	if not can_suggest_sales_quote_routing_legs(doc):
		return False

	rows = suggest_sales_quote_routing_legs(
		shipper=getattr(doc, "shipper", None),
		consignee=getattr(doc, "consignee", None),
		origin_port=getattr(doc, "origin_port", None),
		destination_port=getattr(doc, "destination_port", None),
		main_service=getattr(doc, "main_service", None),
		transport_mode=getattr(doc, "transport_mode", None),
	)
	if not rows:
		return False

	doc.set("routing_legs", [])
	for row in rows:
		doc.append("routing_legs", row)
	return True


@frappe.whitelist()
def get_suggested_sales_quote_routing_legs(
	shipper=None,
	consignee=None,
	origin_port=None,
	destination_port=None,
	main_service=None,
	transport_mode=None,
):
	"""Desk API: suggested routing legs for Sales Quote (#1120)."""
	origin_port = _strip(origin_port)
	destination_port = _strip(destination_port)
	from_master = (
		_legs_from_freight_routing(origin_port, destination_port)
		if origin_port and destination_port
		else None
	)
	legs = (
		from_master
		if from_master
		else suggest_sales_quote_routing_legs(
			shipper=shipper,
			consignee=consignee,
			origin_port=origin_port,
			destination_port=destination_port,
			main_service=main_service,
			transport_mode=transport_mode,
		)
	)
	source = "freight_routing" if from_master else ("parties_and_ports" if legs else None)
	return {"legs": legs, "source": source}
