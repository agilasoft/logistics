# Copyright (c) 2026, Agilasoft and contributors
"""Add Legacy Job No and copy it from the document name on existing legacy files."""

from __future__ import annotations

import frappe


FILES = (
	("Air Shipment", "air_freight", "air_shipment"),
	("Sea Shipment", "sea_freight", "sea_shipment"),
	("Transport Job", "transport", "transport_job"),
	("Declaration", "customs", "declaration"),
	("Warehouse Job", "warehousing", "warehouse_job"),
)


def execute():
	frappe.flags.in_patch = True
	for doctype, module, name in FILES:
		if not frappe.db.exists("DocType", doctype):
			continue
		frappe.reload_doc(module, "doctype", name, force=True)
		if not frappe.db.has_column(doctype, "legacy_job_no"):
			continue
		table = f"tab{doctype}"
		legacy = "ifnull(is_legacy_job, 0) = 1"
		if frappe.db.has_column(doctype, "is_beginning_job"):
			legacy = f"({legacy} or ifnull(is_beginning_job, 0) = 1)"
		frappe.db.sql(
			f"""
			update `{table}`
			set legacy_job_no = name
			where {legacy} and ifnull(legacy_job_no, '') = ''
			"""
		)
	frappe.clear_cache()
