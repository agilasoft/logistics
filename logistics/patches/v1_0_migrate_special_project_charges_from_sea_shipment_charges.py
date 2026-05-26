# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Move Special Project charge rows from Sea Shipment Charges to Special Project Charges."""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.table_exists("tabSea Shipment Charges"):
		return
	if not frappe.db.table_exists("tabSpecial Project Charges"):
		return

	old_rows = frappe.db.sql(
		"""
		SELECT name FROM `tabSea Shipment Charges`
		WHERE parenttype = 'Special Project' AND parentfield = 'charges'
		""",
		as_dict=True,
	)
	if not old_rows:
		return

	old_names = [r.name for r in old_rows]
	sea_meta = frappe.get_meta("Sea Shipment Charges")
	sp_meta = frappe.get_meta("Special Project Charges")
	common_fields = [
		f.fieldname
		for f in sea_meta.fields
		if f.fieldname in sp_meta.fieldnames and f.fieldname not in ("name",)
	]
	# Standard child-table columns present on both tables
	for col in (
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"idx",
		"parent",
		"parentfield",
		"parenttype",
	):
		if col in sea_meta.fieldnames and col in sp_meta.fieldnames and col not in common_fields:
			common_fields.append(col)

	columns = ", ".join(f"`{c}`" for c in common_fields)
	frappe.db.sql(
		f"""
		INSERT INTO `tabSpecial Project Charges` ({columns})
		SELECT {columns}
		FROM `tabSea Shipment Charges`
		WHERE parenttype = 'Special Project' AND parentfield = 'charges'
		"""
	)

	for ref_table, ref_field in (
		("Sales Quote Weight Break", "reference_doctype"),
		("Sales Quote Qty Break", "reference_doctype"),
	):
		if not frappe.db.table_exists(f"tab{ref_table}"):
			continue
		frappe.db.sql(
			f"""
			UPDATE `tab{ref_table}`
			SET `{ref_field}` = 'Special Project Charges'
			WHERE `{ref_field}` = 'Sea Shipment Charges'
				AND reference_no IN %(names)s
			""",
			{"names": old_names},
		)

	frappe.db.sql(
		"""
		DELETE FROM `tabSea Shipment Charges`
		WHERE parenttype = 'Special Project' AND parentfield = 'charges'
		"""
	)
	frappe.db.commit()
