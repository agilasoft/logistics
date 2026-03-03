# Set quotation_type = "Regular" for existing Sales Quotes (Unified DocType)
from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.table_exists("Sales Quote"):
		return
	# Set default quotation_type for existing records
	try:
		frappe.db.sql("""
			UPDATE `tabSales Quote`
			SET quotation_type = 'Regular'
			WHERE quotation_type IS NULL OR quotation_type = ''
		""")
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(f"Patch v1_0_add_quotation_type_to_sales_quote: {e}", "Quotation Type Migration")
