# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""
Warehouse doctypes (e.g. Warehouse Job Item) use ``fetch_from: item.volume`` on the ``volume`` field.
When the Item doctype has no ``volume`` field, link validation (validate_link_and_fetch) fails with:
DataError: Field not permitted in query: volume
"""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Item"):
		return
	if frappe.get_meta("Item").has_field("volume"):
		return
	if frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": "volume"}):
		return

	# After weight UOM; keeps physical-dimension group together
	insert_after = "weight_uom"
	if not frappe.get_meta("Item").get_field(insert_after):
		for candidate in ("weight_per_unit", "net_weight", "stock_uom"):
			if frappe.get_meta("Item").get_field(candidate):
				insert_after = candidate
				break
		else:
			return

	frappe.get_doc(
		{
			"doctype": "Custom Field",
			"dt": "Item",
			"fieldname": "volume",
			"fieldtype": "Float",
			"label": "Volume",
			"description": "Item volume (e.g. m³) for warehouse capacity and line-level fetch; optional.",
			"insert_after": insert_after,
		}
	).insert(ignore_permissions=True)
	frappe.db.commit()
