# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Drop Sales Quote Service table after migration to main_service + charges."""

import frappe


def execute():
	"""Drop tabSales Quote Service table."""
	if frappe.db.table_exists("Sales Quote Service"):
		frappe.db.sql("DROP TABLE IF EXISTS `tabSales Quote Service`")
		frappe.db.commit()
