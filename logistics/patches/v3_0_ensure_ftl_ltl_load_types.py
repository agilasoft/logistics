# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Ensure FTL and LTL Load Type masters exist for transport template validation (#1122)."""

from __future__ import annotations

import frappe


def execute():
	for row in (
		{
			"load_type_name": "FTL",
			"description": "Full Truck Load",
			"transport": 1,
			"non_container": 1,
			"is_active": 1,
		},
		{
			"load_type_name": "LTL",
			"description": "Less than Truck Load",
			"transport": 1,
			"non_container": 1,
			"is_active": 1,
		},
	):
		name = row["load_type_name"]
		if frappe.db.exists("Load Type", name):
			doc = frappe.get_doc("Load Type", name)
			updated = False
			for field in ("transport", "non_container", "is_active"):
				if not doc.get(field):
					doc.set(field, 1)
					updated = True
			if updated:
				doc.save(ignore_permissions=True)
			continue

		doc = frappe.new_doc("Load Type")
		doc.update(row)
		doc.insert(ignore_permissions=True)
