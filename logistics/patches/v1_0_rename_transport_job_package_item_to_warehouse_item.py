# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Rename Transport Job Package column item -> warehouse_item (align with package-level Warehouse Item link)."""

import frappe
from frappe.utils import get_table_name


def execute():
	_rename_column_if_exists("Transport Job Package", "item", "warehouse_item")
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
			"rename_transport_job_package_item: " + str(e),
			"Patch v1_0_rename_transport_job_package_item_to_warehouse_item",
		)
