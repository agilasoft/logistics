# -*- coding: utf-8 -*-
"""Backfill release journal bill_no and drop stored Cash Advance Request rollup columns."""

from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.exists("DocType", "Cash Advance Request"):
		return

	# Link existing release journal entries before virtual-field migration.
	if frappe.db.has_column("Cash Advance Request", "advance_journal_entry"):
		rows = frappe.db.sql(
			"""
			SELECT name, advance_journal_entry
			FROM `tabCash Advance Request`
			WHERE IFNULL(advance_journal_entry, '') != ''
			"""
		)
		for request_name, je_name in rows:
			if not je_name or not frappe.db.exists("Journal Entry", je_name):
				continue
			current_bill_no = frappe.db.get_value("Journal Entry", je_name, "bill_no")
			if not current_bill_no:
				frappe.db.set_value("Journal Entry", je_name, "bill_no", request_name, update_modified=False)

	for fieldname in (
		"total_liquidated",
		"returned",
		"refunded",
		"unliquidated",
		"advance_journal_entry",
		"refund_return_date",
		"reference",
		"from_to",
	):
		if frappe.db.has_column("Cash Advance Request", fieldname):
			frappe.db.sql_ddl(f"ALTER TABLE `tabCash Advance Request` DROP COLUMN `{fieldname}`")

	frappe.clear_cache(doctype="Cash Advance Request")
