# -*- coding: utf-8 -*-
# Copyright (c) 2025, www.agilasoft.com and contributors
"""Add Profitability (from GL) section and HTML field to job/shipment doctypes."""

import frappe

PROFITABILITY_DOCTYPES = [
	"Air Shipment",
	"Sea Shipment",
	"Transport Job",
	"Warehouse Job",
	"Declaration",
	"General Job",
]

SECTION_BREAK = {
	"fieldname": "profitability_section_break",
	"fieldtype": "Section Break",
	"label": "Profitability (from GL)",
	"collapsible": 1,
}

HTML_FIELD = {
	"fieldname": "profitability_section_html",
	"fieldtype": "HTML",
	"label": "Revenue, Cost, Profit, WIP, Accrual",
	"read_only": 1,
	"no_copy": 1,
}

INSERT_AFTER_OPTIONS = ("accrual_closed", "job_number", "company")


def _find_insert_after(meta):
	for name in INSERT_AFTER_OPTIONS:
		if meta.get_field(name):
			return name
	return None


def execute():
	for dt in PROFITABILITY_DOCTYPES:
		if not frappe.db.exists("DocType", dt):
			continue
		meta = frappe.get_meta(dt)
		doc = frappe.get_doc("DocType", dt)
		dirty = False

		insert_after = _find_insert_after(meta)
		if not insert_after:
			continue

		if not meta.get_field("profitability_section_break"):
			doc.append("fields", {
				**SECTION_BREAK,
				"insert_after": insert_after,
			})
			dirty = True
			insert_after = "profitability_section_break"

		if not meta.get_field("profitability_section_html"):
			doc.append("fields", {
				**HTML_FIELD,
				"insert_after": insert_after,
			})
			dirty = True

		if dirty:
			doc.flags.ignore_validate = True
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			frappe.clear_cache(doctype=dt)
