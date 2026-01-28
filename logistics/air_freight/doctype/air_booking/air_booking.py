# Copyright (c) 2025, logistics.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, flt


class AirBooking(Document):
	def validate(self):
		"""Validate Air Booking data"""
		self.validate_required_fields()
		self.validate_dates()
		self.validate_accounts()
		self.calculate_chargeable_weight()
	
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
			# Check if Profit Center doctype has a company field before validating
			# Profit Center may not have a company field in this installation
			try:
				profit_center_meta = frappe.get_meta("Profit Center")
				if profit_center_meta.has_field("company"):
					profit_center_company = frappe.db.get_value("Profit Center", self.profit_center, "company")
					if profit_center_company and profit_center_company != self.company:
						frappe.throw(_("Profit Center {0} does not belong to Company {1}").format(
							self.profit_center, self.company
							))
			except Exception:
				# If Profit Center doesn't have company field, skip validation
				pass
		
		if self.branch:
			# Check if Branch doctype has a company field before validating
			# Branch may not have a company field in this installation
			try:
				branch_meta = frappe.get_meta("Branch")
				if branch_meta.has_field("company"):
					branch_company = frappe.db.get_value("Branch", self.branch, "company")
					if branch_company and branch_company != self.company:
						frappe.throw(_("Branch {0} does not belong to Company {1}").format(
							self.branch, self.company
							))
			except Exception:
				# If Branch doesn't have company field, skip validation
				pass
	
	def calculate_chargeable_weight(self):
		"""Calculate chargeable weight based on volume and weight"""
		if not self.volume and not self.weight:
			return
		
		# Get volume to weight divisor
		divisor = self.get_volume_to_weight_divisor()
		
		# Calculate volume weight
		volume_weight = 0
		if self.volume and divisor:
			# Convert volume from m³ to cm³, then divide by divisor
			# Volume in m³ * 1,000,000 cm³/m³ / divisor = volume weight in kg
			volume_weight = flt(self.volume) * (1000000.0 / divisor)
		
		# Calculate chargeable weight (higher of actual weight or volume weight)
		if self.weight and volume_weight:
			self.chargeable = max(flt(self.weight), volume_weight)
		elif self.weight:
			self.chargeable = flt(self.weight)
		elif volume_weight:
			self.chargeable = volume_weight
		else:
			self.chargeable = 0
	
	def get_volume_to_weight_divisor(self):
		"""Get the volume to weight divisor based on factor type and airline settings"""
		# Default to IATA standard
		divisor = 6000
		
		# Get factor type (default to IATA if not set)
		factor_type = self.volume_to_weight_factor_type or "IATA"
		
		if factor_type == "IATA":
			# IATA standard: 6000 divisor (equivalent to 167 kg/m³)
			divisor = 6000
		elif factor_type == "Custom":
			# Check if custom divisor is overridden on Air Booking
			if self.custom_volume_to_weight_divisor:
				divisor = flt(self.custom_volume_to_weight_divisor)
			# Otherwise, get from Airline
			elif self.airline:
				airline_divisor = frappe.db.get_value("Airline", self.airline, "volume_to_weight_divisor")
				if airline_divisor:
					divisor = flt(airline_divisor)
				else:
					# Default to IATA if airline doesn't have a divisor set
					divisor = 6000
			else:
				# Default to IATA if no airline selected
				divisor = 6000
		
		return divisor
	
	@frappe.whitelist()
	def fetch_quotations(self):
		"""
		Fetch quotations from Sales Quote and populate Air Booking fields.
		
		Returns:
			dict: Result with status and message
		"""
		try:
			if not self.sales_quote:
				frappe.throw(_("Please select a Sales Quote first"))
			
			# Check if Sales Quote has air freight details using database query to avoid SQL errors
			air_freight_count = frappe.db.count("Sales Quote Air Freight", {
				"parent": self.sales_quote,
				"parenttype": "Sales Quote"
			})
			if air_freight_count == 0:
				frappe.throw(_("No Air Freight lines found in Sales Quote {0}").format(self.sales_quote))
			
			# Get Sales Quote fields using get_value to avoid loading child tables
			sales_quote_data = frappe.db.get_value("Sales Quote", self.sales_quote, [
				"customer", "shipper", "consignee", "location_from", "location_to",
				"air_direction", "weight", "volume", "chargeable",
				"service_level", "incoterm", "additional_terms", "airline",
				"freight_agent", "air_house_type", "air_release_type", "air_entry_type",
				"air_etd", "air_eta", "air_house_bl", "air_packs", "air_inner",
				"air_gooda_value", "air_insurance", "air_description", "air_marks_and_nos",
				"company", "branch", "cost_center", "profit_center", "origin_port", "destination_port"
			], as_dict=True)
			
			if not sales_quote_data:
				frappe.throw(_("Sales Quote {0} not found").format(self.sales_quote))
			
			# Map basic fields from Sales Quote to Air Booking
			if not self.local_customer:
				self.local_customer = sales_quote_data.get("customer")
			if not self.shipper:
				self.shipper = sales_quote_data.get("shipper")
			if not self.consignee:
				self.consignee = sales_quote_data.get("consignee")
			if not self.origin_port:
				# Try origin_port first, then fall back to location_from
				self.origin_port = sales_quote_data.get("origin_port") or sales_quote_data.get("location_from")
			if not self.destination_port:
				# Try destination_port first, then fall back to location_to
				self.destination_port = sales_quote_data.get("destination_port") or sales_quote_data.get("location_to")
			if not self.direction:
				self.direction = sales_quote_data.get("air_direction")
			if not self.weight:
				self.weight = sales_quote_data.get("weight")
			if not self.volume:
				self.volume = sales_quote_data.get("volume")
			if not self.chargeable:
				self.chargeable = sales_quote_data.get("chargeable")
			if not self.service_level:
				self.service_level = sales_quote_data.get("service_level")
			if not self.incoterm:
				self.incoterm = sales_quote_data.get("incoterm")
			if not self.additional_terms:
				self.additional_terms = sales_quote_data.get("additional_terms")
			if not self.airline:
				self.airline = sales_quote_data.get("airline")
			if not self.freight_agent:
				self.freight_agent = sales_quote_data.get("freight_agent")
			if not self.house_type:
				self.house_type = sales_quote_data.get("air_house_type")
			if not self.release_type:
				self.release_type = sales_quote_data.get("air_release_type")
			if not self.entry_type:
				self.entry_type = sales_quote_data.get("air_entry_type")
			if not self.etd:
				self.etd = sales_quote_data.get("air_etd")
			if not self.eta:
				self.eta = sales_quote_data.get("air_eta")
			if not self.house_bl:
				self.house_bl = sales_quote_data.get("air_house_bl")
			if not self.packs:
				self.packs = sales_quote_data.get("air_packs")
			if not self.inner:
				self.inner = sales_quote_data.get("air_inner")
			if not self.goods_value:
				self.goods_value = sales_quote_data.get("air_gooda_value")
			if not self.insurance:
				self.insurance = sales_quote_data.get("air_insurance")
			if not self.description:
				self.description = sales_quote_data.get("air_description")
			if not self.marks_and_nos:
				self.marks_and_nos = sales_quote_data.get("air_marks_and_nos")
			if not self.company:
				self.company = sales_quote_data.get("company")
			if not self.branch:
				self.branch = sales_quote_data.get("branch")
			if not self.cost_center:
				self.cost_center = sales_quote_data.get("cost_center")
			if not self.profit_center:
				self.profit_center = sales_quote_data.get("profit_center")
			
			# Populate charges from Sales Quote Air Freight
			# Pass the sales quote name instead of loading the full document to avoid SQL errors
			self._populate_charges_from_sales_quote(self.sales_quote)
			
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
				f"Error fetching quotations for Air Booking {self.name}: {str(e)}",
				"Air Booking - Fetch Quotations Error"
			)
			frappe.throw(_("Error fetching quotations: {0}").format(str(e)))
	
	def _populate_charges_from_sales_quote(self, sales_quote_name):
		"""Populate charges from Sales Quote Air Freight records
		
		Args:
			sales_quote_name: Name of the Sales Quote (string) or Sales Quote document
		"""
		try:
			# Handle both document and name inputs
			if isinstance(sales_quote_name, str):
				sq_name = sales_quote_name
			else:
				sq_name = sales_quote_name.name
			
			# Clear existing charges
			self.set("charges", [])
			
			# Get Sales Quote Air Freight records
			sales_quote_air_freight_records = frappe.get_all(
				"Sales Quote Air Freight",
				filters={"parent": sq_name, "parenttype": "Sales Quote"},
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
				charge_row = self._map_sales_quote_air_freight_to_charge(sqaf_record)
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
				"Air Booking - Charges Population Error"
			)
			raise
	
	def _normalize_uom_for_air_booking_charges(self, uom_value, unit_type=None):
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
	
	def _map_sales_quote_air_freight_to_charge(self, sqaf_record):
		"""Map sales_quote_air_freight record to air_shipment_charges format"""
		try:
			# Get the item details
			item_doc = frappe.get_doc("Item", sqaf_record.item_code)
			
			# Get default currency
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
				quantity = flt(self.weight) or 0
			elif charge_basis == "Per m³":
				quantity = flt(self.volume) or 0
			elif charge_basis == "Per package":
				if hasattr(self, 'packages') and self.packages:
					quantity = len(self.packages)
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
			
			# Normalize UOM value to match Air Booking Charges Select field options
			normalized_uom = self._normalize_uom_for_air_booking_charges(
				sqaf_record.uom,
				sqaf_record.unit_type
			)
			
			# Map the fields
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
				"Air Booking Mapping Error"
			)
			return None
	
	@frappe.whitelist()
	def check_conversion_readiness(self):
		"""
		Check if Air Booking is ready for conversion to Air Shipment.
		
		Returns:
			dict: Status with missing_fields list and is_ready boolean
		"""
		missing_fields = []
		
		# Validate link fields that will be copied
		if self.service_level and not frappe.db.exists("Service Level Agreement", self.service_level):
			missing_fields.append({
				"field": "service_level",
				"label": "Service Level",
				"tab": "Details",
				"message": f"Service Level '{self.service_level}' does not exist"
			})
		
		if self.release_type and not frappe.db.exists("Release Type", self.release_type):
			missing_fields.append({
				"field": "release_type",
				"label": "Release Type",
				"tab": "Details",
				"message": f"Release Type '{self.release_type}' does not exist"
			})
		
		if hasattr(self, 'uld_type') and self.uld_type and not frappe.db.exists("ULD Type", self.uld_type):
			missing_fields.append({
				"field": "uld_type",
				"label": "ULD Type",
				"tab": "Details",
				"message": f"ULD Type '{self.uld_type}' does not exist"
			})
		
		# Validate ports exist as UNLOCO
		if self.origin_port and not frappe.db.exists("UNLOCO", self.origin_port):
			missing_fields.append({
				"field": "origin_port",
				"label": "Origin Port",
				"tab": "Details",
				"message": f"Origin Port '{self.origin_port}' is not a valid UNLOCO code"
			})
		
		if self.destination_port and not frappe.db.exists("UNLOCO", self.destination_port):
			missing_fields.append({
				"field": "destination_port",
				"label": "Destination Port",
				"tab": "Details",
				"message": f"Destination Port '{self.destination_port}' is not a valid UNLOCO code"
			})
		
		return {
			"is_ready": len(missing_fields) == 0,
			"missing_fields": missing_fields
		}
	
	def validate_before_conversion(self):
		"""
		Validate that all required fields are present before conversion to Air Shipment.
		
		Raises:
			frappe.ValidationError: If required fields are missing
		"""
		readiness = self.check_conversion_readiness()
		
		if not readiness["is_ready"]:
			messages = [field["message"] for field in readiness["missing_fields"]]
			frappe.throw(_("Cannot convert to Air Shipment. Missing or invalid fields:\n{0}").format("\n".join(f"- {msg}" for msg in messages)))
	
	@frappe.whitelist()
	def convert_to_shipment(self):
		"""
		Convert Air Booking to Air Shipment.
		
		Returns:
			dict: Result with created Air Shipment name and status
		"""
		try:
			# Validate before conversion
			self.validate_before_conversion()
			
			# Create new Air Shipment
			air_shipment = frappe.new_doc("Air Shipment")
			
			# Map basic fields from Air Booking to Air Shipment
			air_shipment.local_customer = self.local_customer
			air_shipment.booking_date = self.booking_date or today()
			# Note: air_booking field doesn't exist in Air Shipment, so we skip it
			air_shipment.sales_quote = self.sales_quote
			air_shipment.shipper = self.shipper
			air_shipment.consignee = self.consignee
			air_shipment.origin_port = self.origin_port
			air_shipment.destination_port = self.destination_port  # Both now use UNLOCO
			air_shipment.direction = self.direction
			air_shipment.weight = self.weight
			air_shipment.volume = self.volume
			air_shipment.chargeable = self.chargeable
			# Only copy service_level if it exists as a valid record
			if self.service_level and frappe.db.exists("Service Level Agreement", self.service_level):
				air_shipment.service_level = self.service_level
			else:
				# Explicitly clear the field if the record doesn't exist
				air_shipment.service_level = None
			air_shipment.incoterm = self.incoterm
			air_shipment.additional_terms = self.additional_terms
			air_shipment.airline = self.airline
			air_shipment.freight_agent = self.freight_agent
			# Only copy uld_type if it exists as a valid record
			if self.uld_type and frappe.db.exists("ULD Type", self.uld_type):
				air_shipment.uld_type = self.uld_type
			else:
				# Explicitly clear the field if the record doesn't exist
				air_shipment.uld_type = None
			air_shipment.house_type = self.house_type
			# Only copy release_type if it exists as a valid record
			if self.release_type and frappe.db.exists("Release Type", self.release_type):
				air_shipment.release_type = self.release_type
			else:
				# Explicitly clear the field if the record doesn't exist
				air_shipment.release_type = None
			air_shipment.entry_type = self.entry_type  # Both now have same options
			air_shipment.house_bl = self.house_bl
			air_shipment.packs = self.packs
			air_shipment.inner = self.inner
			air_shipment.goods_value = self.goods_value  # Both now use goods_value
			air_shipment.insurance = self.insurance
			air_shipment.description = self.description
			air_shipment.marks_and_nos = self.marks_and_nos
			air_shipment.etd = self.etd
			air_shipment.eta = self.eta
			air_shipment.company = self.company
			air_shipment.branch = self.branch
			air_shipment.cost_center = self.cost_center
			air_shipment.profit_center = self.profit_center
			
			# Copy packages if they exist (from Air Booking Packages to Air Shipment Packages)
			if hasattr(self, 'packages') and self.packages:
				for package in self.packages:
					air_shipment.append("packages", {
						"commodity": package.commodity,
						"hs_code": package.hs_code,
						"reference_no": package.reference_no,
						"goods_description": package.goods_description,
						"no_of_packs": package.no_of_packs,
						"uom": package.uom,
						"weight": package.weight,
						"volume": package.volume
					})
			
			# Copy charges (from Air Booking Charges to Air Shipment Charges)
			if hasattr(self, 'charges') and self.charges:
				for charge in self.charges:
					air_shipment.append("charges", {
						"item_code": charge.item_code,
						"item_name": charge.item_name,
						"charge_type": charge.charge_type,
						"charge_category": charge.charge_category,
						"description": charge.description,
						"charge_basis": charge.charge_basis,
						"rate": charge.rate,
						"currency": charge.currency,
						"quantity": charge.quantity,
						"unit_of_measure": charge.unit_of_measure,
						"calculation_method": charge.calculation_method,
						"discount_percentage": charge.discount_percentage,
						"base_amount": charge.base_amount,
						"discount_amount": charge.discount_amount,
						"tax_amount": charge.tax_amount,
						"surcharge_amount": charge.surcharge_amount,
						"total_amount": charge.total_amount,
						"billing_status": charge.billing_status,
						"invoice_reference": charge.invoice_reference
					})
			
			# Final validation check before insert - ensure all link fields are valid
			# This prevents errors during insert/after_insert hooks
			if hasattr(air_shipment, 'service_level') and air_shipment.service_level:
				if not frappe.db.exists("Service Level Agreement", air_shipment.service_level):
					air_shipment.service_level = None
			if hasattr(air_shipment, 'release_type') and air_shipment.release_type:
				if not frappe.db.exists("Release Type", air_shipment.release_type):
					air_shipment.release_type = None
			
			# Insert the Air Shipment
			try:
				air_shipment.insert(ignore_permissions=True)
			except (frappe.ValidationError, frappe.LinkValidationError) as e:
				# If validation fails due to invalid link fields, clear them and try again
				if "Could not find" in str(e) or "Invalid link" in str(e) or isinstance(e, frappe.LinkValidationError):
					# Clear potentially invalid link fields
					if hasattr(air_shipment, 'service_level') and air_shipment.service_level:
						if not frappe.db.exists("Service Level Agreement", air_shipment.service_level):
							air_shipment.service_level = None
					if hasattr(air_shipment, 'release_type') and air_shipment.release_type:
						if not frappe.db.exists("Release Type", air_shipment.release_type):
							air_shipment.release_type = None
					# Try insert again
					air_shipment.insert(ignore_permissions=True)
				else:
					raise
			
			# Save the Air Shipment (after_insert may have already saved it, but we save again to be sure)
			try:
				air_shipment.save(ignore_permissions=True)
			except (frappe.ValidationError, frappe.LinkValidationError) as e:
				# If validation fails due to invalid link fields, clear them and try again
				if "Could not find" in str(e) or "Invalid link" in str(e) or isinstance(e, frappe.LinkValidationError):
					# Clear potentially invalid link fields
					if hasattr(air_shipment, 'service_level') and air_shipment.service_level:
						if not frappe.db.exists("Service Level Agreement", air_shipment.service_level):
							air_shipment.service_level = None
					if hasattr(air_shipment, 'release_type') and air_shipment.release_type:
						if not frappe.db.exists("Release Type", air_shipment.release_type):
							air_shipment.release_type = None
					# Try save again
					air_shipment.save(ignore_permissions=True)
				else:
					raise
			
			frappe.msgprint(
				_("Air Shipment {0} created successfully from Air Booking {1}").format(air_shipment.name, self.name),
				title=_("Air Shipment Created"),
				indicator="green"
			)
			
			return {
				"success": True,
				"message": _("Air Shipment {0} created successfully").format(air_shipment.name),
				"air_shipment": air_shipment.name
			}
			
		except Exception as e:
			frappe.log_error(
				f"Error converting Air Booking {self.name} to Air Shipment: {str(e)}",
				"Air Booking - Convert to Shipment Error"
			)
			frappe.throw(_("Error converting to shipment: {0}").format(str(e)))

