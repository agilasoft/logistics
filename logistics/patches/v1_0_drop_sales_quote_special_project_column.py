# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Drop orphan ``tabSales Quote.special_project`` column after field removal."""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.has_column("Sales Quote", "special_project"):
		return
	frappe.db.sql_ddl("ALTER TABLE `tabSales Quote` DROP COLUMN `special_project`")
