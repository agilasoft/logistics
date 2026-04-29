# -*- coding: utf-8 -*-
# Copyright (c) 2026, Logistics Team and contributors
"""Add Item.custom_container_charge — operational GL (Item dimension) roll-up on Container; not netted against deposit."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Item"):
		return
	if frappe.db.has_column("Item", "custom_container_charge"):
		return
	if frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": "custom_container_charge"}):
		return

	insert_after = "custom_container_deposit_charge"
	if not frappe.get_meta("Item").get_field(insert_after):
		insert_after = "item_group"
		if not frappe.get_meta("Item").get_field(insert_after):
			insert_after = "stock_uom"

	frappe.get_doc(
		{
			"doctype": "Custom Field",
			"dt": "Item",
			"fieldname": "custom_container_charge",
			"fieldtype": "Check",
			"label": "Container charge",
			"description": (
				"When set, GL lines carrying this Item (Item accounting dimension) are included in Container "
				"charges total and the Charge GL table. Deposit amount is not reduced by these charges."
			),
			"depends_on": "eval:doc.custom_logistics_charge_item",
			"insert_after": insert_after,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
