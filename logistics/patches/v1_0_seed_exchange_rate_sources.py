# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Seed Exchange Rate Source master rows (IATA, Central Bank, Internal, Manual)."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Exchange Rate Source"):
		return

	sources = [
		{"source_code": "IATA", "source_name": "IATA", "sort_order": 10},
		{"source_code": "CB", "source_name": "Central Bank", "sort_order": 20},
		{"source_code": "INT", "source_name": "Internal", "sort_order": 30},
		{"source_code": "MAN", "source_name": "Manual", "sort_order": 40},
	]
	for row in sources:
		if frappe.db.exists("Exchange Rate Source", row["source_code"]):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Exchange Rate Source",
				"source_code": row["source_code"],
				"source_name": row["source_name"],
				"is_active": 1,
				"sort_order": row["sort_order"],
			}
		)
		doc.insert(ignore_permissions=True)
