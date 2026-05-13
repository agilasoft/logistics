# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Rename Select option ``Custom`` → ``Customs`` for charge service_type and Sales Quote main_service (legacy rows)."""

import frappe
from frappe.utils import get_table_name

_CUSTOM_TO_CUSTOMS = ("Customs", "Custom")

_UNIFIED_CHARGE_DOCTYPES = (
	"Sales Quote Charge",
	"Change Request Charge",
	"Cost Sheet Charge",
)

_OPERATIONAL_CHARGE_DOCTYPES = (
	"Sea Booking Charges",
	"Air Booking Charges",
	"Sea Shipment Charges",
	"Air Shipment Charges",
	"Declaration Charges",
	"Declaration Order Charges",
	"Transport Order Charges",
	"Transport Job Charges",
	"Warehouse Job Charges",
)


def execute():
	for dt in _UNIFIED_CHARGE_DOCTYPES:
		if not frappe.db.exists("DocType", dt):
			continue
		table = get_table_name(dt)
		frappe.db.sql(
			"UPDATE `{}` SET `service_type`=%s WHERE `service_type`=%s".format(table),
			_CUSTOM_TO_CUSTOMS,
		)

	for dt in _OPERATIONAL_CHARGE_DOCTYPES:
		if not frappe.db.exists("DocType", dt):
			continue
		table = get_table_name(dt)
		frappe.db.sql(
			"UPDATE `{}` SET `service_type`=%s WHERE `service_type`=%s".format(table),
			_CUSTOM_TO_CUSTOMS,
		)

	if frappe.db.exists("DocType", "Sales Quote"):
		frappe.db.sql(
			"UPDATE `tabSales Quote` SET `main_service`=%s WHERE `main_service`=%s",
			_CUSTOM_TO_CUSTOMS,
		)

	if frappe.db.exists("DocType", "Internal Job Detail"):
		frappe.db.sql(
			"UPDATE `tabInternal Job Detail` SET `service_type`=%s WHERE `service_type`=%s",
			_CUSTOM_TO_CUSTOMS,
		)
