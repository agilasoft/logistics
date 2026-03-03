# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Fix Weight Break/Qty Break button depends_on to support both calculation_method and charge_basis."""

import frappe

# doctypes that use charge_basis for selling (e.g. Air Booking Charges)
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

# depends_on that checks both calculation_method and charge_basis
DEPENDS_ON_MAP = {
	"selling_weight_break": "eval:(doc.calculation_method or doc.charge_basis) == 'Weight Break'",
	"cost_weight_break": "eval:(doc.cost_calculation_method or doc.cost_charge_basis) == 'Weight Break'",
	"selling_qty_break": "eval:(doc.calculation_method or doc.charge_basis) == 'Qty Break'",
	"cost_qty_break": "eval:(doc.cost_calculation_method or doc.cost_charge_basis) == 'Qty Break'",
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
