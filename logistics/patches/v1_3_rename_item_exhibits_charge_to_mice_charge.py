# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Rename Item.custom_exhibits_charge -> custom_mice_charge (MICE rebrand)."""

from __future__ import unicode_literals

import json

import frappe


def execute():
	if not frappe.db.exists("DocType", "Item"):
		return

	old_fn = "custom_exhibits_charge"
	new_fn = "custom_mice_charge"

	if frappe.db.has_column("Item", old_fn) and not frappe.db.has_column("Item", new_fn):
		frappe.db.sql(
			f"ALTER TABLE `tabItem` CHANGE `{old_fn}` `{new_fn}` tinyint(4) NOT NULL DEFAULT 0"
		)

	cf_name = frappe.db.get_value("Custom Field", {"dt": "Item", "fieldname": old_fn})
	if cf_name:
		frappe.db.set_value(
			"Custom Field",
			cf_name,
			{
				"fieldname": new_fn,
				"label": "MICE Charge",
				"name": f"Item-{new_fn}",
			},
			update_modified=False,
		)
	elif not frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": new_fn}):
		insert_after = "custom_special_project_charge"
		if not frappe.get_meta("Item").get_field(insert_after):
			insert_after = "custom_customs_charge"
		frappe.get_doc(
			{
				"doctype": "Custom Field",
				"dt": "Item",
				"fieldname": new_fn,
				"fieldtype": "Check",
				"label": "MICE Charge",
				"insert_after": insert_after,
			}
		).insert(ignore_permissions=True)

	_update_item_field_order(old_fn, new_fn)
	frappe.clear_cache(doctype="Item")
	frappe.db.commit()


def _update_item_field_order(old_fn: str, new_fn: str):
	ps_name = frappe.db.get_value(
		"Property Setter",
		{"doc_type": "Item", "property": "field_order", "doctype_or_field": "DocType"},
		"name",
	)
	if not ps_name:
		return
	ps = frappe.get_doc("Property Setter", ps_name)
	try:
		order = json.loads(ps.value or "[]")
	except (TypeError, ValueError):
		return
	if not isinstance(order, list):
		return
	changed = False
	for i, fn in enumerate(order):
		if fn == old_fn:
			order[i] = new_fn
			changed = True
	if changed:
		ps.value = json.dumps(order)
		ps.save(ignore_permissions=True)

	col_break = frappe.db.get_value(
		"Custom Field", {"dt": "Item", "fieldname": "custom_column_break_vxxpu"}, "name"
	)
	if col_break:
		frappe.db.set_value(
			"Custom Field",
			col_break,
			"insert_after",
			new_fn,
			update_modified=False,
		)
