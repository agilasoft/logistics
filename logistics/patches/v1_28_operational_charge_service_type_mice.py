# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Add MICE (and align Special Project) on operational charge child service_type Select fields."""

import frappe

from logistics.utils.charge_service_type import OPERATIONAL_CHARGE_CHILD_SERVICE_TYPE_OPTIONS

CHARGE_DOCTYPES = (
	"Declaration Order Charges",
	"Declaration Charges",
	"Transport Order Charges",
	"Transport Job Charges",
	"Air Booking Charges",
	"Air Shipment Charges",
	"Sea Booking Charges",
	"Sea Shipment Charges",
	"Warehouse Job Charges",
)


def execute():
	for dt in CHARGE_DOCTYPES:
		if not frappe.db.exists("DocType", dt):
			continue
		frappe.db.set_value(
			"DocField",
			{"parent": dt, "fieldname": "service_type"},
			"options",
			OPERATIONAL_CHARGE_CHILD_SERVICE_TYPE_OPTIONS,
		)
	frappe.clear_cache()
