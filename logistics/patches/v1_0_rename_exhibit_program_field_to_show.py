# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Rename exhibit_program / exhibit_phase_order link fields to show / event_order."""

from __future__ import annotations

import frappe
from frappe.model.utils.rename_field import rename_field


def execute():
	_renames = (
		("Event Order", "exhibit_program", "event"),
		("Event Job", "exhibit_program", "event"),
		("Event Job", "exhibit_phase_order", "event_order"),
		("Event Plan", "exhibit_program", "event"),
		("Sales Quote", "exhibit_program", "event"),
	)
	for doctype, old_field, new_field in _renames:
		if not frappe.db.exists("DocType", doctype):
			continue
		if not frappe.db.table_exists(f"tab{doctype}"):
			continue
		if not frappe.db.has_column(doctype, old_field):
			continue
		if frappe.db.has_column(doctype, new_field):
			continue
		rename_field(doctype, old_field, new_field)

	for old_parent, new_parent in (
		("Exhibit Program", "Event"),
		("Exhibit Phase Order", "Event Order"),
		("Exhibit Phase Job", "Event Job"),
	):
		if frappe.db.table_exists("tabEvent Charges"):
			frappe.db.sql(
				"UPDATE `tabEvent Charges` SET parenttype = %s WHERE parenttype = %s",
				(new_parent, old_parent),
			)
		for child in (
			"Event Milestone",
			"Event Billing",
			"Event Delivery",
			"Event Scoping Activity",
			"Event Service Activity",
		):
			if frappe.db.table_exists(f"tab{child}"):
				frappe.db.sql(
					f"UPDATE `tab{child}` SET parenttype = %s WHERE parenttype = %s",
					(new_parent, old_parent),
				)

	frappe.db.commit()
