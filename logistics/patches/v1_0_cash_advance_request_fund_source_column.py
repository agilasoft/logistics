# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Rename Cash Advance Request column get_from -> fund_source if present (pre DocType sync)."""

from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.table_exists("tabCash Advance Request"):
		return
	if not frappe.db.has_column("tabCash Advance Request", "get_from"):
		return
	if frappe.db.has_column("tabCash Advance Request", "fund_source"):
		return
	frappe.db.sql(
		"ALTER TABLE `tabCash Advance Request` CHANGE COLUMN `get_from` `fund_source` VARCHAR(140)"
	)
	frappe.db.commit()
