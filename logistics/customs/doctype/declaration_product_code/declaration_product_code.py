# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class DeclarationProductCode(Document):
	def validate(self):
		if not self.product_code and self.item_code:
			self.product_code = self.item_code


@frappe.whitelist()
def get_declaration_product_code_details(name):
	"""Return fields to populate Commercial Invoice Line Item when Declaration Product Code is selected."""
	if not name:
		return {}
	doc = frappe.get_doc("Declaration Product Code", name)
	return {
		"item": doc.item_code,
		"product_code": doc.product_code or doc.item_code,
		"procedure_code": doc.procedure_code,
		"tariff": doc.tariff_number or doc.hs_code,
		"goods_description": doc.goods_description,
		"commodity_code": doc.commodity_code,
		"goods_origin": doc.goods_origin,
		"preference": doc.preference,
	}
