# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Migrate Special Project Service child-table rows to top-level documents.

Run in ``pre_model_sync`` before ``Special Project Service`` loses ``istable``.
Stashed rows are restored by ``v3_0_restore_special_project_service_documents``.
"""

from __future__ import annotations

import frappe


_STASH_TABLE = "_Logistics SP Service Child Stash"


def execute():
	table = "tabSpecial Project Service"
	if not frappe.db.table_exists(table):
		return
	if not frappe.db.has_column("Special Project Service", "parenttype"):
		return

	frappe.db.sql_ddl(
		f"""
		CREATE TABLE IF NOT EXISTS `{_STASH_TABLE}` (
			`name` varchar(140) NOT NULL,
			`parent` varchar(140),
			`row_json` longtext,
			PRIMARY KEY (`name`)
		) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
		"""
	)
	rows = frappe.db.sql(
		f"""
		SELECT * FROM `{table}`
		WHERE parenttype = 'Special Project' AND parentfield = 'special_project_services'
		""",
		as_dict=True,
	)
	import json

	for row in rows:
		parent = (row.pop("parent", None) or "").strip()
		row_name = (row.pop("name", None) or "").strip()
		for key in ("parenttype", "parentfield", "idx", "creation", "modified", "owner", "modified_by", "docstatus"):
			row.pop(key, None)
		row["parent_booking_type"] = "Special Project"
		row["parent_booking_name"] = parent
		frappe.db.sql(
			f"""
			INSERT INTO `{_STASH_TABLE}` (`name`, `parent`, `row_json`)
			VALUES (%s, %s, %s)
			ON DUPLICATE KEY UPDATE `parent` = VALUES(`parent`), `row_json` = VALUES(`row_json`)
			""",
			(row_name, parent, json.dumps(row, default=str)),
		)

	frappe.db.sql_ddl(f"DROP TABLE `{table}`")
	frappe.db.commit()
