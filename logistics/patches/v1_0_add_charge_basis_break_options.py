# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Add Weight Break and Qty Break options to charge_basis for charge doctypes that use it."""

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
		field = meta.get_field("charge_basis")
		if not field or not field.options:
			continue
		opts = field.options or ""
		if "Weight Break" in opts and "Qty Break" in opts:
			continue
		new_opts = opts.rstrip()
		if "Weight Break" not in new_opts:
			new_opts += BREAK_OPTIONS
		elif "Qty Break" not in new_opts:
			new_opts += "\nQty Break"
		if new_opts != opts:
			frappe.db.set_value(
				"DocField",
				{"parent": dt, "fieldname": "charge_basis"},
				"options",
				new_opts,
			)
			frappe.clear_cache(doctype=dt)
	frappe.db.commit()
