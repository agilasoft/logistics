# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

import frappe


def execute():
	"""Ensure IATA Settings is a proper Single DocType with one canonical record."""
	doctype = "IATA Settings"
	if not frappe.db.exists("DocType", doctype):
		return

	saved = {}
	latest_name = frappe.db.get_value(doctype, {}, "name", order_by="modified desc")
	if latest_name:
		saved = frappe.db.get_value(doctype, latest_name, "*", as_dict=True) or {}

	frappe.db.sql("DELETE FROM `tabIATA Settings`")
	frappe.db.sql("DELETE FROM tabSingles WHERE doctype = %s", (doctype,))

	if not frappe.get_meta(doctype).issingle:
		frappe.db.set_value("DocType", doctype, "issingle", 1)

	frappe.clear_cache(doctype=doctype)

	doc = frappe.new_doc(doctype)
	skip = {
		"name",
		"doctype",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"idx",
	}
	for key, value in saved.items():
		if key in skip or value is None:
			continue
		if key in doc.as_dict():
			doc.set(key, value)

	doc.flags.ignore_permissions = True
	doc.flags.ignore_validate = True
	doc.insert(ignore_permissions=True)
	frappe.db.commit()
