# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Restore ``MICE Project.sales_quote`` column used by Sales Quote Connections and PQ programme quotes."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "MICE Project"):
		return
	frappe.db.updatedb("MICE Project")
	frappe.clear_cache(doctype="MICE Project")
