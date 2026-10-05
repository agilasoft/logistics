# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Remove linked-service milestone copies from the Sea Shipment grid.

Those rows stay on the Transport Order, Transport Job, or Declaration.
"""

import frappe


def execute():
	if not frappe.db.table_exists("Sea Shipment Milestone"):
		return
	if not frappe.db.has_column("Sea Shipment Milestone", "from_service"):
		return
	frappe.db.sql(
		"""
		delete from `tabSea Shipment Milestone`
		where parenttype = 'Sea Shipment'
			and ifnull(from_service, 0) = 1
		"""
	)
