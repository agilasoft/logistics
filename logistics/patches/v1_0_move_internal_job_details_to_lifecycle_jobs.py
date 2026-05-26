# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Move ``internal_job_details`` rows on Special Project and Exhibit to the new
``lifecycle_jobs`` table backed by the ``Lifecycle Job`` child DocType.

This patch:
- Ensures the ``Lifecycle Job`` DocType is available (reloading from disk).
- Copies eligible rows from ``tabInternal Job Detail`` to ``tabLifecycle Job``,
  preserving columns that exist on both, plus lifecycle-stage / sp_* / financial
  columns that previously lived on ``Internal Job Detail`` and were moved here.
- Re-points each copied row's parentfield to ``lifecycle_jobs``.
- Deletes the migrated rows from ``tabInternal Job Detail`` so the old field
  has no lingering data.
"""

from __future__ import annotations

import frappe

_PARENT_DOCTYPES = ("Special Project", "Exhibit")

# Lifecycle / sp_* columns that previously lived on Internal Job Detail
# (controlled by ``depends_on`` in the JSON) and now belong solely to Lifecycle Job.
# Financial columns (planned_cost/actual_cost/planned_revenue/actual_revenue) are
# preserved on Internal Job Detail because the internal-job rollup writes them on
# operational-doc Main Services (Air/Sea Shipment, Transport Job, Declaration).
_LIFECYCLE_EXTRA_COLUMNS = (
	"lifecycle_stage",
	"activity_code",
	"activity_name",
	"lifecycle_activity_status",
	"sp_site",
	"sp_manpower",
	"sp_skilled",
	"sp_equipment_type",
	"sp_handling",
	"sp_resource_notes",
)


def _column_exists(table: str, column: str) -> bool:
	rows = frappe.db.sql(
		"""
		SELECT COLUMN_NAME
		FROM INFORMATION_SCHEMA.COLUMNS
		WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
		""",
		(table, column),
	)
	return bool(rows)


def execute():
	frappe.reload_doc("special_projects", "doctype", "lifecycle_job", force=True)
	frappe.reload_doc("logistics", "doctype", "internal_job_detail", force=True)

	old_table = "tabInternal Job Detail"
	new_table = "tabLifecycle Job"

	if not frappe.db.table_exists(new_table):
		frappe.db.sql_ddl(
			"""
			CREATE TABLE IF NOT EXISTS `tabLifecycle Job` LIKE `tabInternal Job Detail`
			"""
		)

	old_columns = {
		row[0]
		for row in frappe.db.sql(
			"""
			SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
			WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
			""",
			(old_table,),
		)
		or []
	}
	new_columns = {
		row[0]
		for row in frappe.db.sql(
			"""
			SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
			WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
			""",
			(new_table,),
		)
		or []
	}

	shared_columns = sorted(old_columns & new_columns)
	if not shared_columns:
		return

	col_csv = ", ".join("`{0}`".format(c) for c in shared_columns)
	placeholders = ", ".join(["%s"] * len(_PARENT_DOCTYPES))

	insert_sql = (
		"INSERT INTO `{new}` ({cols}) "
		"SELECT {cols} FROM `{old}` "
		"WHERE parenttype IN ({phs}) AND parentfield = 'internal_job_details' "
		"AND name NOT IN (SELECT name FROM `{new}`)"
	).format(new=new_table, cols=col_csv, old=old_table, phs=placeholders)
	frappe.db.sql(insert_sql, _PARENT_DOCTYPES)

	frappe.db.sql(
		"UPDATE `{new}` SET parentfield = 'lifecycle_jobs' "
		"WHERE parenttype IN ({phs}) AND parentfield = 'internal_job_details'".format(
			new=new_table, phs=placeholders
		),
		_PARENT_DOCTYPES,
	)

	frappe.db.sql(
		"DELETE FROM `{old}` WHERE parenttype IN ({phs}) AND parentfield = 'internal_job_details'".format(
			old=old_table, phs=placeholders
		),
		_PARENT_DOCTYPES,
	)

	for col in _LIFECYCLE_EXTRA_COLUMNS:
		if _column_exists("tabInternal Job Detail", col):
			try:
				frappe.db.sql_ddl(
					"ALTER TABLE `tabInternal Job Detail` DROP COLUMN `{0}`".format(col)
				)
			except Exception:
				frappe.log_error(
					title="Move lifecycle column to Lifecycle Job",
					message=f"Could not drop column {col} from tabInternal Job Detail",
				)

	frappe.db.commit()
