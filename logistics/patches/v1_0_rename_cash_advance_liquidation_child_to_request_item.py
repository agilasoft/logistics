# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Rename child DocType Cash Advance Liquidation -> Cash Advance Request Item so Cash Advance Liquidation can be a parent doctype."""

from __future__ import unicode_literals

import frappe


def execute():
	if frappe.db.exists("DocType", "Cash Advance Request Item"):
		_fix_parentfield()
		frappe.db.commit()
		return

	if frappe.db.exists("DocType", "Cash Advance Liquidation"):
		meta = frappe.get_meta("Cash Advance Liquidation")
		if meta.istable:
			frappe.rename_doc("DocType", "Cash Advance Liquidation", "Cash Advance Request Item", force=True)

	_fix_parentfield()
	frappe.db.commit()


def _fix_parentfield():
	if not frappe.db.table_exists("tabCash Advance Request Item"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabCash Advance Request Item`
		SET parentfield=%(pf)s
		WHERE parenttype=%(pt)s
			AND IFNULL(parentfield, '') IN ('', 'liquidation')
		""",
		{"pf": "items", "pt": "Cash Advance Request"},
	)
