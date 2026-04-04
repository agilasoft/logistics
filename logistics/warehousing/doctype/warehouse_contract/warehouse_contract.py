# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class WarehouseContract(Document):
	def validate(self):
		"""Validate Warehouse Contract data"""
		# Get original sales_quote from database if document exists
		original_sales_quote = None
		if not self.is_new():
			try:
				original_sales_quote = frappe.db.get_value(self.doctype, self.name, 'sales_quote')
			except Exception:
				pass
		
		# Validate One-off Sales Quote not already converted
		if self.sales_quote:
			from logistics.pricing_center.doctype.sales_quote.sales_quote import validate_one_off_quote_not_converted
			validate_one_off_quote_not_converted(self.sales_quote, self.doctype, self.name)
		
		# Handle sales_quote field clearing - reset One-off quote if cleared
		if not self.is_new() and original_sales_quote and not self.sales_quote:
			# sales_quote was cleared, check if it was a One-off quote and reset it
			try:
				if frappe.db.exists("Sales Quote", original_sales_quote):
					sq = frappe.get_doc("Sales Quote", original_sales_quote)
					if sq.quotation_type == "One-off":
						from logistics.pricing_center.doctype.sales_quote.sales_quote import reset_one_off_quote_on_cancel
						reset_one_off_quote_on_cancel(original_sales_quote)
			except Exception:
				pass
	
	def after_submit(self):
		"""Update One-off Sales Quote status to Converted when Warehouse Contract is submitted."""
		if self.sales_quote:
			from logistics.pricing_center.doctype.sales_quote.sales_quote import update_one_off_quote_on_submit
			update_one_off_quote_on_submit(self.sales_quote, self.name, self.doctype)
	
	def on_cancel(self):
		"""Reset One-off Sales Quote status when Warehouse Contract is cancelled."""
		if self.sales_quote:
			from logistics.pricing_center.doctype.sales_quote.sales_quote import reset_one_off_quote_on_cancel
			reset_one_off_quote_on_cancel(self.sales_quote)


@frappe.whitelist()
def get_rates_from_sales_quote(warehouse_contract, sales_quote):
	"""Get rates from Sales Quote Charge (Warehousing) or Sales Quote Warehouse (legacy)."""
	if not sales_quote:
		frappe.throw("Please select a Sales Quote first")
	
	# Get the Warehouse Contract document
	warehouse_contract_doc = frappe.get_doc("Warehouse Contract", warehouse_contract)
	
	# Get the Sales Quote document
	sales_quote_doc = frappe.get_doc("Sales Quote", sales_quote)
	
	# Prefer Sales Quote Charge (service_type=Warehousing)
	warehouse_items = []
	if hasattr(sales_quote_doc, "charges") and sales_quote_doc.charges:
		warehouse_items = [c for c in sales_quote_doc.charges if c.get("service_type") == "Warehousing"]
	if not warehouse_items and hasattr(sales_quote_doc, "warehousing") and sales_quote_doc.warehousing:
		warehouse_items = list(sales_quote_doc.warehousing)
	
	if not warehouse_items:
		frappe.throw("No warehouse rates found in the selected Sales Quote")
	
	# Clear existing items
	warehouse_contract_doc.items = []
	
	# Import rates from Sales Quote Charge (Warehousing) or Sales Quote Warehouse (legacy)
	for warehouse_item in warehouse_items:
		contract_item = warehouse_contract_doc.append("items", {})
		# Support both Sales Quote Charge (item_code) and Sales Quote Warehouse (item)
		item_ref = warehouse_item.get("item_code") or warehouse_item.get("item")
		contract_item.item_charge = item_ref
		contract_item.item_name = warehouse_item.get("item_name")
		contract_item.currency = warehouse_item.get("currency") or warehouse_item.get("selling_currency")
		contract_item.rate = warehouse_item.get("unit_rate")
		contract_item.calculation_method = warehouse_item.get("calculation_method")
		contract_item.unit_type = warehouse_item.get("unit_type")
		contract_item.uom = warehouse_item.get("uom")
		contract_item.minimum_quantity = warehouse_item.get("minimum_quantity")
		contract_item.minimum_charge = warehouse_item.get("minimum_charge")
		contract_item.maximum_charge = warehouse_item.get("maximum_charge")
		contract_item.base_amount = warehouse_item.get("base_amount")
		# Legacy Sales Quote Warehouse fields (storage_charge, etc. come from Item via fetch_from when set)
		if warehouse_item.get("storage_charge") is not None:
			contract_item.storage_charge = warehouse_item.storage_charge
		if warehouse_item.get("inbound_charge") is not None:
			contract_item.inbound_charge = warehouse_item.inbound_charge
		if warehouse_item.get("outbound_charge") is not None:
			contract_item.outbound_charge = warehouse_item.outbound_charge
		if warehouse_item.get("vas_charge") is not None:
			contract_item.vas_charge = warehouse_item.vas_charge
		if warehouse_item.get("stocktake_charge") is not None:
			contract_item.stocktake_charge = warehouse_item.stocktake_charge
		if warehouse_item.get("handling_unit_type"):
			contract_item.handling_unit_type = warehouse_item.handling_unit_type
		if warehouse_item.get("storage_type"):
			contract_item.storage_type = warehouse_item.storage_type
		if warehouse_item.get("volume_calculation_method"):
			contract_item.volume_calculation_method = warehouse_item.volume_calculation_method
		if warehouse_item.get("billing_time_unit"):
			contract_item.billing_time_unit = warehouse_item.billing_time_unit
		if warehouse_item.get("billing_time_multiplier") is not None:
			contract_item.billing_time_multiplier = warehouse_item.billing_time_multiplier
		if warehouse_item.get("minimum_billing_time") is not None:
			contract_item.minimum_billing_time = warehouse_item.minimum_billing_time
	
	# Save the document
	warehouse_contract_doc.save()
	
	return True
