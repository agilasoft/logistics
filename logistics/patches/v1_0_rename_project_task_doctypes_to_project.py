# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Rename Project Task Order → Project Order and Project Task Job → Project Job.

Runs in pre_model_sync so the database DocType names match the shipped JSON before migrate
sync loads the new ``project_order`` / ``project_job`` modules.

``frappe.rename_doc`` is invoked with ``rename_dynamic_links`` monkey-patched out: walking the
dynamic link map probes every table that declares a Dynamic Link field, and any pre-existing
schema drift (column declared in a DocType but not yet synced to the table) would surface as an
``Unknown column`` error during this pre-model-sync patch. We rewrite the affected Select /
Dynamic Link string values explicitly below, so skipping the framework's traversal is safe.

The patch is idempotent and recovers from a partially-applied previous run where
``rename_parent_and_child`` updated the DocType row name but ``after_rename`` never got to run
the SQL ``RENAME TABLE`` (and where Frappe's later schema sync auto-created an empty shell
table at the new name).
"""

import frappe
from frappe.model import rename_doc as _rename_doc_mod


# Job is renamed first because Project Order's connections (and any downstream Dynamic Links)
# reference Project Job.
_DOCTYPE_RENAMES = (
	("Project Task Job", "Project Job"),
	("Project Task Order", "Project Order"),
)

# Tables / fields where the old DocType label is stored as a string value (Select or Data) and
# must be rewritten after the DocType has been renamed.
_SELECT_VALUE_REWRITES = (
	("tabInternal Job Detail", "job_type", "Project Task Job", "Project Job"),
	("tabInternal Job Detail", "job_type", "Project Task Order", "Project Order"),
	("tabAir Shipment", "main_job_type", "Project Task Job", "Project Job"),
	("tabSea Shipment", "main_job_type", "Project Task Job", "Project Job"),
	("tabTransport Job", "main_job_type", "Project Task Job", "Project Job"),
	("tabWarehouse Job", "main_job_type", "Project Task Job", "Project Job"),
	("tabDeclaration", "main_job_type", "Project Task Job", "Project Job"),
	("tabExhibit Job", "main_job_type", "Project Task Job", "Project Job"),
	("tabProject Task Job", "main_job_type", "Project Task Job", "Project Job"),
	("tabProject Job", "main_job_type", "Project Task Job", "Project Job"),
)


def _table_exists(name: str) -> bool:
	return bool(frappe.db.sql("SHOW TABLES LIKE %s", (name,)))


def _row_count(table: str) -> int:
	try:
		return int(frappe.db.sql(f"SELECT COUNT(*) FROM `{table}`")[0][0])
	except Exception:
		return 0


def _column_count(table: str) -> int:
	try:
		return len(frappe.db.sql(f"DESCRIBE `{table}`"))
	except Exception:
		return 0


def _recover_partial_table_rename(old_doctype: str, new_doctype: str) -> None:
	"""DocType row was renamed in a previous failed run but the table wasn't.

	The schema sync may have since auto-created an empty shell table at the new name. Drop the
	empty shell (if any) and rename the old table to take its place.
	"""
	old_table = f"tab{old_doctype}"
	new_table = f"tab{new_doctype}"
	if not _table_exists(old_table):
		return

	if _table_exists(new_table):
		# Only safe to drop an auto-created shell (no rows). Otherwise the operator must merge
		# rows by hand.
		if _row_count(new_table) == 0:
			frappe.db.sql_ddl(f"DROP TABLE `{new_table}`")
		else:
			frappe.throw(
				f"Cannot rename {old_table} → {new_table}: target table has {_row_count(new_table)} "
				"rows. Manual data merge required."
			)

	frappe.db.sql_ddl(f"RENAME TABLE `{old_table}` TO `{new_table}`")
	frappe.db.commit()


def _rename_doctype(old_name: str, new_name: str) -> None:
	old_exists = frappe.db.exists("DocType", old_name)
	new_exists = frappe.db.exists("DocType", new_name)

	if not old_exists and not new_exists:
		return

	if not old_exists and new_exists:
		# Possible mid-rename state: DocType row was renamed but table rename was interrupted.
		_recover_partial_table_rename(old_name, new_name)
		return

	if old_exists and new_exists:
		# Stale duplicate DocType row at the new name — drop only if it carries no data.
		if frappe.db.count(new_name) == 0:
			frappe.delete_doc("DocType", new_name, force=True, ignore_missing=True)
			# fall through to normal rename below
		else:
			frappe.throw(
				f"Cannot rename {old_name} → {new_name}: both DocTypes exist with data in {new_name}."
			)

	# Normal path: rename the DocType, table, link values, customizations, etc.
	original_rename_dynamic_links = _rename_doc_mod.rename_dynamic_links
	_rename_doc_mod.rename_dynamic_links = lambda *args, **kwargs: None
	try:
		frappe.rename_doc(
			"DocType",
			old_name,
			new_name,
			force=True,
			merge=False,
		)
	finally:
		_rename_doc_mod.rename_dynamic_links = original_rename_dynamic_links


def _rewrite_select_value(table: str, field: str, old_value: str, new_value: str) -> None:
	if not frappe.db.table_exists(table):
		return
	try:
		columns = {row.get("Field") for row in frappe.db.sql(f"DESCRIBE `{table}`", as_dict=True)}
	except Exception:
		return
	if field not in columns:
		return
	frappe.db.sql(
		f"UPDATE `{table}` SET `{field}` = %s WHERE `{field}` = %s",
		(new_value, old_value),
	)


def execute():
	frappe.flags.in_patch = True
	try:
		for old_name, new_name in _DOCTYPE_RENAMES:
			_rename_doctype(old_name, new_name)

		for table, field, old_value, new_value in _SELECT_VALUE_REWRITES:
			_rewrite_select_value(table, field, old_value, new_value)

		frappe.db.commit()
	finally:
		frappe.flags.in_patch = False
