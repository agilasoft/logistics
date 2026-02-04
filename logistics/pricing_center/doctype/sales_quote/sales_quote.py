# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt
from frappe.utils import today, getdate, flt


class SalesQuote(Document):
	def validate(self):
		"""Validate Sales Quote including capacity"""
		self.validate_vehicle_type_capacity()
	
	def validate_vehicle_type_capacity(self):
		"""Validate vehicle type capacity when vehicle_type is assigned. Uses Transport tab dimensions."""
		if not getattr(self, 'vehicle_type', None) or not getattr(self, 'is_transport', None):
			return
		
		try:
			from logistics.transport.capacity.vehicle_type_capacity import get_vehicle_type_capacity_info
			from logistics.transport.capacity.uom_conversion import convert_weight, convert_volume, get_default_uoms
			from logistics.utils.default_uom import get_default_uoms_for_domain

			# Use Transport tab dimensions (fallback to old top-level for backward compat)
			required_weight = flt(getattr(self, 'transport_weight', None) or getattr(self, 'weight', 0))
			required_weight_uom = getattr(self, 'transport_weight_uom', None) or getattr(self, 'weight_uom', None)
			required_volume = flt(getattr(self, 'transport_volume', None) or getattr(self, 'volume', 0))
			required_volume_uom = getattr(self, 'transport_volume_uom', None) or getattr(self, 'volume_uom', None)
			if not required_weight_uom or not required_volume_uom:
				defaults = get_default_uoms_for_domain("transport")
				required_weight_uom = required_weight_uom or defaults.get("weight_uom")
				required_volume_uom = required_volume_uom or defaults.get("volume_uom")
			default_uoms = get_default_uoms(self.company)
			required_weight_uom = required_weight_uom or default_uoms.get('weight')
			required_volume_uom = required_volume_uom or default_uoms.get('volume')

			if required_weight == 0 and required_volume == 0:
				return  # No requirements to validate

			# Convert to standard UOMs for comparison
			required_weight_std = convert_weight(required_weight, required_weight_uom, default_uoms['weight'], self.company)
			required_volume_std = convert_volume(required_volume, required_volume_uom, default_uoms['volume'], self.company)

			# Get vehicle type capacity (average or minimum from vehicles of this type)
			capacity_info = get_vehicle_type_capacity_info(self.vehicle_type, self.company)

			# Check if capacity is sufficient (compare in standard UOMs)
			if required_weight_std > 0 and capacity_info.get('max_weight', 0) < required_weight_std:
				frappe.msgprint(_("Warning: Required weight ({0} {1}) may exceed typical capacity for vehicle type {2}").format(
					required_weight, required_weight_uom, self.vehicle_type
				), indicator='orange')

			if required_volume_std > 0 and capacity_info.get('max_volume', 0) < required_volume_std:
				frappe.msgprint(_("Warning: Required volume ({0} {1}) may exceed typical capacity for vehicle type {2}").format(
					required_volume, required_volume_uom, self.vehicle_type
				), indicator='orange')
		except ImportError:
			# Capacity management not fully implemented yet
			pass
		except Exception as e:
			frappe.log_error(f"Error validating vehicle type capacity in Sales Quote: {str(e)}", "Capacity Validation Error")
	def validate(self):
		"""Validate Sales Quote data"""
		self.validate_vehicle_type_load_type()
		self.validate_vehicle_type_capacity()
	
	def validate_vehicle_type_load_type(self):
		"""Validate that the selected vehicle_type is allowed for the selected load_type"""
		if not self.vehicle_type or not self.load_type:
			return
		
		# Check if the vehicle_type has the selected load_type in its allowed_load_types
		allowed_load_types = frappe.db.get_all(
			"Vehicle Type Load Types",
			filters={"parent": self.vehicle_type},
			fields=["load_type"]
		)
		
		allowed_load_type_names = [alt.load_type for alt in allowed_load_types]
		
		if self.load_type not in allowed_load_type_names:
			frappe.throw(
				_("Vehicle Type '{0}' is not allowed for Load Type '{1}'. Please select a Vehicle Type that allows this Load Type.").format(
					self.vehicle_type, self.load_type
				),
				title=_("Invalid Vehicle Type")
			)
	
	def _determine_transport_job_type(self, current_job_type, load_type, container_type):
		"""
		Determine the appropriate transport_job_type based on load_type compatibility.
		
		Args:
			current_job_type: The currently set transport_job_type (may be None)
			load_type: The load_type name
			container_type: The container_type (may be None)
		
		Returns:
			str: The appropriate transport_job_type
		"""
		if not load_type:
			# If no load_type, default to Non-Container
			return current_job_type or "Non-Container"
		
		# Get load type's allowed job type flags
		load_type_doc = frappe.db.get_value(
			"Load Type",
			load_type,
			["container", "non_container", "special", "oversized", "multimodal", "heavy_haul"],
			as_dict=True
		)
		
		if not load_type_doc:
			# If load_type doesn't exist, default to Non-Container
			return current_job_type or "Non-Container"
		
		# Map transport_job_type to boolean field name
		field_map = {
			"Container": "container",
			"Non-Container": "non_container",
			"Special": "special",
			"Oversized": "oversized",
			"Multimodal": "multimodal",
			"Heavy Haul": "heavy_haul"
		}
		
		# Helper function to find the best default job type based on load_type flags
		def find_best_job_type():
			"""Find the best default job type based on load_type's allowed flags."""
			# Priority: Container > Non-Container > Special > Oversized > Multimodal > Heavy Haul
			if load_type_doc.get("container"):
				# If Container is allowed and container_type is provided, prefer Container
				if container_type:
					return "Container"
				# If Container is allowed but container_type is missing, check if Non-Container is also allowed
				if load_type_doc.get("non_container"):
					return "Non-Container"
				# If only Container is allowed but container_type is missing, throw error
				frappe.throw(
					_("Load Type '{0}' requires Container job type, but Container Type is missing. Please set Container Type in Sales Quote.").format(
						load_type
					),
					title=_("Missing Container Type")
				)
			elif load_type_doc.get("non_container"):
				return "Non-Container"
			elif load_type_doc.get("special"):
				return "Special"
			elif load_type_doc.get("oversized"):
				return "Oversized"
			elif load_type_doc.get("multimodal"):
				return "Multimodal"
			elif load_type_doc.get("heavy_haul"):
				return "Heavy Haul"
			else:
				# No job types are allowed for this load_type, default to Non-Container
				# (validation will catch this later)
				return "Non-Container"
		
		# If transport_job_type is already set, validate it's compatible with load_type
		if current_job_type:
			allowed_field = field_map.get(current_job_type)
			if allowed_field and load_type_doc.get(allowed_field):
				# Current job type is allowed, but check if Container requires container_type
				if current_job_type == "Container" and not container_type:
					# Container job type requires container_type, check if Non-Container is also allowed
					if load_type_doc.get("non_container"):
						return "Non-Container"
					# If only Container is allowed but container_type is missing, throw error
					frappe.throw(
						_("Container job type requires Container Type, but it is missing. Please set Container Type in Sales Quote."),
						title=_("Missing Container Type")
					)
				return current_job_type
			else:
				# Current job type is not allowed for this load_type, find an alternative
				return find_best_job_type()
		
		# No job type set, determine default based on load_type's allowed job types
		return find_best_job_type()
	
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
			
			# Note: Allow multiple Transport Orders from the same Sales Quote (as per UI requirements)
			# Removed check that prevented multiple orders from same Sales Quote
			
			# Create new Transport Order
			transport_order = frappe.new_doc("Transport Order")
			
			# Map basic fields from Sales Quote to Transport Order
			transport_order.customer = self.customer
			transport_order.booking_date = today()  # Use current system date
			transport_order.sales_quote = self.name  # Set Sales Quote number (e.g., SQU000000158)
			transport_order.transport_template = getattr(self, 'transport_template', None)
			transport_order.load_type = self.load_type
			transport_order.vehicle_type = self.vehicle_type
			transport_order.transport_job_type = getattr(self, 'transport_job_type', None)
			transport_order.company = self.company
			transport_order.branch = self.branch
			transport_order.cost_center = self.cost_center
			transport_order.profit_center = self.profit_center
			
			# Set scheduled_date (required field) - use current system date
			transport_order.scheduled_date = today()
			
			# Copy container_type from Sales Quote if it exists
			container_type = getattr(self, 'container_type', None)
			if container_type:
				transport_order.container_type = container_type
			
			# Determine appropriate transport_job_type based on load_type compatibility
			transport_order.transport_job_type = self._determine_transport_job_type(
				transport_order.transport_job_type,
				transport_order.load_type,
				container_type
			)
			
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
			
			# Set flags to skip validations when creating from Sales Quote
			transport_order.flags.skip_container_no_validation = True
			transport_order.flags.skip_vehicle_type_validation = True
			transport_order.flags.skip_special_requirements_validation = True
			# Flag to prevent on_change from interfering when creating from Sales Quote
			transport_order.flags.skip_sales_quote_on_change = True
			
			# Insert the Transport Order first
			transport_order.insert(ignore_permissions=True)
			
			# Reload the document to ensure we're working with the saved state
			transport_order.reload()
			
			# Re-set flag after reload to prevent on_change from interfering
			transport_order.flags.skip_sales_quote_on_change = True
			
			# Ensure sales_quote field is preserved after reload
			transport_order.sales_quote = self.name
			
			# Populate charges from Sales Quote Transport AFTER insert to ensure they're saved
			_populate_charges_from_sales_quote(transport_order, self)
			
			# Save the Transport Order again to persist the charges and sales_quote
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
					
					# Ensure sales_quote field is preserved after leg plan creation
					transport_order.reload()
					transport_order.sales_quote = self.name
					transport_order.flags.skip_sales_quote_on_change = True
					transport_order.save(ignore_permissions=True)
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
			error_msg = str(e)
			# Truncate error message for logging if too long (error log title has 140 char limit)
			# Keep log message short - just the essential info
			log_msg = f"SQ {self.name}: {error_msg[:100]}" if len(error_msg) > 100 else f"SQ {self.name}: {error_msg}"
			frappe.log_error(
				log_msg,
				"Sales Quote to Transport Order Creation Error"
			)
			frappe.throw(f"Error creating Transport Order: {error_msg}")

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
			
			# Check if Sales Quote has air freight details using database query to avoid SQL errors
			air_freight_count = frappe.db.count("Sales Quote Air Freight", {
				"parent": self.name,
				"parenttype": "Sales Quote"
			})
			if air_freight_count == 0:
				frappe.throw(_("No Air Freight lines found in this Sales Quote."))
			
			# Get port fields from Air tab (preferred) or fall back to Transport tab
			origin_airport = getattr(self, 'origin_port', None)
			destination_airport = getattr(self, 'destination_port', None)
			
			# Fall back to Transport tab location fields if Air tab fields are not set
			if not origin_airport:
				origin_airport = getattr(self, 'location_from', None)
			if not destination_airport:
				destination_airport = getattr(self, 'location_to', None)
			
			# Clean up airport fields: strip whitespace and convert empty strings to None
			if origin_airport:
				origin_airport = str(origin_airport).strip() or None
			if destination_airport:
				destination_airport = str(destination_airport).strip() or None
			
			# Check if origin and destination ports are set (required for Air Shipment)
			missing_fields = []
			if not origin_airport:
				missing_fields.append("Origin Port")
			if not destination_airport:
				missing_fields.append("Destination Port")
			
			if missing_fields:
				error_msg = _("Cannot create Air Shipment: {0} {1} required in Sales Quote.").format(
					", ".join(missing_fields),
					"is" if len(missing_fields) == 1 else "are"
				)
				instructions = _(
					"To fix this:\n"
					"1. Go to the 'Air' tab in this Sales Quote\n"
					"2. In the 'Routing & Dates' section, fill in:\n"
					"   - 'Origin Port' - select a valid Location for the origin port\n"
					"   - 'Destination Port' - select a valid Location for the destination port\n"
					"3. Save the Sales Quote\n"
					"4. Then try creating the Air Shipment again\n\n"
					"Note: You can also use 'Location From' and 'Location To' in the Transport tab as an alternative."
				)
				frappe.throw(
					f"{error_msg}\n\n{instructions}",
					title=_("Required Fields Missing")
				)
			
			# Verify that origin_airport and destination_airport are valid Location/UNLOCO records
			# Air Shipment requires UNLOCO records
			if not frappe.db.exists("UNLOCO", origin_airport):
				if not frappe.db.exists("Location", origin_airport):
					frappe.throw(_("Origin Airport '{0}' is not a valid UNLOCO or Location. Please select a valid Location record in the Air tab.").format(origin_airport))
			
			if not frappe.db.exists("UNLOCO", destination_airport):
				if not frappe.db.exists("Location", destination_airport):
					frappe.throw(_("Destination Airport '{0}' is not a valid UNLOCO or Location. Please select a valid Location record in the Air tab.").format(destination_airport))
			
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
			air_shipment.origin_port = origin_airport
			air_shipment.destination_port = destination_airport
			air_shipment.direction = getattr(self, 'direction', None)
			# Use Air tab dimensions (fallback to old top-level for backward compat)
			weight = getattr(self, 'air_weight', None) or getattr(self, 'weight', None)
			air_shipment.weight = weight if weight and flt(weight) > 0 else None
			volume = getattr(self, 'air_volume', None) or getattr(self, 'volume', None)
			air_shipment.volume = volume if volume and flt(volume) > 0 else None
			chargeable = getattr(self, 'air_chargeable', None) or getattr(self, 'chargeable', None)
			air_shipment.chargeable = chargeable if chargeable and flt(chargeable) > 0 else None
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
	def create_sea_shipment_from_sales_quote(self):
		"""
		Create a Sea Shipment from a Sales Quote when the quote is tagged as One-Off.
		
		Returns:
			dict: Result with created Sea Shipment name and status
		"""
		try:
			# Check if the quote is tagged as One-Off
			if not self.one_off:
				frappe.throw(_("This Sales Quote is not tagged as One-Off. Only One-Off quotes can create Sea Shipments."))
			
			# Check if Sales Quote has sea freight details
			if not self.sea_freight:
				frappe.throw(_("No Sea Freight lines found in this Sales Quote."))
			
			# Get location fields from Sales Quote
			location_type = getattr(self, 'location_type', None)
			location_from = getattr(self, 'location_from', None)
			location_to = getattr(self, 'location_to', None)
			
			# Check if origin and destination ports are set (required for Sea Shipment)
			missing_fields = []
			if not location_from:
				missing_fields.append("Origin Port (Location From)")
			if not location_to:
				missing_fields.append("Destination Port (Location To)")
			
			if missing_fields:
				frappe.throw(
					_("Cannot create Sea Shipment: {0} {1} required in Sales Quote. Please set the Location Type to 'UNLOCO' and fill in Location From and Location To fields in the Sales Quote before creating a Sea Shipment.").format(
						", ".join(missing_fields),
						"is" if len(missing_fields) == 1 else "are"
					),
					title=_("Required Fields Missing")
				)
			
			# Verify that location_from and location_to are valid UNLOCO records
			if not frappe.db.exists("UNLOCO", location_from):
				frappe.throw(_("Origin Port '{0}' is not a valid UNLOCO code. Please ensure Location From in Sales Quote references a valid UNLOCO record.").format(location_from))
			
			if not frappe.db.exists("UNLOCO", location_to):
				frappe.throw(_("Destination Port '{0}' is not a valid UNLOCO code. Please ensure Location To in Sales Quote references a valid UNLOCO record.").format(location_to))
			
			# Allow creation of multiple Sea Shipments from the same Sales Quote
			# No duplicate prevention - users can create multiple shipments as needed
			
			# Create new Sea Shipment
			sea_shipment = frappe.new_doc("Sea Shipment")
			
			# Map basic fields from Sales Quote to Sea Shipment
			sea_shipment.local_customer = self.customer
			sea_shipment.booking_date = today()
			sea_shipment.sales_quote = self.name
			sea_shipment.shipper = getattr(self, 'shipper', None)
			sea_shipment.consignee = getattr(self, 'consignee', None)
			sea_shipment.origin_port = location_from
			sea_shipment.destination_port = location_to
			sea_shipment.direction = getattr(self, 'direction', None)
			# Use Sea tab dimensions (fallback to old top-level for backward compat)
			weight = getattr(self, 'sea_weight', None) or getattr(self, 'weight', None)
			sea_shipment.weight = weight if weight and flt(weight) > 0 else None
			volume = getattr(self, 'sea_volume', None) or getattr(self, 'volume', None)
			sea_shipment.volume = volume if volume and flt(volume) > 0 else None
			chargeable = getattr(self, 'sea_chargeable', None) or getattr(self, 'chargeable', None)
			sea_shipment.chargeable = chargeable if chargeable and flt(chargeable) > 0 else None
			sea_shipment.service_level = getattr(self, 'service_level', None)
			sea_shipment.incoterm = getattr(self, 'incoterm', None)
			sea_shipment.additional_terms = getattr(self, 'additional_terms', None)
			sea_shipment.company = self.company
			sea_shipment.branch = self.branch
			sea_shipment.cost_center = self.cost_center
			sea_shipment.profit_center = self.profit_center
			
			# Insert the Sea Shipment
			sea_shipment.insert(ignore_permissions=True)
			
			# Populate charges from Sales Quote Sea Freight
			_populate_charges_from_sales_quote_sea_freight(sea_shipment, self)
			
			# Save the Sea Shipment
			sea_shipment.save(ignore_permissions=True)
			
			# Prepare success message
			success_msg = f"Sea Shipment {sea_shipment.name} created successfully from Sales Quote {self.name}"
			
			frappe.msgprint(
				success_msg,
				title="Sea Shipment Created",
				indicator="green"
			)
			
			return {
				"success": True,
				"message": f"Sea Shipment {sea_shipment.name} created successfully.",
				"sea_shipment": sea_shipment.name
			}
			
		except Exception as e:
			frappe.log_error(f"Error creating Sea Shipment: {str(e)}", "Sales Quote - Create Sea Shipment")
			frappe.throw(f"Error creating Sea Shipment: {str(e)}")

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
	def create_air_booking_from_sales_quote(self):
		"""
		Create an Air Booking from a Sales Quote when the quote is tagged as One-Off.
		
		Returns:
			dict: Result with created Air Booking name and status
		"""
		try:
			# Check if the quote is tagged as One-Off
			if not self.one_off:
				frappe.throw(_("This Sales Quote is not tagged as One-Off. Only One-Off quotes can create Air Bookings."))
			
			# Check if Sales Quote has air freight details using database query to avoid SQL errors
			air_freight_count = frappe.db.count("Sales Quote Air Freight", {
				"parent": self.name,
				"parenttype": "Sales Quote"
			})
			if air_freight_count == 0:
				frappe.throw(_("No Air Freight lines found in this Sales Quote."))
			
			# Get port fields from Air tab (preferred) or fall back to Transport tab
			origin_airport = getattr(self, 'origin_port', None)
			destination_airport = getattr(self, 'destination_port', None)
			
			# Fall back to Transport tab location fields if Air tab fields are not set
			if not origin_airport:
				origin_airport = getattr(self, 'location_from', None)
			if not destination_airport:
				destination_airport = getattr(self, 'location_to', None)
			
			# Clean up airport fields: strip whitespace and convert empty strings to None
			if origin_airport:
				origin_airport = str(origin_airport).strip() or None
			if destination_airport:
				destination_airport = str(destination_airport).strip() or None
			
			# Check if origin and destination ports are set (required for Air Booking)
			missing_fields = []
			if not origin_airport:
				missing_fields.append("Origin Port")
			if not destination_airport:
				missing_fields.append("Destination Port")
			
			if missing_fields:
				error_msg = _("Cannot create Air Booking: {0} {1} required in Sales Quote.").format(
					", ".join(missing_fields),
					"is" if len(missing_fields) == 1 else "are"
				)
				instructions = _(
					"To fix this:\n"
					"1. Go to the 'Air' tab in this Sales Quote\n"
					"2. In the 'Routing & Dates' section, fill in:\n"
					"   - 'Origin Port' - select a valid Location for the origin port\n"
					"   - 'Destination Port' - select a valid Location for the destination port\n"
					"3. Save the Sales Quote\n"
					"4. Then try creating the Air Booking again\n\n"
					"Note: You can also use 'Location From' and 'Location To' in the Transport tab as an alternative."
				)
				frappe.throw(
					f"{error_msg}\n\n{instructions}",
					title=_("Required Fields Missing")
				)
			
			# Verify that origin_airport and destination_airport are valid Location records
			# Air Booking accepts Location records
			if not frappe.db.exists("Location", origin_airport):
				# Also check if it's a UNLOCO record (in case Location doctype doesn't include it)
				if not frappe.db.exists("UNLOCO", origin_airport):
					frappe.throw(_("Origin Port '{0}' is not a valid Location. Please select a valid Location record in the Air tab.").format(origin_airport))
			
			if not frappe.db.exists("Location", destination_airport):
				# Also check if it's a UNLOCO record (in case Location doctype doesn't include it)
				if not frappe.db.exists("UNLOCO", destination_airport):
					frappe.throw(_("Destination Port '{0}' is not a valid Location. Please select a valid Location record in the Air tab.").format(destination_airport))
			
			# Allow creation of multiple Air Bookings from the same Sales Quote
			# No duplicate prevention - users can create multiple bookings as needed
			
			# Create new Air Booking
			air_booking = frappe.new_doc("Air Booking")
			
			# Map basic fields from Sales Quote to Air Booking
			air_booking.local_customer = self.customer
			air_booking.booking_date = today()
			air_booking.sales_quote = self.name
			air_booking.shipper = getattr(self, 'shipper', None)
			air_booking.consignee = getattr(self, 'consignee', None)
			# Set origin and destination airports (already validated above)
			air_booking.origin_port = origin_airport
			air_booking.destination_port = destination_airport
			
			# Double-check that fields are set before insert
			if not air_booking.origin_port:
				frappe.throw(_("Origin Port is required. Please set Origin Port in the Air tab of Sales Quote."))
			if not air_booking.destination_port:
				frappe.throw(_("Destination Port is required. Please set Destination Port in the Air tab of Sales Quote."))
			air_booking.direction = getattr(self, 'air_direction', None) or getattr(self, 'direction', None)
			air_booking.weight = getattr(self, 'air_weight', None) or getattr(self, 'weight', None)
			air_booking.volume = getattr(self, 'air_volume', None) or getattr(self, 'volume', None)
			air_booking.chargeable = getattr(self, 'air_chargeable', None) or getattr(self, 'chargeable', None)
			air_booking.service_level = getattr(self, 'service_level', None)
			air_booking.incoterm = getattr(self, 'incoterm', None)
			air_booking.additional_terms = getattr(self, 'additional_terms', None)
			air_booking.airline = getattr(self, 'airline', None)
			air_booking.freight_agent = getattr(self, 'freight_agent', None)
			air_booking.house_type = getattr(self, 'air_house_type', None)
			air_booking.release_type = getattr(self, 'air_release_type', None)
			air_booking.entry_type = getattr(self, 'air_entry_type', None)
			air_booking.etd = getattr(self, 'air_etd', None)
			air_booking.eta = getattr(self, 'air_eta', None)
			air_booking.house_bl = getattr(self, 'air_house_bl', None)
			air_booking.packs = getattr(self, 'air_packs', None)
			air_booking.inner = getattr(self, 'air_inner', None)
			air_booking.gooda_value = getattr(self, 'air_gooda_value', None)
			air_booking.insurance = getattr(self, 'air_insurance', None)
			air_booking.description = getattr(self, 'air_description', None)
			air_booking.marks_and_nos = getattr(self, 'air_marks_and_nos', None)
			air_booking.company = self.company
			air_booking.branch = self.branch
			air_booking.cost_center = self.cost_center
			air_booking.profit_center = self.profit_center
			
			# Insert the Air Booking
			air_booking.insert(ignore_permissions=True)
			
			# Populate charges from Sales Quote Air Freight using fetch_quotations method
			# Wrap in try-except to handle any errors gracefully
			try:
				air_booking.fetch_quotations()
			except Exception as fetch_error:
				# Log the error but don't fail the creation
				frappe.log_error(
					f"Error fetching quotations for Air Booking {air_booking.name}: {str(fetch_error)}",
					"Air Booking - Fetch Quotations Error"
				)
				# Continue without populating charges - user can populate them manually later
				frappe.msgprint(
					_("Air Booking created successfully, but charges could not be automatically populated from Sales Quote. You can populate them manually using the 'Fetch Quotations' button."),
					indicator="orange",
					title=_("Charges Not Populated")
				)
			
			# Save the Air Booking
			air_booking.save(ignore_permissions=True)
			
			return {
				"success": True,
				"message": f"Air Booking {air_booking.name} created successfully.",
				"air_booking": air_booking.name
			}
			
		except frappe.ValidationError as e:
			# Re-raise validation errors as-is (they already have proper messages)
			raise
		except Exception as e:
			frappe.log_error(f"Error creating Air Booking: {str(e)}", "Sales Quote - Create Air Booking")
			frappe.throw(f"Error creating Air Booking: {str(e)}")

	@frappe.whitelist()
	def create_sea_booking_from_sales_quote(self):
		"""
		Create a Sea Booking from a Sales Quote when the quote is tagged as One-Off.
		
		Returns:
			dict: Result with created Sea Booking name and status
		"""
		try:
			# Check if the quote is tagged as One-Off
			if not self.one_off:
				frappe.throw(_("This Sales Quote is not tagged as One-Off. Only One-Off quotes can create Sea Bookings."))
			
			# Check if Sales Quote has sea freight details
			if not self.sea_freight:
				frappe.throw(_("No Sea Freight lines found in this Sales Quote."))
			
			# Get location fields from Sales Quote
			location_type = getattr(self, 'location_type', None)
			location_from = getattr(self, 'location_from', None)
			location_to = getattr(self, 'location_to', None)
			
			# Check if origin and destination ports are set (required for Sea Booking)
			missing_fields = []
			if not location_from:
				missing_fields.append("Origin Port (Location From)")
			if not location_to:
				missing_fields.append("Destination Port (Location To)")
			
			if missing_fields:
				frappe.throw(
					_("Cannot create Sea Booking: {0} {1} required in Sales Quote. Please set the Location Type to 'UNLOCO' and fill in Location From and Location To fields in the Sales Quote before creating a Sea Booking.").format(
						", ".join(missing_fields),
						"is" if len(missing_fields) == 1 else "are"
					),
					title=_("Required Fields Missing")
				)
			
			# Verify that location_from and location_to are valid UNLOCO records
			if not frappe.db.exists("UNLOCO", location_from):
				frappe.throw(_("Origin Port '{0}' is not a valid UNLOCO code. Please ensure Location From in Sales Quote references a valid UNLOCO record.").format(location_from))
			
			if not frappe.db.exists("UNLOCO", location_to):
				frappe.throw(_("Destination Port '{0}' is not a valid UNLOCO code. Please ensure Location To in Sales Quote references a valid UNLOCO record.").format(location_to))
			
			# Allow creation of multiple Sea Bookings from the same Sales Quote
			# No duplicate prevention - users can create multiple bookings as needed
			
			# Create new Sea Booking
			sea_booking = frappe.new_doc("Sea Booking")
			
			# Map basic fields from Sales Quote to Sea Booking
			sea_booking.local_customer = self.customer
			sea_booking.booking_date = today()
			sea_booking.sales_quote = self.name
			sea_booking.shipper = getattr(self, 'shipper', None)
			sea_booking.consignee = getattr(self, 'consignee', None)
			sea_booking.origin_port = location_from
			sea_booking.destination_port = location_to
			sea_booking.direction = getattr(self, 'direction', None)
			sea_booking.weight = getattr(self, 'sea_weight', None) or getattr(self, 'weight', None)
			sea_booking.volume = getattr(self, 'sea_volume', None) or getattr(self, 'volume', None)
			sea_booking.chargeable = getattr(self, 'sea_chargeable', None) or getattr(self, 'chargeable', None)
			sea_booking.service_level = getattr(self, 'service_level', None)
			sea_booking.incoterm = getattr(self, 'incoterm', None)
			sea_booking.additional_terms = getattr(self, 'additional_terms', None)
			sea_booking.company = self.company
			sea_booking.branch = self.branch
			sea_booking.cost_center = self.cost_center
			sea_booking.profit_center = self.profit_center
			
			# Insert the Sea Booking
			sea_booking.insert(ignore_permissions=True)
			
			# Populate charges from Sales Quote Sea Freight using fetch_quotations method
			sea_booking.fetch_quotations()
			
			# Save the Sea Booking
			sea_booking.save(ignore_permissions=True)
			
			return {
				"success": True,
				"message": f"Sea Booking {sea_booking.name} created successfully.",
				"sea_booking": sea_booking.name
			}
			
		except Exception as e:
			frappe.log_error(f"Error creating Sea Booking: {str(e)}", "Sales Quote - Create Sea Booking")
			frappe.throw(f"Error creating Sea Booking: {str(e)}")


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
def create_sea_shipment_from_sales_quote(sales_quote_name):
	"""
	Standalone function to create Sea Shipment from Sales Quote.
	This function can be called from JavaScript.
	"""
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return sales_quote.create_sea_shipment_from_sales_quote()


