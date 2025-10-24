# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, getdate


class SalesQuote(Document):
	@frappe.whitelist()
	def create_transport_order_from_sales_quote(self):
		"""
		Create a Transport Order from a Sales Quote when the quote is tagged as One-Off.
		
		Returns:
			dict: Result with created Transport Order name and status
		"""
		try:
			# Check if the quote is tagged as One-Off
			if not self.one_off:
				frappe.throw(_("This Sales Quote is not tagged as One-Off. Only One-Off quotes can create Transport Orders."))
			
			# Check if Sales Quote has transport details
			if not self.transport:
				frappe.throw(_("No transport details found in this Sales Quote."))
			
			# Allow creation of multiple Transport Orders from the same Sales Quote
			# No duplicate prevention - users can create multiple orders as needed
			
			# Create new Transport Order
			transport_order = frappe.new_doc("Transport Order")
			
			# Map basic fields from Sales Quote to Transport Order
			transport_order.customer = self.customer
			transport_order.booking_date = today()
			transport_order.sales_quote = self.name
			transport_order.transport_template = getattr(self, 'transport_template', None)
			transport_order.load_type = self.load_type
			transport_order.vehicle_type = self.vehicle_type
			transport_order.transport_job_type = getattr(self, 'transport_job_type', None)
			transport_order.company = self.company
			transport_order.branch = self.branch
			transport_order.cost_center = self.cost_center
			transport_order.profit_center = self.profit_center
			
			# Debug: Log sales_quote and transport_template fields
			frappe.log_error(f"SQ: {self.name}", "Debug Sales Quote")
			frappe.log_error(f"Template: {getattr(self, 'transport_template', 'NONE')}", "Debug Template")
			
			# Set location fields directly
			try:
				transport_order.location_type = getattr(self, 'location_type', None)
				transport_order.location_from = getattr(self, 'location_from', None)
				transport_order.location_to = getattr(self, 'location_to', None)
				
				# Debug: Log all available fields
				frappe.log_error(f"SQ Loc: {getattr(self, 'location_type', 'NONE')}|{getattr(self, 'location_from', 'NONE')}|{getattr(self, 'location_to', 'NONE')}", "Debug SQ Locations")
				frappe.log_error(f"TO Loc: {transport_order.location_type}|{transport_order.location_from}|{transport_order.location_to}", "Debug TO Locations")
			except Exception as e:
				frappe.log_error(f"Error setting location fields: {str(e)}", "Debug Location Fields Error")
			
			# Insert the Transport Order
			transport_order.insert(ignore_permissions=True)
			
			# Populate charges from Sales Quote Transport
			_populate_charges_from_sales_quote(transport_order, self)
			
			# Save the Transport Order
			transport_order.save(ignore_permissions=True)
			
			# Debug: Log final values after save
			frappe.log_error(f"Final: SQ={transport_order.sales_quote}, T={getattr(transport_order, 'transport_template', 'NONE')}", "Debug Final Basic")
			frappe.log_error(f"Final Loc: {getattr(transport_order, 'location_type', 'NONE')}|{getattr(transport_order, 'location_from', 'NONE')}|{getattr(transport_order, 'location_to', 'NONE')}", "Debug Final Locations")
			
			# Run Get Leg Plan if transport template is available
			if transport_order.transport_template:
				try:
					frappe.log_error(f"Running Leg Plan for TO: {transport_order.name}", "Debug Leg Plan")
					from logistics.transport.doctype.transport_order.transport_order import action_get_leg_plan
					leg_plan_result = action_get_leg_plan(
						docname=transport_order.name,
						replace=1,
						save=1
					)
					# Log key results separately to avoid truncation
					frappe.log_error(f"Legs Added: {leg_plan_result.get('legs_added', 0)}", "Debug Leg Count")
					frappe.log_error(f"Template: {leg_plan_result.get('template', 'NONE')}", "Debug Leg Template")
					frappe.log_error(f"Success: {leg_plan_result.get('ok', False)}", "Debug Leg Success")
				except Exception as e:
					frappe.log_error(f"Error running Get Leg Plan: {str(e)}", "Debug Leg Plan Error")
			
			# Prepare success message
			success_msg = f"Transport Order {transport_order.name} created successfully from Sales Quote {self.name}"
			if transport_order.transport_template:
				success_msg += f" with leg plan populated from template {transport_order.transport_template}"
			
			frappe.msgprint(
				success_msg,
				title="Transport Order Created",
				indicator="green"
			)
			
			return {
				"success": True,
				"message": f"Transport Order {transport_order.name} created successfully.",
				"transport_order": transport_order.name
			}
			
		except Exception as e:
			frappe.log_error(
				f"Error creating Transport Order from Sales Quote {self.name}: {str(e)}",
				"Sales Quote to Transport Order Creation Error"
			)
			frappe.throw(f"Error creating Transport Order: {str(e)}")

	@frappe.whitelist()
	def create_warehouse_contract_from_sales_quote(self):
		"""
		Create a Warehouse Contract from a Sales Quote when the quote is submitted and has warehousing items.
		
		Returns:
			dict: Result with created Warehouse Contract name and status
		"""
		try:
			# Check if the quote is submitted
			if self.docstatus != 1:
				frappe.throw(_("This Sales Quote must be submitted before creating a Warehouse Contract."))
			
			# Check if Sales Quote has warehousing details
			if not self.warehousing:
				frappe.throw(_("No warehousing details found in this Sales Quote."))
			
			# Create new Warehouse Contract
			warehouse_contract = frappe.new_doc("Warehouse Contract")
			
			# Map basic fields from Sales Quote to Warehouse Contract
			warehouse_contract.customer = self.customer
			warehouse_contract.date = today()
			warehouse_contract.valid_until = self.valid_until
			warehouse_contract.site = self.site
			warehouse_contract.sales_quote = self.name
			warehouse_contract.company = self.company
			warehouse_contract.branch = self.branch
			warehouse_contract.profit_center = self.profit_center
			warehouse_contract.cost_center = self.cost_center
			
			# Insert the Warehouse Contract
			warehouse_contract.insert(ignore_permissions=True)
			
			# Import rates from Sales Quote using the existing function
			from logistics.warehousing.doctype.warehouse_contract.warehouse_contract import get_rates_from_sales_quote
			get_rates_from_sales_quote(warehouse_contract.name, self.name)
			
			# Prepare success message
			success_msg = f"Warehouse Contract {warehouse_contract.name} created successfully from Sales Quote {self.name}"
			
			frappe.msgprint(
				success_msg,
				title="Warehouse Contract Created",
				indicator="green"
			)
			
			return {
				"success": True,
				"message": f"Warehouse Contract {warehouse_contract.name} created successfully.",
				"warehouse_contract": warehouse_contract.name
			}
			
		except Exception as e:
			frappe.log_error(
				f"Error creating Warehouse Contract from Sales Quote {self.name}: {str(e)}",
				"Sales Quote to Warehouse Contract Creation Error"
			)
			frappe.throw(f"Error creating Warehouse Contract: {str(e)}")


