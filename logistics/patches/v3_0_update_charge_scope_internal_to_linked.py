# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Migrate charge_scope Internal Job → Linked and internal_job → linked_service on charge child tables."""

from __future__ import unicode_literals

import frappe
from frappe.model.utils.rename_field import rename_field

_CHARGE_TABLES = (
	"Sales Quote Charge",
	"Air Booking Charges",
	"Air Shipment Charges",
	"Sea Booking Charges",
	"Sea Shipment Charges",
	"Transport Order Charges",
	"Transport Job Charges",
	"Declaration Charges",
	"Declaration Order Charges",
	"Warehouse Job Charges",
	"Inbound Order Charges",
	"Release Order Charges",
	"MICE Project Charges",
	"Change Request Charge",
)


def execute():
	for dt in _CHARGE_TABLES:
		if not frappe.db.exists("DocType", dt):
			continue
		meta = frappe.get_meta(dt)
		if meta.has_field("internal_job") and not meta.has_field("linked_service"):
			rename_field(dt, "internal_job", "linked_service")
		if frappe.db.table_exists(f"tab{dt}"):
			frappe.db.sql(
				f"""
				UPDATE `tab{dt}`
				SET charge_scope = 'Linked'
				WHERE charge_scope = 'Internal Job'
				"""
			)
	frappe.db.commit()