@frappe.whitelist()
def create_warehouse_contract_from_sales_quote(sales_quote_name):
	"""
	Standalone function to create Warehouse Contract from Sales Quote.
	This function can be called from JavaScript.
	"""
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return sales_quote.create_warehouse_contract_from_sales_quote()


@frappe.whitelist()
def create_air_booking_from_sales_quote(sales_quote_name):
	"""
	Standalone function to create Air Booking from Sales Quote.
	This function can be called from JavaScript.
	
	Workaround for child table 'company' column error:
	Frappe tries to include 'company' in child table SELECT queries, but child tables
	don't have a 'company' column (it's on the parent). This is a Frappe framework issue.
	
	We work around this by using frappe.db.get_value to get parent fields directly,
	avoiding the need to load the document and trigger child table queries.
	"""
	try:
		# Get parent document fields using db.get_value to avoid loading child tables
		# This prevents the 'company' column error in child table queries
		sales_quote_data = frappe.db.get_value(
			"Sales Quote",
			sales_quote_name,
			[
				"one_off", "customer", "company", "branch", "cost_center", "profit_center",
				"shipper", "consignee", "service_level", "incoterm", "additional_terms",
				"air_weight", "air_volume", "air_chargeable",
				"weight", "volume", "chargeable",
				"air_direction", "airline", "freight_agent",
				"air_house_type", "air_release_type", "air_entry_type",
				"air_etd", "air_eta", "air_house_bl", "air_packs", "air_inner",
				"air_gooda_value", "air_insurance", "air_description", "air_marks_and_nos",
				"origin_port", "destination_port", "location_from", "location_to"
			],
			as_dict=True
		)
		
		if not sales_quote_data:
			frappe.throw(_("Sales Quote {0} not found").format(sales_quote_name))
		
		# Check if the quote is tagged as One-Off
		if not sales_quote_data.get("one_off"):
			frappe.throw(_("This Sales Quote is not tagged as One-Off. Only One-Off quotes can create Air Bookings."))
		
		# Check if Sales Quote has air freight details using database query to avoid SQL errors
		air_freight_count = frappe.db.count("Sales Quote Air Freight", {
			"parent": sales_quote_name,
			"parenttype": "Sales Quote"
		})
		if air_freight_count == 0:
			frappe.throw(_("No Air Freight lines found in this Sales Quote."))
		
		# Get port fields from Air tab (preferred) or fall back to Transport tab
		origin_airport = sales_quote_data.get("origin_port")
		destination_airport = sales_quote_data.get("destination_port")
		
		# Fall back to Transport tab location fields if Air tab fields are not set
		if not origin_airport:
			origin_airport = sales_quote_data.get("location_from")
		if not destination_airport:
			destination_airport = sales_quote_data.get("location_to")
		
		# Clean up airport fields: strip whitespace and convert empty strings to None
		if origin_airport:
			origin_airport = str(origin_airport).strip() or None
		if destination_airport:
			destination_airport = str(destination_airport).strip() or None
		
		# Check if origin and destination ports are set (required for Air Booking)
		missing_fields = []
		if not origin_airport:
			missing_fields.append("Origin Port")
		if not destination_airport:
			missing_fields.append("Destination Port")
		
		if missing_fields:
			error_msg = _("Cannot create Air Booking: {0} {1} required in Sales Quote.").format(
				", ".join(missing_fields),
				"is" if len(missing_fields) == 1 else "are"
			)
			instructions = _(
				"To fix this:\n"
				"1. Go to the 'Air' tab in this Sales Quote\n"
				"2. In the 'Routing & Dates' section, fill in:\n"
				"   - 'Origin Port' - select a valid Location for the origin port\n"
				"   - 'Destination Port' - select a valid Location for the destination port\n"
				"3. Save the Sales Quote\n"
				"4. Then try creating the Air Booking again\n\n"
				"Note: You can also use 'Location From' and 'Location To' in the Transport tab as an alternative."
			)
			frappe.throw(
				f"{error_msg}\n\n{instructions}",
				title=_("Required Fields Missing")
			)
		
		# Verify that origin_airport and destination_airport are valid Location records
		if not frappe.db.exists("Location", origin_airport):
			if not frappe.db.exists("UNLOCO", origin_airport):
				frappe.throw(_("Origin Port '{0}' is not a valid Location. Please select a valid Location record in the Air tab.").format(origin_airport))
		
		if not frappe.db.exists("Location", destination_airport):
			if not frappe.db.exists("UNLOCO", destination_airport):
				frappe.throw(_("Destination Port '{0}' is not a valid Location. Please select a valid Location record in the Air tab.").format(destination_airport))
		
		# Create new Air Booking
		air_booking = frappe.new_doc("Air Booking")
		
		# Map basic fields from Sales Quote to Air Booking
		air_booking.local_customer = sales_quote_data.get("customer")
		air_booking.booking_date = today()
		air_booking.sales_quote = sales_quote_name
		air_booking.shipper = sales_quote_data.get("shipper")
		air_booking.consignee = sales_quote_data.get("consignee")
		air_booking.origin_port = origin_airport
		air_booking.destination_port = destination_airport
		
		# Double-check that fields are set before insert
		if not air_booking.origin_port:
			frappe.throw(_("Origin Port is required. Please set Origin Port in the Air tab of Sales Quote."))
		if not air_booking.destination_port:
			frappe.throw(_("Destination Port is required. Please set Destination Port in the Air tab of Sales Quote."))
		
		air_booking.direction = sales_quote_data.get("air_direction") or sales_quote_data.get("direction")
		air_booking.weight = sales_quote_data.get("air_weight") or sales_quote_data.get("weight")
		air_booking.volume = sales_quote_data.get("air_volume") or sales_quote_data.get("volume")
		air_booking.chargeable = sales_quote_data.get("air_chargeable") or sales_quote_data.get("chargeable")
		air_booking.service_level = sales_quote_data.get("service_level")
		air_booking.incoterm = sales_quote_data.get("incoterm")
		air_booking.additional_terms = sales_quote_data.get("additional_terms")
		air_booking.airline = sales_quote_data.get("airline")
		air_booking.freight_agent = sales_quote_data.get("freight_agent")
		air_booking.house_type = sales_quote_data.get("air_house_type")
		air_booking.release_type = sales_quote_data.get("air_release_type")
		air_booking.entry_type = sales_quote_data.get("air_entry_type")
		air_booking.etd = sales_quote_data.get("air_etd")
		air_booking.eta = sales_quote_data.get("air_eta")
		air_booking.house_bl = sales_quote_data.get("air_house_bl")
		air_booking.packs = sales_quote_data.get("air_packs")
		air_booking.inner = sales_quote_data.get("air_inner")
		air_booking.gooda_value = sales_quote_data.get("air_gooda_value")
		air_booking.insurance = sales_quote_data.get("air_insurance")
		air_booking.description = sales_quote_data.get("air_description")
		air_booking.marks_and_nos = sales_quote_data.get("air_marks_and_nos")
		air_booking.company = sales_quote_data.get("company")
		air_booking.branch = sales_quote_data.get("branch")
		air_booking.cost_center = sales_quote_data.get("cost_center")
		air_booking.profit_center = sales_quote_data.get("profit_center")
		
		# Insert the Air Booking
		air_booking.insert(ignore_permissions=True)
		
		# Populate charges from Sales Quote Air Freight using fetch_quotations method
		# Wrap in try-except to handle any errors gracefully
		try:
			air_booking.fetch_quotations()
		except Exception as fetch_error:
			# Log the error but don't fail the creation
			frappe.log_error(
				f"Error fetching quotations for Air Booking {air_booking.name}: {str(fetch_error)}",
				"Air Booking - Fetch Quotations Error (Post-Insert)"
			)
			frappe.msgprint(
				_("Warning: Failed to populate charges from Sales Quote. Please populate manually. Error: {0}").format(str(fetch_error)),
				indicator="orange"
			)
		
		# Save the Air Booking
		air_booking.save(ignore_permissions=True)
		
		return {
			"success": True,
			"message": f"Air Booking {air_booking.name} created successfully.",
			"air_booking": air_booking.name
		}
		
	except frappe.ValidationError:
		raise # Re-raise Frappe ValidationErrors directly
	except Exception as e:
		frappe.log_error(f"Error creating Air Booking: {str(e)}", "Sales Quote - Create Air Booking")
		frappe.throw(f"Error creating Air Booking: {str(e)}")


