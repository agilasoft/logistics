# Drop One-Off Quote doctype tables (doctype removed, no data migration)
from __future__ import unicode_literals

import frappe


def execute():
	# Drop child tables first (parenttype references parent)
	tables = [
		"tabOne-Off Quote Warehouse",
		"tabOne-Off Quote Transport",
		"tabOne-Off Quote Customs",
		"tabOne-Off Quote Air Freight",
		"tabOne-Off Quote Sea Freight",
		"tabOne-Off Quote",
	]
	for table in tables:
		if frappe.db.table_exists(table):
			frappe.db.sql(f"DROP TABLE IF EXISTS `{table}`")
	frappe.db.commit()
