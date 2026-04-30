# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors

"""FCL transport: require container rows with Container No (Sea Shipment / ops)."""

from frappe import _
import frappe


def validate_fcl_container_numbers_required(doc):
	"""
	For FCL transport mode, require at least one container row and a Container No on every row.

	Intended for Sea Shipment submission — Sea Booking stays a booking without this gate.
	"""
	if (getattr(doc, "transport_mode", None) or "").strip() != "FCL":
		return

	containers = getattr(doc, "containers", None) or []
	if not containers:
		frappe.throw(
			_("For FCL mode, add at least one container with Container No before submitting."),
			title=_("Missing Container No"),
		)

	empty_rows = []
	for row in containers:
		if not (getattr(row, "container_no", None) or "").strip():
			empty_rows.append(getattr(row, "idx", None) or "?")

	if empty_rows:
		frappe.throw(
			_("For FCL mode, Container No is mandatory. Fill Container No in row(s): {0}.").format(
				", ".join(str(r) for r in empty_rows)
			),
			title=_("Missing Container No"),
		)
