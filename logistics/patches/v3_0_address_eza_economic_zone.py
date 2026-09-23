# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Gate Address Economic Zone on EZA; backfill EZA for addresses that already have a zone."""

from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
	_ensure_field_props()
	_backfill_eza_from_zone()
	frappe.clear_cache(doctype="Address")


def _ensure_field_props():
	create_custom_fields(
		{
			"Address": [
				{
					"fieldname": "custom_eza",
					"label": "EZA",
					"fieldtype": "Check",
					"insert_after": "custom_column_break_audyr",
					"module": "Transport",
				},
				{
					"fieldname": "custom_economic_zone",
					"label": "Economic Zone",
					"fieldtype": "Link",
					"options": "Economic Zone",
					"insert_after": "custom_eza",
					"depends_on": "eval:doc.custom_eza",
					"mandatory_depends_on": "eval:doc.custom_eza",
					"module": "Transport",
				},
			]
		},
		update=True,
	)


def _backfill_eza_from_zone():
	"""Addresses with a zone but EZA off would hide the zone after depends_on — flip EZA on."""
	if not frappe.db.has_column("Address", "custom_economic_zone"):
		return
	if not frappe.db.has_column("Address", "custom_eza"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabAddress`
		SET custom_eza = 1
		WHERE IFNULL(custom_economic_zone, '') != ''
		  AND IFNULL(custom_eza, 0) = 0
		"""
	)
