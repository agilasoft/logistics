"""Mark existing Transport Vehicle permit rows as required.

The Required checkbox defaults to checked for new rows. Rows that already
existed before the column was added are stored as unchecked, so recorded
permits would not be enforced. This patch checks them once. Optional permits
can be unchecked after migrate, before enforcement is turned on.
"""

import frappe


def execute():
	if not frappe.db.table_exists("Transport Vehicle Permits"):
		return
	if not frappe.db.has_column("Transport Vehicle Permits", "required"):
		return
	frappe.db.sql(
		"""
		UPDATE `tabTransport Vehicle Permits`
		SET required = 1
		WHERE IFNULL(required, 0) = 0
		"""
	)
