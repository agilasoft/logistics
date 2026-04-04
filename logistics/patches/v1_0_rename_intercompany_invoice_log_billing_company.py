# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Rename billing_company -> main_job_company on Intercompany Invoice Log (align with Main Job company)."""

import frappe
from frappe.utils import get_table_name


def execute():
	_rename_column_if_exists("Intercompany Invoice Log", "billing_company", "main_job_company")
	frappe.db.commit()


def _rename_column_if_exists(doctype: str, old_name: str, new_name: str) -> None:
	if not frappe.db.exists("DocType", doctype):
		return
	table = get_table_name(doctype)
	try:
		columns = frappe.db.sql("SHOW COLUMNS FROM `{0}`".format(table), as_dict=True)
		col_names = [c.get("Field") for c in columns]
		if old_name not in col_names or new_name in col_names:
			return
		old_col = next((c for c in columns if c.get("Field") == old_name), None)
		if not old_col:
			return
		col_type = old_col.get("Type") or "varchar(140)"
		frappe.db.sql(
			"ALTER TABLE `{0}` CHANGE COLUMN `{1}` `{2}` {3}".format(table, old_name, new_name, col_type)
		)
	except Exception as e:
		frappe.log_error(
			"rename_intercompany_invoice_log: " + str(e),
			"Patch v1_0_rename_intercompany_invoice_log_billing_company",
		)
