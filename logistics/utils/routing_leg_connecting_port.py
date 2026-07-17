# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Default connecting start port from the previous routing leg's end port."""

from __future__ import annotations

from typing import Any

# Child doctype → (start_field, end_field)
ROUTING_LEG_PORT_FIELDS: dict[str, tuple[str, str]] = {
	"Air Booking Routing Leg": ("load_port", "discharge_port"),
	"Air Shipment Routing Leg": ("load_port", "discharge_port"),
	"Sea Booking Routing Leg": ("load_port", "discharge_port"),
	"Sea Shipment Routing Leg": ("load_port", "discharge_port"),
	"Sales Quote Routing Leg": ("origin", "destination"),
}

PARENT_ROUTING_LEG_CHILD: dict[str, str] = {
	"Air Booking": "Air Booking Routing Leg",
	"Air Shipment": "Air Shipment Routing Leg",
	"Sea Booking": "Sea Booking Routing Leg",
	"Sea Shipment": "Sea Shipment Routing Leg",
	"Sales Quote": "Sales Quote Routing Leg",
}


def _strip(value: Any) -> str:
	if value is None:
		return ""
	return str(value).strip()


def _row_get(row: Any, fieldname: str) -> Any:
	if row is None:
		return None
	if isinstance(row, dict):
		return row.get(fieldname)
	return getattr(row, fieldname, None)


def connecting_start_port_for_new_leg(
	legs: list[Any],
	new_leg_name: str,
	*,
	child_doctype: str | None = None,
	parent_doctype: str | None = None,
) -> str | None:
	"""
	Return the previous leg's end port to use as the new leg's start port.

	Only for an empty start on the new leg. Returns None when there is nothing to fill.
	"""
	if child_doctype is None and parent_doctype:
		child_doctype = PARENT_ROUTING_LEG_CHILD.get(parent_doctype)
	if not child_doctype:
		return None

	fields = ROUTING_LEG_PORT_FIELDS.get(child_doctype)
	if not fields:
		return None
	start_field, end_field = fields

	ordered = sorted(legs or [], key=lambda r: int(_row_get(r, "idx") or 0))
	pos = next((i for i, leg in enumerate(ordered) if _row_get(leg, "name") == new_leg_name), -1)
	if pos <= 0:
		return None

	new_leg = ordered[pos]
	if _strip(_row_get(new_leg, start_field)):
		return None

	prev_end = _strip(_row_get(ordered[pos - 1], end_field))
	return prev_end or None


def apply_connecting_port_default_to_row(
	legs: list[Any],
	new_leg: Any,
	*,
	child_doctype: str | None = None,
	parent_doctype: str | None = None,
) -> str | None:
	"""Set start port on ``new_leg`` from previous end when empty. Returns the value set, or None."""
	if child_doctype is None and parent_doctype:
		child_doctype = PARENT_ROUTING_LEG_CHILD.get(parent_doctype)
	if not child_doctype:
		return None

	fields = ROUTING_LEG_PORT_FIELDS.get(child_doctype)
	if not fields:
		return None
	start_field, _end_field = fields

	name = _row_get(new_leg, "name")
	if not name:
		return None

	value = connecting_start_port_for_new_leg(
		legs,
		name,
		child_doctype=child_doctype,
		parent_doctype=parent_doctype,
	)
	if not value:
		return None

	if isinstance(new_leg, dict):
		new_leg[start_field] = value
	else:
		new_leg.set(start_field, value)
	return value
