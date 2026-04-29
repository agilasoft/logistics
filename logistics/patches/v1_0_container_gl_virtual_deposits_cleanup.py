# -*- coding: utf-8 -*-
# Copyright (c) 2026, Logistics Team and contributors
"""
Migrate Container refund_request_journal_entry to Container Refund Link; remove legacy child DocTypes.
"""

from __future__ import unicode_literals

import frappe


def execute():
	# 1) Refund links from old Container Deposit child rows
	if frappe.db.table_exists("tabContainer Deposit") and frappe.db.table_exists("tabContainer Refund Link"):
		rows = frappe.db.sql(
			"""
			SELECT parent, purchase_invoice, refund_request_journal_entry
			FROM `tabContainer Deposit`
			WHERE IFNULL(refund_request_journal_entry, '') != '' AND IFNULL(purchase_invoice, '') != ''
			""",
			as_dict=True,
		)
		for r in rows or []:
			exists = frappe.db.sql(
				"""
				SELECT name FROM `tabContainer Refund Link`
				WHERE parent = %s AND purchase_invoice = %s LIMIT 1
				""",
				(r.parent, r.purchase_invoice),
			)
			if exists:
				continue
			try:
				doc = frappe.get_doc("Container", r.parent)
				doc.append(
					"refund_links",
					{
						"purchase_invoice": r.purchase_invoice,
						"journal_entry": r.refund_request_journal_entry,
					},
				)
				doc.save(ignore_permissions=True)
			except Exception:
				frappe.log_error(
					title="Container Refund Link migration",
					message=frappe.get_traceback(),
				)
	# 2) Remove legacy child doctypes
	for dt in ("Container Deposit", "Container Charge Line"):
		if frappe.db.exists("DocType", dt):
			try:
				frappe.delete_doc("DocType", dt, force=True, ignore_permissions=True)
			except Exception:
				frappe.log_error(
					title="Container child doctype drop",
					message=frappe.get_traceback(),
				)
