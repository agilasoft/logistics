# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Remove sequence column from Milestone Template Item (use idx for ordering)."""

from __future__ import unicode_literals

import frappe


def execute():
	"""Drop sequence column if it exists."""
	if frappe.db.has_column("Milestone Template Item", "sequence"):
		frappe.db.sql("ALTER TABLE `tabMilestone Template Item` DROP COLUMN `sequence`")
