# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Promote Unit Breaks from Custom Fields onto charge DocTypes (#1397).

Deletes leftover Custom Field rows without dropping columns so native DocFields
from JSON keep the existing checkbox values.
"""

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

UNIT_BREAK_FIELDS = [
	"use_unit_breaks",
	"selling_unit_break",
	"cost_use_unit_breaks",
	"cost_unit_break",
]


def execute():
	for dt in CHARGE_DOCTYPES:
		if not frappe.db.exists("DocType", dt):
			continue
		for fieldname in UNIT_BREAK_FIELDS:
			# Bypass Document.on_trash so the table column is kept for the DocField.
			frappe.db.delete("Custom Field", {"dt": dt, "fieldname": fieldname})
		frappe.clear_cache(doctype=dt)
	frappe.clear_cache()
