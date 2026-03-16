# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Add is_other_service and other_service_reference to charge doctypes for Other Services integration."""

import frappe

CHARGE_DOCTYPES = [
	"Transport Order Charges",
	"Transport Job Charges",
	"Declaration Order Charges",
	"Declaration Charges",
]

IS_OTHER_SERVICE_FIELD = {
	"fieldname": "is_other_service",
	"fieldtype": "Check",
	"label": "From Other Services",
	"default": 0,
	"read_only_depends_on": "eval:doc.is_other_service",
	"insert_after": "item_code",
}

OTHER_SERVICE_REF_FIELD = {
	"fieldname": "other_service_reference",
	"fieldtype": "Data",
	"label": "Other Service Reference",
	"read_only": 1,
	"insert_after": "is_other_service",
}

INSERT_AFTER_FALLBACKS = ("item_code", "charge_item", "item_name", "calculation_method")


def _find_insert_after(meta, fallbacks):
	for name in fallbacks:
		if meta.get_field(name):
			return name
	return None


def execute():
	for dt in CHARGE_DOCTYPES:
		if not frappe.db.exists("DocType", dt):
			continue
		meta = frappe.get_meta(dt)
		doc = frappe.get_doc("DocType", dt)
		dirty = False

		if not meta.get_field("is_other_service"):
			insert_after = _find_insert_after(meta, INSERT_AFTER_FALLBACKS)
			if insert_after:
				doc.append("fields", {
					**IS_OTHER_SERVICE_FIELD,
					"insert_after": insert_after,
				})
				dirty = True

		if not meta.get_field("other_service_reference"):
			insert_after = "is_other_service" if meta.get_field("is_other_service") else _find_insert_after(meta, INSERT_AFTER_FALLBACKS)
			if insert_after:
				doc.append("fields", {
					**OTHER_SERVICE_REF_FIELD,
					"insert_after": insert_after,
				})
				dirty = True

		if dirty:
			doc.save(ignore_permissions=True)
	frappe.db.commit()
