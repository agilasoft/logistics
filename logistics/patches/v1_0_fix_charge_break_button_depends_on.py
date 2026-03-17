# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Fix Weight Break/Qty Break button depends_on to use calculation_method."""

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

DEPENDS_ON_MAP = {
	"selling_weight_break": "eval:doc.revenue_calculation_method == 'Weight Break'",
	"cost_weight_break": "eval:doc.cost_calculation_method == 'Weight Break'",
	"selling_qty_break": "eval:doc.revenue_calculation_method == 'Qty Break'",
	"cost_qty_break": "eval:doc.cost_calculation_method == 'Qty Break'",
}


def execute():
	for dt in CHARGE_DOCTYPES:
		if not frappe.db.exists("DocType", dt):
			continue
		for fieldname, depends_on in DEPENDS_ON_MAP.items():
			cf = frappe.db.exists(
				"Custom Field",
				{"dt": dt, "fieldname": fieldname},
			)
			if cf:
				frappe.db.set_value("Custom Field", cf, "depends_on", depends_on)
	frappe.db.commit()
	frappe.clear_cache()
