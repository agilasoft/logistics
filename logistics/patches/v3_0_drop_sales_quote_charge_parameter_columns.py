# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Drop per-row routing parameter columns from Sales Quote Charge (parameters now on Services)."""

from __future__ import unicode_literals

import frappe

from logistics.utils.sales_quote_charge_parameters import (
	SALES_QUOTE_CHARGE_PARAMETER_FIELDS,
	refresh_sales_quote_charge_parameters_display,
)


_COLUMNS_TO_DROP = tuple(
	fn for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS if fn != "charge_group"
)


def execute():
	if not frappe.db.exists("DocType", "Sales Quote Charge"):
		return
	frappe.db.updatedb("Sales Quote Charge")
	for column in _COLUMNS_TO_DROP:
		_drop_column_if_exists("Sales Quote Charge", column)
	_backfill_parameters_display()
	frappe.clear_cache(doctype="Sales Quote Charge")


def _drop_column_if_exists(doctype: str, column: str) -> None:
	if not frappe.db.table_exists(doctype):
		return
	columns = {c.lower() for c in frappe.db.get_table_columns(doctype)}
	if column.lower() not in columns:
		return
	frappe.db.sql_ddl(f"ALTER TABLE `tab{doctype}` DROP COLUMN `{column}`")


def _backfill_parameters_display() -> None:
	if not frappe.db.table_exists("tabSales Quote"):
		return
	if "parameters" not in {c.lower() for c in frappe.db.get_table_columns("Sales Quote Charge")}:
		return
	quotes = frappe.get_all("Sales Quote", pluck="name", limit_page_length=0)
	for name in quotes:
		try:
			doc = frappe.get_doc("Sales Quote", name)
		except Exception:
			continue
		changed = False
		for row in doc.get("charges") or []:
			before = getattr(row, "parameters", None) or ""
			after = refresh_sales_quote_charge_parameters_display(row, doc)
			if after != before:
				changed = True
		if changed:
			doc.flags.ignore_validate = True
			doc.save(ignore_permissions=True)
	frappe.db.commit()
