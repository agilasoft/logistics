# Copyright (c) 2025, Agilasoft Cloud Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class DeclarationOrder(Document):
	def before_save(self):
		from logistics.utils.module_integration import run_propagate_on_link
		run_propagate_on_link(self)


@frappe.whitelist()
def get_sales_quote_details(sales_quote):
	"""Return customer, company, customs_authority from Sales Quote for use in form."""
	if not sales_quote:
		return {}
	out = frappe.db.get_value(
		"Sales Quote",
		sales_quote,
		["customer", "company", "customs_authority", "branch", "cost_center", "profit_center"],
		as_dict=True,
	)
	return out or {}
