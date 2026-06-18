# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Merge quote-level charge row parameters into Sales Quote Service Scope header fields where blank."""

from __future__ import unicode_literals

import frappe

from logistics.utils.sales_quote_charge_parameters import (
	SALES_QUOTE_CHARGE_PARAMETER_FIELDS,
)


def execute():
	if not frappe.db.table_exists("tabSales Quote"):
		return
	quotes = frappe.get_all("Sales Quote", pluck="name", limit_page_length=0)
	for name in quotes:
		try:
			doc = frappe.get_doc("Sales Quote", name)
		except Exception:
			continue
		changed = False
		for row in doc.get("charges") or []:
			if (getattr(row, "charge_scope", None) or "Main").strip() not in ("Main", ""):
				continue
			for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS:
				if not getattr(doc, fn, None) and getattr(row, fn, None):
					doc.set(fn, getattr(row, fn))
					changed = True
		if changed:
			doc.flags.ignore_validate = True
			doc.save(ignore_permissions=True)
	frappe.db.commit()