@frappe.whitelist()
def create_transport_order_from_sales_quote(sales_quote_name):
	"""
	Standalone function to create Transport Order from Sales Quote.
	This function can be called from JavaScript.
	"""
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return sales_quote.create_transport_order_from_sales_quote()


@frappe.whitelist()
def create_warehouse_contract_from_sales_quote(sales_quote_name):
	"""
	Standalone function to create Warehouse Contract from Sales Quote.
	This function can be called from JavaScript.
	"""
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return sales_quote.create_warehouse_contract_from_sales_quote()


def _populate_charges_from_sales_quote(transport_order, sales_quote):
	"""
	Populate charges in Transport Order from Sales Quote Transport records.
	
	Args:
		transport_order: Transport Order document
		sales_quote: Sales Quote document
	"""
	try:
		# Clear existing charges
		transport_order.set("charges", [])
		
		# Get Sales Quote Transport records
		sales_quote_transport_records = frappe.get_all(
			"Sales Quote Transport",
			filters={"parent": sales_quote.name, "parenttype": "Sales Quote"},
			fields=[
				"item_code",
				"item_name", 
				"calculation_method",
				"uom",
				"currency",
				"unit_rate",
				"unit_type",
				"minimum_quantity",
				"minimum_charge",
				"maximum_charge",
				"base_amount"
			],
			order_by="idx"
		)
		
		# Map and populate charges
		charges_added = 0
		for sqt_record in sales_quote_transport_records:
			charge_row = _map_sales_quote_transport_to_charge(sqt_record, transport_order)
			if charge_row:
				transport_order.append("charges", charge_row)
				charges_added += 1
		
		if charges_added > 0:
			frappe.msgprint(
				f"Successfully populated {charges_added} charges from Sales Quote",
				title="Charges Updated",
				indicator="green"
			)
		
	except Exception as e:
		frappe.log_error(
			f"Error populating charges from sales quote: {str(e)}",
			"Sales Quote Charges Population Error"
		)
		raise


def _map_sales_quote_transport_to_charge(sqt_record, transport_order):
	"""
	Map sales_quote_transport record to transport_order_charges format.
	
	Args:
		sqt_record: Sales Quote Transport record
		transport_order: Transport Order document
		
	Returns:
		dict: Mapped charge data
	"""
	try:
		# Get the item details to fetch additional required fields
		item_doc = frappe.get_doc("Item", sqt_record.item_code)
		
		# Get default currency from system settings
		default_currency = frappe.get_system_settings("currency") or "USD"
		
		# Get default vehicle type if not set in transport order
		default_vehicle_type = transport_order.vehicle_type
		if not default_vehicle_type:
			# Try to get a default vehicle type from the system
			vehicle_types = frappe.get_all("Vehicle Type", limit=1)
			default_vehicle_type = vehicle_types[0].name if vehicle_types else ""
		
		# Map the fields from sales_quote_transport to transport_order_charges
		charge_data = {
			"item_code": sqt_record.item_code,
			"item_name": sqt_record.item_name or item_doc.item_name,
			"calculation_method": sqt_record.calculation_method or "Per Unit",
			"uom": sqt_record.uom or item_doc.stock_uom,
			"currency": sqt_record.currency or default_currency,
			"rate": sqt_record.unit_rate or 0,
			"unit_type": sqt_record.unit_type,
			"minimum_quantity": sqt_record.minimum_quantity,
			"minimum_charge": sqt_record.minimum_charge,
			"maximum_charge": sqt_record.maximum_charge,
			"base_amount": sqt_record.base_amount,
			# Set default values for required fields in transport_order_charges
			"load_type": transport_order.load_type or "FTL",
			"vehicle_type": default_vehicle_type,
			"quantity": 1  # Default quantity
		}
		
		return charge_data
		
	except Exception as e:
		frappe.log_error(
			f"Error mapping sales quote transport record: {str(e)}",
			"Sales Quote Transport Mapping Error"
		)
		return None
