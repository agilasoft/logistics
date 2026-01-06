# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WarehouseContract(Document):
	pass


@frappe.whitelist()
def get_rates_from_sales_quote(warehouse_contract, sales_quote):
	"""Get rates from Sales Quote warehouse table and populate warehouse contract items"""
	if not sales_quote:
		frappe.throw("Please select a Sales Quote first")
	
	# Get the Warehouse Contract document
	warehouse_contract_doc = frappe.get_doc("Warehouse Contract", warehouse_contract)
	
	# Get the Sales Quote document
	sales_quote_doc = frappe.get_doc("Sales Quote", sales_quote)
	
	if not sales_quote_doc.warehousing:
		frappe.throw("No warehouse rates found in the selected Sales Quote")
	
	# Clear existing items
	warehouse_contract_doc.items = []
	
	# Import rates from Sales Quote warehouse table
	for warehouse_item in sales_quote_doc.warehousing:
		contract_item = warehouse_contract_doc.append("items", {})
		
		# Map fields from Sales Quote Warehouse to Warehouse Contract Item
		contract_item.item_charge = warehouse_item.item
		contract_item.item_name = warehouse_item.item_name
		contract_item.storage_charge = warehouse_item.storage_charge
		contract_item.inbound_charge = warehouse_item.inbound_charge
		contract_item.outbound_charge = warehouse_item.outbound_charge
		contract_item.vas_charge = warehouse_item.vas_charge
		contract_item.stocktake_charge = warehouse_item.stocktake_charge
		contract_item.handling_unit_type = warehouse_item.handling_unit_type
		contract_item.storage_type = warehouse_item.storage_type
		contract_item.calculation_method = warehouse_item.calculation_method
		contract_item.unit_type = warehouse_item.unit_type
		contract_item.volume_calculation_method = warehouse_item.volume_calculation_method
		contract_item.uom = warehouse_item.uom
		contract_item.billing_time_unit = warehouse_item.billing_time_unit
		contract_item.billing_time_multiplier = warehouse_item.billing_time_multiplier
		contract_item.minimum_billing_time = warehouse_item.minimum_billing_time
		contract_item.currency = warehouse_item.selling_currency
		contract_item.rate = warehouse_item.unit_rate
		# Copy calculation method fields
		contract_item.minimum_quantity = warehouse_item.minimum_quantity
		contract_item.minimum_charge = warehouse_item.minimum_charge
		contract_item.maximum_charge = warehouse_item.maximum_charge
		contract_item.base_amount = warehouse_item.base_amount
	
	# Save the document
	warehouse_contract_doc.save()
	
	return True
