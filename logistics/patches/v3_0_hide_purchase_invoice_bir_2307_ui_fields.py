# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Hide redundant BIR Form 2307 party fields on Purchase Invoice (issue #1673).

Tax registration for Company and Supplier is already shown from master data;
the BIR 2307 section on the Details tab only duplicates that information.
BIR 2307 printing still uses phtax context from masters via the print format.
"""

from __future__ import annotations

import frappe

DOCTYPE = "Purchase Invoice"

# Custom fields added by phtax (same shape as on Sales Invoice).
BIR_2307_UI_FIELDNAMES = (
	"bir_2307_section",
	"payee_tin",
	"payee_branch_code",
	"column_break_bir1",
	"payor_tin",
	"payor_branch_code",
)


def execute():
	if not frappe.db.exists("DocType", DOCTYPE):
		return

	meta = frappe.get_meta(DOCTYPE)
	changed = False
	for fieldname in BIR_2307_UI_FIELDNAMES:
		if not meta.get_field(fieldname):
			continue
		if _hide_field(fieldname):
			changed = True

	if changed:
		frappe.clear_cache(doctype=DOCTYPE)


def _hide_field(fieldname: str) -> bool:
	property_setter_name = f"{DOCTYPE}-{fieldname}-hidden"
	if frappe.db.exists("Property Setter", property_setter_name):
		current = frappe.db.get_value("Property Setter", property_setter_name, "value")
		if str(current) == "1":
			return False
		frappe.db.set_value("Property Setter", property_setter_name, "value", "1")
		return True

	frappe.make_property_setter(
		{
			"doctype": DOCTYPE,
			"doctype_or_field": "DocField",
			"fieldname": fieldname,
			"property": "hidden",
			"value": "1",
			"property_type": "Check",
		},
		validate_fields_for_doctype=False,
	)
	return True
