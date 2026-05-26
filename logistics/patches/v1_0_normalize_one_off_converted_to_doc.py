# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
"""Normalize One-off ``converted_to_doc`` to ``{Doctype} {name}`` and sync ``status``. Idempotent."""

import frappe

from logistics.pricing_center.doctype.sales_quote.sales_quote import (
	_infer_one_off_converted_ref_from_links,
	normalize_one_off_converted_to_ref,
)


def execute():
	if not frappe.db.exists("DocType", "Sales Quote"):
		return

	names = frappe.get_all(
		"Sales Quote",
		filters={"quotation_type": "One-off", "docstatus": ["<", 2]},
		pluck="name",
	)
	link_cols = ["converted_to_doc"]
	if frappe.db.has_column("Sales Quote", "converted_to_doctype"):
		link_cols.extend(["converted_to_doctype", "converted_to_name"])
	for name in names:
		row = frappe.db.get_value("Sales Quote", name, link_cols, as_dict=True) or {}
		current = (row.get("converted_to_doc") or "").strip()
		ref = None
		if current:
			ref = normalize_one_off_converted_to_ref(
				current,
				row.get("converted_to_doctype"),
				row.get("converted_to_name"),
			)
		else:
			ref = _infer_one_off_converted_ref_from_links(name)
		if not ref:
			frappe.db.set_value(
				"Sales Quote",
				name,
				"status",
				"Draft",
				update_modified=False,
			)
			continue
		frappe.db.set_value(
			"Sales Quote",
			name,
			{"converted_to_doc": ref, "status": "Converted"},
			update_modified=False,
		)
