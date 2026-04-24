# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Align Custom Field depends_on for charge weight-break buttons (after HTML→Button migration / prior clears)."""

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
]
DEPENDS_ON = {
	"selling_weight_break": "eval:doc.revenue_calculation_method=='Weight Break'",
	"cost_weight_break": "eval:doc.cost_calculation_method=='Weight Break'",
}


def execute():
	for dt in CHARGE_DOCTYPES:
		if not frappe.db.exists("DocType", dt):
			continue
		for fieldname, depends_on in DEPENDS_ON.items():
			cf_name = frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname})
			if not cf_name:
				continue
			frappe.db.set_value("Custom Field", cf_name, "depends_on", depends_on)
	frappe.db.commit()
	frappe.clear_cache()
