# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Add Item flags for Special Project and MICE charge item link filtering."""

from __future__ import unicode_literals

import json

import frappe


_FIELDS = (
	(
		"custom_special_project_charge",
		"Special Project Charge",
		"custom_customs_charge",
	),
	(
		"custom_mice_charge",
		"MICE Charge",
		"custom_special_project_charge",
	),
)


def execute():
	if not frappe.db.exists("DocType", "Item"):
		return

	meta = frappe.get_meta("Item")
	insert_anchor = "custom_customs_charge"
	if not meta.get_field(insert_anchor):
		insert_anchor = "custom_warehousing_charge"
	if not meta.get_field(insert_anchor):
		insert_anchor = "item_group"

	last_fieldname = insert_anchor
	for fieldname, label, insert_after in _FIELDS:
		if frappe.db.has_column("Item", fieldname):
			last_fieldname = fieldname
			continue
		if frappe.db.exists("Custom Field", {"dt": "Item", "fieldname": fieldname}):
			last_fieldname = fieldname
			continue
		if not meta.get_field(insert_after):
			insert_after = insert_anchor
		frappe.get_doc(
			{
				"doctype": "Custom Field",
				"dt": "Item",
				"fieldname": fieldname,
				"fieldtype": "Check",
				"label": label,
				"insert_after": insert_after,
			}
		).insert(ignore_permissions=True)
		last_fieldname = fieldname

	_update_item_field_order(last_fieldname)
	frappe.clear_cache(doctype="Item")
	frappe.db.commit()


def _update_item_field_order(last_charge_flag: str):
	"""Insert new flags after custom_customs_charge in Item field_order property setter."""
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

	to_insert = [fn for fn, _, _ in _FIELDS if fn not in order]
	if not to_insert:
		return

	anchor = "custom_customs_charge"
	if anchor not in order:
		anchor = last_charge_flag
	try:
		idx = order.index(anchor) + 1
	except ValueError:
		order.extend(to_insert)
	else:
		for fn in reversed(to_insert):
			if fn not in order:
				order.insert(idx, fn)

	ps.value = json.dumps(order)
	ps.save(ignore_permissions=True)

	# Keep column break after the new flags when it followed customs_charge.
	col_break = frappe.db.get_value(
		"Custom Field", {"dt": "Item", "fieldname": "custom_column_break_vxxpu"}, "name"
	)
	if col_break:
		frappe.db.set_value(
			"Custom Field",
			col_break,
			"insert_after",
			last_charge_flag,
			update_modified=False,
		)
