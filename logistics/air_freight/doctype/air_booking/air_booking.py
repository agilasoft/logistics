# Copyright (c) 2025, logistics.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, flt
from frappe.contacts.doctype.address.address import get_address_display
from typing import Dict, Any


def _sync_quote_and_sales_quote(doc):
	"""Sync quote_type/quote with sales_quote for backward compatibility."""
	if getattr(doc, "quote_type", None) == "Sales Quote" and getattr(doc, "quote", None):
		doc.sales_quote = doc.quote
	elif getattr(doc, "quote_type", None) == "One-Off Quote":
		doc.sales_quote = None
	elif not getattr(doc, "quote_type", None) and getattr(doc, "sales_quote", None):
		doc.quote_type = "Sales Quote"
		doc.quote = doc.sales_quote


def _normalize_packing_group_for_shipment(value):
	"""Air Shipment Packages.packing_group is Select I/II/III; only pass allowed values."""
	if value is None:
		return None
	s = (value or "").strip()
	if s in ("", "I", "II", "III"):
		return s
	return None


class AirBooking(Document):
	def validate(self):
		"""Validate Air Booking data"""
		from logistics.utils.module_integration import set_billing_company_from_sales_quote
		set_billing_company_from_sales_quote(self)
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
		
		# Validate quote field when quote_type is One-Off Quote (quote might reference Sales Quote)
		if getattr(self, "quote_type", None) == "One-Off Quote" and getattr(self, "quote", None):
			# Check if quote is a Sales Quote (new system) and validate it
			if frappe.db.exists("Sales Quote", self.quote):
				from logistics.pricing_center.doctype.sales_quote.sales_quote import validate_one_off_quote_not_converted
				validate_one_off_quote_not_converted(self.quote, self.doctype, self.name)
		
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
		
		self.validate_required_fields()
		self.validate_dates()
		self.validate_accounts()
		try:
			from logistics.utils.measurements import apply_measurement_uom_conversion_to_children
			apply_measurement_uom_conversion_to_children(self, "packages", company=getattr(self, "company", None))
		except Exception:
			pass
		# Aggregate package volumes and weights to header (with UOM conversion) unless overridden
		if not getattr(self, "override_volume_weight", False):
			self.aggregate_volume_from_packages()
			self.aggregate_weight_from_packages()
		# Always calculate chargeable weight (even if volume/weight are 0)
		self.calculate_chargeable_weight()
		# Validate weight is greater than 0
		weight = flt(self.weight) if hasattr(self, 'weight') and self.weight is not None else 0
		if weight <= 0:
			frappe.throw(_("Weight must be greater than 0 before submitting Air Booking"))
		# Validate volume is not less than 0
		volume = flt(self.volume) if hasattr(self, 'volume') and self.volume is not None else 0
		if volume < 0:
			frappe.throw(_("Volume cannot be less than 0 for Air Booking"))
		self._update_packing_summary()
	
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
		
		# Validate entry_type if set (industry standard: Direct, Transit, Transshipment, ATA Carnet)
		if self.entry_type:
			valid_entry_types = ["Direct", "Transit", "Transshipment", "ATA Carnet"]
			if self.entry_type not in valid_entry_types:
				frappe.throw(_(
					"Entry Type cannot be \"{0}\". It should be one of \"{1}\""
				).format(
					self.entry_type,
					"\", \"".join(valid_entry_types)
				))
	
	def validate_dates(self):
		"""Validate date logic"""
		from frappe.utils import getdate
		
		# Validate ETD is not after ETA (allows same-day shipments)
		if self.etd and self.eta:
			if getdate(self.etd) > getdate(self.eta):
				frappe.throw(_("ETD (Estimated Time of Departure) must be on or before ETA (Estimated Time of Arrival)"))
	
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

	def after_insert(self):
		"""Commit so the new document is visible when the client navigates to the form (avoids 'Air Booking ... not found').
		Without this, the next request (form load after redirect) may not see the row if the transaction is not yet committed."""
		frappe.db.commit()
		# Verify the doc is visible (helps diagnose read-replica lag if it is not)
		if not frappe.db.exists(self.doctype, self.name):
			frappe.log_error(
				f"Air Booking {self.name} not visible after commit in after_insert. Check DB replication if using read replicas.",
				"Air Booking after_insert visibility",
			)

	def before_submit(self):
		"""Validate packages and required dates before submitting the Air Booking."""
		# Validate quote is not empty
		quote_type = getattr(self, "quote_type", None)
		has_quote = False
		
		if quote_type == "Sales Quote":
			has_quote = bool(self.sales_quote)
		elif quote_type == "One-Off Quote":
			has_quote = bool(getattr(self, "quote", None))
		else:
			# If quote_type is not set, check sales_quote (backward compatibility)
			has_quote = bool(self.sales_quote)
		
		if not has_quote:
			frappe.throw(_("Quote is required. Please select a quote before submitting the Air Booking."))
		
		# Validate charges is not empty
		charges = getattr(self, 'charges', []) or []
		if not charges:
			frappe.throw(_("Charges are required. Please add at least one charge before submitting the Air Booking."))
		
		# Validate packages is not empty
		packages = getattr(self, 'packages', []) or []
		if not packages:
			frappe.throw(_("Packages are required. Please add at least one package before submitting the Air Booking."))
		
		# Validate ETD is required
		if not self.etd:
			frappe.throw(_("ETD (Estimated Time of Departure) is required before submitting the Air Booking."))
		
		# Validate ETA is required
		if not self.eta:
			frappe.throw(_("ETA (Estimated Time of Arrival) is required before submitting the Air Booking."))
	
	def aggregate_volume_from_packages(self):
		"""Set header volume from sum of package volumes, converted to base/default volume UOM (used for chargeable weight)."""
		if getattr(self, "override_volume_weight", False):
			return
		packages = getattr(self, "packages", []) or []
		if not packages:
			if hasattr(self, "volume"):
				self.volume = 0
			return
		try:
			from logistics.utils.measurements import convert_volume, get_aggregation_volume_uom, get_default_uoms
			target_volume_uom = get_aggregation_volume_uom(company=getattr(self, "company", None))
			if not target_volume_uom:
				# Set volume to 0 explicitly instead of leaving it unchanged
				if hasattr(self, "volume"):
					self.volume = 0
				# Log error so users know there's a configuration issue
				frappe.log_error(
					f"Volume aggregation skipped for Air Booking {self.name}: "
					f"Target volume UOM not configured in Logistics Settings. "
					f"Please set 'Base Volume UOM' or 'Default Volume UOM' in Logistics Settings.",
					"Air Booking - Missing Target Volume UOM"
				)
				return
			defaults = get_default_uoms(company=getattr(self, "company", None))
			target_normalized = str(target_volume_uom).strip().upper()
			total = 0
			for pkg in packages:
				pkg_vol = flt(getattr(pkg, "volume", 0) or 0)
				if pkg_vol <= 0:
					continue
				pkg_volume_uom = getattr(pkg, "volume_uom", None) or defaults.get("volume")
				if not pkg_volume_uom:
					continue
				if str(pkg_volume_uom).strip().upper() == target_normalized:
					total += pkg_vol
				else:
					total += convert_volume(
						pkg_vol,
						from_uom=pkg_volume_uom,
						to_uom=target_volume_uom,
						company=getattr(self, "company", None),
					)
			# Always set volume, even if 0
			self.volume = total if total > 0 else 0
		except Exception as e:
			# Log error but still set volume to 0 to ensure field is set
			frappe.log_error(
				f"Error aggregating volume from packages for Air Booking {self.name}: {str(e)}",
				"Air Booking - Volume Aggregation Error"
			)
			self.volume = 0
	
	def aggregate_weight_from_packages(self):
		"""Set header weight from sum of package weights, converted to base/default weight UOM."""
		if getattr(self, "override_volume_weight", False):
			return
		packages = getattr(self, "packages", []) or []
		if not packages:
			if hasattr(self, "weight"):
				self.weight = 0
			return
		try:
			from logistics.utils.measurements import convert_weight, get_default_uoms
			defaults = get_default_uoms(company=getattr(self, "company", None))
			target_weight_uom = defaults.get("weight")  # Typically "Kg"
			if not target_weight_uom:
				return
			target_normalized = str(target_weight_uom).strip().upper()
			total = 0
			for pkg in packages:
				pkg_weight = flt(getattr(pkg, "weight", 0) or 0)
				if pkg_weight <= 0:
					continue
				pkg_weight_uom = getattr(pkg, "weight_uom", None) or defaults.get("weight")
				if not pkg_weight_uom:
					continue
				if str(pkg_weight_uom).strip().upper() == target_normalized:
					total += pkg_weight
				else:
					total += convert_weight(
						pkg_weight,
						from_uom=pkg_weight_uom,
						to_uom=target_weight_uom,
						company=getattr(self, "company", None),
					)
			# Always set weight, even if 0
			self.weight = total if total > 0 else 0
		except Exception as e:
			# Log error but still set weight to 0 to ensure field is set
			frappe.log_error(
				f"Error aggregating weight from packages for Air Booking {self.name}: {str(e)}",
				"Air Booking - Weight Aggregation Error"
			)
			self.weight = 0
	
	@frappe.whitelist()
	def aggregate_volume_from_packages_api(self):
		"""Whitelisted API method to aggregate volume and weight from packages for client-side calls."""
		self.aggregate_volume_from_packages()
		self.aggregate_weight_from_packages()
		self._update_packing_summary()
		self.calculate_chargeable_weight()
		return {
			"total_volume": getattr(self, "total_volume", None) or getattr(self, "volume", None),
			"total_weight": getattr(self, "total_weight", None) or getattr(self, "weight", None),
			"chargeable": self.chargeable
		}

	@frappe.whitelist()
	def recalculate_package_volumes_api(self):
		"""Recalculate volume for each package from dimensions (Dimension Volume UOM Conversion). Returns list of {name, volume} for client to apply."""
		from logistics.utils.measurements import calculate_volume_from_dimensions, get_default_uoms

		packages = getattr(self, "packages", []) or []
		company = getattr(self, "company", None)
		defaults = get_default_uoms(company=company) if company else {}
		result = []
		for pkg in packages:
			name = pkg.get("name") or getattr(pkg, "name", None)
			if not name:
				continue
			length = flt(pkg.get("length") or getattr(pkg, "length", 0))
			width = flt(pkg.get("width") or getattr(pkg, "width", 0))
			height = flt(pkg.get("height") or getattr(pkg, "height", 0))
			dimension_uom = pkg.get("dimension_uom") or getattr(pkg, "dimension_uom", None) or defaults.get("dimension")
			volume_uom = pkg.get("volume_uom") or getattr(pkg, "volume_uom", None) or defaults.get("volume")
			if not dimension_uom or not volume_uom:
				result.append({"name": name, "volume": 0})
				continue
			if length <= 0 or width <= 0 or height <= 0:
				result.append({"name": name, "volume": 0})
				continue
			try:
				vol = calculate_volume_from_dimensions(
					length=length, width=width, height=height,
					dimension_uom=dimension_uom, volume_uom=volume_uom, company=company
				)
				result.append({"name": name, "volume": vol})
			except Exception:
				result.append({"name": name, "volume": 0})
		return result

	def calculate_chargeable_weight(self):
		"""Calculate chargeable weight based on volume and weight"""
		# Check if both volume and weight are None/not set (not just 0)
		# We need to calculate even if one is 0, as long as the other has a value
		volume_is_none = getattr(self, "volume", None) is None
		weight_is_none = getattr(self, "weight", None) is None
		if volume_is_none and weight_is_none:
			# Both are None - nothing to calculate
			if hasattr(self, "chargeable"):
				self.chargeable = 0
			return
		
		# Get volume to weight divisor
		divisor = self.get_volume_to_weight_divisor()
		
		# Validate divisor is positive
		if divisor <= 0:
			IATA_DIVISOR = 1000000.0 / 167.0  # IATA standard: exactly 167 kg/m³
			frappe.log_error(
				f"Invalid divisor ({divisor}) for Air Booking {self.name}. Using IATA standard {IATA_DIVISOR:.2f}.",
				"Air Booking - Invalid Divisor"
			)
			divisor = IATA_DIVISOR  # Default to IATA standard
		
		# Get and validate volume and weight
		volume = flt(self.volume or 0)
		weight = flt(self.weight or 0)
		
		# Validate non-negative values
		if volume < 0:
			frappe.log_error(
				f"Negative volume ({volume}) for Air Booking {self.name}. Setting to 0.",
				"Air Booking - Negative Volume"
			)
			volume = 0
		
		if weight < 0:
			frappe.log_error(
				f"Negative weight ({weight}) for Air Booking {self.name}. Setting to 0.",
				"Air Booking - Negative Weight"
			)
			weight = 0
		
		# Calculate volume weight
		volume_weight = 0
		if volume > 0 and divisor > 0:
			# Convert volume from m³ to cm³, then divide by divisor
			# Volume in m³ * 1,000,000 cm³/m³ / divisor = volume weight in kg
			volume_weight = volume * (1000000.0 / divisor)
		
		# Calculate chargeable weight (higher of actual weight or volume weight)
		if weight > 0 and volume_weight > 0:
			self.chargeable = max(weight, volume_weight)
		elif weight > 0:
			self.chargeable = weight
		elif volume_weight > 0:
			self.chargeable = volume_weight
		else:
			self.chargeable = 0

	def _update_packing_summary(self):
		"""Update total_packages, total_volume, total_weight from packages."""
		packages = getattr(self, "packages", []) or []
		self.total_packages = sum(flt(getattr(p, "no_of_packs", 0) or 0) for p in packages)
		self.total_volume = flt(self.volume) if self.volume else 0
		self.total_weight = flt(self.weight) if self.weight else 0
	
	def get_volume_to_weight_divisor(self):
		"""Get the volume to weight divisor based on factor type and airline settings"""
		# IATA standard: 167 kg/m³
		# Divisor calculation: 1,000,000 cm³ / 167 kg = 5988.02 (exactly 1,000,000 / 167)
		IATA_DIVISOR = 1000000.0 / 167.0  # = 5988.023952095808, gives exactly 167 kg/m³
		
		# Default to IATA standard
		divisor = IATA_DIVISOR
		
		# Get factor type (default to IATA if not set)
		factor_type = self.volume_to_weight_factor_type or "IATA"
		
		if factor_type == "IATA":
			# IATA standard: divisor that gives exactly 167 kg/m³
			divisor = IATA_DIVISOR
		elif factor_type == "Custom":
			# Check if custom divisor is overridden on Air Booking
			if self.custom_volume_to_weight_divisor:
				divisor = flt(self.custom_volume_to_weight_divisor)
				# Validate divisor is positive
				if divisor <= 0:
					frappe.log_error(
						f"Invalid custom divisor ({divisor}) on Air Booking {self.name}. Using IATA standard {IATA_DIVISOR:.2f}.",
						"Air Booking - Invalid Custom Divisor"
					)
					divisor = IATA_DIVISOR
			# Otherwise, get from Airline
			elif self.airline:
				airline_divisor = frappe.db.get_value("Airline", self.airline, "volume_to_weight_divisor")
				if airline_divisor:
					divisor = flt(airline_divisor)
					# Validate divisor is positive
					if divisor <= 0:
						frappe.log_error(
							f"Invalid airline divisor ({divisor}) for Airline {self.airline}. Using IATA standard {IATA_DIVISOR:.2f}.",
							"Air Booking - Invalid Airline Divisor"
						)
						divisor = IATA_DIVISOR
				else:
					# Default to IATA if airline doesn't have a divisor set
					divisor = IATA_DIVISOR
			else:
				# Default to IATA if no airline selected
				divisor = IATA_DIVISOR
		
		return divisor
	
	def _map_sales_quote_entry_type_to_air_booking(self, sales_quote_entry_type):
		"""
		Validate and return entry type. Options are aligned across Sales Quote and Air Booking.
		Unified options (industry standard): Direct, Transit, Transshipment, ATA Carnet
		"""
		if not sales_quote_entry_type:
			return None
		valid = ["Direct", "Transit", "Transshipment", "ATA Carnet"]
		return sales_quote_entry_type if sales_quote_entry_type in valid else None
	
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
			
			# Set flag to skip on_change handler to prevent it from interfering with charge population
			# This flag prevents on_change from clearing/populating charges when fields are modified
			self.flags.skip_sales_quote_on_change = True
			# Also set a flag to indicate we're fetching quotations (for JavaScript to know not to trigger handlers)
			self.flags.fetching_quotations = True
			
			# Check if Sales Quote has air charges (new structure) or air freight (legacy)
			air_charge_count = frappe.db.count("Sales Quote Charge", {
				"parent": self.sales_quote,
				"parenttype": "Sales Quote",
				"service_type": "Air"
			})
			air_freight_count = frappe.db.count("Sales Quote Air Freight", {
				"parent": self.sales_quote,
				"parenttype": "Sales Quote"
			}) if frappe.db.table_exists("Sales Quote Air Freight") else 0
			if air_charge_count == 0 and air_freight_count == 0:
				frappe.msgprint(
					_("No Air Freight lines found in Sales Quote {0}. Only basic fields will be populated.").format(self.sales_quote),
					indicator="orange"
				)
			
			# Get Sales Quote fields using get_value to avoid loading child tables
			sales_quote_data = frappe.db.get_value("Sales Quote", self.sales_quote, [
				"customer", "shipper", "consignee", "location_from", "location_to",
				"air_direction", "weight", "volume", "chargeable",
				"service_level", "incoterm", "additional_terms", "airline",
				"tc_name", "terms",
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
			# Normalize legacy house_type values
			if self.house_type == "Direct":
				self.house_type = "Standard House"
			elif self.house_type == "Consolidation":
				self.house_type = "Co-load Master"
			if not self.release_type:
				self.release_type = sales_quote_data.get("air_release_type")
			if not self.entry_type:
				sales_quote_entry_type = sales_quote_data.get("air_entry_type")
				if sales_quote_entry_type:
					mapped_entry_type = self._map_sales_quote_entry_type_to_air_booking(sales_quote_entry_type)
					if mapped_entry_type:
						self.entry_type = mapped_entry_type
			if not self.etd:
				self.etd = sales_quote_data.get("air_etd")
			if not self.eta:
				self.eta = sales_quote_data.get("air_eta")
			if not self.house_awb:
				self.house_awb = sales_quote_data.get("air_house_bl")
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
			if not self.tc_name:
				self.tc_name = sales_quote_data.get("tc_name")
			if not self.terms:
				self.terms = sales_quote_data.get("terms")
			
			# Sync quote_type and quote with sales_quote to prevent them from being cleared on reload
			# This ensures the quotation fields stay in sync after fetch_quotations
			if self.sales_quote:
				self.quote_type = "Sales Quote"
				self.quote = self.sales_quote
			
			# Populate charges from Sales Quote Charge (Air) or Sales Quote Air Freight (legacy)
			air_charge_count = frappe.db.count("Sales Quote Charge", {
				"parent": self.sales_quote,
				"parenttype": "Sales Quote",
				"service_type": "Air"
			})
			air_freight_count = frappe.db.count("Sales Quote Air Freight", {
				"parent": self.sales_quote,
				"parenttype": "Sales Quote"
			}) if frappe.db.table_exists("Sales Quote Air Freight") else 0
			charges_count = 0
			if air_charge_count > 0 or air_freight_count > 0:
				# Pass the sales quote name instead of loading the full document to avoid SQL errors
				charges_count = self._populate_charges_from_sales_quote(self.sales_quote)
			
			# Log all calculation_methods before normalization
			if hasattr(self, 'charges') and self.charges:
				frappe.logger().info(
					f"[Air Booking] fetch_quotations: BEFORE _normalize_charges_before_save() - "
					f"Found {len(self.charges)} charge(s)"
				)
				for idx, charge in enumerate(self.charges):
					calc_method = getattr(charge, 'revenue_calculation_method', None)
					item_code = getattr(charge, 'item_code', 'Unknown')
					frappe.logger().info(
						f"[Air Booking] fetch_quotations: Charge {idx+1}/{len(self.charges)} BEFORE normalization - "
						f"item_code: {item_code}, calculation_method: '{calc_method}'"
					)
			
			# Normalize all charges before save to prevent _validate_selects() errors
			# This ensures calculation_method values like "Per m³" are converted to "Per Unit" with proper UOM
			self._normalize_charges_before_save()
			
			# Log all calculation_methods after normalization and before save
			if hasattr(self, 'charges') and self.charges:
				frappe.logger().info(
					f"[Air Booking] fetch_quotations: AFTER _normalize_charges_before_save(), BEFORE save() - "
					f"Found {len(self.charges)} charge(s)"
				)
				for idx, charge in enumerate(self.charges):
					calc_method = getattr(charge, 'revenue_calculation_method', None)
					item_code = getattr(charge, 'item_code', 'Unknown')
					frappe.logger().info(
						f"[Air Booking] fetch_quotations: Charge {idx+1}/{len(self.charges)} BEFORE save() - "
						f"item_code: {item_code}, calculation_method: '{calc_method}'"
					)
					# Validate it's in the valid list
					valid_calc_methods = [
						"Per Unit", "Fixed Amount", "Flat Rate", "Base Plus Additional",
						"First Plus Additional", "Percentage", "Location-based", "Weight Break", "Qty Break"
					]
					if calc_method not in valid_calc_methods:
						frappe.log_error(
							f"CRITICAL: Charge for item {item_code} has invalid calculation_method '{calc_method}' "
							f"BEFORE save(). This will cause _validate_selects() error!",
							"Air Booking - Invalid Calculation Method Before Save"
						)
			
			# Save the document to persist the changes (charges and other fields)
			# This ensures charges are saved before the form reloads
			# Keep the flag set during save to prevent on_change from running
			frappe.logger().info(
				f"[Air Booking] fetch_quotations: About to call save() for Air Booking {self.name}"
			)
			self.save(ignore_permissions=True)
			frappe.logger().info(
				f"[Air Booking] fetch_quotations: save() completed successfully for Air Booking {self.name}"
			)
			
			# Clear the flags after charge population and save
			self.flags.skip_sales_quote_on_change = False
			self.flags.fetching_quotations = False
			
			# Build message based on charges fetched
			if charges_count > 0:
				message = _("Quotations fetched successfully from Sales Quote {0}. {1} charge(s) populated.").format(
					self.sales_quote, charges_count
				)
				indicator = "green"
			elif air_charge_count > 0 or air_freight_count > 0:
				message = _("Quotations fetched successfully from Sales Quote {0} but no charges could be mapped. Please check the Sales Quote Air charges.").format(
					self.sales_quote
				)
				indicator = "orange"
			else:
				message = _("Quotations fetched successfully from Sales Quote {0} but no charges fetched (no Air charges found in Sales Quote).").format(
					self.sales_quote
				)
				indicator = "orange"
			
			frappe.msgprint(
				message,
				title=_("Success"),
				indicator=indicator
			)
			
			return {
				"success": True,
				"message": message,
				"charges_count": charges_count
			}
			
		except Exception as e:
			# Clear the flags even on error
			self.flags.skip_sales_quote_on_change = False
			self.flags.fetching_quotations = False
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
			
			# Get records from Sales Quote Charge (service_type=Air) or Sales Quote Air Freight (legacy)
			charge_fields = [
				"item_code", "item_name", "calculation_method", "uom", "currency",
				"unit_rate", "unit_type", "minimum_quantity", "minimum_charge",
				"maximum_charge", "base_amount", "estimated_revenue", "charge_type", "bill_to"
			]
			sales_quote_air_freight_records = frappe.get_all(
				"Sales Quote Charge",
				filters={"parent": sq_name, "parenttype": "Sales Quote", "service_type": "Air"},
				fields=charge_fields,
				order_by="idx"
			)
			if not sales_quote_air_freight_records and frappe.db.table_exists("Sales Quote Air Freight"):
				sales_quote_air_freight_records = frappe.get_all(
					"Sales Quote Air Freight",
					filters={"parent": sq_name, "parenttype": "Sales Quote"},
					fields=charge_fields,
					order_by="idx"
				)
			
			# Normalize calculation_method values in fetched records before processing
			valid_calc_methods = [
				"Per Unit", "Fixed Amount", "Flat Rate", "Base Plus Additional",
				"First Plus Additional", "Percentage", "Location-based", "Weight Break", "Qty Break"
			]
			for sqaf_record in sales_quote_air_freight_records:
				if sqaf_record.get("calculation_method"):
					original = sqaf_record["calculation_method"]
					# Quick normalization check - if it contains invalid patterns, normalize it
					method_str = str(original).strip()
					method_lower = method_str.lower()
					invalid_patterns = ["m³", "m^3", "m3", "per m³", "per m3", "per kg", "per package", "per shipment"]
					if any(pattern in method_lower for pattern in invalid_patterns) or method_str not in valid_calc_methods:
						if "per" in method_lower and any(unit in method_lower for unit in ["m3", "kg", "kilogram", "package", "shipment", "piece"]):
							sqaf_record['calculation_method'] = "Per Unit"
							frappe.logger().info(
								f"[Air Booking] Normalized calculation_method in fetched record: '{original}' → 'Per Unit' "
								f"for item {sqaf_record.get('item_code', 'Unknown')}"
							)
						elif method_str not in valid_calc_methods:
							sqaf_record['calculation_method'] = "Per Unit"
							frappe.logger().info(
								f"[Air Booking] Normalized invalid calculation_method in fetched record: '{original}' → 'Per Unit' "
								f"for item {sqaf_record.get('item_code', 'Unknown')}"
							)
			
			# Log all calculation_methods from Sales Quote Air Freight records
			frappe.logger().info(
				f"[Air Booking] _populate_charges_from_sales_quote: Found {len(sales_quote_air_freight_records)} Sales Quote Air Freight records"
			)
			for idx, sqaf_record in enumerate(sales_quote_air_freight_records):
				frappe.logger().info(
					f"[Air Booking] _populate_charges_from_sales_quote: Record {idx+1}/{len(sales_quote_air_freight_records)} - "
					f"item_code: {sqaf_record.get('item_code', 'N/A')}, "
					f"calculation_method: '{sqaf_record.get('calculation_method', 'N/A')}', "
					f"unit_type: {sqaf_record.get('unit_type', 'N/A')}, "
					f"uom: {sqaf_record.get('uom', 'N/A')}"
				)
			
			# Map and populate charges
			charges_added = 0
			errors = []
			for sqaf_record in sales_quote_air_freight_records:
				try:
					item_code = sqaf_record.get('item_code', 'Unknown')
					original_calc_method = sqaf_record.get('calculation_method', 'N/A')
					frappe.logger().info(
						f"[Air Booking] _populate_charges_from_sales_quote: Mapping charge for item {item_code}, "
						f"original calculation_method: '{original_calc_method}'"
					)
					charge_row = self._map_sales_quote_air_freight_to_charge(sqaf_record)
					if charge_row:
						mapped_calc_method = charge_row.get('revenue_calculation_method', 'N/A')
						frappe.logger().info(
							f"[Air Booking] _populate_charges_from_sales_quote: Successfully mapped charge for item {item_code}, "
							f"mapped calculation_method: '{mapped_calc_method}'"
						)
						
						# Final safety check: ensure calculation_method is valid before appending
						valid_calc_methods = [
							"Per Unit", "Fixed Amount", "Flat Rate", "Base Plus Additional",
							"First Plus Additional", "Percentage", "Location-based", "Weight Break", "Qty Break"
						]
						if mapped_calc_method not in valid_calc_methods:
							frappe.log_error(
								f"CRITICAL: charge_row has invalid calculation_method '{mapped_calc_method}' "
								f"for item {item_code} before append(). Forcing to 'Per Unit'.",
								"Air Booking - Invalid Calculation Method in charge_row"
							)
							charge_row['revenue_calculation_method'] = "Per Unit"
							mapped_calc_method = "Per Unit"
							frappe.logger().info(
								f"[Air Booking] _populate_charges_from_sales_quote: Fixed invalid calculation_method, "
								f"now: '{mapped_calc_method}' for item {item_code}"
							)
						
						self.append("charges", charge_row)
						
						# Verify the appended charge has correct calculation_method
						last_charge = self.charges[-1] if self.charges else None
						if last_charge:
							appended_calc_method = getattr(last_charge, 'revenue_calculation_method', None)
							frappe.logger().info(
								f"[Air Booking] _populate_charges_from_sales_quote: After append(), "
								f"charge calculation_method: '{appended_calc_method}' for item {item_code}"
							)
							if appended_calc_method not in valid_calc_methods:
								frappe.log_error(
									f"CRITICAL: Appended charge has invalid calculation_method '{appended_calc_method}' "
									f"for item {item_code}. This will cause _validate_selects() error!",
									"Air Booking - Invalid Calculation Method After Append"
								)
								# Force fix it
								last_charge.revenue_calculation_method = "Per Unit"
								frappe.logger().info(
									f"[Air Booking] _populate_charges_from_sales_quote: Fixed appended charge, "
									f"calculation_method now: 'Per Unit' for item {item_code}"
								)
						
						charges_added += 1
					else:
						errors.append(f"Failed to map charge for item {sqaf_record.get('item_code', 'Unknown')}")
				except Exception as e:
					item_code = sqaf_record.get('item_code', 'Unknown')
					error_msg = f"Error mapping charge for item {item_code}: {str(e)}"
					errors.append(error_msg)
					frappe.log_error(error_msg, "Air Booking - Charge Mapping Error")
			
			# Log any errors but don't fail the entire operation
			if errors:
				frappe.log_error(
					f"Some charges failed to populate:\n" + "\n".join(errors),
					"Air Booking - Charges Population Warnings"
				)
			
			# Return count of charges added (don't show message here, let fetch_quotations handle it)
			return charges_added
			
		except Exception as e:
			frappe.log_error(
				f"Error populating charges from Sales Quote: {str(e)}",
				"Air Booking - Charges Population Error"
			)
			raise
	
	def _extract_uom_from_calculation_method(self, calculation_method):
		"""
		Extract UOM from calculation_method values like "Per m³", "Per kg", etc.
		
		Args:
			calculation_method: Calculation method string that may contain UOM (e.g., "Per m³", "Per kg")
		
		Returns:
			Extracted UOM value (e.g., "m³", "kg") or None if no UOM found
		"""
		if not calculation_method:
			return None
		
		calc_method_lower = str(calculation_method).lower().strip()
		
		# Map of patterns to UOM values
		uom_patterns = {
			"m³": "m³",
			"m3": "m³",
			"m^3": "m³",
			"cbm": "m³",
			"cubic meter": "m³",
			"kg": "kg",
			"kilogram": "kg",
			"kilograms": "kg",
			"kgs": "kg",
			"package": "package",
			"packages": "package",
			"pkg": "package",
			"pkgs": "package",
			"piece": "package",
			"pieces": "package",
			"pc": "package",
			"pcs": "package",
			"shipment": "shipment",
			"shipments": "shipment",
		}
		
		# Check for "per [unit]" pattern
		if "per" in calc_method_lower:
			# Extract the part after "per"
			parts = calc_method_lower.split("per", 1)
			if len(parts) > 1:
				unit_part = parts[1].strip()
				# Check against known patterns
				for pattern, uom in uom_patterns.items():
					if pattern in unit_part:
						return uom
		
		return None
	
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
	
	def _normalize_charges_before_save(self):
		"""
		Normalize all charges before save() to prevent _validate_selects() errors.
		Converts calculation_method values like "Per m³" to "Per Unit" with proper UOM.
		"""
		if not hasattr(self, 'charges') or not self.charges:
			return
		
		frappe.logger().info(
			f"[Air Booking] _normalize_charges_before_save: START - Processing {len(self.charges)} charge(s)"
		)
		
		# Log all calculation_methods before normalization
		for idx, charge in enumerate(self.charges):
			calc_method = getattr(charge, 'revenue_calculation_method', None)
			item_code = getattr(charge, 'item_code', 'Unknown')
			frappe.logger().info(
				f"[Air Booking] _normalize_charges_before_save: Charge {idx+1}/{len(self.charges)} - "
				f"item_code: {item_code}, calculation_method BEFORE normalization: '{calc_method}'"
			)
		
		valid_calc_methods = [
			"Per Unit", "Fixed Amount", "Flat Rate", "Base Plus Additional",
			"First Plus Additional", "Percentage", "Location-based", "Weight Break", "Qty Break"
		]
		
		normalized_count = 0
		for charge in self.charges:
			original_calc_method = getattr(charge, 'revenue_calculation_method', None)
			item_code = getattr(charge, 'item_code', 'Unknown')
			if not original_calc_method:
				frappe.logger().info(
					f"[Air Booking] _normalize_charges_before_save: Charge for item {item_code} has no calculation_method, skipping"
				)
				continue
			
			# Check if calculation_method is invalid
			if original_calc_method not in valid_calc_methods:
				frappe.logger().info(
					f"[Air Booking] _normalize_charges_before_save: Found invalid calculation_method '{original_calc_method}' "
					f"for item {item_code}, will normalize to 'Per Unit'"
				)
				# Extract UOM from calculation_method if present
				extracted_uom = self._extract_uom_from_calculation_method(original_calc_method)
				
				# Convert to "Per Unit"
				charge.revenue_calculation_method = "Per Unit"
				
				# Set UOM if extracted and not already set
				current_uom = getattr(charge, 'unit_of_measure', None) or getattr(charge, 'uom', None)
				if extracted_uom and not current_uom:
					# Normalize the extracted UOM
					normalized_extracted_uom = self._normalize_uom_for_air_booking_charges(extracted_uom)
					if normalized_extracted_uom:
						if hasattr(charge, 'unit_of_measure'):
							charge.unit_of_measure = normalized_extracted_uom
						if hasattr(charge, 'uom'):
							charge.uom = normalized_extracted_uom
						
						frappe.logger().info(
							f"[Air Booking] Normalized charge: calculation_method '{original_calc_method}' → 'Per Unit', "
							f"UOM set to '{normalized_extracted_uom}' for item {getattr(charge, 'item_code', 'Unknown')}"
						)
				
				normalized_count += 1
				final_calc_method = getattr(charge, 'revenue_calculation_method', None)
				frappe.logger().info(
					f"[Air Booking] _normalize_charges_before_save: Normalized calculation_method '{original_calc_method}' → '{final_calc_method}' "
					f"for charge item {item_code}"
				)
		
		# Log all calculation_methods after normalization
		for idx, charge in enumerate(self.charges):
			calc_method = getattr(charge, 'revenue_calculation_method', None)
			item_code = getattr(charge, 'item_code', 'Unknown')
			frappe.logger().info(
				f"[Air Booking] _normalize_charges_before_save: Charge {idx+1}/{len(self.charges)} - "
				f"item_code: {item_code}, calculation_method AFTER normalization: '{calc_method}'"
			)
		
		if normalized_count > 0:
			frappe.logger().info(
				f"[Air Booking] _normalize_charges_before_save: COMPLETE - Normalized {normalized_count} charge(s) before save() to prevent _validate_selects() errors"
			)
		else:
			frappe.logger().info(
				f"[Air Booking] _normalize_charges_before_save: COMPLETE - No charges needed normalization"
			)
	
	def _map_sales_quote_air_freight_to_charge(self, sqaf_record):
		"""Map sales_quote_air_freight record to air_shipment_charges format"""
		try:
			# Validate item_code is present
			if not sqaf_record.get("item_code"):
				frappe.log_error(
					f"Missing item_code in Sales Quote Air Freight record",
					"Air Booking - Missing Item Code"
				)
				return None
			
			# Get the item details
			if not frappe.db.exists("Item", sqaf_record.item_code):
				frappe.log_error(
					f"Item {sqaf_record.item_code} does not exist",
					"Air Booking - Invalid Item Code"
				)
				return None
			
			item_doc = frappe.get_doc("Item", sqaf_record.item_code)
			
			# Get default currency
			default_currency = frappe.get_system_settings("currency") or "USD"
			
			# Get quantity based on unit_type
			quantity = 0
			unit_type = sqaf_record.get("unit_type")
			if unit_type == "Weight":
				quantity = flt(self.weight) or 0
			elif unit_type == "Volume":
				quantity = flt(self.volume) or 0
			elif unit_type in ["Package", "Piece"]:
				if hasattr(self, 'packages') and self.packages:
					quantity = len(self.packages)
				else:
					quantity = 1
			elif unit_type == "Shipment":
				quantity = 1
			elif not unit_type:
				# Default quantity for fixed/flat rate charges
				quantity = 1
			
			# Determine charge_type: first from Sales Quote Air Freight record, then from item, then default
			charge_type = "Revenue"
			# First check if charge_type is set in the Sales Quote Air Freight record
			if hasattr(sqaf_record, 'charge_type') and sqaf_record.charge_type:
				charge_type = sqaf_record.charge_type
			# Fall back to item's custom_charge_type if not set in Sales Quote Air Freight
			elif hasattr(item_doc, 'custom_charge_type') and item_doc.custom_charge_type:
				charge_type = item_doc.custom_charge_type
			
			# Determine charge_category from item or use default
			charge_category = "Other"
			if hasattr(item_doc, 'custom_charge_category'):
				charge_category = item_doc.custom_charge_category or "Other"
			
			# Get the original calculation_method from Sales Quote Air Freight
			sqaf_calc_method = (sqaf_record.get("calculation_method") or "").strip()
			item_code = sqaf_record.get('item_code', 'Unknown')
			
			# Define valid calculation methods for Air Booking Charges
			valid_calc_methods = [
				"Per Unit", "Fixed Amount", "Flat Rate", "Base Plus Additional",
				"First Plus Additional", "Percentage", "Location-based", "Weight Break", "Qty Break"
			]
			
			# STEP 1: Extract UOM from calculation_method if it contains unit strings
			# This handles cases like "Per m³", "Per kg", "Per package", "Per shipment"
			extracted_uom_from_calc_method = None
			if sqaf_calc_method:
				extracted_uom_from_calc_method = self._extract_uom_from_calculation_method(sqaf_calc_method)
			
			# STEP 2: Normalize calculation_method - convert any "Per [unit]" pattern to "Per Unit"
			# This ensures calculation_method never contains unit strings
			calculation_method = sqaf_calc_method
			if sqaf_calc_method:
				# Normalize for comparison (handle special characters like m³)
				calc_method_lower = sqaf_calc_method.lower().strip()
				calc_method_normalized = calc_method_lower.replace("m³", "m3").replace("m^3", "m3")
				
				# Check for "Per [unit]" patterns that should be converted to "Per Unit"
				unit_patterns = ["m³", "m3", "m^3", "kg", "kilogram", "package", "packages", 
				                 "pkg", "pkgs", "piece", "pieces", "pc", "pcs", "shipment", "shipments"]
				
				# If calculation_method contains "per" followed by any unit, convert to "Per Unit"
				if "per" in calc_method_normalized and any(unit in calc_method_normalized for unit in unit_patterns):
					# Log the conversion for debugging
					if sqaf_calc_method not in valid_calc_methods:
						frappe.logger().info(
							f"[Air Booking] _map_sales_quote_air_freight_to_charge: Normalizing calculation_method "
							f"'{sqaf_calc_method}' → 'Per Unit' for item {item_code}. "
							f"Extracted UOM: {extracted_uom_from_calc_method or 'None'}"
						)
						frappe.log_error(
							f"Sales Quote Air Freight record has calculation_method '{sqaf_calc_method}' "
							f"containing unit string for item {item_code}. This should be fixed in the Sales Quote. "
							f"Converting to 'Per Unit' and moving unit to UOM field. Extracted UOM: {extracted_uom_from_calc_method or 'None'}",
							"Air Booking - Calculation Method with Unit String"
						)
					calculation_method = "Per Unit"
				# If it's already a valid method, keep it
				elif sqaf_calc_method in valid_calc_methods:
					calculation_method = sqaf_calc_method
				# Handle case-insensitive matching for valid method variations
				else:
					calc_method_normalized_lower = calc_method_normalized
					if calc_method_normalized_lower in ["per unit", "perunit"]:
						calculation_method = "Per Unit"
					elif calc_method_normalized_lower in ["fixed amount", "fixedamount"]:
						calculation_method = "Fixed Amount"
					elif calc_method_normalized_lower in ["flat rate", "flatrate"]:
						calculation_method = "Flat Rate"
					elif calc_method_normalized_lower in ["base plus additional", "baseplusadditional"]:
						calculation_method = "Base Plus Additional"
					elif calc_method_normalized_lower in ["first plus additional", "firstplusadditional"]:
						calculation_method = "First Plus Additional"
					elif calc_method_normalized_lower in ["percentage"]:
						calculation_method = "Percentage"
					elif calc_method_normalized_lower in ["location-based", "locationbased"]:
						calculation_method = "Location-based"
					elif calc_method_normalized_lower in ["weight break", "weightbreak"]:
						calculation_method = "Weight Break"
					elif calc_method_normalized_lower in ["qty break", "qtybreak", "quantity break", "quantitybreak"]:
						calculation_method = "Qty Break"
					elif calc_method_normalized_lower in ["automatic", "manual"]:
						calculation_method = "Per Unit"
						frappe.log_error(
							f"Sales Quote Air Freight calculation_method '{sqaf_calc_method}' is deprecated. "
							f"Converting to 'Per Unit' for item {item_code}.",
							"Air Booking - Deprecated Calculation Method"
						)
					else:
						# Default to "Per Unit" if unit_type is set, otherwise "Flat Rate"
						if sqaf_record.get("unit_type"):
							calculation_method = "Per Unit"
						else:
							calculation_method = "Flat Rate"
						frappe.log_error(
							f"Sales Quote Air Freight calculation_method '{sqaf_calc_method}' could not be mapped. "
							f"Using default '{calculation_method}' for item {item_code}.",
							"Air Booking - Unmapped Calculation Method"
						)
			
			# Final validation: ensure calculation_method is always valid
			if calculation_method not in valid_calc_methods:
				frappe.log_error(
					f"CRITICAL: calculation_method '{calculation_method}' is not in valid list after normalization. "
					f"Original value was '{sqaf_calc_method}'. Item: {item_code}. Forcing to 'Per Unit'.",
					"Air Booking - Critical Calculation Method Validation Failure"
				)
				calculation_method = "Per Unit"
			
			# STEP 3: Normalize UOM value using _normalize_uom_for_air_booking_charges()
			# Priority: extracted UOM from calculation_method > record UOM > unit_type inference
			normalized_uom = None
			
			# First, try to use UOM extracted from calculation_method
			if extracted_uom_from_calc_method:
				normalized_uom = self._normalize_uom_for_air_booking_charges(
					extracted_uom_from_calc_method,
					sqaf_record.unit_type
				)
				frappe.logger().info(
					f"[Air Booking] _map_sales_quote_air_freight_to_charge: Using UOM extracted from calculation_method "
					f"'{sqaf_calc_method}': '{extracted_uom_from_calc_method}' → '{normalized_uom}' for item {item_code}"
				)
			
			# If no UOM was extracted from calculation_method, try the record's UOM field
			if not normalized_uom and sqaf_record.get("uom"):
				normalized_uom = self._normalize_uom_for_air_booking_charges(
					sqaf_record.uom,
					sqaf_record.unit_type
				)
			
			# If still no UOM, infer from unit_type
			if not normalized_uom:
				normalized_uom = self._normalize_uom_for_air_booking_charges(
					None,
					sqaf_record.unit_type
				)
			
			# Log final values
			frappe.logger().info(
				f"[Air Booking] _map_sales_quote_air_freight_to_charge: FINAL values for item {item_code} - "
				f"calculation_method: '{calculation_method}' (original: '{sqaf_calc_method}'), uom: '{normalized_uom}'"
			)
			
			# Map the fields
			charge_data = {
				"item_code": sqaf_record.item_code,
				"item_name": sqaf_record.item_name or item_doc.item_name,
				"charge_type": charge_type,
				"charge_category": charge_category,
				"revenue_calculation_method": calculation_method,
				"rate": sqaf_record.unit_rate or 0,
				"currency": sqaf_record.currency or default_currency,
				"quantity": quantity,
				"unit_of_measure": normalized_uom,
				"revenue_calculation_method": calculation_method,
				"billing_status": "To Bill",
				"bill_to": getattr(sqaf_record, "bill_to", None),
			}
			
			# Add minimum/maximum charge if available
			if sqaf_record.minimum_charge:
				charge_data["minimum_charge"] = sqaf_record.minimum_charge
			if sqaf_record.maximum_charge:
				charge_data["maximum_charge"] = sqaf_record.maximum_charge
			
			# Log the final charge_data calculation_method
			frappe.logger().info(
				f"[Air Booking] _map_sales_quote_air_freight_to_charge: RETURNING charge_data with calculation_method: "
				f"'{charge_data.get('revenue_calculation_method', 'N/A')}' for item {item_code}"
			)
			
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
		# Check if both quote and charges are empty
		quote_type = getattr(self, "quote_type", None)
		has_quote = False
		
		if quote_type == "Sales Quote":
			has_quote = bool(self.sales_quote)
		elif quote_type == "One-Off Quote":
			has_quote = bool(getattr(self, "quote", None))
		else:
			# If quote_type is not set, check sales_quote (backward compatibility)
			has_quote = bool(self.sales_quote)
		
		has_charges = bool(hasattr(self, 'charges') and self.charges and len(self.charges) > 0)
		
		if not has_quote and not has_charges:
			frappe.throw(_("Cannot convert to Air Shipment. Either a Quote or Charges must be present."))
		
		readiness = self.check_conversion_readiness()
		
		if not readiness["is_ready"]:
			messages = [field["message"] for field in readiness["missing_fields"]]
			frappe.throw(_("Cannot convert to Air Shipment. Missing or invalid fields:\n{0}").format("\n".join(f"- {msg}" for msg in messages)))
	
	@frappe.whitelist()
	def convert_to_shipment(self):
		"""
		Convert Air Booking to Air Shipment.
		
		Enforces 1:1 relationship - one Air Booking can only have one Air Shipment.
		
		Returns:
			dict: Result with created Air Shipment name and status
		"""
		try:
			# Check if Air Shipment already exists for this Air Booking (1:1 relationship)
			existing_shipment = frappe.db.get_value("Air Shipment", {"air_booking": self.name}, "name")
			if existing_shipment:
				frappe.throw(_(
					"Air Shipment {0} already exists for this Air Booking. "
					"One Air Booking can only have one Air Shipment."
				).format(existing_shipment))
			
			# Validate volume is greater than 0 before conversion
			volume = flt(self.volume) if hasattr(self, 'volume') and self.volume is not None else 0
			if volume <= 0:
				frappe.throw(_("Volume must be greater than 0 before converting to Air Shipment"))
			
			# Validate before conversion
			self.validate_before_conversion()
			
			# Create new Air Shipment
			air_shipment = frappe.new_doc("Air Shipment")
			
			# Map basic fields from Air Booking to Air Shipment
			air_shipment.local_customer = self.local_customer
			air_shipment.booking_date = self.booking_date or today()
			air_shipment.air_booking = self.name
			air_shipment.sales_quote = self.sales_quote
			air_shipment.shipper = self.shipper
			air_shipment.consignee = self.consignee
			if hasattr(self, "sending_agent") and self.sending_agent:
				air_shipment.sending_agent = self.sending_agent
			if hasattr(self, "receiving_agent") and self.receiving_agent:
				air_shipment.receiving_agent = self.receiving_agent
			if hasattr(self, "broker") and self.broker:
				air_shipment.broker = self.broker

			# Copy address and contact from Booking if set, otherwise populate from Shipper/Consignee
			if hasattr(self, "shipper_address") and self.shipper_address:
				air_shipment.shipper_address = self.shipper_address
			if hasattr(self, "shipper_address_display") and self.shipper_address_display:
				air_shipment.shipper_address_display = self.shipper_address_display
			if hasattr(self, "consignee_address") and self.consignee_address:
				air_shipment.consignee_address = self.consignee_address
			if hasattr(self, "consignee_address_display") and self.consignee_address_display:
				air_shipment.consignee_address_display = self.consignee_address_display
			if hasattr(self, "shipper_contact") and self.shipper_contact:
				air_shipment.shipper_contact = self.shipper_contact
			if hasattr(self, "shipper_contact_display") and self.shipper_contact_display:
				air_shipment.shipper_contact_display = self.shipper_contact_display
			if hasattr(self, "consignee_contact") and self.consignee_contact:
				air_shipment.consignee_contact = self.consignee_contact
			if hasattr(self, "consignee_contact_display") and self.consignee_contact_display:
				air_shipment.consignee_contact_display = self.consignee_contact_display
			if hasattr(self, "notify_party") and self.notify_party:
				air_shipment.notify_party = self.notify_party
			if hasattr(self, "notify_party_address") and self.notify_party_address:
				air_shipment.notify_party_address = self.notify_party_address
			# Populate addresses and contacts from Shipper/Consignee primary if not set on Booking
			if self.shipper and (not air_shipment.shipper_address or not air_shipment.shipper_contact):
				try:
					shipper_doc = frappe.get_doc("Shipper", self.shipper)
					# Populate shipper address if not already set from Booking (pick_address preferred for transport)
					shipper_addr = getattr(shipper_doc, 'pick_address', None) or getattr(shipper_doc, 'shipper_primary_address', None)
					if not air_shipment.shipper_address and shipper_addr:
						air_shipment.shipper_address = shipper_addr
						air_shipment.shipper_address_display = get_address_display(shipper_addr)
					# Populate shipper contact if not already set from Booking
					if not air_shipment.shipper_contact and hasattr(shipper_doc, 'shipper_primary_contact') and shipper_doc.shipper_primary_contact:
						air_shipment.shipper_contact = shipper_doc.shipper_primary_contact
						# Populate contact display field
						try:
							contact_doc = frappe.get_doc("Contact", shipper_doc.shipper_primary_contact)
							contact_parts = []
							if contact_doc.first_name or contact_doc.last_name:
								contact_parts.append(" ".join(filter(None, [contact_doc.first_name, contact_doc.last_name])))
							if contact_doc.designation:
								contact_parts.append(contact_doc.designation)
							if contact_doc.phone:
								contact_parts.append(contact_doc.phone)
							if contact_doc.mobile_no:
								contact_parts.append(contact_doc.mobile_no)
							if contact_doc.email_id:
								contact_parts.append(contact_doc.email_id)
							air_shipment.shipper_contact_display = "\n".join(contact_parts)
						except Exception:
							pass
				except Exception as e:
					frappe.log_error(f"Error fetching shipper address/contact: {str(e)}", "Air Booking - Convert to Shipment")
			
			if self.consignee and (not air_shipment.consignee_address or not air_shipment.consignee_contact):
				try:
					consignee_doc = frappe.get_doc("Consignee", self.consignee)
					# Populate consignee address if not already set from Booking (delivery_address preferred for transport)
					consignee_addr = getattr(consignee_doc, 'delivery_address', None) or getattr(consignee_doc, 'consignee_primary_address', None)
					if not air_shipment.consignee_address and consignee_addr:
						air_shipment.consignee_address = consignee_addr
						air_shipment.consignee_address_display = get_address_display(consignee_addr)
					# Populate consignee contact if not already set from Booking
					if not air_shipment.consignee_contact and hasattr(consignee_doc, 'consignee_primary_contact') and consignee_doc.consignee_primary_contact:
						air_shipment.consignee_contact = consignee_doc.consignee_primary_contact
						# Populate contact display field
						try:
							contact_doc = frappe.get_doc("Contact", consignee_doc.consignee_primary_contact)
							contact_parts = []
							if contact_doc.first_name or contact_doc.last_name:
								contact_parts.append(" ".join(filter(None, [contact_doc.first_name, contact_doc.last_name])))
							if contact_doc.designation:
								contact_parts.append(contact_doc.designation)
							if contact_doc.phone:
								contact_parts.append(contact_doc.phone)
							if contact_doc.mobile_no:
								contact_parts.append(contact_doc.mobile_no)
							if contact_doc.email_id:
								contact_parts.append(contact_doc.email_id)
							air_shipment.consignee_contact_display = "\n".join(contact_parts)
						except Exception:
							pass
				except Exception as e:
					frappe.log_error(f"Error fetching consignee address/contact: {str(e)}", "Air Booking - Convert to Shipment")
			
			air_shipment.origin_port = self.origin_port
			air_shipment.destination_port = self.destination_port  # Both now use UNLOCO
			air_shipment.direction = self.direction
			air_shipment.total_weight = getattr(self, "total_weight", None) or getattr(self, "weight", None)
			air_shipment.total_volume = getattr(self, "total_volume", None) or getattr(self, "volume", None)
			air_shipment.chargeable = self.chargeable
			air_shipment.etd = self.etd
			air_shipment.eta = self.eta
			if hasattr(self, "atd") and self.atd:
				air_shipment.atd = self.atd
			if hasattr(self, "ata") and self.ata:
				air_shipment.ata = self.ata
			# Only copy service_level if it exists as a valid record
			if self.service_level and frappe.db.exists("Logistics Service Level", self.service_level):
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
			# Normalize legacy house_type values
			if air_shipment.house_type == "Direct":
				air_shipment.house_type = "Standard House"
			elif air_shipment.house_type == "Consolidation":
				air_shipment.house_type = "Co-load Master"
			# Only copy release_type if it exists as a valid record
			if self.release_type and frappe.db.exists("Release Type", self.release_type):
				air_shipment.release_type = self.release_type
			else:
				# Explicitly clear the field if the record doesn't exist
				air_shipment.release_type = None
			air_shipment.entry_type = self.entry_type  # Both now have same options
			air_shipment.house_awb = self.house_awb
			air_shipment.packs = self.packs
			air_shipment.inner = self.inner
			air_shipment.goods_value = self.goods_value  # Both now use goods_value
			air_shipment.insurance = self.insurance
			air_shipment.description = self.description
			air_shipment.marks_and_nos = self.marks_and_nos
			air_shipment.company = self.company
			air_shipment.branch = self.branch
			air_shipment.cost_center = self.cost_center
			air_shipment.profit_center = self.profit_center
			# Copy measurement override and costing fields
			if hasattr(self, "override_volume_weight"):
				air_shipment.override_volume_weight = self.override_volume_weight or 0
			if hasattr(self, "project") and self.project:
				air_shipment.project = self.project
			if hasattr(self, "job_costing_number") and self.job_costing_number:
				air_shipment.job_costing_number = self.job_costing_number
			# Copy DG fields
			if hasattr(self, "contains_dangerous_goods"):
				air_shipment.contains_dangerous_goods = self.contains_dangerous_goods or 0
			if hasattr(self, "dg_declaration_complete"):
				air_shipment.dg_declaration_complete = self.dg_declaration_complete or 0
			if hasattr(self, "dg_compliance_status"):
				air_shipment.dg_compliance_status = self.dg_compliance_status
			if hasattr(self, "dg_emergency_contact"):
				air_shipment.dg_emergency_contact = self.dg_emergency_contact
			if hasattr(self, "dg_emergency_phone"):
				air_shipment.dg_emergency_phone = self.dg_emergency_phone
			if hasattr(self, "dg_emergency_email"):
				air_shipment.dg_emergency_email = self.dg_emergency_email
			# Copy notes and terms
			if hasattr(self, "tc_name") and self.tc_name:
				air_shipment.tc_name = self.tc_name
			if hasattr(self, "terms") and self.terms:
				air_shipment.terms = self.terms
			if hasattr(self, "internal_notes") and self.internal_notes:
				air_shipment.internal_notes = self.internal_notes
			if hasattr(self, "client_notes") and self.client_notes:
				air_shipment.client_notes = self.client_notes
			
			# Copy document_list_template if set
			if hasattr(self, "document_list_template") and self.document_list_template:
				air_shipment.document_list_template = self.document_list_template
			
			# Copy milestone_template and milestones (from Air Booking Milestone to Air Shipment Milestone)
			if hasattr(self, "milestone_template") and self.milestone_template:
				air_shipment.milestone_template = self.milestone_template
			if hasattr(self, "milestones") and self.milestones:
				for m in self.milestones:
					air_shipment.append("milestones", {
						"milestone": getattr(m, "milestone", None),
						"status": getattr(m, "status", None),
						"planned_start": getattr(m, "planned_start", None),
						"planned_end": getattr(m, "planned_end", None),
						"actual_start": getattr(m, "actual_start", None),
						"actual_end": getattr(m, "actual_end", None),
						"source": getattr(m, "source", None),
						"fetched_at": getattr(m, "fetched_at", None),
					})
			
			# Copy documents if they exist (from Air Booking Documents to Air Shipment Documents)
			if hasattr(self, 'documents') and self.documents:
				# Get valid fields from Job Document meta
				doc_meta = frappe.get_meta("Job Document")
				doc_fields = {f.fieldname for f in doc_meta.fields if f.fieldtype not in ("Section Break", "Column Break", "Tab Break")}
				for doc_row in self.documents:
					shipment_doc = air_shipment.append("documents", {})
					# Copy all valid fields from booking document to shipment document
					for field in doc_fields:
						if hasattr(doc_row, field):
							val = getattr(doc_row, field, None)
							if val is not None and field not in ("name", "owner", "creation", "modified", "modified_by", "parent", "parenttype", "parentfield", "idx"):
								shipment_doc.set(field, val)
			
			# Copy packages if they exist (from Air Booking Packages to Air Shipment Packages)
			if hasattr(self, 'packages') and self.packages:
				for package in self.packages:
					air_shipment.append("packages", {
						"commodity": getattr(package, "commodity", None),
						"hs_code": getattr(package, "hs_code", None),
						"reference_no": getattr(package, "reference_no", None),
						"goods_description": getattr(package, "goods_description", None),
						"no_of_packs": getattr(package, "no_of_packs", None),
						"uom": getattr(package, "uom", None),
						"weight": getattr(package, "weight", None),
						"volume": getattr(package, "volume", None),
						"dimension_uom": getattr(package, "dimension_uom", None),
						"length": getattr(package, "length", None),
						"width": getattr(package, "width", None),
						"height": getattr(package, "height", None),
						"volume_uom": getattr(package, "volume_uom", None),
						"weight_uom": getattr(package, "weight_uom", None),
						# Dangerous goods package fields (so shipment validation passes when booking has DG data)
						"dg_substance": getattr(package, "dg_substance", None),
						"un_number": getattr(package, "un_number", None),
						"proper_shipping_name": getattr(package, "proper_shipping_name", None),
						"dg_class": getattr(package, "dg_class", None),
						"packing_group": _normalize_packing_group_for_shipment(getattr(package, "packing_group", None)),
						"emergency_contact_name": getattr(package, "emergency_contact_name", None),
						"emergency_contact_phone": getattr(package, "emergency_contact_phone", None),
					})
			
			# Copy charges (from Air Booking Charges to Air Shipment Charges)
			if hasattr(self, 'charges') and self.charges:
				for charge in self.charges:
					# Safely get UOM - AirBookingCharges may use 'unit_of_measure' but AirShipmentCharges uses 'uom'
					# Use getattr to safely access attributes that may not exist in the schema
					uom_value = getattr(charge, 'unit_of_measure', None) or getattr(charge, 'uom', None)
					
					air_shipment.append("charges", {
						"item_code": getattr(charge, 'item_code', None),
						"item_name": getattr(charge, 'item_name', None),
						"charge_type": getattr(charge, 'charge_type', None),
						"charge_category": getattr(charge, 'charge_category', None),
						"description": getattr(charge, 'description', None),
						"revenue_calculation_method": getattr(charge, 'revenue_calculation_method', None),
						"rate": getattr(charge, 'rate', None),
						"currency": getattr(charge, 'currency', None),
						"quantity": getattr(charge, 'quantity', None),
						"uom": uom_value,  # AirShipmentCharges uses 'uom', not 'unit_of_measure'
						"discount_percentage": getattr(charge, 'discount_percentage', None),
						"base_amount": getattr(charge, 'base_amount', None),
						"discount_amount": getattr(charge, 'discount_amount', None),
						"tax_amount": getattr(charge, 'tax_amount', None),
						"surcharge_amount": getattr(charge, 'surcharge_amount', None),
						"total_amount": getattr(charge, 'total_amount', None),
						"billing_status": getattr(charge, 'billing_status', None),
						"invoice_reference": getattr(charge, 'invoice_reference', None),
						"bill_to": getattr(charge, 'bill_to', None),
						"pay_to": getattr(charge, 'pay_to', None),
					})
			
			# Copy routing legs (from Air Booking Routing Leg to Air Shipment Routing Leg)
			# Note: Order is determined by idx (automatically set by Frappe), not leg_order
			if hasattr(self, 'routing_legs') and self.routing_legs:
				for leg in self.routing_legs:
					air_shipment.append("routing_legs", {
						"mode": getattr(leg, 'mode', None),
						"type": getattr(leg, 'type', None),
						"status": getattr(leg, 'status', None),
						"charter_route": getattr(leg, 'charter_route', None),
						"notes": getattr(leg, 'notes', None),
						"vessel": getattr(leg, 'vessel', None),
						"voyage_no": getattr(leg, 'voyage_no', None),
						"shipping_line": getattr(leg, 'shipping_line', None),
						"flight_no": getattr(leg, 'flight_no', None),
						"airline": getattr(leg, 'airline', None),
						"load_port": getattr(leg, 'load_port', None),
						"etd": getattr(leg, 'etd', None),
						"atd": getattr(leg, 'atd', None),
						"discharge_port": getattr(leg, 'discharge_port', None),
						"eta": getattr(leg, 'eta', None),
						"ata": getattr(leg, 'ata', None)
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
			
			# Ensure commit before client navigates (avoids "not found" on form load)
			frappe.db.commit()
			
			# Populate documents from template
			try:
				from logistics.document_management.api import populate_documents_from_template
				populate_documents_from_template("Air Shipment", air_shipment.name)
			except Exception as e:
				# Log error but don't fail the conversion
				frappe.log_error(
					f"Error populating documents for Air Shipment {air_shipment.name}: {str(e)}",
					"Air Booking - Populate Documents Error"
				)
			
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
	
	def after_submit(self):
		"""Update One-off Sales Quote status to Converted when Air Booking is submitted."""
		if self.sales_quote:
			from logistics.pricing_center.doctype.sales_quote.sales_quote import update_one_off_quote_on_submit
			update_one_off_quote_on_submit(self.sales_quote, self.name, self.doctype)

	@frappe.whitelist()
	def get_dashboard_html(self):
		"""Generate HTML for Dashboard tab: Run Sheet layout with map, milestones."""
		try:
			from logistics.document_management.api import get_document_alerts_html, get_dashboard_alerts_html
			from logistics.document_management.dashboard_layout import (
				build_run_sheet_style_dashboard,
				build_map_segments_from_routing_legs,
				get_dg_dashboard_html,
				get_unloco_coords,
			)

			status = "Submitted" if self.docstatus == 1 else "Cancelled" if self.docstatus == 2 else "Draft"
			header_items = [
				("Status", status),
				("ETD", str(self.etd) if self.etd else "—"),
				("ETA", str(self.eta) if self.eta else "—"),
				("Packages", str(len(self.packages or []))),
				("Weight", frappe.format_value(self.total_weight or 0, df=dict(fieldtype="Float"))),
			]
			if getattr(self, "airline", None):
				header_items.append(("Airline", self.airline))

			try:
				doc_alerts = get_document_alerts_html("Air Booking", self.name or "new")
			except Exception:
				doc_alerts = ""

			dg_route_below_html = get_dg_dashboard_html(self)

			milestone_rows = list(self.get("milestones") or [])
			milestone_details = {}
			if milestone_rows:
				names = [m.milestone for m in milestone_rows if m.milestone]
				if names:
					for lm in frappe.get_all("Logistics Milestone", filters={"name": ["in", names]}, fields=["name", "description"]):
						milestone_details[lm.name] = lm.description or lm.name

			cards_html = ""
			for i, m in enumerate(milestone_rows, 1):
				st = (m.status or "Planned").lower().replace(" ", "-")
				desc = milestone_details.get(m.milestone, m.milestone or "Milestone")
				planned = frappe.utils.format_datetime(m.planned_end) if m.planned_end else "—"
				actual = frappe.utils.format_datetime(m.actual_end) if m.actual_end else "—"
				cards_html += f"""
				<div class="dash-card {st}">
					<div class="card-header"><h5>{desc}</h5><span class="card-num">#{i}</span></div>
					<div class="card-details">Planned: {planned}<br>Actual: {actual}</div>
					<span class="card-badge {st}">{m.status or "Planned"}</span>
				</div>"""

			map_segments = build_map_segments_from_routing_legs(
				getattr(self, "routing_legs", None) or []
			)
			map_points = []
			if not map_segments:
				o = get_unloco_coords(self.origin_port)
				d = get_unloco_coords(self.destination_port)
				if o:
					map_points.append(o)
				if d and (not map_points or (d.get("lat") != map_points[-1].get("lat")) or (d.get("lon") != map_points[-1].get("lon"))):
					map_points.append(d)

			alerts_html = get_dashboard_alerts_html("Air Booking", self.name or "new")
			return build_run_sheet_style_dashboard(
				header_title=self.name or "Air Booking",
				header_subtitle="Air Booking",
				header_items=header_items,
				cards_html=cards_html or "<div class=\"text-muted\">No milestones. Use Get Milestones in Actions to generate from template.</div>",
				map_points=map_points,
				map_segments=map_segments,
				map_id_prefix="air-booking-dash-map",
				doc_alerts_html=doc_alerts,
				alerts_html=alerts_html,
				straight_line=True,
				origin_label=self.origin_port or None,
				destination_label=self.destination_port or None,
				route_below_html=dg_route_below_html,
			)
		except Exception as e:
			frappe.log_error(f"Air Booking get_dashboard_html: {str(e)}", "Air Booking Dashboard")
			return "<div class='alert alert-warning'>Error loading dashboard.</div>"

	def on_cancel(self):
		"""Reset One-off Sales Quote status when Air Booking is cancelled."""
		if self.sales_quote:
			from logistics.pricing_center.doctype.sales_quote.sales_quote import reset_one_off_quote_on_cancel
			reset_one_off_quote_on_cancel(self.sales_quote)


@frappe.whitelist()
def air_booking_exists(docname):
	"""Return True if the Air Booking exists. Used by client to poll before navigating so form load does not show 'not found'."""
	if not docname or docname == "new":
		return False
	return bool(frappe.db.exists("Air Booking", docname))


@frappe.whitelist()
def get_air_booking_dashboard_html(docname):
	"""Return dashboard HTML by docname. Catches DoesNotExistError so the client never sees 'Air Booking ... not found' when loading HTML fields."""
	if not docname or docname == "new":
		return "<div class='alert alert-info'>Save the document to view the dashboard.</div>"
	try:
		doc = frappe.get_doc("Air Booking", docname)
	except frappe.DoesNotExistError:
		return "<div class='alert alert-info'>Dashboard will load shortly. Refresh the page if it does not appear.</div>"
	return doc.get_dashboard_html()


@frappe.whitelist()
def aggregate_volume_from_packages_api(doc=None):
	"""Module-level wrapper so full-path RPC (e.g. from Air Booking Packages) can call the doc method."""
	if doc is None:
		frappe.throw(_("Document is required"))
	# Client sends doc as JSON string (Frappe request.prepare stringifies objects); parse so we load from dict, not by name
	if isinstance(doc, str):
		parsed = frappe.parse_json(doc)
		if isinstance(parsed, dict) and parsed.get("doctype"):
			doc = parsed
	try:
		booking = frappe.get_doc(doc) if isinstance(doc, dict) else frappe.get_doc("Air Booking", doc)
		return booking.aggregate_volume_from_packages_api()
	except frappe.DoesNotExistError:
		# Document not saved yet (e.g. unsaved form); return harmless fallback so UI does not show error
		return {"total_volume": None, "total_weight": None, "chargeable": None}


@frappe.whitelist()
def recalculate_all_charges(docname):
	"""Recalculate all charges based on current Air Booking data."""
	booking = frappe.get_doc("Air Booking", docname)
	if not booking.charges:
		return {"success": False, "message": _("No charges found to recalculate")}
	try:
		charges_recalculated = 0
		for charge in booking.charges:
			if hasattr(charge, "calculate_charge_amount"):
				charge.calculate_charge_amount(parent_doc=booking)
				charges_recalculated += 1
		booking.save()
		return {
			"success": True,
			"message": _("Successfully recalculated {0} charges").format(charges_recalculated),
			"charges_recalculated": charges_recalculated,
		}
	except Exception as e:
		frappe.log_error(str(e), "Air Booking - Recalculate Charges Error")
		frappe.throw(_("Error recalculating charges: {0}").format(str(e)))


@frappe.whitelist()
def get_available_one_off_quotes(air_booking_name: str = None) -> Dict[str, Any]:
	"""Get list of One-Off Quotes that are not yet linked to an Air Booking and not converted.

	Excludes One-Off Quotes that are:
	1. Already linked to another Air Booking
	2. Already converted (status = "Converted" or converted_to_doc is set)

	This prevents users from selecting quotes that have already been converted or used.
	"""
	try:
		# Get all One-Off Quotes already linked to Air Bookings (excluding current booking)
		used_quotes = frappe.get_all(
			"Air Booking",
			filters={
				"quote_type": "One-Off Quote",
				"quote": ["is", "set"],
				"name": ["!=", air_booking_name or ""]
			},
			pluck="quote"
		)

		# Get all converted One-Off Quotes (status = "Converted" or converted_to_doc is set)
		converted_quotes = frappe.get_all(
			"One-Off Quote",
			filters={
				"status": "Converted"
			},
			pluck="name"
		)

		# Also get quotes with converted_to_doc set (in case status wasn't updated)
		quotes_with_conversion = frappe.get_all(
			"One-Off Quote",
			filters={
				"converted_to_doc": ["is", "set"]
			},
			pluck="name"
		)

		# Combine all excluded quotes
		excluded_quotes = list(set(used_quotes + converted_quotes + quotes_with_conversion))

		# Return filter to exclude used and converted quotes
		filters = {}
		if excluded_quotes:
			filters["name"] = ["not in", excluded_quotes]

		# Also filter to only show One-Off Quotes that have air enabled
		def _has_field(doctype: str, fieldname: str) -> bool:
			try:
				return frappe.get_meta(doctype).has_field(fieldname)
			except Exception:
				return False

		if _has_field("Sales Quote", "main_service"):
			filters["main_service"] = "Air"

		return {"filters": filters}
	except Exception as e:
		frappe.log_error(
			f"Error getting available One-Off Quotes: {str(e)}",
			"Air Booking Quote Query Error"
		)
		return {"filters": {}}


@frappe.whitelist()
def get_available_sales_quotes(air_booking_name: str = None) -> Dict[str, Any]:
	"""Get list of Sales Quotes that are available for Air Booking.
	
	Excludes Sales Quotes that are:
	1. One-off quotes already linked to another Air Booking (via sales_quote field)
	2. One-off quotes that are converted (status = "Converted")
	
	This prevents users from selecting one-off quotes that have already been used.
	"""
	try:
		# Get all One-off Sales Quotes already linked to Air Bookings (excluding current booking)
		used_one_off_quotes = frappe.get_all(
			"Air Booking",
			filters={
				"sales_quote": ["is", "set"],
				"name": ["!=", air_booking_name or ""],
				"docstatus": ["!=", 2]  # Exclude cancelled documents
			},
			pluck="sales_quote"
		)
		
		# Filter to only One-off quotes from the used list
		if used_one_off_quotes:
			one_off_used = frappe.get_all(
				"Sales Quote",
				filters={
					"name": ["in", used_one_off_quotes],
					"quotation_type": "One-off"
				},
				pluck="name"
			)
		else:
			one_off_used = []
		
		# Get all converted One-off Sales Quotes (status = "Converted")
		converted_one_off_quotes = frappe.get_all(
			"Sales Quote",
			filters={
				"quotation_type": "One-off",
				"status": "Converted"
			},
			pluck="name"
		)
		
		# Combine all excluded one-off quotes
		excluded_one_off_quotes = list(set(one_off_used + converted_one_off_quotes))
		
		# Build filters - always require main_service = Air
		filters = {
			"main_service": "Air"
		}
		
		# Exclude used and converted one-off quotes
		# Use _or to allow:
		# - All non-One-off quotes (quotation_type != "One-off")
		# - One-off quotes that are not in the excluded list
		if excluded_one_off_quotes:
			# Structure: Show non-One-off OR (One-off that's not excluded)
			# Since we can't easily do AND within _or, we'll exclude by name
			# This means: main_service="Air" AND (quotation_type != "One-off" OR name not in excluded)
			filters["_or"] = [
				["quotation_type", "!=", "One-off"],
				["name", "not in", excluded_one_off_quotes]
			]
		else:
			# No excluded quotes, but still exclude converted one-off quotes
			filters["_or"] = [
				["quotation_type", "!=", "One-off"],
				["quotation_type", "=", "One-off", "status", "!=", "Converted"]
			]
		
		return {"filters": filters}
	except Exception as e:
		frappe.log_error(
			f"Error getting available Sales Quotes: {str(e)}",
			"Air Booking Sales Quote Query Error"
		)
		# Return basic filter on error
		return {
			"filters": {
				"main_service": "Air",
				"_or": [
					["quotation_type", "!=", "One-off"],
					["quotation_type", "=", "One-off", "status", "!=", "Converted"]
				]
			}
		}

