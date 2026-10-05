# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Drop retired transport DocTypes when their tables have no rows.

Proof of Delivery is an empty controller. Delivery evidence stays on the
Transport Leg print format. Plate Coding Rule is no longer enforced; plate
coding lives on Truck Ban Constraint. A site that still has rows keeps the
DocType in the database.
"""

from __future__ import annotations

PROOF_OF_DELIVERY = "Proof of Delivery"
PLATE_CODING_RULE = "Plate Coding Rule"
PLATE_CODING_DIGITS = "Plate Coding Restricted Digits"


def doctypes_to_drop(row_counts):
	"""Return DocTypes that can be removed. Child rows are dropped before the parent."""
	drop = []
	if not row_counts.get(PROOF_OF_DELIVERY, 0):
		drop.append(PROOF_OF_DELIVERY)
	if not row_counts.get(PLATE_CODING_RULE, 0) and not row_counts.get(PLATE_CODING_DIGITS, 0):
		drop.append(PLATE_CODING_DIGITS)
		drop.append(PLATE_CODING_RULE)
	return drop


def execute():
	import frappe

	counts = {
		PROOF_OF_DELIVERY: _row_count(frappe, PROOF_OF_DELIVERY),
		PLATE_CODING_RULE: _row_count(frappe, PLATE_CODING_RULE),
		PLATE_CODING_DIGITS: _row_count(frappe, PLATE_CODING_DIGITS),
	}
	for name in doctypes_to_drop(counts):
		if frappe.db.exists("DocType", name):
			frappe.delete_doc("DocType", name, force=True, ignore_permissions=True)


def _row_count(frappe, doctype):
	if not frappe.db.table_exists(doctype):
		return 0
	return frappe.db.count(doctype)
