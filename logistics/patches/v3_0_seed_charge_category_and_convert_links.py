# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Seed Charge Category master and convert Select fields to Link.

Document names match the previous Select option labels (e.g. Freight) so
existing row values and hard-coded comparisons (95/5 rule) keep working.
"""

from __future__ import annotations

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

# Union of all former Select options across charge tables + Item.
DEFAULT_CATEGORIES = (
	"Freight",
	"Fuel Surcharge",
	"Security Surcharge",
	"War Risk Surcharge",
	"Terminal Handling",
	"Port Charges",
	"Customs Clearance",
	"Documentation",
	"Insurance",
	"Storage",
	"Detention",
	"Demurrage",
	"Handling",
	"Other",
	# Consolidation / programme-specific
	"Booth Construction",
	"Booth Dismantling",
	"Utilities",
	"Transportation",
	"Customs",
	"Surcharges",
)

LINK_FILTERS_ACTIVE = '[["Charge Category", "disabled", "=", 0]]'


def execute():
	if not frappe.db.exists("DocType", "Charge Category"):
		return

	_seed_categories()
	_convert_item_custom_field()
	_clear_orphan_values()
	frappe.clear_cache()


def _seed_categories():
	for name in DEFAULT_CATEGORIES:
		if frappe.db.exists("Charge Category", name):
			frappe.db.set_value(
				"Charge Category",
				name,
				{"disabled": 0},
				update_modified=False,
			)
			continue
		doc = frappe.new_doc("Charge Category")
		doc.category_name = name
		doc.disabled = 0
		doc.insert(ignore_permissions=True)


def _convert_item_custom_field():
	"""Ensure Item.custom_charge_category is Link → Charge Category.

	Custom Field does not allow Select→Link via Document.save(); update via db.
	"""
	cf_name = "Item-custom_charge_category"
	if not frappe.db.exists("Custom Field", cf_name):
		create_custom_fields(
			{
				"Item": [
					{
						"fieldname": "custom_charge_category",
						"fieldtype": "Link",
						"label": "Charge Category",
						"options": "Charge Category",
						"insert_after": "custom_logistics_charge_item",
						"depends_on": "eval:doc.custom_logistics_charge_item",
						"description": (
							"Used for logistics charge classification "
							"(e.g. Taxable Freight Item picker, 95/5 split)."
						),
						"link_filters": LINK_FILTERS_ACTIVE,
					},
				]
			},
			update=True,
		)
		return

	frappe.db.set_value(
		"Custom Field",
		cf_name,
		{
			"fieldtype": "Link",
			"options": "Charge Category",
			"link_filters": LINK_FILTERS_ACTIVE,
			"translatable": 0,
		},
		update_modified=False,
	)
	frappe.clear_cache(doctype="Item")


def _clear_orphan_values():
	"""Null out charge_category values that are not valid Charge Category names.

	Select→Link keeps string storage; orphaned labels would fail link validation.
	"""
	valid = set(frappe.get_all("Charge Category", pluck="name"))
	if not valid:
		return

	# Child / charge tables with charge_category
	for doctype in frappe.get_all(
		"DocField",
		filters={"fieldname": "charge_category", "fieldtype": "Link", "options": "Charge Category"},
		pluck="parent",
		distinct=True,
	):
		if not frappe.db.table_exists(doctype):
			continue
		rows = frappe.db.sql(
			f"""
			SELECT name, charge_category
			FROM `tab{doctype}`
			WHERE IFNULL(charge_category, '') != ''
			""",
			as_dict=True,
		)
		for row in rows:
			if row.charge_category not in valid:
				frappe.db.set_value(doctype, row.name, "charge_category", None, update_modified=False)

	# customs_charge_category on various doctypes
	for doctype in frappe.get_all(
		"DocField",
		filters={
			"fieldname": "customs_charge_category",
			"fieldtype": "Link",
			"options": "Charge Category",
		},
		pluck="parent",
		distinct=True,
	):
		if not frappe.db.table_exists(doctype):
			continue
		rows = frappe.db.sql(
			f"""
			SELECT name, customs_charge_category
			FROM `tab{doctype}`
			WHERE IFNULL(customs_charge_category, '') != ''
			""",
			as_dict=True,
		)
		for row in rows:
			if row.customs_charge_category not in valid:
				frappe.db.set_value(
					doctype, row.name, "customs_charge_category", None, update_modified=False
				)

	# Item custom field
	if frappe.db.has_column("Item", "custom_charge_category"):
		rows = frappe.db.sql(
			"""
			SELECT name, custom_charge_category
			FROM `tabItem`
			WHERE IFNULL(custom_charge_category, '') != ''
			""",
			as_dict=True,
		)
		for row in rows:
			if row.custom_charge_category not in valid:
				frappe.db.set_value(
					"Item", row.name, "custom_charge_category", None, update_modified=False
				)
