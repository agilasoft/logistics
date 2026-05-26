# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Align Lifecycle Job job_type with Project Order links after Special Project create flow fix."""

from __future__ import annotations

import frappe


def _rewrite_select(table: str, field: str, old_value: str, new_value: str) -> None:
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


def _fix_project_job_rows_pointing_at_orders() -> None:
	table = "tabLifecycle Job"
	if not frappe.db.table_exists(table):
		return
	if not frappe.db.table_exists("tabProject Order"):
		return
	frappe.db.sql(
		f"""
		UPDATE `{table}` AS lj
		INNER JOIN `tabProject Order` AS po ON po.name = lj.job_no
		SET lj.job_type = 'Project Order'
		WHERE lj.job_type = 'Project Job' AND IFNULL(lj.job_no, '') != ''
		"""
	)


def execute():
	frappe.flags.in_patch = True
	try:
		for old_value, new_value in (
			("Project Task Order", "Project Order"),
			("Project Task Job", "Project Job"),
		):
			_rewrite_select("tabLifecycle Job", "job_type", old_value, new_value)
		_fix_project_job_rows_pointing_at_orders()
		frappe.db.commit()
	finally:
		frappe.flags.in_patch = False
