# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, flt, getdate


def map_sales_quote_entry_type_to_air_booking(sales_quote_entry_type):
	"""
	Validate and return entry type for Air Booking. Options are aligned across Sales Quote and Air Booking.
	
	Unified options (industry standard): Direct, Transit, Transshipment, ATA Carnet
	
	Args:
		sales_quote_entry_type: Entry type value from Sales Quote
	
	Returns:
		str: Entry type value for Air Booking, or None if invalid
	"""
	if not sales_quote_entry_type:
		return None
	
	valid_entry_types = ["Direct", "Transit", "Transshipment", "ATA Carnet"]
	if sales_quote_entry_type in valid_entry_types:
		return sales_quote_entry_type
	
	frappe.log_error(
		f"Invalid entry_type value '{sales_quote_entry_type}' from Sales Quote. "
		f"Valid values: {', '.join(valid_entry_types)}.",
		"Sales Quote - Entry Type"
	)
	return None


class SalesQuote(Document):
	def validate(self):
		"""Validate Sales Quote data"""
		self.validate_additional_charge_job()
		self.validate_vehicle_type_load_type()
		self.validate_vehicle_type_capacity()
		self.validate_multimodal_main_job()

	def validate_additional_charge_job(self):
		"""When Additional Charge is checked, Job Type and Job are required."""
		if getattr(self, "additional_charge", 0):
			if not getattr(self, "job_type", None) or not getattr(self, "job", None):
				frappe.throw(_("For Additional Charge quotes, Job Type and Job are required."))

	def validate_multimodal_main_job(self):
		"""When multimodal routing legs exist, exactly one leg must be Main Job."""
		legs = getattr(self, "routing_legs", None) or []
		if not legs:
			return
		main_count = sum(1 for r in legs if getattr(r, "is_main_job", 0))
		if main_count == 0:
			frappe.throw(_("Multimodal routing requires exactly one Main Job. Please check 'Main Job' on the leg that will do customer billing."))
		if main_count > 1:
			frappe.throw(_("Only one routing leg can be the Main Job. Please uncheck 'Main Job' on the extra leg(s)."))
	
	def validate_vehicle_type_load_type(self):
		"""Validate that the selected vehicle_type is allowed for the selected load_type in each transport row"""
		if not self.is_transport or not self.transport:
			return
		
		# Iterate through transport child table rows
		for transport_row in self.transport:
			vehicle_type = getattr(transport_row, 'vehicle_type', None)
			load_type = getattr(transport_row, 'load_type', None)
			
			# Skip validation if either field is missing
			if not vehicle_type or not load_type:
				continue
			
			# Check if the vehicle_type has the selected load_type in its allowed_load_types
			allowed_load_types = frappe.db.get_all(
				"Vehicle Type Load Types",
				filters={"parent": vehicle_type},
				fields=["load_type"]
			)
			
			allowed_load_type_names = [alt.load_type for alt in allowed_load_types]
			
			if load_type not in allowed_load_type_names:
				frappe.throw(
					_("Vehicle Type '{0}' is not allowed for Load Type '{1}' in row {2}. Please select a Vehicle Type that allows this Load Type.").format(
						vehicle_type, load_type, transport_row.idx
					),
					title=_("Invalid Vehicle Type")
				)
	
	def validate_vehicle_type_capacity(self):
		"""Validate vehicle type capacity when vehicle_type is assigned. Uses Transport tab dimensions."""
		if not getattr(self, 'is_transport', None):
			return
		
		# Check if any transport row has vehicle_type
		has_vehicle_type = False
		if self.transport:
			for transport_row in self.transport:
				if getattr(transport_row, 'vehicle_type', None):
					has_vehicle_type = True
					break
		
		if not has_vehicle_type:
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

			# Validate capacity for each transport row with vehicle_type
			for transport_row in self.transport:
				vehicle_type = getattr(transport_row, 'vehicle_type', None)
				if not vehicle_type:
					continue
				
				# Get vehicle type capacity (average or minimum from vehicles of this type)
				capacity_info = get_vehicle_type_capacity_info(vehicle_type, self.company)

				# Check if capacity is sufficient (compare in standard UOMs)
				if required_weight_std > 0 and capacity_info.get('max_weight', 0) < required_weight_std:
					frappe.msgprint(_("Warning: Required weight ({0} {1}) may exceed typical capacity for vehicle type {2} in row {3}").format(
						required_weight, required_weight_uom, vehicle_type, transport_row.idx
					), indicator='orange')

				if required_volume_std > 0 and capacity_info.get('max_volume', 0) < required_volume_std:
					frappe.msgprint(_("Warning: Required volume ({0} {1}) may exceed typical capacity for vehicle type {2} in row {3}").format(
						required_volume, required_volume_uom, vehicle_type, transport_row.idx
					), indicator='orange')
		except ImportError:
			# Capacity management not fully implemented yet
			pass
		except Exception as e:
			frappe.log_error(f"Error validating vehicle type capacity in Sales Quote: {str(e)}", "Capacity Validation Error")
	
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
	def create_air_shipment_from_sales_quote(self):
		"""
		Create an Air Shipment from a Sales Quote when the quote is tagged as One-Off.
		
		Returns:
			dict: Result with created Air Shipment name and status
		"""
		try:
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
			
			# Ensure commit before client navigates (avoids "not found" on form load)
			frappe.db.commit()
			
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
			
			# Ensure commit before client navigates (avoids "not found" on form load)
			frappe.db.commit()
			
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
			
			# Ensure commit before client navigates (avoids "not found" on form load)
			frappe.db.commit()
			
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

	def _map_sales_quote_entry_type_to_air_booking(self, sales_quote_entry_type):
		"""Wrapper method that calls the module-level mapping function"""
		return map_sales_quote_entry_type_to_air_booking(sales_quote_entry_type)
	
