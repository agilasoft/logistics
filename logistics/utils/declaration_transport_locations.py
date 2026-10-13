# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Location and container rules when a Declaration creates a Transport Order.

The Linked Service is the only source for Location Type, Location From, and
Location To. Declaration ports are not copied, and an empty from/to on the
service stays empty on the transport order.
"""

from __future__ import annotations

from typing import Any


class DeclarationContainerChoiceError(Exception):
	"""The user must pick a declaration container, or the pick does not match."""

	def __init__(self, code: str):
		self.code = code
		super().__init__(code)


def _text(row: Any, fieldname: str) -> str:
	if row is None:
		return ""
	if isinstance(row, dict):
		value = row.get(fieldname)
	else:
		value = getattr(row, fieldname, None)
	if value is None:
		return ""
	return str(value).strip()


def linked_service_transport_locations(row: Any) -> dict[str, str | None]:
	"""Location Type / From / To stored on the linked service row.

	Missing values stay empty. This does not fall back to ports or to UNLOCO.
	"""
	return {
		"location_type": _text(row, "location_type") or None,
		"location_from": _text(row, "location_from") or None,
		"location_to": _text(row, "location_to") or None,
	}


def apply_linked_service_locations(order: Any, row: Any) -> None:
	"""Write linked-service locations onto the transport order, including blanks."""
	locations = linked_service_transport_locations(row)
	order.location_type = locations["location_type"]
	order.location_from = locations["location_from"]
	order.location_to = locations["location_to"]


def choose_declaration_container(
	containers: list[dict[str, Any]] | None,
	*,
	linked_container_no: str | None,
	selected: str | None,
) -> dict[str, Any] | None:
	"""Decide which declaration container the new transport order carries.

	A container number already on the linked service wins, and this returns
	None so the caller leaves that value alone. One container on the
	declaration is used automatically. Several containers require ``selected``
	to match a container link or container number.
	"""
	if (linked_container_no or "").strip():
		return None

	rows = list(containers or [])
	picked = (selected or "").strip()
	if picked:
		for row in rows:
			keys = {
				(row.get("container") or "").strip(),
				(row.get("container_number") or "").strip(),
			}
			if picked in keys:
				return row
		raise DeclarationContainerChoiceError("invalid")

	if len(rows) == 1:
		return rows[0]
	if len(rows) > 1:
		raise DeclarationContainerChoiceError("required")
	return None
