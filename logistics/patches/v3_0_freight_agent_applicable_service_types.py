# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Backfill Applicable Service Types on existing Freight Agent masters (#1118)."""

import frappe


def execute():
	# Existing agents with no flags configured should remain usable for every service.
	frappe.db.sql(
		"""
		UPDATE `tabFreight Agent`
		SET air = 1, sea = 1, transport = 1, customs = 1, warehousing = 1
		WHERE COALESCE(air, 0) = 0
		  AND COALESCE(sea, 0) = 0
		  AND COALESCE(transport, 0) = 0
		  AND COALESCE(customs, 0) = 0
		  AND COALESCE(warehousing, 0) = 0
		"""
	)
