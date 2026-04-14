# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Rename hazardous -> contains_dangerous_goods on Transport Order, Transport Job, Transport Leg (align with freight)."""

import frappe


def execute():
	for doctype in ("Transport Order", "Transport Job", "Transport Leg"):
		_rename_column_if_exists(doctype, "hazardous", "contains_dangerous_goods")
	frappe.db.commit()


def _rename_column_if_exists(doctype: str, old_name: str, new_name: str) -> None:
	if not frappe.db.exists("DocType", doctype):
		return
	table = "tab" + doctype.replace(" ", " ")
	try:
		columns = frappe.db.sql("SHOW COLUMNS FROM `{0}`".format(table), as_dict=True)
		col_names = [c.get("Field") for c in columns]
		if old_name not in col_names or new_name in col_names:
			return
		old_col = next((c for c in columns if c.get("Field") == old_name), None)
		if not old_col:
			return
		col_type = old_col.get("Type") or "int(1) not null default 0"
		frappe.db.sql(
			"ALTER TABLE `{0}` CHANGE COLUMN `{1}` `{2}` {3}".format(table, old_name, new_name, col_type)
		)
	except Exception as e:
		frappe.log_error(
			"rename_transport_hazardous: " + str(e),
			"Patch v1_0_rename_transport_hazardous_to_contains_dangerous_goods",
		)
