# Copyright (c) 2025, logistics.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, flt


class SeaBooking(Document):
	def validate(self):
		"""Validate Sea Booking data"""
		self.validate_required_fields()
		self.validate_dates()
		self.validate_accounts()
	
	def validate_required_fields(self):
		"""Validate required fields"""
		if not self.booking_date:
			frappe.throw(_("Booking Date is required"))
		
		if not self.local_customer:
			frappe.throw(_("Local Customer is required"))
		
		if not self.direction:
			frappe.throw(_("Direction is required"))
		
		if not self.shipper:
			frappe.throw(_("Shipper is required"))
		
		if not self.consignee:
			frappe.throw(_("Consignee is required"))
		
		if not self.origin_port:
			frappe.throw(_("Origin Port is required"))
		
		if not self.destination_port:
			frappe.throw(_("Destination Port is required"))
	
	def validate_dates(self):
		"""Validate date logic"""
		from frappe.utils import getdate
		
		# Validate ETD is before ETA
		if self.etd and self.eta:
			if getdate(self.etd) >= getdate(self.eta):
				frappe.throw(_("ETD (Estimated Time of Departure) must be before ETA (Estimated Time of Arrival)"))
	
	def validate_accounts(self):
		"""Validate that cost center, profit center, and branch belong to the company"""
		if not self.company:
			return
		
		if self.cost_center:
			cost_center_company = frappe.db.get_value("Cost Center", self.cost_center, "company")
			if cost_center_company and cost_center_company != self.company:
				frappe.throw(_("Cost Center {0} does not belong to Company {1}").format(
					self.cost_center, self.company
				))
		
		if self.profit_center:
			profit_center_company = frappe.db.get_value("Profit Center", self.profit_center, "company")
			if profit_center_company and profit_center_company != self.company:
				frappe.throw(_("Profit Center {0} does not belong to Company {1}").format(
					self.profit_center, self.company
				))
		
		if self.branch:
			branch_company = frappe.db.get_value("Branch", self.branch, "company")
			if branch_company and branch_company != self.company:
				frappe.throw(_("Branch {0} does not belong to Company {1}").format(
					self.branch, self.company
				))
	
	@frappe.whitelist()
	def fetch_quotations(self):
		"""
		Fetch quotations from Sales Quote and populate Sea Booking fields.
		
		Returns:
			dict: Result with status and message
		"""
		try:
			if not self.sales_quote:
				frappe.throw(_("Please select a Sales Quote first"))
			
			# Get Sales Quote document
			sales_quote = frappe.get_doc("Sales Quote", self.sales_quote)
			
			# Check if Sales Quote has sea freight details
			# Note: Sales Quote Sea Freight child table may not exist yet
			# If it doesn't exist, we'll still populate basic fields
			sea_freight_exists = frappe.db.exists("Sales Quote Sea Freight", {
				"parent": self.sales_quote,
				"parenttype": "Sales Quote"
			})
			
			if not sea_freight_exists:
				frappe.msgprint(
					_("No Sea Freight lines found in Sales Quote {0}. Only basic fields will be populated.").format(self.sales_quote),
					indicator="orange"
				)
			
			# Map basic fields from Sales Quote to Sea Booking
			if not self.local_customer:
				self.local_customer = sales_quote.customer
			if not self.shipper:
				self.shipper = getattr(sales_quote, 'shipper', None)
			if not self.consignee:
				self.consignee = getattr(sales_quote, 'consignee', None)
			if not self.origin_port:
				self.origin_port = getattr(sales_quote, 'location_from', None)
			if not self.destination_port:
				self.destination_port = getattr(sales_quote, 'location_to', None)
			if not self.direction:
				self.direction = getattr(sales_quote, 'direction', None)
			if not self.weight:
				self.weight = getattr(sales_quote, 'weight', None)
			if not self.volume:
				self.volume = getattr(sales_quote, 'volume', None)
			if not self.chargeable:
				self.chargeable = getattr(sales_quote, 'chargeable', None)
			if not self.service_level:
				self.service_level = getattr(sales_quote, 'service_level', None)
			if not self.incoterm:
				self.incoterm = getattr(sales_quote, 'incoterm', None)
			if not self.additional_terms:
				self.additional_terms = getattr(sales_quote, 'additional_terms', None)
			if not self.company:
				self.company = sales_quote.company
			if not self.branch:
				self.branch = sales_quote.branch
			if not self.cost_center:
				self.cost_center = sales_quote.cost_center
			if not self.profit_center:
				self.profit_center = sales_quote.profit_center
			
			# Populate charges from Sales Quote Sea Freight (if child table exists)
			sea_freight_exists = frappe.db.exists("Sales Quote Sea Freight", {
				"parent": self.sales_quote,
				"parenttype": "Sales Quote"
			})
			if sea_freight_exists:
				self._populate_charges_from_sales_quote(sales_quote)
			
			frappe.msgprint(
				_("Quotations fetched successfully from Sales Quote {0}").format(self.sales_quote),
				title=_("Success"),
				indicator="green"
			)
			
			return {
				"success": True,
				"message": _("Quotations fetched successfully")
			}
			
		except Exception as e:
			frappe.log_error(
				f"Error fetching quotations for Sea Booking {self.name}: {str(e)}",
				"Sea Booking - Fetch Quotations Error"
			)
			frappe.throw(_("Error fetching quotations: {0}").format(str(e)))
	
	def _populate_charges_from_sales_quote(self, sales_quote):
		"""Populate charges from Sales Quote Sea Freight records"""
		try:
			# Clear existing charges
			self.set("charges", [])
			
			# Get Sales Quote Sea Freight records
			# Note: Adjust the child table name if it's different
			sales_quote_sea_freight_records = frappe.get_all(
				"Sales Quote Sea Freight",
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
			
			# If Sales Quote Sea Freight doesn't exist, return early
			if not sales_quote_sea_freight_records:
				frappe.msgprint(
					_("No Sea Freight charges found in Sales Quote. Charges will not be populated."),
					indicator="orange"
				)
				return
			
			# Map and populate charges
			charges_added = 0
			for sqsf_record in sales_quote_sea_freight_records:
				charge_row = self._map_sales_quote_sea_freight_to_charge(sqsf_record)
				if charge_row:
					self.append("charges", charge_row)
					charges_added += 1
			
			if charges_added > 0:
				frappe.msgprint(
					_("Successfully populated {0} charges from Sales Quote").format(charges_added),
					title=_("Charges Updated"),
					indicator="green"
				)
			
		except Exception as e:
			frappe.log_error(
				f"Error populating charges from Sales Quote: {str(e)}",
				"Sea Booking - Charges Population Error"
			)
			# Don't raise - allow booking to be saved even if charges fail
			frappe.msgprint(
				_("Warning: Could not populate all charges from Sales Quote: {0}").format(str(e)),
				indicator="orange"
			)
	
	def _map_sales_quote_sea_freight_to_charge(self, sqsf_record):
		"""Map sales_quote_sea_freight record to sea_shipment_charges format"""
		try:
			# Get the item details
			item_doc = frappe.get_doc("Item", sqsf_record.item_code)
			
			# Get default currency
			default_currency = frappe.get_system_settings("currency") or "USD"
			
			# Map unit_type to charge_basis
			unit_type_to_charge_basis = {
				"Weight": "Per kg",
				"Volume": "Per m³",
				"Package": "Per package",
				"Piece": "Per package",
				"Shipment": "Per shipment",
				"Container": "Per container"
			}
			charge_basis = unit_type_to_charge_basis.get(sqsf_record.unit_type, "Fixed amount")
			
			# Get quantity based on charge basis
			quantity = 0
			if charge_basis == "Per kg":
				quantity = flt(self.weight) or 0
			elif charge_basis == "Per m³":
				quantity = flt(self.volume) or 0
			elif charge_basis == "Per package":
				if hasattr(self, 'packages') and self.packages:
					quantity = len(self.packages)
				else:
					quantity = 1
			elif charge_basis == "Per container":
				if hasattr(self, 'containers') and self.containers:
					quantity = len(self.containers)
				else:
					quantity = 1
			elif charge_basis == "Per shipment":
				quantity = 1
			
			# Determine charge_type and charge_category from item or use defaults
			charge_type = "Other"
			charge_category = "Other"
			
			if hasattr(item_doc, 'custom_charge_type'):
				charge_type = item_doc.custom_charge_type or "Other"
			if hasattr(item_doc, 'custom_charge_category'):
				charge_category = item_doc.custom_charge_category or "Other"
			
			# Map the fields - adjust based on actual Sea Shipment Charges structure
			charge_data = {
				"item_code": sqsf_record.item_code,
				"item_name": sqsf_record.item_name or item_doc.item_name,
				"charge_type": charge_type,
				"charge_category": charge_category,
				"charge_basis": charge_basis,
				"rate": sqsf_record.unit_rate or 0,
				"currency": sqsf_record.currency or default_currency,
				"quantity": quantity,
				"unit_of_measure": sqsf_record.uom or (charge_basis.replace("Per ", "").replace("kg", "kg").replace("m³", "m³")),
				"calculation_method": sqsf_record.calculation_method or "Manual",
				"billing_status": "Pending"
			}
			
			# Add minimum/maximum charge if available
			if sqsf_record.minimum_charge:
				charge_data["minimum_charge"] = sqsf_record.minimum_charge
			if sqsf_record.maximum_charge:
				charge_data["maximum_charge"] = sqsf_record.maximum_charge
			
			return charge_data
			
		except Exception as e:
			frappe.log_error(
				f"Error mapping sales quote sea freight record: {str(e)}",
				"Sea Booking Mapping Error"
			)
			return None
	
	@frappe.whitelist()
	def convert_to_shipment(self):
		"""
		Convert Sea Booking to Sea Shipment.
		
		Returns:
			dict: Result with created Sea Shipment name and status
		"""
		try:
			# Create new Sea Shipment
			sea_shipment = frappe.new_doc("Sea Shipment")
			
			# Map basic fields from Sea Booking to Sea Shipment
			sea_shipment.local_customer = self.local_customer
			sea_shipment.booking_date = self.booking_date or today()
			sea_shipment.sea_booking = self.name
			sea_shipment.sales_quote = self.sales_quote
			sea_shipment.shipper = self.shipper
			sea_shipment.consignee = self.consignee
			sea_shipment.origin_port = self.origin_port
			sea_shipment.destination_port = self.destination_port
			sea_shipment.direction = self.direction
			sea_shipment.weight = self.weight
			sea_shipment.volume = self.volume
			sea_shipment.chargeable = self.chargeable
			sea_shipment.service_level = self.service_level
			sea_shipment.incoterm = self.incoterm
			sea_shipment.additional_terms = self.additional_terms
			sea_shipment.shipping_line = self.shipping_line
			sea_shipment.freight_agent = self.freight_agent
			sea_shipment.house_type = self.house_type
			sea_shipment.release_type = self.release_type
			sea_shipment.entry_type = self.entry_type
			sea_shipment.house_bl = self.house_bl
			sea_shipment.packs = self.packs
			sea_shipment.inner = self.inner
			sea_shipment.good_value = self.good_value
			sea_shipment.insurance = self.insurance
			sea_shipment.description = self.description
			sea_shipment.marks_and_nos = self.marks_and_nos
			sea_shipment.etd = self.etd
			sea_shipment.eta = self.eta
			sea_shipment.transport_mode = self.transport_mode
			sea_shipment.company = self.company
			sea_shipment.branch = self.branch
			sea_shipment.cost_center = self.cost_center
			sea_shipment.profit_center = self.profit_center
			
			# Copy containers if they exist (from Sea Booking Containers to Sea Freight Containers)
			if hasattr(self, 'containers') and self.containers:
				for container in self.containers:
					sea_shipment.append("containers", {
						"container_no": container.container_no,
						"seal_no": container.seal_no,
						"type": container.type,
						"mode": container.mode,
						"delivery_modes": container.delivery_modes,
						"sealed_by": container.sealed_by,
						"other_references": container.other_references
					})
			
			# Copy packages if they exist (from Sea Booking Packages to Sea Freight Packages)
			if hasattr(self, 'packages') and self.packages:
				for package in self.packages:
					sea_shipment.append("packages", {
						"commodity": package.commodity,
						"hs_code": package.hs_code,
						"reference_no": package.reference_no,
						"container": package.container,
						"goods_description": package.goods_description,
						"no_of_packs": package.no_of_packs,
						"uom": package.uom,
						"weight": package.weight,
						"volume": package.volume
					})
			
			# Copy charges (from Sea Booking Charges to Sea Freight Charges)
			if hasattr(self, 'charges') and self.charges:
				for charge in self.charges:
					sea_shipment.append("charges", {
						"charge_item": charge.charge_item,
						"charge_name": charge.charge_name,
						"charge_type": charge.charge_type,
						"item_tax_template": charge.item_tax_template,
						"invoice_type": charge.invoice_type,
						"charge_description": charge.charge_description,
						"bill_to": charge.bill_to,
						"selling_currency": charge.selling_currency,
						"selling_amount": charge.selling_amount,
						"pay_to": charge.pay_to,
						"buying_currency": charge.buying_currency,
						"buying_amount": charge.buying_amount,
						"revenue_calc_type": charge.revenue_calc_type,
						"base_amount": charge.base_amount,
						"per_unit_rate": charge.per_unit_rate,
						"unit": charge.unit,
						"minimum": charge.minimum,
						"cost_calc_type": charge.cost_calc_type
					})
			
			# Insert the Sea Shipment
			sea_shipment.insert(ignore_permissions=True)
			
			# Save the Sea Shipment
			sea_shipment.save(ignore_permissions=True)
			
			frappe.msgprint(
				_("Sea Shipment {0} created successfully from Sea Booking {1}").format(sea_shipment.name, self.name),
				title=_("Sea Shipment Created"),
				indicator="green"
			)
			
			return {
				"success": True,
				"message": _("Sea Shipment {0} created successfully").format(sea_shipment.name),
				"sea_shipment": sea_shipment.name
			}
			
		except Exception as e:
			frappe.log_error(
				f"Error converting Sea Booking {self.name} to Sea Shipment: {str(e)}",
				"Sea Booking - Convert to Shipment Error"
			)
			frappe.throw(_("Error converting to shipment: {0}").format(str(e)))