@frappe.whitelist()
def create_transport_order_from_sales_quote(sales_quote_name):
	"""
	Create a Transport Order from Sales Quote. Populates job_no on matching routing leg if multimodal.
	"""
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return _create_transport_order_from_sales_quote(sales_quote)


@frappe.whitelist()
def create_air_booking_from_sales_quote(sales_quote_name):
	"""
	Create an Air Booking from Sales Quote. Populates job_no on matching routing leg if multimodal.
	"""
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return _create_air_booking_from_sales_quote(sales_quote)


@frappe.whitelist()
def create_sea_booking_from_sales_quote(sales_quote_name):
	"""
	Create a Sea Booking from Sales Quote. Populates job_no on matching routing leg if multimodal.
	"""
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return _create_sea_booking_from_sales_quote(sales_quote)


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
def create_sales_invoice_from_sales_quote(sales_quote_name, posting_date=None):
	"""
	Create Sales Invoice from multimodal Sales Quote.
	Uses Main Job for billing; aggregates or splits per billing_mode.
	- Consolidated: One invoice with charges from Main Job + all Sub-Jobs.
	- Per Product: Separate invoice per routing leg that has a job.
	"""
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	return _create_sales_invoice_from_multimodal_quote(sales_quote, posting_date)


def _create_sales_invoice_from_multimodal_quote(sales_quote, posting_date=None):
	"""Create Sales Invoice from multimodal Sales Quote using Main Job and billing_mode."""
	legs = getattr(sales_quote, "routing_legs", None) or []
	if not legs:
		frappe.throw(_("No routing legs found. Add routing legs and designate one as Main Job."))

	main_leg = next((r for r in legs if getattr(r, "is_main_job", 0)), None)
	if not main_leg or not getattr(main_leg, "job_no", None):
		frappe.throw(_("Main Job must have a linked job (job_no). Create the jobs from this quote first."))

	billing_mode = getattr(sales_quote, "billing_mode", None) or "Consolidated"
	posting_date = posting_date or today()

	if billing_mode == "Per Product":
		return _create_separate_invoices_per_leg(sales_quote, legs, posting_date)
	else:
		return _create_consolidated_invoice(sales_quote, legs, main_leg, posting_date)


