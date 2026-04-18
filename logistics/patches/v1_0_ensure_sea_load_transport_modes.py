# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Create Transport Mode masters for sea load types (FCL, LCL, …) used on bookings, quotes, and charge rows.

Sales Quote Sea Freight and related UIs use FCL/LCL as values; unified Sales Quote Charge stores the same
in a Link field, which requires matching ``tabTransport Mode`` rows (name = mode_code).
"""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Transport Mode"):
		return

	# mode_name and primary_document are unique on Transport Mode — avoid colliding with the generic "Sea" row.
	modes = [
		{
			"mode_code": "FCL",
			"mode_name": "Full Container Load",
			"primary_document": "Sea Shipment - FCL",
			"description": "Sea freight — full container load",
			"sea": 1,
		},
		{
			"mode_code": "LCL",
			"mode_name": "Less than Container Load",
			"primary_document": "Sea Shipment - LCL",
			"description": "Sea freight — less than container load",
			"sea": 1,
		},
		{
			"mode_code": "Break Bulk",
			"mode_name": "Break Bulk (Sea)",
			"primary_document": "Sea Shipment - Break Bulk",
			"description": "Sea freight — break bulk",
			"sea": 1,
		},
		{
			"mode_code": "RoRo",
			"mode_name": "Roll-on/Roll-off",
			"primary_document": "Sea Shipment - RoRo",
			"description": "Sea freight — roll-on/roll-off",
			"sea": 1,
		},
	]
	for m in modes:
		if frappe.db.exists("Transport Mode", m["mode_code"]):
			continue
		doc = frappe.new_doc("Transport Mode")
		doc.update(m)
		doc.insert()
