# -*- coding: utf-8 -*-
"""Backfill Cash Advance Request liquidation totals from submitted liquidations."""

from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.exists("DocType", "Cash Advance Liquidation"):
		return

	requests = frappe.db.sql(
		"""
		SELECT DISTINCT cash_advance_request
		FROM `tabCash Advance Liquidation`
		WHERE docstatus = 1 AND IFNULL(cash_advance_request, '') != ''
		"""
	)
	if not requests:
		return

	from logistics.cash_advance.totals_sync import sync_cash_advance_request_totals

	for (request_name,) in requests:
		sync_cash_advance_request_totals(request_name)
