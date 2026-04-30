# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Remove depends_on from Custom Field copies of charge weight-break HTML fields (keeps them visible for client stubs/editor)."""

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
FIELDNAMES = ("selling_weight_break", "cost_weight_break")


def execute():
	for dt in CHARGE_DOCTYPES:
		if not frappe.db.exists("DocType", dt):
			continue
		for fieldname in FIELDNAMES:
			cf_name = frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname})
			if not cf_name:
				continue
			frappe.db.set_value("Custom Field", cf_name, "depends_on", None)
	frappe.db.commit()
	frappe.clear_cache()
