# Copyright (c) 2026, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Rename accounting dimension column job_costing_number → job_number on GL, invoices, and all
doctypes that had the field. Updates Custom Field, Accounting Dimension.fieldname, Property
Setter, and removes stale DocField rows for the old name.

Runs after model sync so DocType JSON can introduce `job_number` first; this patch merges
data if both columns exist, then drops the legacy column.
"""

import frappe

OLD = "job_costing_number"
NEW = "job_number"


def execute():
	if not frappe.db.table_exists("GL Entry"):
		return True

	columns_done = _rename_or_merge_columns_on_all_tables()
	# Always reconcile metadata: first migrate may rename columns only; a later run then skips
	# column work but Custom Field rows can still reference the old fieldname.
	_update_custom_fields()
	_update_accounting_dimension()
	_update_property_setters()
	_remove_stale_docfields()
	frappe.db.commit()
	frappe.clear_cache()
	for dt in columns_done:
		try:
			frappe.clear_cache(doctype=dt)
		except Exception:
			pass

	return True


def _rename_or_merge_columns_on_all_tables():
	"""Return list of doctypes whose physical table was touched."""
	touched = []
	for dt in frappe.get_all("DocType", pluck="name"):
		try:
			if not frappe.db.table_exists(dt):
				continue
		except Exception:
			continue
		cols = frappe.db.get_table_columns(dt)
		if OLD not in cols:
			continue
		if NEW in cols:
			frappe.db.sql(
				f"""
				UPDATE `tab{dt}`
				SET `{NEW}` = `{OLD}`
				WHERE (`{NEW}` IS NULL OR `{NEW}` = '')
				AND (`{OLD}` IS NOT NULL AND `{OLD}` != '')
				"""
			)
			try:
				frappe.db.sql_ddl(f"ALTER TABLE `tab{dt}` DROP COLUMN `{OLD}`")
			except Exception:
				pass
		else:
			frappe.db.rename_column(dt, OLD, NEW)
		touched.append(dt)
	return touched


def _update_custom_fields():
	for cf in frappe.get_all("Custom Field", filters={"fieldname": OLD}, fields=["name", "dt"]):
		new_name = f"{cf.dt}-{NEW}"
		if frappe.db.exists("Custom Field", new_name):
			frappe.delete_doc("Custom Field", cf.name, force=True, ignore_permissions=True)
			continue
		frappe.db.sql(
			"UPDATE `tabCustom Field` SET name=%s, fieldname=%s WHERE name=%s",
			(new_name, NEW, cf.name),
		)


def _update_accounting_dimension():
	frappe.db.sql(
		"""
		UPDATE `tabAccounting Dimension`
		SET fieldname=%s
		WHERE fieldname=%s AND document_type=%s
		""",
		(NEW, OLD, "Job Number"),
	)


def _update_property_setters():
	frappe.db.sql(
		"UPDATE `tabProperty Setter` SET field_name=%s WHERE field_name=%s",
		(NEW, OLD),
	)


def _remove_stale_docfields():
	frappe.db.sql("DELETE FROM `tabDocField` WHERE fieldname=%s", (OLD,))
