# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Add Unit Breaks checkbox/button and Value unit type to charge child tables (#1126)."""

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
	"Special Project Charges",
	"Exhibit Charges",
	"MICE Project Charges",
	"Sales Quote Charge",
	"Tariff Charge",
]

UNIT_TYPE_FIELDS = ("unit_type", "cost_unit_type")
VALUE_UNIT_OPTION = "Value"

UNIT_BREAK_FIELDS = [
	{
		"fieldname": "use_unit_breaks",
		"fieldtype": "Check",
		"label": "Unit Breaks",
		"insert_after": "revenue_calc_notes",
		"depends_on": "eval:doc.revenue_calculation_method=='Per Unit' && !['Cost','Disbursement'].includes(doc.charge_type)",
	},
	{
		"fieldname": "selling_unit_break",
		"fieldtype": "Button",
		"label": "Manage Unit Breaks",
		"insert_after": "use_unit_breaks",
		"depends_on": "eval:doc.use_unit_breaks && doc.revenue_calculation_method=='Per Unit' && !['Cost','Disbursement'].includes(doc.charge_type)",
	},
	{
		"fieldname": "cost_use_unit_breaks",
		"fieldtype": "Check",
		"label": "Unit Breaks",
		"insert_after": "cost_calc_notes",
		"depends_on": "eval:doc.cost_calculation_method=='Per Unit' && doc.charge_type != 'Revenue'",
	},
	{
		"fieldname": "cost_unit_break",
		"fieldtype": "Button",
		"label": "Manage Unit Breaks",
		"insert_after": "cost_use_unit_breaks",
		"depends_on": "eval:doc.cost_use_unit_breaks && doc.cost_calculation_method=='Per Unit' && doc.charge_type != 'Revenue'",
	},
]


def _append_value_unit_type(doctype: str) -> None:
	meta = frappe.get_meta(doctype)
	for fieldname in UNIT_TYPE_FIELDS:
		field = meta.get_field(fieldname)
		if not field or not field.options:
			continue
		opts = field.options or ""
		if VALUE_UNIT_OPTION in opts.split("\n"):
			continue
		new_opts = opts.rstrip() + f"\n{VALUE_UNIT_OPTION}"
		frappe.db.set_value(
			"DocField",
			{"parent": doctype, "fieldname": fieldname},
			"options",
			new_opts,
		)


def _rename_breaks_section_label(doctype: str) -> None:
	for fieldname in ("section_break_weight_breaks", "weight_breaks_section", "calculation_notes_section"):
		if frappe.db.exists("DocField", {"parent": doctype, "fieldname": fieldname}):
			frappe.db.set_value(
				"DocField",
				{"parent": doctype, "fieldname": fieldname},
				"label",
				"Breaks",
			)


def _ensure_unit_break_fields(doctype: str) -> None:
	meta = frappe.get_meta(doctype)
	last_insert = None
	for fdef in UNIT_BREAK_FIELDS:
		if meta.get_field(fdef["fieldname"]):
			last_insert = fdef["fieldname"]
			continue
		insert_after = fdef.get("insert_after")
		if not meta.get_field(insert_after):
			insert_after = last_insert or "section_break_weight_breaks" or "cost_calc_notes"
		if not meta.get_field(insert_after):
			for f in meta.fields:
				if f.fieldtype not in ("Section Break", "Column Break"):
					insert_after = f.fieldname
					break
		if not insert_after:
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Custom Field",
				"dt": doctype,
				"fieldname": fdef["fieldname"],
				"fieldtype": fdef["fieldtype"],
				"label": fdef["label"],
				"insert_after": insert_after,
				"depends_on": fdef.get("depends_on"),
			}
		)
		doc.insert(ignore_permissions=True)
		last_insert = fdef["fieldname"]
		meta = frappe.get_meta(doctype)


def execute():
	for dt in CHARGE_DOCTYPES:
		if not frappe.db.exists("DocType", dt):
			continue
		_append_value_unit_type(dt)
		_rename_breaks_section_label(dt)
		_ensure_unit_break_fields(dt)
		frappe.clear_cache(doctype=dt)
	frappe.db.commit()
