# Copyright (c) 2026, www.agilasoft.com and contributors
"""Migrate Sales Quote Weight Break rate_type to M/N/Q format."""

import frappe

RATE_TYPE_MAP = {
	"Normal": "N (Normal)",
	"Minimum": "M (Minimum)",
	"Weight Break": "Q (Quantity Break)",
}


def execute():
	"""Map old rate_type values to new M/N/Q format."""
	for old_val, new_val in RATE_TYPE_MAP.items():
		frappe.db.sql(
			"""
			UPDATE `tabSales Quote Weight Break`
			SET rate_type = %(new_val)s
			WHERE rate_type = %(old_val)s
			""",
			{"old_val": old_val, "new_val": new_val},
		)
	frappe.db.commit()
