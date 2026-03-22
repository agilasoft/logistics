# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Add Weight Break and Qty Break button fields to charge doctypes."""

import frappe

CHARGE_DOCTYPES = [
	"Air Booking Charges",
	"Air Shipment Charges",
	"Sea Booking Charges",
	"Sea Shipment Charges",
	"Transport Order Charges",
	"Transport Job Charges",
	"Declaration Charges",
	"Declaration Order Charges",
]

BUTTON_FIELDS = [
	{
		"fieldname": "selling_weight_break",
		"fieldtype": "Button",
		"label": "Weight Break",
		"insert_after": "unit_type",
		"depends_on": "eval:doc.calculation_method == 'Weight Break'",
	},
	{
		"fieldname": "cost_weight_break",
		"fieldtype": "Button",
		"label": "Weight Break",
		"insert_after": "selling_weight_break",
		"depends_on": "eval:doc.cost_calculation_method == 'Weight Break'",
	},
	{
		"fieldname": "selling_qty_break",
		"fieldtype": "Button",
		"label": "Qty Break",
		"insert_after": "cost_weight_break",
		"depends_on": "eval:doc.calculation_method == 'Qty Break'",
	},
	{
		"fieldname": "cost_qty_break",
		"fieldtype": "Button",
		"label": "Qty Break",
		"insert_after": "selling_qty_break",
		"depends_on": "eval:doc.cost_calculation_method == 'Qty Break'",
	},
]


def execute():
	for dt in CHARGE_DOCTYPES:
		if not frappe.db.exists("DocType", dt):
			continue
		meta = frappe.get_meta(dt)
		last_insert = None
		for fdef in BUTTON_FIELDS:
			if meta.get_field(fdef["fieldname"]):
				last_insert = fdef["fieldname"]
				continue
			insert_after = fdef.get("insert_after")
			if not meta.get_field(insert_after):
				insert_after = last_insert or "unit_type" or "calculation_method" or "quantity"
			if not meta.get_field(insert_after):
				for f in meta.fields:
					if f.fieldtype not in ("Section Break", "Column Break"):
						insert_after = f.fieldname
						break
			if not insert_after:
				continue
			doc = frappe.get_doc({
				"doctype": "Custom Field",
				"dt": dt,
				"fieldname": fdef["fieldname"],
				"fieldtype": "Button",
				"label": fdef["label"],
				"insert_after": insert_after,
				"depends_on": fdef.get("depends_on"),
			})
			doc.insert(ignore_permissions=True)
			last_insert = fdef["fieldname"]
			meta = frappe.get_meta(dt)  # Refresh meta after add
	frappe.db.commit()
