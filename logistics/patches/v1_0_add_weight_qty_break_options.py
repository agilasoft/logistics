# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Add Weight Break and Qty Break options to calculation_method and cost_calculation_method in charge doctypes."""

import frappe

CHARGE_DOCTYPES = [
	"Air Booking Charges",
	"Air Shipment Charges",
	"Sea Booking Charges",
	"Sea Freight Charges",
	"Transport Order Charges",
	"Transport Job Charges",
	"Declaration Charges",
	"Declaration Order Charges",
]

BREAK_OPTIONS = "\nWeight Break\nQty Break"


def execute():
	for dt in CHARGE_DOCTYPES:
		if not frappe.db.exists("DocType", dt):
			continue
		meta = frappe.get_meta(dt)
		updated = False

		for fieldname in ("calculation_method", "cost_calculation_method"):
			field = meta.get_field(fieldname)
			if not field or not field.options:
				continue
			opts = field.options or ""
			if "Weight Break" in opts and "Qty Break" in opts:
				continue
			# Add options if missing
			new_opts = opts.rstrip()
			if "Weight Break" not in new_opts:
				new_opts += BREAK_OPTIONS
			elif "Qty Break" not in new_opts:
				new_opts += "\nQty Break"
			if new_opts != opts:
				frappe.db.set_value(
					"DocField",
					{"parent": dt, "fieldname": fieldname},
					"options",
					new_opts,
				)
				updated = True

		if updated:
			frappe.clear_cache(doctype=dt)
	frappe.db.commit()
