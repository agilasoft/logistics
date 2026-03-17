# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Backfill update_trigger_type from trigger_type on Milestone Template Item (redesign: Date Based / Field Based)."""

from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.has_column("Milestone Template Item", "update_trigger_type"):
		return
	if not frappe.db.has_column("Milestone Template Item", "trigger_type"):
		return
	frappe.db.sql("""
		UPDATE `tabMilestone Template Item`
		SET update_trigger_type = CASE
			WHEN IFNULL(trigger_type, '') = 'Parent date field sync' THEN 'Date Based'
			WHEN IFNULL(trigger_type, '') = 'Parent field condition' THEN 'Field Based'
			ELSE 'None'
		END
		WHERE IFNULL(update_trigger_type, '') = ''
	""")
	frappe.db.commit()
