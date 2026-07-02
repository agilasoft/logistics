# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Drop persisted ``tabSpecial Project Service Detail`` rows for Special Project.

The Services grid is virtual; source of truth is ``Special Project Service`` documents.
"""

from __future__ import annotations

import frappe


def execute():
	table = "tabSpecial Project Service Detail"
	if not frappe.db.table_exists(table):
		return
	if frappe.db.has_column("Special Project Service Detail", "parenttype"):
		frappe.db.delete("Special Project Service Detail", {"parenttype": "Special Project"})
	frappe.db.sql_ddl(f"DROP TABLE `{table}`")
	frappe.db.commit()
