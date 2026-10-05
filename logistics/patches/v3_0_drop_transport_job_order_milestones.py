# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Remove Transport Order milestone copies from the Transport Job grid.

Those rows stay on the Transport Order. The job timeline reads them live.
"""

import frappe


def execute():
	if not frappe.db.table_exists("Transport Job Milestone"):
		return
	if not frappe.db.has_column("Transport Job Milestone", "from_booking"):
		return
	frappe.db.sql(
		"""
		delete from `tabTransport Job Milestone`
		where parenttype = 'Transport Job'
			and ifnull(from_booking, 0) = 1
		"""
	)
