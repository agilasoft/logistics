# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Retry drop of Sales Quote Charge parameter columns (fix table_exists check in prior patch)."""

from __future__ import unicode_literals

from logistics.patches.v3_0_drop_sales_quote_charge_parameter_columns import (
	_COLUMNS_TO_DROP,
	_backfill_parameters_display,
	_drop_column_if_exists,
)

import frappe


def execute():
	if not frappe.db.exists("DocType", "Sales Quote Charge"):
		return
	for column in _COLUMNS_TO_DROP:
		_drop_column_if_exists("Sales Quote Charge", column)
	_backfill_parameters_display()
	frappe.clear_cache(doctype="Sales Quote Charge")
