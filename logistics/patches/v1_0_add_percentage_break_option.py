# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Add Percentage Break option to calculation method fields on charge and rate doctypes."""

import frappe

CHARGE_DOCTYPES = [
	"Air Booking Charges",
	"Air Shipment Charges",
	"Sea Booking Charges",
	"Sea Shipment Charges",
	"Sea Consolidation Charges",
	"Transport Order Charges",
	"Transport Job Charges",
	"Declaration Charges",
	"Declaration Order Charges",
	"Sales Quote Charge",
	"Tariff Charge",
	"Change Request Charge",
	"Special Project Charges",
	"MICE Project Charges",
	"Exhibit Charges",
	"Air Freight Rate",
	"Sea Freight Rate",
	"Transport Rate",
	"Customs Rate",
	"Warehouse Rate",
]

METHOD_FIELDS = (
	"calculation_method",
	"cost_calculation_method",
	"revenue_calculation_method",
)


def execute():
	for dt in CHARGE_DOCTYPES:
		if not frappe.db.exists("DocType", dt):
			continue
		meta = frappe.get_meta(dt)
		updated = False
		for fieldname in METHOD_FIELDS:
			field = meta.get_field(fieldname)
			if not field or not field.options:
				continue
			opts = field.options or ""
			if "Percentage Break" in opts:
				continue
			new_opts = opts.rstrip() + "\nPercentage Break"
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
