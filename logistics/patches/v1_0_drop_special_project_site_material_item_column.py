# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Drop orphan ``item`` columns from Special Project site material child tables."""

from __future__ import annotations

import frappe


def execute():
	for doctype in ("Special Project Site Material", "Special Project Site Receipt"):
		table = f"tab{doctype}"
		if frappe.db.has_column(doctype, "item"):
			frappe.db.sql_ddl(f"ALTER TABLE `{table}` DROP COLUMN `item`")
