# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Add Item.custom_container_deposit_charge for Purchase Invoice container-deposit line detection."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Item"):
		return
	if frappe.db.has_column("Item", "custom_container_deposit_charge"):
		return
	if frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": "custom_container_deposit_charge"}):
		return

	insert_after = "item_group"
	if not frappe.get_meta("Item").get_field(insert_after):
		insert_after = "stock_uom"

	frappe.get_doc(
		{
			"doctype": "Custom Field",
			"dt": "Item",
			"fieldname": "custom_container_deposit_charge",
			"fieldtype": "Check",
			"label": "Container deposit charge",
			"description": "When set, Purchase Invoice lines for Sea Shipment / Declaration can post expense to Deposits Pending for Refund Request (Sea Freight Settings).",
			"insert_after": insert_after,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
