# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Drop orphan ``item`` columns from Special Project site material child tables.

Historical: kept for already-run installations. On fresh installs this no-ops because
the underlying tables no longer carry an ``item`` column (and the Site Material table
has since been renamed to ``Special Project Package``).
"""

from __future__ import annotations

import frappe


def execute():
	# Include both the legacy ("Special Project Site Material") and the renamed
	# ("Special Project Package") doctype names so the patch is safe to re-run
	# regardless of install timing.
	for doctype in (
		"Special Project Site Material",
		"Special Project Package",
		"Special Project Site Receipt",
	):
		table = f"tab{doctype}"
		if not frappe.db.table_exists(table):
			continue
		columns = {c["Field"] for c in frappe.db.sql(f"SHOW COLUMNS FROM `{table}`", as_dict=True)}
		if "item" in columns:
			frappe.db.sql_ddl(f"ALTER TABLE `{table}` DROP COLUMN `item`")
