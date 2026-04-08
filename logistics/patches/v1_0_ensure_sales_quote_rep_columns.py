# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Sync Sales Quote table so rep columns (e.g. sales_rep) exist for permission/match SQL in link search."""

import frappe


def execute():
	if not frappe.db.table_exists("Sales Quote"):
		return
	if not frappe.db.exists("DocType", "Sales Quote"):
		return
	frappe.db.updatedb("Sales Quote")