def _create_consolidated_invoice(sales_quote, legs, main_leg, posting_date):
	"""Create one Sales Invoice aggregating charges from Main Job + all Sub-Jobs."""
	main_job_type = getattr(main_leg, "job_type", None)
	main_job_no = getattr(main_leg, "job_no", None)
	if not main_job_type or not main_job_no:
		frappe.throw(_("Main Job leg must have job_type and job_no set."))

	# Get header from Main Job
	main_doc = frappe.get_doc(main_job_type, main_job_no)
	customer = getattr(main_doc, "customer", None) or getattr(main_doc, "local_customer", None) or sales_quote.customer
	company = getattr(main_doc, "company", None) or sales_quote.company
	if not customer or not company:
		frappe.throw(_("Customer and Company are required. Set them on the Main Job or Sales Quote."))

	# Collect invoice items from all legs with job_no
	all_items = []
	for leg in legs:
		job_type = getattr(leg, "job_type", None)
		job_no = getattr(leg, "job_no", None)
		if not job_type or not job_no:
			continue
		items = _get_invoice_items_from_job(job_type, job_no, customer)
		for item in items:
			item["description"] = item.get("description") or f"{job_type} {job_no} (Leg {getattr(leg, 'leg_order', '')})"
			all_items.append(item)

	if not all_items:
		frappe.throw(_("No charges found in any linked job. Add charges to the jobs before creating the invoice."))

	# Create Sales Invoice
	si = frappe.new_doc("Sales Invoice")
	si.customer = customer
	si.company = company
	si.posting_date = posting_date
	si.quotation_no = sales_quote.name
	if getattr(main_doc, "branch", None):
		si.branch = main_doc.branch
	elif sales_quote.branch:
		si.branch = sales_quote.branch
	if getattr(main_doc, "cost_center", None):
		si.cost_center = main_doc.cost_center
	elif sales_quote.cost_center:
		si.cost_center = sales_quote.cost_center
	if getattr(main_doc, "profit_center", None):
		si.profit_center = main_doc.profit_center
	elif sales_quote.profit_center:
		si.profit_center = sales_quote.profit_center
	if getattr(main_doc, "job_costing_number", None):
		si.job_costing_number = main_doc.job_costing_number

	base_remarks = _("Auto-created from Sales Quote {0} (Consolidated - Main Job: {1})").format(sales_quote.name, main_job_no)
	si.remarks = base_remarks

	for item in all_items:
		si.append("items", item)

	si.set_missing_values()
	si.insert(ignore_permissions=True)

	return {"success": True, "sales_invoice": si.name, "message": _("Sales Invoice {0} created (Consolidated).").format(si.name)}


def _create_separate_invoices_per_leg(sales_quote, legs, posting_date):
	"""Create separate Sales Invoice per routing leg that has a job."""
	invoices_created = []
	for leg in legs:
		job_type = getattr(leg, "job_type", None)
		job_no = getattr(leg, "job_no", None)
		if not job_type or not job_no:
			continue
		try:
			if job_type == "Transport Job":
				from logistics.transport.doctype.transport_job.transport_job import create_sales_invoice
				result = create_sales_invoice(job_no)
				if result and result.get("sales_invoice"):
					invoices_created.append(result["sales_invoice"])
			elif job_type == "Sea Shipment":
				shipment = frappe.get_doc("Sea Shipment", job_no)
				customer = getattr(shipment, "local_customer", None) or sales_quote.customer
				from logistics.sea_freight.doctype.sea_shipment.sea_shipment import create_sales_invoice as sea_create_si
				inv = sea_create_si(job_no, posting_date, customer)
				if inv:
					invoices_created.append(inv.name)
			elif job_type == "Air Shipment":
				shipment = frappe.get_doc("Air Shipment", job_no)
				if getattr(shipment, "create_sales_invoice", None):
					result = shipment.create_sales_invoice()
					if result and result.get("sales_invoice"):
						invoices_created.append(result["sales_invoice"])
		except Exception as e:
			frappe.log_error(str(e), "Multimodal Per-Product Invoice")
			frappe.msgprint(_("Could not create invoice for {0} {1}: {2}").format(job_type, job_no, str(e)), indicator="orange")

	if not invoices_created:
		frappe.throw(_("No invoices could be created. Ensure jobs have charges and are in a billable state."))

	return {"success": True, "sales_invoices": invoices_created, "message": _("Created {0} Sales Invoice(s).").format(len(invoices_created))}


