# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

import frappe


def execute():
	"""Convert legacy global IATA Settings into one record per Company."""
	doctype = "IATA Settings"
	if not frappe.db.exists("DocType", doctype):
		return

	frappe.db.set_value("DocType", doctype, "issingle", 0)
	frappe.clear_cache(doctype=doctype)

	data = _load_legacy_iata_settings_data(doctype)

	companies = frappe.get_all("Company", pluck="name")
	if not companies:
		return

	skip_keys = {
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"idx",
		"company",
	}

	for company in companies:
		if frappe.db.exists(doctype, company):
			continue

		doc = frappe.new_doc(doctype)
		doc.company = company
		if data:
			for key, value in data.items():
				if key in skip_keys or value is None:
					continue
				if doc.meta.has_field(key):
					doc.set(key, value)

		doc.flags.ignore_permissions = True
		doc.flags.ignore_validate = True
		doc.insert(ignore_permissions=True)

	frappe.db.sql("DELETE FROM tabSingles WHERE doctype = %s", (doctype,))
	if frappe.db.exists(doctype, doctype):
		frappe.db.delete(doctype, doctype)

	frappe.db.commit()


def _load_legacy_iata_settings_data(doctype):
	if frappe.db.exists(doctype, doctype):
		return frappe.db.get_value(doctype, doctype, "*", as_dict=True)

	latest_name = frappe.db.get_value(doctype, {}, "name", order_by="modified desc")
	if latest_name:
		return frappe.db.get_value(doctype, latest_name, "*", as_dict=True)

	return None
