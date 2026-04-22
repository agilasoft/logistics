# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
"""Remove Customize Form fields for UNLOCO; schema belongs in ``unloco.json`` only."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "UNLOCO"):
		return

	custom_rows = frappe.get_all(
		"Custom Field",
		filters={"dt": "UNLOCO"},
		fields=["name", "fieldname"],
	)

	fieldnames = list({r.fieldname for r in custom_rows if r.fieldname}) if custom_rows else []

	if fieldnames:
		for ps in frappe.get_all(
			"Property Setter",
			filters={"doc_type": "UNLOCO", "field_name": ["in", fieldnames]},
			pluck="name",
		):
			frappe.delete_doc("Property Setter", ps, force=True, ignore_missing=True)

		for row in custom_rows:
			frappe.delete_doc("Custom Field", row.name, force=True, ignore_permissions=True)

		frappe.db.commit()

	frappe.reload_doc("logistics", "doctype", "unloco")

	# ``attach_whdt`` was removed from app JSON; drop DB column if it still exists.
	if frappe.db.has_column("UNLOCO", "attach_whdt"):
		try:
			frappe.db.sql("ALTER TABLE `tabUNLOCO` DROP COLUMN `attach_whdt`")
		except Exception:
			frappe.log_error(frappe.get_traceback(), "UNLOCO: could not drop attach_whdt column")

	frappe.db.commit()
	frappe.clear_cache(doctype="UNLOCO")
