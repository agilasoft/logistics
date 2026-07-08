# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Validate UNLOCO ports against a Freight Agent's covered locations."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

_DIRECTIONS = frozenset({"Import", "Export", "Domestic"})


def _strip(value: Any) -> str:
	if value is None:
		return ""
	return str(value).strip()


def get_freight_agent_covered_unlocos(freight_agent: str | None) -> set[str]:
	"""Return UNLOCO codes covered by the freight agent."""
	freight_agent = _strip(freight_agent)
	if not freight_agent or not frappe.db.exists("Freight Agent", freight_agent):
		return set()

	rows = frappe.db.get_all(
		"Freight Agent Covered Location",
		filters={"parent": freight_agent, "parenttype": "Freight Agent", "parentfield": "covered_unlocs"},
		pluck="unloco",
	)
	covered = {_strip(u) for u in rows if _strip(u)}
	if covered:
		return covered

	default_unloco = _strip(frappe.db.get_value("Freight Agent", freight_agent, "default_unloco"))
	return {default_unloco} if default_unloco else set()


def freight_agent_has_coverage_defined(freight_agent: str | None) -> bool:
	return bool(get_freight_agent_covered_unlocos(freight_agent))


def _ports_to_validate_for_direction(
	direction: str | None,
	origin_port: str | None,
	destination_port: str | None,
) -> list[tuple[str, str]]:
	direction = _strip(direction)
	origin_port = _strip(origin_port)
	destination_port = _strip(destination_port)
	ports: list[tuple[str, str]] = []

	if direction == "Import":
		if destination_port:
			ports.append((_("Destination Port"), destination_port))
	elif direction == "Export":
		if origin_port:
			ports.append((_("Origin Port"), origin_port))
	elif direction == "Domestic":
		if origin_port:
			ports.append((_("Origin Port"), origin_port))
		if destination_port:
			ports.append((_("Destination Port"), destination_port))
	else:
		if origin_port:
			ports.append((_("Origin Port"), origin_port))
		if destination_port:
			ports.append((_("Destination Port"), destination_port))

	return ports


def _coverage_mismatch_message(
	freight_agent: str,
	field_label: str,
	port: str,
	*,
	context_label: str | None = None,
) -> str:
	agent_label = frappe.db.get_value("Freight Agent", freight_agent, "freight_agent_name") or freight_agent
	prefix = f"{context_label}: " if context_label else ""
	return _(
		"{0}Freight Agent {1} does not cover {2} ({3}). "
		"Choose a port from the agent's Covered UNLOCOs or select a different Freight Agent."
	).format(prefix, agent_label, field_label, port)


def validate_freight_agent_covers_ports(
	freight_agent: str | None,
	origin_port: str | None = None,
	destination_port: str | None = None,
	direction: str | None = None,
	*,
	context_label: str | None = None,
) -> None:
	"""Raise when a freight agent is set but required ports are outside its coverage."""
	freight_agent = _strip(freight_agent)
	if not freight_agent:
		return

	covered = get_freight_agent_covered_unlocos(freight_agent)
	if not covered:
		return

	direction = _strip(direction)
	if direction and direction not in _DIRECTIONS:
		direction = None

	for field_label, port in _ports_to_validate_for_direction(direction, origin_port, destination_port):
		if port not in covered:
			frappe.throw(
				_coverage_mismatch_message(
					freight_agent,
					field_label,
					port,
					context_label=context_label,
				),
				title=_("Freight Agent Location Coverage"),
			)


def validate_sales_quote_freight_agent_locations(doc) -> None:
	"""Validate Sales Quote header and Air/Sea charge routing against freight agent coverage."""
	quotation_type = getattr(doc, "quotation_type", None)
	if quotation_type not in ("One-off", "Regular"):
		return
	if getattr(doc, "additional_charge", 0):
		return

	main_service = getattr(doc, "main_service", None)
	doc_direction = _strip(getattr(doc, "direction", None)) or None
	doc_origin = _strip(getattr(doc, "origin_port", None)) or None
	doc_dest = _strip(getattr(doc, "destination_port", None)) or None

	if main_service == "Air":
		validate_freight_agent_covers_ports(
			getattr(doc, "freight_agent", None),
			doc_origin,
			doc_dest,
			doc_direction,
			context_label=_("Sales Quote"),
		)
	elif main_service == "Sea":
		validate_freight_agent_covers_ports(
			getattr(doc, "freight_agent_sea", None),
			doc_origin,
			doc_dest,
			doc_direction,
			context_label=_("Sales Quote"),
		)

	from logistics.utils.charge_service_type import canonical_charge_service_type_for_storage
	from logistics.utils.sales_quote_charge_parameters import effective_charge_row_parameters

	for idx, row in enumerate(getattr(doc, "charges", None) or [], start=1):
		st = canonical_charge_service_type_for_storage(getattr(row, "service_type", None))
		if st == "air":
			agent_field = "freight_agent"
		elif st == "sea":
			agent_field = "freight_agent_sea"
		else:
			continue

		params = effective_charge_row_parameters(row, doc)
		agent = _strip(params.get(agent_field))
		if not agent:
			continue

		direction = _strip(params.get("direction")) or doc_direction
		origin = _strip(params.get("origin_port")) or doc_origin
		destination = _strip(params.get("destination_port")) or doc_dest
		validate_freight_agent_covers_ports(
			agent,
			origin,
			destination,
			direction,
			context_label=_("Charge line {0}").format(idx),
		)


def validate_booking_freight_agent_locations(doc, *, context_label: str | None = None) -> None:
	"""Validate Air/Sea Booking ports against the booking freight agent coverage."""
	label = context_label or frappe.bold(_(doc.doctype))
	validate_freight_agent_covers_ports(
		getattr(doc, "freight_agent", None),
		getattr(doc, "origin_port", None),
		getattr(doc, "destination_port", None),
		getattr(doc, "direction", None),
		context_label=label,
	)


@frappe.whitelist()
def check_freight_agent_covers_ports(
	freight_agent=None,
	origin_port=None,
	destination_port=None,
	direction=None,
):
	"""Desk helper: return coverage result without saving."""
	try:
		validate_freight_agent_covers_ports(
			freight_agent,
			origin_port,
			destination_port,
			direction,
		)
	except frappe.ValidationError as exc:
		return {"valid": False, "message": str(exc)}
	return {"valid": True}
