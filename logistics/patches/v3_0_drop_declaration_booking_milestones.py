# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Remove Declaration Order milestone copies from the Declaration grid.

Those rows stay on the Declaration Order. The declaration timeline reads them live.
"""

import frappe


def execute():
	if not frappe.db.table_exists("Declaration Milestone"):
		return
	if not frappe.db.has_column("Declaration Milestone", "from_booking"):
		return
	frappe.db.sql(
		"""
		delete from `tabDeclaration Milestone`
		where parenttype = 'Declaration'
			and ifnull(from_booking, 0) = 1
		"""
	)