@frappe.whitelist()
def create_sea_booking_from_sales_quote(sales_quote_name):
	"""
	Standalone function to create Sea Booking from Sales Quote.
	This function can be called from JavaScript.
	"""
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return sales_quote.create_sea_booking_from_sales_quote()


@frappe.whitelist()
def get_vehicle_types_for_load_type(load_type):
	"""
	Get list of Vehicle Types that have the specified load_type in their allowed_load_types.
	
	Args:
		load_type: The Load Type name to filter by
		
	Returns:
		dict: List of Vehicle Type names that allow the specified load_type
	"""
	if not load_type:
		return {"vehicle_types": []}
	
	# Verify that the load_type exists
	if not frappe.db.exists("Load Type", load_type):
		return {"vehicle_types": []}
	
	# Get all Vehicle Types that have this load_type in their allowed_load_types child table
	vehicle_types = frappe.db.sql("""
		SELECT DISTINCT parent
		FROM `tabVehicle Type Load Types`
		WHERE load_type = %s
		AND parent IS NOT NULL
	""", (load_type,), as_dict=True)
	
	vehicle_type_names = [vt.parent for vt in vehicle_types if vt.parent]
	
	return {"vehicle_types": vehicle_type_names}


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


def _normalize_uom_for_air_booking_charges(uom_value, unit_type=None):
	"""
	Normalize UOM value from Link field (UOM DocType name) to Select field options.
	
	Air Booking Charges has a Select field with options: "kg", "m³", "package", "shipment", "hour", "day"
	This function converts UOM record names (like "Kg", "KG", "M³", etc.) to the allowed lowercase values.
	
	Args:
		uom_value: UOM value from Link field (could be "Kg", "kg", "M³", etc.)
		unit_type: Optional unit_type to help determine the correct UOM
	
	Returns:
		Normalized UOM value matching one of the allowed options
	"""
	if not uom_value:
		# If no UOM provided, try to infer from unit_type
		if unit_type == "Weight":
			return "kg"
		elif unit_type == "Volume":
			return "m³"
		elif unit_type in ["Package", "Piece"]:
			return "package"
		elif unit_type == "Shipment":
			return "shipment"
		elif unit_type == "Operation Time":
			return "hour"
		else:
			return "package"  # Default fallback
	
	# Normalize the UOM value (case-insensitive matching)
	uom_lower = str(uom_value).strip().lower()
	
	# Map common UOM variations to allowed values
	uom_mapping = {
		# Weight variations -> "kg"
		"kg": "kg",
		"kilogram": "kg",
		"kilograms": "kg",
		"kgs": "kg",
		# Volume variations -> "m³"
		"m³": "m³",
		"m3": "m³",
		"cbm": "m³",
		"cubic meter": "m³",
		"cubic meters": "m³",
		"m^3": "m³",
		# Package variations -> "package"
		"package": "package",
		"packages": "package",
		"pkg": "package",
		"pkgs": "package",
		"piece": "package",
		"pieces": "package",
		"pc": "package",
		"pcs": "package",
		# Shipment variations -> "shipment"
		"shipment": "shipment",
		"shipments": "shipment",
		"ship": "shipment",
		# Hour variations -> "hour"
		"hour": "hour",
		"hours": "hour",
		"hr": "hour",
		"hrs": "hour",
		# Day variations -> "day"
		"day": "day",
		"days": "day",
		"d": "day",
	}
	
	# Check if we have a direct match
	if uom_lower in uom_mapping:
		return uom_mapping[uom_lower]
	
	# If no match found, try to infer from unit_type
	if unit_type:
		if unit_type == "Weight":
			return "kg"
		elif unit_type == "Volume":
			return "m³"
		elif unit_type in ["Package", "Piece"]:
			return "package"
		elif unit_type == "Shipment":
			return "shipment"
		elif unit_type == "Operation Time":
			return "hour"
	
	# Default fallback
	return "package"


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
		
		# Normalize UOM value to match Air Booking Charges Select field options
		normalized_uom = _normalize_uom_for_air_booking_charges(
			sqaf_record.uom,
			sqaf_record.unit_type
		)
		
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
			"unit_of_measure": normalized_uom,
			"calculation_method": "Automatic",  # Set to "Automatic" since charge is auto-populated from Sales Quote
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


