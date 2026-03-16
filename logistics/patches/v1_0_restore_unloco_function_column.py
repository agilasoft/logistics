# Copyright (c) 2025, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Restore the 'function' column on tabUNLOCO so that forms or customizations
that still send this field can save. The column is added only if missing
(e.g. after v1_0_drop_unloco_function_column). Uses backticks because
'function' is a MySQL reserved word.
"""

import frappe


def execute():
	if not frappe.db.table_exists("UNLOCO"):
		return
	if frappe.db.has_column("UNLOCO", "function"):
		return
	frappe.db.sql(
		"ALTER TABLE `tabUNLOCO` ADD COLUMN `function` VARCHAR(140) DEFAULT NULL"
	)
	frappe.db.commit()
