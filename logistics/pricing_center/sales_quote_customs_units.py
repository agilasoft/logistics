# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Unit types a Sales Quote customs charge may use."""

from __future__ import annotations


# Aligned with Declaration Charges (includes Value for Percentage Break; Job/Trip supported).
CUSTOMS_ALLOWED_UNIT_TYPES = frozenset({
	"Weight",
	"Volume",
	"Distance",
	"Package",
	"Piece",
	"TEU",
	"Container",
	"Operation Time",
	"Job",
	"Trip",
	"Value",
})
CUSTOMS_ALLOWED_UNIT_TYPES_DISPLAY = (
	"Weight",
	"Volume",
	"Distance",
	"Package",
	"Piece",
	"TEU",
	"Container",
	"Operation Time",
	"Job",
	"Trip",
	"Value",
)


def customs_allowed_unit_types_text():
	"""Quoted unit-type list used in the validation message."""
	return ", ".join(f'"{unit}"' for unit in CUSTOMS_ALLOWED_UNIT_TYPES_DISPLAY)


def customs_unit_type_problem(unit_type, cost_unit_type):
	"""Return ``unit_type`` or ``cost_unit_type`` for the first disallowed value.

	A blank unit type is allowed. Selling unit type is checked before cost unit type.
	"""
	if unit_type and unit_type not in CUSTOMS_ALLOWED_UNIT_TYPES:
		return "unit_type"
	if cost_unit_type and cost_unit_type not in CUSTOMS_ALLOWED_UNIT_TYPES:
		return "cost_unit_type"
	return None