def _get_invoice_items_from_job(job_type, job_name, customer):
	"""Extract Sales Invoice items from a job/shipment. Returns list of item dicts."""
	items = []
	doc = frappe.get_doc(job_type, job_name)

	if job_type == "Transport Job":
		charges = doc.get("charges") or []
		for ch in charges:
			item_code = getattr(ch, "item_code", None)
			if not item_code:
				continue
			qty = flt(getattr(ch, "quantity", 1))
			unit_rate = flt(getattr(ch, "unit_rate", 0))
			est_rev = flt(getattr(ch, "estimated_revenue", 0))
			rate = est_rev / qty if (est_rev > 0 and qty > 0) else unit_rate
			items.append({
				"item_code": item_code,
				"item_name": getattr(ch, "item_name", None) or item_code,
				"qty": qty,
				"rate": rate,
				"uom": getattr(ch, "uom", None),
			})
	elif job_type == "Sea Shipment":
		charges = doc.get("charges") or []
		for ch in charges:
			if getattr(ch, "bill_to", None) != customer:
				continue
			items.append({
				"item_code": getattr(ch, "charge_item", None),
				"item_name": getattr(ch, "charge_name", None),
				"description": getattr(ch, "charge_description", None),
				"qty": 1,
				"rate": flt(getattr(ch, "selling_amount", 0)),
			})
	elif job_type == "Air Shipment":
		charges = doc.get("charges") or []
		for ch in charges:
			item_code = getattr(ch, "item_code", None)
			if not item_code:
				continue
			qty = flt(getattr(ch, "quantity", 1))
			rate = flt(getattr(ch, "rate", 0))
			total = flt(getattr(ch, "total_amount", 0))
			if total > 0 and qty > 0:
				rate = total / qty
			items.append({
				"item_code": item_code,
				"item_name": getattr(ch, "item_name", None) or item_code,
				"qty": qty,
				"rate": rate,
			})

	return items


def _create_transport_order_from_sales_quote(sales_quote):
	"""Create Transport Order from Sales Quote and update routing leg job_no if multimodal."""
	if not getattr(sales_quote, "is_transport", False):
		frappe.throw(_("Only Sales Quotes with Transport enabled can create Transport Orders."))
	if not sales_quote.transport:
		frappe.throw(_("No transport lines found in this Sales Quote."))

	from logistics.transport.doctype.transport_order.transport_order import _sync_quote_and_sales_quote

	# Use first transport row for location/params
	first = sales_quote.transport[0]
	location_from = getattr(first, "location_from", None) or getattr(sales_quote, "location_from", None)
	location_to = getattr(first, "location_to", None) or getattr(sales_quote, "location_to", None)
	if not location_from or not location_to:
		frappe.throw(_("Location From and Location To are required. Set them in the Transport tab."))

	transport_order = frappe.new_doc("Transport Order")
	transport_order.customer = sales_quote.customer
	transport_order.booking_date = today()
	transport_order.scheduled_date = today()
	transport_order.quote_type = "Sales Quote"
	transport_order.quote = sales_quote.name
	transport_order.sales_quote = sales_quote.name
	_sync_quote_and_sales_quote(transport_order)

	transport_order.transport_template = getattr(first, "transport_template", None)
	transport_order.load_type = getattr(first, "load_type", None)
	transport_order.vehicle_type = getattr(first, "vehicle_type", None)
	transport_order.container_type = getattr(first, "container_type", None)
	transport_order.company = sales_quote.company
	transport_order.branch = sales_quote.branch
	transport_order.cost_center = sales_quote.cost_center
	transport_order.profit_center = sales_quote.profit_center
	transport_order.location_type = getattr(first, "location_type", None)
	transport_order.location_from = location_from
	transport_order.location_to = location_to

	transport_order.transport_job_type = sales_quote._determine_transport_job_type(
		current_job_type=None,
		load_type=transport_order.load_type,
		container_type=transport_order.container_type,
	)

	transport_order.flags.skip_container_no_validation = True
	transport_order.flags.skip_container_type_validation = True
	transport_order.flags.skip_vehicle_type_validation = True
	transport_order.flags.skip_sales_quote_on_change = True

	transport_order.insert(ignore_permissions=True)
	transport_order.reload()
	transport_order.quote_type = "Sales Quote"
	transport_order.quote = sales_quote.name
	transport_order.sales_quote = sales_quote.name
	_sync_quote_and_sales_quote(transport_order)
	_populate_charges_from_sales_quote(transport_order, sales_quote)
	transport_order.save(ignore_permissions=True)

	_update_routing_leg_job(
		sales_quote.name,
		mode="Road",
		job_type="Transport Order",
		job_no=transport_order.name,
	)
	frappe.db.commit()
	return {"success": True, "transport_order": transport_order.name, "message": _("Transport Order {0} created.").format(transport_order.name)}


