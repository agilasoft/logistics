# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Rename Special Project Site Material -> Special Project Package.

Companion field renames:
- Special Project.site_materials (table) -> packages
- Special Project.site_materials_summary -> packages_summary (HTML virtual, no data)
- Special Project Site Receipt.site_material_row -> package_row
- Project Job Material.site_material_row -> package_row
"""

import frappe


def _raw_table_exists(table_name: str) -> bool:
	"""Robust table check that does not depend on Frappe's DocType cache.

	``frappe.db.table_exists`` accepts a DocType name and prefixes ``tab`` internally,
	so it's wrong here where we already have the fully-qualified ``tab<DocType>`` name.
	Bypass that and query information_schema directly.
	"""
	rows = frappe.db.sql(
		"SELECT 1 FROM information_schema.tables "
		"WHERE table_schema = DATABASE() AND table_name = %s",
		(table_name,),
	)
	return bool(rows)


def _column_names(table: str) -> set[str]:
	rows = frappe.db.sql(f"SHOW COLUMNS FROM `{table}`", as_dict=True)
	return {r["Field"] for r in rows}


def _rename_or_drop_legacy_column(table: str, old: str, new: str, col_def: str = "INT NULL") -> None:
	"""Rename ``old`` -> ``new`` if only ``old`` exists; otherwise drop ``old`` after
	backfilling ``new`` from ``old`` where ``new`` is empty.

	Uses ``frappe.db.sql_ddl`` and commits explicitly before DDL to avoid
	``ImplicitCommitError`` when called after other write statements.
	"""
	cols = _column_names(table)
	if old in cols and new not in cols:
		frappe.db.commit()
		frappe.db.sql_ddl(f"ALTER TABLE `{table}` CHANGE `{old}` `{new}` {col_def}")
	elif old in cols and new in cols:
		frappe.db.sql(
			f"UPDATE `{table}` SET `{new}` = `{old}` "
			f"WHERE (`{new}` IS NULL OR `{new}` = 0) AND `{old}` IS NOT NULL"
		)
		frappe.db.commit()
		frappe.db.sql_ddl(f"ALTER TABLE `{table}` DROP COLUMN `{old}`")


def execute():
	# 1. Rename the DocType (renames tabSpecial Project Site Material -> tabSpecial Project Package).
	if frappe.db.exists("DocType", "Special Project Site Material") and not frappe.db.exists(
		"DocType", "Special Project Package"
	):
		frappe.rename_doc(
			"DocType",
			"Special Project Site Material",
			"Special Project Package",
			force=True,
			merge=False,
		)
		frappe.db.commit()

	# 2. Update child rows' parentfield: site_materials -> packages on Special Project.
	if _raw_table_exists("tabSpecial Project Package"):
		frappe.db.sql(
			"""
			UPDATE `tabSpecial Project Package`
			SET parentfield = %s
			WHERE parenttype = %s AND parentfield = %s
			""",
			("packages", "Special Project", "site_materials"),
		)
		frappe.db.commit()

	# 3. Rename site_material_row -> package_row on Special Project Site Receipt.
	if _raw_table_exists("tabSpecial Project Site Receipt"):
		_rename_or_drop_legacy_column(
			"tabSpecial Project Site Receipt",
			"site_material_row",
			"package_row",
		)

	# 4. Rename site_material_row -> package_row on Project Job Material.
	if _raw_table_exists("tabProject Job Material"):
		_rename_or_drop_legacy_column(
			"tabProject Job Material",
			"site_material_row",
			"package_row",
		)

	frappe.db.commit()

	# Clear cached metadata so subsequent reloads pick up the new names.
	frappe.clear_cache(doctype="Special Project")
	if frappe.db.exists("DocType", "Special Project Package"):
		frappe.clear_cache(doctype="Special Project Package")
	if frappe.db.exists("DocType", "Special Project Site Receipt"):
		frappe.clear_cache(doctype="Special Project Site Receipt")
	if frappe.db.exists("DocType", "Project Job Material"):
		frappe.clear_cache(doctype="Project Job Material")
