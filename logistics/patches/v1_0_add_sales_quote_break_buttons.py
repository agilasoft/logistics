# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Add missing Qty Break buttons and ensure Weight/Qty Break buttons in Sales Quote charge tables."""

import frappe

SALES_QUOTE_CHARGE_DOCTYPES = [
	"Sales Quote Air Freight",
	"Sales Quote Sea Freight",
]

# Qty Break buttons - missing from Sales Quote child doctypes
QTY_BREAK_BUTTONS = [
	{
		"fieldname": "selling_qty_break",
		"fieldtype": "Button",
		"label": "Qty Break",
		"insert_after": "selling_weight_break",
		"depends_on": "eval:doc.calculation_method == 'Qty Break'",
	},
	{
		"fieldname": "cost_qty_break",
		"fieldtype": "Button",
		"label": "Qty Break",
		"insert_after": "cost_weight_break",
		"depends_on": "eval:doc.cost_calculation_method == 'Qty Break'",
	},
]


def execute():
	for dt in SALES_QUOTE_CHARGE_DOCTYPES:
		if not frappe.db.exists("DocType", dt):
			continue
		meta = frappe.get_meta(dt)
		for fdef in QTY_BREAK_BUTTONS:
			if meta.get_field(fdef["fieldname"]):
				continue
			insert_after = fdef.get("insert_after")
			if not meta.get_field(insert_after):
				# Fallback: use cost_weight_break or selling_weight_break or first suitable field
				insert_after = "cost_weight_break" if "cost" in fdef["fieldname"] else "selling_weight_break"
			if not meta.get_field(insert_after):
				for f in meta.fields:
					if f.fieldtype not in ("Section Break", "Column Break") and f.fieldname:
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
				"in_list_view": 1,
			})
			doc.insert(ignore_permissions=True)
			meta = frappe.get_meta(dt)

		# Ensure break buttons are visible in list view (grid columns)
		for fieldname in ("selling_weight_break", "cost_weight_break", "selling_qty_break", "cost_qty_break"):
			field = meta.get_field(fieldname)
			if field and not field.in_list_view:
				# Update DocField or Custom Field
				if frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname}):
					frappe.db.sql("""
						UPDATE `tabCustom Field` SET in_list_view = 1
						WHERE dt = %s AND fieldname = %s
					""", (dt, fieldname))
				else:
					frappe.db.sql("""
						UPDATE tabDocField SET in_list_view = 1
						WHERE parent = %s AND fieldname = %s
					""", (dt, fieldname))
	frappe.db.commit()
