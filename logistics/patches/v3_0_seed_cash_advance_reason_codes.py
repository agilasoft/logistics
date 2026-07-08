# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Seed default Cash Advance Reason Code options for due date extensions."""

from __future__ import annotations

import frappe

DEFAULT_REASON_CODES = (
	("EXT-OPS", "Operational extension"),
	("EXT-EMR", "Emergency or urgent need"),
	("EXT-APR", "Management approval"),
)


def execute():
	if not frappe.db.exists("DocType", "Cash Advance Reason Code"):
		return

	for reason_code, description in DEFAULT_REASON_CODES:
		if frappe.db.exists("Cash Advance Reason Code", reason_code):
			frappe.db.set_value(
				"Cash Advance Reason Code",
				reason_code,
				{"description": description, "is_active": 1},
				update_modified=False,
			)
			continue
		doc = frappe.new_doc("Cash Advance Reason Code")
		doc.reason_code = reason_code
		doc.description = description
		doc.is_active = 1
		doc.insert(ignore_permissions=True)

	frappe.db.commit()
