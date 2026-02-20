# Backfill quote_type and quote from sales_quote for Transport Order, Air Booking, Sea Booking
from __future__ import unicode_literals

import frappe


def execute():
	for doctype in ("Transport Order", "Air Booking", "Sea Booking"):
		if not frappe.db.table_exists(doctype):
			continue
		# Check if quote_type column exists (new schema)
		try:
			frappe.db.sql("""
				UPDATE `tab{0}`
				SET quote_type = 'Sales Quote', quote = sales_quote
				WHERE sales_quote IS NOT NULL AND sales_quote != ''
				AND (quote_type IS NULL OR quote_type = '')
			""".format(doctype))
		except Exception:
			pass
	frappe.db.commit()
