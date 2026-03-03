# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Remove weight_breaks/qty_breaks Custom Fields; follow Sales Quote pattern (reference-based only)."""

import frappe

TABLE_FIELDS = ["weight_breaks", "qty_breaks"]
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


def execute():
	"""Remove table Custom Fields so weight/qty breaks use Sales Quote Weight Break / Qty Break only."""
	for dt in CHARGE_DOCTYPES:
		for fieldname in TABLE_FIELDS:
			cf = frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname})
			if cf:
				frappe.delete_doc("Custom Field", cf, ignore_permissions=True, force=True)
	frappe.db.commit()
	frappe.clear_cache()
