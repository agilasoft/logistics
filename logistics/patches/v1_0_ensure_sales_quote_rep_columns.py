# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Sync `tabSales Quote` with DocType metadata (company, rep columns, etc.) for permission match SQL."""

import frappe


def execute():
	if not frappe.db.table_exists("Sales Quote"):
		return
	if not frappe.db.exists("DocType", "Sales Quote"):
		return
	frappe.db.updatedb("Sales Quote")
