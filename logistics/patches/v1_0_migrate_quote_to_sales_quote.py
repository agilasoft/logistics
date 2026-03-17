# Migrate quote/quote_type to sales_quote before removing Dynamic Link fields.
# Copy quote to sales_quote where quote_type='Sales Quote' and sales_quote is empty.
from __future__ import unicode_literals

import frappe


def execute():
	for doctype in ("Air Booking", "Sea Booking", "Transport Order", "Declaration"):
		if not frappe.db.table_exists(doctype):
			continue
		# Check if quote_type and quote columns exist (old schema)
		columns = [c.get("Field") for c in frappe.db.sql("DESCRIBE `tab{0}`".format(doctype), as_dict=True)]
		if "quote_type" not in columns or "quote" not in columns:
			continue
		try:
			frappe.db.sql("""
				UPDATE `tab{0}`
				SET sales_quote = quote
				WHERE quote_type = 'Sales Quote' AND quote IS NOT NULL AND quote != ''
				AND (sales_quote IS NULL OR sales_quote = '')
			""".format(doctype))
		except Exception:
			pass
	frappe.db.commit()
