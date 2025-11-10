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
	def create_air_shipment_from_sales_quote(self):
		"""
		Create an Air Shipment from a Sales Quote when the quote is tagged as One-Off.
		
		Returns:
			dict: Result with created Air Shipment name and status
		"""
		try:
			# Check if the quote is tagged as One-Off
			if not self.one_off:
				frappe.throw(_("This Sales Quote is not tagged as One-Off. Only One-Off quotes can create Air Shipments."))
			
			# Check if Sales Quote has air freight details
			if not self.air_freight:
				frappe.throw(_("No Air Freight lines found in this Sales Quote."))
			
			# Allow creation of multiple Air Shipments from the same Sales Quote
			# No duplicate prevention - users can create multiple shipments as needed
			
			# Create new Air Shipment
			air_shipment = frappe.new_doc("Air Shipment")
			
			# Map basic fields from Sales Quote to Air Shipment
			air_shipment.local_customer = self.customer
			air_shipment.booking_date = today()
			air_shipment.sales_quote = self.name
			air_shipment.shipper = getattr(self, 'shipper', None)
			air_shipment.consignee = getattr(self, 'consignee', None)
			air_shipment.origin_port = getattr(self, 'location_from', None)
			air_shipment.destination_port = getattr(self, 'location_to', None)
			air_shipment.direction = getattr(self, 'direction', None)
			air_shipment.weight = getattr(self, 'weight', None)
			air_shipment.volume = getattr(self, 'volume', None)
			air_shipment.chargeable = getattr(self, 'chargeable', None)
			air_shipment.service_level = getattr(self, 'service_level', None)
			air_shipment.incoterm = getattr(self, 'incoterm', None)
			air_shipment.additional_terms = getattr(self, 'additional_terms', None)
			air_shipment.company = self.company
			air_shipment.branch = self.branch
			air_shipment.cost_center = self.cost_center
			air_shipment.profit_center = self.profit_center
			
			# Insert the Air Shipment
			air_shipment.insert(ignore_permissions=True)
			
			# Populate charges from Sales Quote Air Freight
			_populate_charges_from_sales_quote_air_freight(air_shipment, self)
			
			# Save the Air Shipment
			air_shipment.save(ignore_permissions=True)
			
			# Prepare success message
			success_msg = f"Air Shipment {air_shipment.name} created successfully from Sales Quote {self.name}"
			
			frappe.msgprint(
				success_msg,
				title="Air Shipment Created",
				indicator="green"
			)
			
			return {
				"success": True,
				"message": f"Air Shipment {air_shipment.name} created successfully.",
				"air_shipment": air_shipment.name
			}
			
		except Exception as e:
			frappe.log_error(f"Error creating Air Shipment: {str(e)}", "Sales Quote - Create Air Shipment")
			frappe.throw(f"Error creating Air Shipment: {str(e)}")

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
def create_air_shipment_from_sales_quote(sales_quote_name):
	"""
	Standalone function to create Air Shipment from Sales Quote.
	This function can be called from JavaScript.
	"""
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return sales_quote.create_air_shipment_from_sales_quote()


@frappe.whitelist()
def create_warehouse_contract_from_sales_quote(sales_quote_name):
	"""
	Standalone function to create Warehouse Contract from Sales Quote.
	This function can be called from JavaScript.
	"""
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return sales_quote.create_warehouse_contract_from_sales_quote()


def _populate_charges_from_sales_quote_air_freight(air_shipment, sales_quote):
	"""
	Populate charges in Air Shipment from Sales Quote Air Freight records.
	
	Args:
		air_shipment: Air Shipment document
		sales_quote: Sales Quote document
	"""
	try:
		# Clear existing charges
		air_shipment.set("charges", [])
		
		# Get Sales Quote Air Freight records
		sales_quote_air_freight_records = frappe.get_all(
			"Sales Quote Air Freight",
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
				"base_amount",
				"estimated_revenue"
			],
			order_by="idx"
		)
		
		# Map and populate charges
		charges_added = 0
		for sqaf_record in sales_quote_air_freight_records:
			charge_row = _map_sales_quote_air_freight_to_charge(sqaf_record, air_shipment)
			if charge_row:
				air_shipment.append("charges", charge_row)
				charges_added += 1
		
		if charges_added > 0:
			frappe.msgprint(
				f"Successfully populated {charges_added} charges from Sales Quote",
				title="Charges Updated",
				indicator="green"
			)
		
	except Exception as e:
		frappe.log_error(
			f"Error populating charges from Sales Quote Air Freight: {str(e)}",
			"Sales Quote Air Freight - Charges Population Error"
		)
		raise


def _map_sales_quote_air_freight_to_charge(sqaf_record, air_shipment):
	"""
	Map sales_quote_air_freight record to air_shipment_charges format.
	
	Args:
		sqaf_record: Sales Quote Air Freight record
		air_shipment: Air Shipment document
		
	Returns:
		dict: Mapped charge data
	"""
	try:
		# Get the item details to fetch additional required fields
		item_doc = frappe.get_doc("Item", sqaf_record.item_code)
		
		# Get default currency from system settings
		default_currency = frappe.get_system_settings("currency") or "USD"
		
		# Map unit_type to charge_basis
		unit_type_to_charge_basis = {
			"Weight": "Per kg",
			"Volume": "Per m³",
			"Package": "Per package",
			"Piece": "Per package",
			"Shipment": "Per shipment"
		}
		charge_basis = unit_type_to_charge_basis.get(sqaf_record.unit_type, "Fixed amount")
		
		# Get quantity based on charge basis
		quantity = 0
		if charge_basis == "Per kg":
			quantity = flt(air_shipment.weight) or 0
		elif charge_basis == "Per m³":
			quantity = flt(air_shipment.volume) or 0
		elif charge_basis == "Per package":
			# Get package count from Air Shipment if available
			if hasattr(air_shipment, 'packages') and air_shipment.packages:
				quantity = len(air_shipment.packages)
			else:
				quantity = 1
		elif charge_basis == "Per shipment":
			quantity = 1
		
		# Determine charge_type and charge_category from item or use defaults
		charge_type = "Other"
		charge_category = "Other"
		
		# Try to get charge type from item custom fields or item name
		if hasattr(item_doc, 'custom_charge_type'):
			charge_type = item_doc.custom_charge_type or "Other"
		if hasattr(item_doc, 'custom_charge_category'):
			charge_category = item_doc.custom_charge_category or "Other"
		
		# Map the fields from sales_quote_air_freight to air_shipment_charges
		charge_data = {
			"item_code": sqaf_record.item_code,
			"item_name": sqaf_record.item_name or item_doc.item_name,
			"charge_type": charge_type,
			"charge_category": charge_category,
			"charge_basis": charge_basis,
			"rate": sqaf_record.unit_rate or 0,
			"currency": sqaf_record.currency or default_currency,
			"quantity": quantity,
			"unit_of_measure": sqaf_record.uom or (charge_basis.replace("Per ", "").replace("kg", "kg").replace("m³", "m³")),
			"calculation_method": sqaf_record.calculation_method or "Manual",
			"billing_status": "Pending"
		}
		
		# Add minimum/maximum charge if available
		if sqaf_record.minimum_charge:
			charge_data["minimum_charge"] = sqaf_record.minimum_charge
		if sqaf_record.maximum_charge:
			charge_data["maximum_charge"] = sqaf_record.maximum_charge
		
		return charge_data
		
	except Exception as e:
		frappe.log_error(
			f"Error mapping sales quote air freight record: {str(e)}",
			"Sales Quote Air Freight Mapping Error"
		)
		return None


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
