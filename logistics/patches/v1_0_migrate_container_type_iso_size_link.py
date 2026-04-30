# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Backfill **Container ISO Size** masters and normalize **Container Type** ``iso_size`` when migrating from Data to Link.

Each distinct trimmed value becomes a **Container ISO Size** (name = code). Rows with only whitespace are cleared.
"""

import frappe


def execute():
	if not frappe.db.has_table("tabContainer ISO Size"):
		return

	rows = frappe.db.sql(
		"""
		SELECT name, iso_size
		FROM `tabContainer Type`
		WHERE IFNULL(iso_size, '') != ''
		""",
		as_dict=True,
	)

	for row in rows:
		raw = row.iso_size
		code = (raw or "").strip()
		if not code:
			frappe.db.set_value("Container Type", row.name, "iso_size", None, update_modified=False)
			continue

		if not frappe.db.exists("Container ISO Size", code):
			doc = frappe.new_doc("Container ISO Size")
			doc.code = code
			doc.insert(ignore_permissions=True)

		if raw != code:
			frappe.db.set_value("Container Type", row.name, "iso_size", code, update_modified=False)
