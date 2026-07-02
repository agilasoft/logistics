# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Drop legacy ``service_scope`` column from Linked Service and operational headers."""

from __future__ import unicode_literals

import frappe

_LINKED_SERVICE_DT = (
	"Linked Service",
	"Internal Job",
)

_OPERATIONAL_DT = (
	"Air Booking",
	"Air Shipment",
	"Sea Booking",
	"Sea Shipment",
	"Transport Order",
	"Transport Job",
	"Declaration",
	"Declaration Order",
	"Warehouse Job",
	"Inbound Order",
	"Release Order",
	"Project Job",
	"MICE Job",
	"Exhibit Job",
)


def execute():
	for dt in _LINKED_SERVICE_DT + _OPERATIONAL_DT:
		if not frappe.db.table_exists(f"tab{dt}"):
			continue
		frappe.db.updatedb(dt)
		_drop_column_if_exists(dt, "service_scope")
		frappe.clear_cache(doctype=dt)


def _drop_column_if_exists(doctype: str, column: str) -> None:
	if not frappe.db.table_exists(doctype):
		return
	columns = {c.lower() for c in frappe.db.get_table_columns(doctype)}
	if column.lower() not in columns:
		return
	frappe.db.sql_ddl(f"ALTER TABLE `tab{doctype}` DROP COLUMN `{column}`")
