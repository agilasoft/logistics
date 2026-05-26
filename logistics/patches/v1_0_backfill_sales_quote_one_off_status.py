# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# For license information, please see license.txt
"""Backfill One-off Sales Quote ``status`` and normalize ``converted_to_doc`` display.

The field is read-only in the desk (Draft | Converted); some rows were saved with a blank value
or a bare document id. Idempotent.
"""

import frappe

from logistics.pricing_center.doctype.sales_quote.sales_quote import (
	_infer_one_off_converted_ref_from_links,
	normalize_one_off_converted_to_ref,
)


def execute():
	if not frappe.db.exists("DocType", "Sales Quote"):
		return

	frappe.db.sql(
		"""
		UPDATE `tabSales Quote`
		SET `status`='Converted'
		WHERE `quotation_type`='One-off'
		  AND IFNULL(NULLIF(TRIM(`status`), ''), '') = ''
		  AND IFNULL(NULLIF(TRIM(`converted_to_doc`), ''), '') != ''
		"""
	)
	frappe.db.sql(
		"""
		UPDATE `tabSales Quote`
		SET `status`='Draft'
		WHERE `quotation_type`='One-off'
		  AND IFNULL(NULLIF(TRIM(`status`), ''), '') = ''
		  AND IFNULL(NULLIF(TRIM(`converted_to_doc`), ''), '') = ''
		"""
	)

	# Normalize legacy "Doctype: Name" or infer from linked jobs when Converted To is empty
	names = frappe.get_all(
		"Sales Quote",
		filters={"quotation_type": "One-off", "docstatus": ["<", 2]},
		pluck="name",
	)
	for name in names:
		current = (frappe.db.get_value("Sales Quote", name, "converted_to_doc") or "").strip()
		if current:
			normalized = normalize_one_off_converted_to_ref(current)
			if normalized and normalized != current:
				frappe.db.set_value("Sales Quote", name, "converted_to_doc", normalized, update_modified=False)
				frappe.db.set_value("Sales Quote", name, "status", "Converted", update_modified=False)
			continue
		inferred = _infer_one_off_converted_ref_from_links(name)
		if inferred:
			frappe.db.set_value("Sales Quote", name, "converted_to_doc", inferred, update_modified=False)
			frappe.db.set_value("Sales Quote", name, "status", "Converted", update_modified=False)
