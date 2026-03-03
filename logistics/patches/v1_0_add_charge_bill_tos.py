# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Add Bill To (Revenue column) and Pay To (Cost column) to charge doctypes."""

import frappe

CHARGE_DOCTYPES = [
	"Air Booking Charges",
	"Sea Booking Charges",
	"Sea Freight Charges",
	"Sales Quote Air Freight",
	"Sales Quote Sea Freight",
	"Sales Quote Transport",
	"Sales Quote Customs",
	"Sales Quote Warehouse",
]

BILL_TO_FIELD = {
	"fieldname": "bill_to",
	"fieldtype": "Link",
	"label": "Bill To",
	"options": "Customer",
	"in_list_view": 1,
	"insert_after": "estimated_revenue",
}

PAY_TO_FIELD = {
	"fieldname": "pay_to",
	"fieldtype": "Link",
	"label": "Pay To",
	"options": "Supplier",
	"in_list_view": 1,
	"insert_after": "estimated_cost",
}

# Fallback insert_after when revenue/cost field names differ
REVENUE_INSERT_FALLBACKS = ("estimated_revenue", "rate", "currency", "unit_rate")
COST_INSERT_FALLBACKS = ("estimated_cost", "unit_cost", "cost_currency")


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

		if not meta.get_field("bill_to"):
			insert_after = BILL_TO_FIELD["insert_after"]
			if not meta.get_field(insert_after):
				insert_after = _find_insert_after(meta, REVENUE_INSERT_FALLBACKS)
			if insert_after:
				doc.append("fields", {
					**BILL_TO_FIELD,
					"insert_after": insert_after,
				})
				dirty = True
		if not meta.get_field("pay_to"):
			insert_after = PAY_TO_FIELD["insert_after"]
			if not meta.get_field(insert_after):
				insert_after = _find_insert_after(meta, COST_INSERT_FALLBACKS)
			if insert_after:
				doc.append("fields", {
					**PAY_TO_FIELD,
					"insert_after": insert_after,
				})
				dirty = True
		if dirty:
			doc.save(ignore_permissions=True)
	frappe.db.commit()
