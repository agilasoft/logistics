# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Show Unit Breaks checkbox only when calculation method is Per Unit (#1397)."""

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
	"MICE Project Consolidation Charges",
	"Change Request Charge",
	"Sales Quote Charge",
	"Tariff Charge",
]

SELLING_CHECK = (
	"eval:doc.revenue_calculation_method=='Per Unit' && "
	"!['Cost','Disbursement'].includes(doc.charge_type)"
)
SELLING_BUTTON = (
	"eval:doc.use_unit_breaks && doc.revenue_calculation_method=='Per Unit' && "
	"!['Cost','Disbursement'].includes(doc.charge_type)"
)
COST_CHECK = "eval:doc.cost_calculation_method=='Per Unit' && doc.charge_type != 'Revenue'"
COST_BUTTON = (
	"eval:doc.cost_use_unit_breaks && doc.cost_calculation_method=='Per Unit' && "
	"doc.charge_type != 'Revenue'"
)
MICE_CONSOL_CHECK = "eval:doc.revenue_calculation_method=='Per Unit'"
MICE_CONSOL_BUTTON = "eval:doc.cost_use_unit_breaks && doc.revenue_calculation_method=='Per Unit'"


def _set_depends_on(doctype: str, fieldname: str, depends_on: str) -> None:
	if not frappe.db.exists("DocType", doctype):
		return
	updated = False
	if frappe.db.exists("DocField", {"parent": doctype, "fieldname": fieldname}):
		frappe.db.set_value(
			"DocField",
			{"parent": doctype, "fieldname": fieldname},
			"depends_on",
			depends_on,
		)
		updated = True
	if frappe.db.exists("Custom Field", {"dt": doctype, "fieldname": fieldname}):
		frappe.db.set_value(
			"Custom Field",
			{"dt": doctype, "fieldname": fieldname},
			"depends_on",
			depends_on,
		)
		updated = True
	if updated:
		frappe.clear_cache(doctype=doctype)


def execute():
	for dt in CHARGE_DOCTYPES:
		if not frappe.db.exists("DocType", dt):
			continue
		meta = frappe.get_meta(dt)
		if dt == "MICE Project Consolidation Charges":
			_set_depends_on(dt, "cost_use_unit_breaks", MICE_CONSOL_CHECK)
			_set_depends_on(dt, "cost_unit_break", MICE_CONSOL_BUTTON)
			continue
		has_rev = bool(meta.get_field("revenue_calculation_method"))
		has_cost = bool(meta.get_field("cost_calculation_method"))
		if meta.get_field("use_unit_breaks") and has_rev:
			_set_depends_on(dt, "use_unit_breaks", SELLING_CHECK)
		if meta.get_field("selling_unit_break") and has_rev:
			_set_depends_on(dt, "selling_unit_break", SELLING_BUTTON)
		if meta.get_field("cost_use_unit_breaks") and has_cost:
			_set_depends_on(dt, "cost_use_unit_breaks", COST_CHECK)
		if meta.get_field("cost_unit_break") and has_cost:
			_set_depends_on(dt, "cost_unit_break", COST_BUTTON)
		frappe.clear_cache(doctype=dt)