def _populate_charges_from_sales_quote_sea_freight(sea_shipment, sales_quote):
	"""
	Populate charges in Sea Shipment from Sales Quote Sea Freight records.
	
	Args:
		sea_shipment: Sea Shipment document
		sales_quote: Sales Quote document
	"""
	try:
		# Clear existing charges
		sea_shipment.set("charges", [])
		
		# Get Sales Quote Sea Freight records
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
		
		# Map and populate charges
		charges_added = 0
		for sqsf_record in sales_quote_sea_freight_records:
			charge_row = _map_sales_quote_sea_freight_to_charge(sqsf_record, sea_shipment)
			if charge_row:
				sea_shipment.append("charges", charge_row)
				charges_added += 1
		
		if charges_added > 0:
			frappe.msgprint(
				f"Successfully populated {charges_added} charges from Sales Quote",
				title="Charges Updated",
				indicator="green"
			)
		
	except Exception as e:
		frappe.log_error(
			f"Error populating charges from Sales Quote Sea Freight: {str(e)}",
			"Sales Quote Sea Freight - Charges Population Error"
		)
		raise


def _map_sales_quote_sea_freight_to_charge(sqsf_record, sea_shipment):
	"""
	Map sales_quote_sea_freight record to sea_shipment_charges format.
	
	Args:
		sqsf_record: Sales Quote Sea Freight record
		sea_shipment: Sea Shipment document
		
	Returns:
		dict: Mapped charge data
	"""
	try:
		# Get the item details to fetch additional required fields
		item_doc = frappe.get_doc("Item", sqsf_record.item_code)
		
		# Get default currency from system settings
		default_currency = frappe.get_system_settings("currency") or "USD"
		
		# Map unit_type to determine quantity
		unit_type_to_unit = {
			"Weight": "kg",
			"Volume": "m³",
			"Package": "package",
			"Piece": "package",
			"Shipment": "shipment",
			"Container": "container"
		}
		unit = unit_type_to_unit.get(sqsf_record.unit_type, "shipment")
		
		# Get quantity based on unit type
		quantity = 0
		if sqsf_record.unit_type == "Weight":
			quantity = flt(sea_shipment.weight) or 0
		elif sqsf_record.unit_type == "Volume":
			quantity = flt(sea_shipment.volume) or 0
		elif sqsf_record.unit_type == "Package":
			# Get package count from Sea Shipment if available
			if hasattr(sea_shipment, 'packages') and sea_shipment.packages:
				quantity = len(sea_shipment.packages)
			else:
				quantity = 1
		elif sqsf_record.unit_type == "Container":
			# Get container count from Sea Shipment if available
			if hasattr(sea_shipment, 'containers') and sea_shipment.containers:
				quantity = len(sea_shipment.containers)
			else:
				quantity = 1
		elif sqsf_record.unit_type == "Shipment":
			quantity = 1
		else:
			quantity = 1
		
		# Calculate selling amount based on calculation method
		selling_amount = 0
		if sqsf_record.calculation_method == "Per Unit":
			selling_amount = (sqsf_record.unit_rate or 0) * quantity
			# Apply minimum/maximum charge
			if sqsf_record.minimum_charge and selling_amount < flt(sqsf_record.minimum_charge):
				selling_amount = flt(sqsf_record.minimum_charge)
			if sqsf_record.maximum_charge and selling_amount > flt(sqsf_record.maximum_charge):
				selling_amount = flt(sqsf_record.maximum_charge)
		elif sqsf_record.calculation_method == "Fixed Amount":
			selling_amount = sqsf_record.unit_rate or 0
		elif sqsf_record.calculation_method == "Base Plus Additional":
			base = flt(sqsf_record.base_amount) or 0
			additional = (sqsf_record.unit_rate or 0) * max(0, quantity - 1)
			selling_amount = base + additional
		elif sqsf_record.calculation_method == "First Plus Additional":
			min_qty = flt(sqsf_record.minimum_quantity) or 1
			if quantity <= min_qty:
				selling_amount = sqsf_record.unit_rate or 0
			else:
				additional = (sqsf_record.unit_rate or 0) * (quantity - min_qty)
				selling_amount = (sqsf_record.unit_rate or 0) + additional
		else:
			selling_amount = sqsf_record.unit_rate or 0
		
		# Determine charge_type from item or use default
		charge_type = "Other"
		if hasattr(item_doc, 'custom_charge_type'):
			charge_type = item_doc.custom_charge_type or "Other"
		
		# Map the fields from sales_quote_sea_freight to sea_shipment_charges
		charge_data = {
			"charge_item": sqsf_record.item_code,
			"charge_name": sqsf_record.item_name or item_doc.item_name,
			"charge_type": charge_type,
			"charge_description": sqsf_record.item_name or item_doc.item_name,
			"bill_to": sea_shipment.local_customer if hasattr(sea_shipment, 'local_customer') else None,
			"selling_currency": sqsf_record.currency or default_currency,
			"selling_amount": selling_amount,
			"per_unit_rate": sqsf_record.unit_rate or 0,
			"unit": unit,
			"revenue_calc_type": sqsf_record.calculation_method or "Manual",
			"base_amount": sqsf_record.base_amount or 0
		}
		
		# Add minimum charge if available
		if sqsf_record.minimum_charge:
			charge_data["minimum"] = sqsf_record.minimum_charge
		
		return charge_data
		
	except Exception as e:
		frappe.log_error(
			f"Error mapping sales quote sea freight record: {str(e)}",
			"Sales Quote Sea Freight Mapping Error"
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
		# Clear existing charges (if any)
		transport_order.set("charges", [])
		
		# Import SALES_QUOTE_CHARGE_FIELDS from transport_order
		from logistics.transport.doctype.transport_order.transport_order import SALES_QUOTE_CHARGE_FIELDS
		
		# Get Sales Quote Transport records with all required fields
		sales_quote_transport_records = frappe.get_all(
			"Sales Quote Transport",
			filters={"parent": sales_quote.name, "parenttype": "Sales Quote"},
			fields=["name"] + SALES_QUOTE_CHARGE_FIELDS,
			order_by="idx"
		)
		
		if not sales_quote_transport_records:
			frappe.msgprint(
				f"No transport charges found in Sales Quote: {sales_quote.name}",
				title="No Charges Found",
				indicator="orange"
			)
			return
		
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
		# Import SALES_QUOTE_CHARGE_FIELDS from transport_order
		from logistics.transport.doctype.transport_order.transport_order import SALES_QUOTE_CHARGE_FIELDS
		
		# Map overlapping fields directly from SALES_QUOTE_CHARGE_FIELDS
		charge_data = {}
		for field in SALES_QUOTE_CHARGE_FIELDS:
			if field in sqt_record:
				charge_data[field] = sqt_record.get(field)
		
		# Fallbacks for essential fields
		if not charge_data.get("item_name") and sqt_record.get("item_code"):
			try:
				item_doc = frappe.get_doc("Item", sqt_record.item_code)
				charge_data["item_name"] = item_doc.item_name
			except:
				charge_data["item_name"] = sqt_record.get("item_name", "")
		
		if not charge_data.get("uom") and sqt_record.get("item_code"):
			try:
				item_doc = item_doc if "item_doc" in locals() else frappe.get_doc("Item", sqt_record.item_code)
				charge_data["uom"] = item_doc.stock_uom
			except:
				charge_data["uom"] = sqt_record.get("uom", "")
		
		# Ensure unit_rate is set
		if charge_data.get("unit_rate") is None:
			charge_data["unit_rate"] = sqt_record.get("unit_rate") or 0
		
		# Ensure quantity is set
		if not charge_data.get("quantity"):
			charge_data["quantity"] = sqt_record.get("quantity") or 1
		
		return charge_data
		
	except Exception as e:
		frappe.log_error(
			f"Error mapping sales quote transport record: {str(e)}",
			"Sales Quote Transport Mapping Error"
		)
		return None
