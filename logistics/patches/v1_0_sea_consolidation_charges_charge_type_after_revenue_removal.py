# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Remap legacy Revenue charge_type on Sea Consolidation Charges after revenue field removal."""

import frappe


def execute():
	if not frappe.db.exists("DocType", "Sea Consolidation Charges"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabSea Consolidation Charges`
		SET `charge_type` = 'Cost'
		WHERE IFNULL(`charge_type`, '') = 'Revenue'
		"""
	)
