# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class StocktakeOrderItem(Document):
	# Measurements are read-only and fetched from Warehouse Item (item.*)
	pass