def _create_air_booking_from_sales_quote(sales_quote):
	"""Create Air Booking from Sales Quote and update routing leg job_no if multimodal."""
	if not getattr(sales_quote, "is_air", False):
		frappe.throw(_("Only Sales Quotes with Air enabled can create Air Bookings."))
	if not sales_quote.air_freight:
		frappe.throw(_("No air freight lines found in this Sales Quote."))

	origin = getattr(sales_quote, "origin_port", None) or (sales_quote.air_freight and getattr(sales_quote.air_freight[0], "origin_port", None))
	dest = getattr(sales_quote, "destination_port", None) or (sales_quote.air_freight and getattr(sales_quote.air_freight[0], "destination_port", None))
	if not origin or not dest:
		frappe.throw(_("Origin Port and Destination Port are required for Air mode."))
	if not sales_quote.shipper or not sales_quote.consignee:
		frappe.throw(_("Shipper and Consignee are required for Air mode."))

	first = sales_quote.air_freight[0]
	air_booking = frappe.new_doc("Air Booking")
	air_booking.booking_date = today()
	air_booking.local_customer = sales_quote.customer
	air_booking.quote_type = "Sales Quote"
	air_booking.quote = sales_quote.name
	air_booking.sales_quote = sales_quote.name
	air_booking.origin_port = origin
	air_booking.destination_port = dest
	air_booking.direction = getattr(first, "air_direction", None) or getattr(sales_quote, "direction", None) or "Export"
	air_booking.shipper = sales_quote.shipper
	air_booking.consignee = sales_quote.consignee
	air_booking.airline = getattr(first, "airline", None)
	air_booking.freight_agent = getattr(first, "freight_agent", None)
	air_booking.house_type = getattr(first, "air_house_type", None)
	# Normalize legacy house_type values
	if air_booking.house_type == "Direct":
		air_booking.house_type = "Standard House"
	elif air_booking.house_type == "Consolidation":
		air_booking.house_type = "Co-load Master"
	air_booking.company = sales_quote.company
	air_booking.branch = sales_quote.branch
	air_booking.cost_center = sales_quote.cost_center
	air_booking.profit_center = sales_quote.profit_center

	air_booking.insert(ignore_permissions=True)
	air_booking.reload()
	air_booking.quote_type = "Sales Quote"
	air_booking.quote = sales_quote.name
	air_booking.sales_quote = sales_quote.name
	from logistics.air_freight.doctype.air_booking.air_booking import _sync_quote_and_sales_quote
	_sync_quote_and_sales_quote(air_booking)
	air_booking.save(ignore_permissions=True)

	_update_routing_leg_job(
		sales_quote.name,
		mode="Air",
		job_type="Air Booking",
		job_no=air_booking.name,
	)
	frappe.db.commit()
	return {"success": True, "air_booking": air_booking.name, "message": _("Air Booking {0} created.").format(air_booking.name)}


