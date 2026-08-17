# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Address EZA / Economic Zone consistency rules."""

from __future__ import annotations

import frappe
from frappe import _


def validate_address_eza(doc, method=None):
	"""
	When EZA is off: clear Economic Zone.
	When EZA is on: Economic Zone is required.
	"""
	if not doc.meta.has_field("custom_eza"):
		return

	eza_on = cint_truthy(doc.get("custom_eza"))
	zone = (doc.get("custom_economic_zone") or "").strip() if doc.meta.has_field("custom_economic_zone") else ""

	if not eza_on:
		if zone and doc.meta.has_field("custom_economic_zone"):
			doc.custom_economic_zone = None
		return

	if not zone:
		frappe.throw(
			_("Economic Zone is required when EZA is enabled."),
			title=_("Economic Zone Required"),
		)


def cint_truthy(value) -> bool:
	try:
		return int(value or 0) == 1
	except (TypeError, ValueError):
		return bool(value)
