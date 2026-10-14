# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Hide Company on Cost Center.

ERPNext still requires the column for the cost center tree and for accounting.
The form, list column, standard filter, and tree "new" dialog no longer show
it. Company stays mandatory in the database sense: new records without one
inherit the parent, or the site default, before validation. The tree filter
still selects which company tree to open.
"""

from __future__ import annotations

import frappe

DOCTYPE = "Cost Center"

FIELD_PROPERTIES = (
	("hidden", "Check", "1"),
	("in_list_view", "Check", "0"),
	("in_standard_filter", "Check", "0"),
	# Tree "New" dialog includes every reqd field. Company is chosen by the tree filter.
	("reqd", "Check", "0"),
)

FIELD_ORDER = (
	'["sb0", "cost_center_name", "cost_center_number", "custom_description", '
	'"parent_cost_center", "custom_branch", "cb0", "is_group", "disabled", '
	'"lft", "rgt", "old_parent"]'
)
SEARCH_FIELDS = "custom_description,parent_cost_center, is_group"


def execute():
	if not frappe.db.exists("DocType", DOCTYPE):
		return

	changed = False
	for prop, property_type, value in FIELD_PROPERTIES:
		if _set_field_property(prop, property_type, value):
			changed = True

	if _set_doctype_property("field_order", "Data", FIELD_ORDER):
		changed = True
	if _set_doctype_property("search_fields", "Data", SEARCH_FIELDS):
		changed = True

	if changed:
		frappe.clear_cache(doctype=DOCTYPE)


def _set_field_property(prop: str, property_type: str, value: str) -> bool:
	name = f"{DOCTYPE}-company-{prop}"
	if frappe.db.exists("Property Setter", name):
		current = frappe.db.get_value("Property Setter", name, "value")
		if str(current) == value:
			return False
		frappe.db.set_value("Property Setter", name, "value", value)
		return True

	frappe.make_property_setter(
		{
			"doctype": DOCTYPE,
			"doctype_or_field": "DocField",
			"fieldname": "company",
			"property": prop,
			"value": value,
			"property_type": property_type,
		},
		validate_fields_for_doctype=False,
	)
	return True


def _set_doctype_property(prop: str, property_type: str, value: str) -> bool:
	name = f"{DOCTYPE}-main-{prop}"
	if frappe.db.exists("Property Setter", name):
		current = frappe.db.get_value("Property Setter", name, "value")
		if str(current) == value:
			return False
		frappe.db.set_value("Property Setter", name, "value", value)
		return True

	frappe.make_property_setter(
		{
			"doctype": DOCTYPE,
			"doctype_or_field": "DocType",
			"property": prop,
			"value": value,
			"property_type": property_type,
		},
		validate_fields_for_doctype=False,
	)
	return True