def _create_sea_booking_from_sales_quote(sales_quote):
	"""Create Sea Booking from Sales Quote and update routing leg job_no if multimodal."""
	if not getattr(sales_quote, "is_sea", False):
		frappe.throw(_("Only Sales Quotes with Sea enabled can create Sea Bookings."))
	if not sales_quote.sea_freight:
		frappe.throw(_("No sea freight lines found in this Sales Quote."))

	first = sales_quote.sea_freight[0] if sales_quote.sea_freight else None
	origin = getattr(first, "origin_port", None) or getattr(sales_quote, "location_from", None)
	dest = getattr(first, "destination_port", None) or getattr(sales_quote, "location_to", None)
	if not origin or not dest:
		frappe.throw(_("Origin Port and Destination Port are required for Sea mode."))
	if not sales_quote.shipper or not sales_quote.consignee:
		frappe.throw(_("Shipper and Consignee are required for Sea mode."))

	sea_booking = frappe.new_doc("Sea Booking")
	sea_booking.booking_date = today()
	sea_booking.local_customer = sales_quote.customer
	sea_booking.quote_type = "Sales Quote"
	sea_booking.quote = sales_quote.name
	sea_booking.sales_quote = sales_quote.name
	sea_booking.origin_port = origin
	sea_booking.destination_port = dest
	sea_booking.direction = getattr(first, "sea_direction", None) or getattr(sales_quote, "direction", None) or "Export"
	if first:
		sea_booking.shipping_line = getattr(first, "shipping_line", None)
		sea_booking.freight_agent = getattr(first, "freight_agent", None)
		sea_booking.transport_mode = getattr(first, "sea_transport_mode", None) or getattr(first, "transport_mode", None) or "FCL"
	else:
		sea_booking.transport_mode = "FCL"
	sea_booking.shipper = sales_quote.shipper
	sea_booking.consignee = sales_quote.consignee
	sea_booking.company = sales_quote.company
	sea_booking.branch = sales_quote.branch
	sea_booking.cost_center = sales_quote.cost_center
	sea_booking.profit_center = sales_quote.profit_center

	sea_booking.insert(ignore_permissions=True)
	sea_booking.reload()
	sea_booking.quote_type = "Sales Quote"
	sea_booking.quote = sales_quote.name
	sea_booking.sales_quote = sales_quote.name
	from logistics.sea_freight.doctype.sea_booking.sea_booking import _sync_quote_and_sales_quote
	_sync_quote_and_sales_quote(sea_booking)
	sea_booking.save(ignore_permissions=True)

	_update_routing_leg_job(
		sales_quote.name,
		mode="Sea",
		job_type="Sea Booking",
		job_no=sea_booking.name,
	)
	frappe.db.commit()
	return {"success": True, "sea_booking": sea_booking.name, "message": _("Sea Booking {0} created.").format(sea_booking.name)}


def _update_routing_leg_job(sales_quote_name, mode, job_type, job_no):
	"""
	Update the first routing leg matching the given mode that has no job_no yet.
	Used when creating Transport Order / Air Booking / Sea Booking from Sales Quote.
	"""
	legs = frappe.get_all(
		"Sales Quote Routing Leg",
		filters=[
			["parent", "=", sales_quote_name],
			["parenttype", "=", "Sales Quote"],
			["mode", "=", mode],
			["job_no", "is", "not set"],
		],
		fields=["name", "idx"],
		order_by="leg_order asc, idx asc",
		limit=1,
	)
	if not legs:
		return
	leg = legs[0]
	frappe.db.set_value(
		"Sales Quote Routing Leg",
		leg.name,
		{"job_type": job_type, "job_no": job_no},
		update_modified=True,
	)
	frappe.db.commit()


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
			except Exception:
				charge_data["item_name"] = sqt_record.get("item_name", "")
		
		if not charge_data.get("uom") and sqt_record.get("item_code"):
			try:
				item_doc = item_doc if "item_doc" in locals() else frappe.get_doc("Item", sqt_record.item_code)
				charge_data["uom"] = item_doc.stock_uom
			except Exception:
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
