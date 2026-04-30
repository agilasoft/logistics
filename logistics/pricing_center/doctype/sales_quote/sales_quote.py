# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import format_date, today, flt, getdate, cint

from logistics.utils.module_integration import copy_sales_quote_fields_to_target
from logistics.utils.party_address_contact_from_masters import (
	append_transport_order_door_leg_from_party_masters,
	populate_air_sea_booking_party_fields_from_masters,
)
from logistics.utils.shipper_consignee_defaults import apply_shipper_consignee_defaults
from logistics.utils.sales_quote_validity import throw_if_sales_quote_expired_for_creation
from logistics.utils.charge_service_type import (
	canonical_charge_service_type_for_storage,
	count_sales_quote_charges_for_service,
	filter_sales_quote_charge_rows_for_operational_doc,
	sales_quote_charge_filters,
	sales_quote_charge_service_types_equal,
)
from logistics.utils.sales_quote_routing import apply_sales_quote_routing_to_booking


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


# Unit types allowed when Sales Quote customs charges are synced to Declaration Order / Declaration Charges.
# Aligned with Sales Quote Customs and other booking/order modules (Job, Trip supported).
CUSTOMS_ALLOWED_UNIT_TYPES = frozenset({
	"Weight", "Volume", "Distance", "Package", "Piece", "TEU", "Container", "Operation Time", "Job", "Trip",
})
CUSTOMS_ALLOWED_UNIT_TYPES_DISPLAY = (
	"Weight", "Volume", "Distance", "Package", "Piece", "TEU", "Container", "Operation Time", "Job", "Trip"
)


def _sq_strip_or_none(val):
	if val is None:
		return None
	s = str(val).strip()
	return s or None


def _sq_charge_row_matches_service(row, service_type_label):
	st = (
		getattr(row, "service_type", None)
		if not isinstance(row, dict)
		else row.get("service_type")
	)
	return sales_quote_charge_service_types_equal(st, service_type_label)


def _sales_quote_has_warehousing_for_contract(sales_quote):
	"""Legacy warehousing child rows or unified charges with service_type Warehousing (matches sales_quote.js + get_rates_from_sales_quote)."""
	if sales_quote.get("warehousing"):
		return True
	for row in sales_quote.get("charges") or []:
		if _sq_charge_row_matches_service(row, "Warehousing"):
			return True
	return False


def throw_if_additional_charge_sales_quote_blocks_booking_order_creation(sales_quote):
	"""Additional-charge quotes (from Change Request) bill an existing job — do not spawn new bookings or orders."""
	if not cint(getattr(sales_quote, "additional_charge", 0)):
		return
	job = _sq_strip_or_none(getattr(sales_quote, "job", None))
	jt = _sq_strip_or_none(getattr(sales_quote, "job_type", None))
	msg = _(
		"This Sales Quote is for additional charges on an existing job (Change Request). "
		"Creating a new booking or order from it is not allowed."
	)
	if job and jt:
		msg = msg + " " + _("Additional charges apply on {0} {1}.").format(jt, job)
	elif job:
		msg = msg + " " + _("Additional charges apply on job {0}.").format(job)
	frappe.throw(msg, title=_("Additional-Charge Quote"))


class SalesQuote(Document):
	def validate(self):
		"""Validate Sales Quote data"""
		self.validate_naming_series_quotation_type()
		self.clear_hidden_one_off_fields_for_non_one_off()
		self.validate_one_off_required_parameters()
		self.validate_additional_charge_job()
		self.validate_load_type_matches_service()
		self.validate_vehicle_type_load_type()
		self.validate_vehicle_type_capacity()
		self.validate_multimodal_main_job()
		self.validate_customs_unit_types()

	def clear_hidden_one_off_fields_for_non_one_off(self):
		"""Prevent link validation errors from hidden One-off fields on Regular/Project quotes."""
		if getattr(self, "quotation_type", None) == "One-off":
			return
		if getattr(self, "transport_mode", None):
			self.transport_mode = None

	def before_submit(self):
		"""Validate before submitting the document"""
		self.validate_main_service_has_charges()
		self.validate_air_sea_charge_ports_before_submit()

	def validate_air_sea_charge_ports_before_submit(self):
		"""At least one Air/Sea charge line must have Origin Port and Destination Port (row or quote-level fallbacks)."""
		doc_origin, doc_dest = self._document_level_origin_destination_for_charges()
		has_air_or_sea = False
		has_complete_corridor = False
		for row in getattr(self, "charges", None) or []:
			st = _sq_strip_or_none(getattr(row, "service_type", None))
			if canonical_charge_service_type_for_storage(st) not in ("air", "sea"):
				continue
			has_air_or_sea = True
			row_o = _sq_strip_or_none(getattr(row, "origin_port", None))
			row_d = _sq_strip_or_none(getattr(row, "destination_port", None))
			eff_o = row_o or doc_origin
			eff_d = row_d or doc_dest
			if eff_o and eff_d:
				has_complete_corridor = True
				break
		if has_air_or_sea and not has_complete_corridor:
			frappe.throw(
				_(
					"At least one Air or Sea charge line must have Origin Port and Destination Port "
					"(on that line or from the quote: Origin Port / Destination Port, or Location From / Location To). "
					"Other Air/Sea lines may leave ports blank."
				),
				title=_("Charge Ports Required"),
			)

	def _document_level_origin_destination_for_charges(self):
		"""Match booking/shipment behavior: prefer port fields, then transport locations."""
		o = _sq_strip_or_none(getattr(self, "origin_port", None))
		d = _sq_strip_or_none(getattr(self, "destination_port", None))
		if not o:
			o = _sq_strip_or_none(getattr(self, "location_from", None))
		if not d:
			d = _sq_strip_or_none(getattr(self, "location_to", None))
		return o, d

	def validate_main_service_has_charges(self):
		"""Require at least one charge line for the selected Main Service (aligned with UI create-booking logic)."""
		if getattr(self, "change_request", None):
			return
		main = getattr(self, "main_service", None)
		if not main:
			return
		if main == "Warehousing":
			if not _sales_quote_has_warehousing_for_contract(self):
				frappe.throw(
					_("Add warehousing details or at least one charge line with Service Type \"Warehousing\"."),
					title=_("Main Service Has No Charges"),
				)
			return
		charges = getattr(self, "charges", None) or []
		if not any(_sq_charge_row_matches_service(r, main) for r in charges):
			frappe.throw(
				_("Add at least one charge line with Service Type \"{0}\" (Main Service).").format(main),
				title=_("Main Service Has No Charges"),
			)

	def on_submit(self):
		"""Additional-charge quotes: push charge lines to the linked job with sales_quote_link."""
		from logistics.pricing_center.additional_charge_to_job import apply_additional_charge_sales_quote_to_job

		apply_additional_charge_sales_quote_to_job(self)

	def on_cancel(self):
		"""Remove job charge lines created from this additional-charge Sales Quote."""
		from logistics.pricing_center.additional_charge_to_job import remove_additional_charge_sales_quote_from_job

		remove_additional_charge_sales_quote_from_job(self)

	def validate_naming_series_quotation_type(self):
		"""Validate that naming_series matches quotation_type"""
		if not self.quotation_type or not self.naming_series:
			return  # Skip validation if either field is empty
		
		# Mapping of quotation_type to allowed naming_series prefixes (dot and hyphen both accepted)
		allowed_prefixes_mapping = {
			"Regular": ("SQU.", "SQU-"),
			"One-off": ("OOQ.", "OOQ-"),
			"Project": ("PQ.", "PQ-"),
		}
		
		allowed_prefixes = allowed_prefixes_mapping.get(self.quotation_type)
		if not allowed_prefixes:
			return  # Unknown quotation_type, skip validation
		
		if not any(self.naming_series.startswith(p) for p in allowed_prefixes):
			expected_example = {
				"Regular": "SQU.#########",
				"One-off": "OOQ.#####",
				"Project": "PQ.#####",
			}.get(self.quotation_type, "")
			expected_display = " / ".join(allowed_prefixes)
			frappe.throw(
				_("Naming Series '{0}' does not match Quotation Type '{1}'. Expected series starting with '{2}' (e.g., {3}).").format(
					self.naming_series,
					self.quotation_type,
					expected_display,
					expected_example,
				),
				title=_("Naming Series Mismatch"),
			)

	def validate_additional_charge_job(self):
		"""When Additional Charge is checked, Job Type and Job are required."""
		if getattr(self, "additional_charge", 0):
			if not getattr(self, "job_type", None) or not getattr(self, "job", None):
				frappe.throw(_("For Additional Charge quotes, Job Type and Job are required."))

	def validate_one_off_required_parameters(self):
		"""Require core parameters for One-off quotes based on service."""
		if getattr(self, "quotation_type", None) != "One-off":
			return

		# Additional-charge quotes are linked to an existing job and should not
		# require full one-off routing parameters to be created.
		if getattr(self, "additional_charge", 0):
			return

		main_service = getattr(self, "main_service", None)

		# Air and Sea flows depend on origin/destination ports.
		if main_service in ("Air", "Sea"):
			missing_fields = []
			if not getattr(self, "origin_port", None):
				missing_fields.append(_("Origin Port"))
			if not getattr(self, "destination_port", None):
				missing_fields.append(_("Destination Port"))
			if missing_fields:
				frappe.throw(
					_("For One-off {0} quotes, these fields are required: {1}.").format(
						main_service,
						", ".join(missing_fields),
					)
				)

		# Transport flow depends on concrete pickup/drop details.
		if main_service == "Transport":
			missing_fields = []
			if not getattr(self, "location_type", None):
				missing_fields.append(_("Location Type"))
			if not getattr(self, "location_from", None):
				missing_fields.append(_("Location From"))
			if not getattr(self, "location_to", None):
				missing_fields.append(_("Location To"))
			if missing_fields:
				frappe.throw(
					_("For One-off Transport quotes, these fields are required: {0}.").format(
						", ".join(missing_fields),
					)
				)

	def validate_multimodal_main_job(self):
		"""When multimodal routing legs exist, require at least one Main Job."""
		legs = getattr(self, "routing_legs", None) or []
		if not legs:
			return
		main_count = sum(1 for r in legs if getattr(r, "is_main_job", 0))
		if main_count == 0:
			frappe.throw(_("Multimodal routing requires at least one Main Job. Please check 'Main Job' on one or more legs."))

	def validate_load_type_matches_service(self):
		"""Load Type must have the checkbox for the current service mode enabled (air/sea/transport/customs/warehousing).

		A Load Type may have several mode flags set; validation only checks that the flag matching the charge's
		service_type (or one-off main_service) is enabled—not that other flags are off.
		"""
		service_to_field = {
			"air": "air",
			"sea": "sea",
			"transport": "transport",
			"custom": "customs",
			"warehousing": "warehousing",
		}

		def _check(load_type_name, service_label, field_name, context):
			if not load_type_name or not field_name:
				return
			if not frappe.db.exists("Load Type", load_type_name):
				return
			if not frappe.db.get_value("Load Type", load_type_name, field_name):
				frappe.throw(
					_("Load Type '{0}' is not valid for {1}. Select a Load Type with '{2}' enabled.").format(
						load_type_name,
						context,
						service_label,
					),
					title=_("Invalid Load Type"),
				)

		if getattr(self, "quotation_type", None) == "One-off" and not getattr(self, "additional_charge", 0):
			main = getattr(self, "main_service", None)
			lt = getattr(self, "load_type", None)
			main_c = canonical_charge_service_type_for_storage(main)
			field = service_to_field.get(main_c)
			if lt and field:
				_check(lt, main, field, _("this quote's Main Service"))

		for row in getattr(self, "charges", None) or []:
			st = getattr(row, "service_type", None)
			lt = getattr(row, "load_type", None)
			st_c = canonical_charge_service_type_for_storage(st)
			field = service_to_field.get(st_c)
			if lt and field:
				_check(lt, st, field, _("charge row {0}").format(getattr(row, "idx", "") or ""))

	def validate_customs_unit_types(self):
		"""Ensure customs charge rows use unit types allowed by Declaration Order / Declaration Charges.
		Prevents submission with e.g. 'Job' so that creating Declaration Order from the quote does not fail."""
		customs_rows = []
		if getattr(self, "charges", None):
			customs_rows = [r for r in self.charges if _sq_charge_row_matches_service(r, "Customs")]
		if getattr(self, "main_service", None) != "Customs" or not customs_rows:
			return
		for idx, row in enumerate(customs_rows, start=1):
			unit_type = getattr(row, "unit_type", None)
			if unit_type and unit_type not in CUSTOMS_ALLOWED_UNIT_TYPES:
				frappe.throw(
					_("Row #{0} (Customs): Unit Type cannot be \"{1}\". It should be one of: {2}.").format(
						idx,
						unit_type,
						", ".join(f'"{u}"' for u in CUSTOMS_ALLOWED_UNIT_TYPES_DISPLAY),
					),
					title=_("Invalid Unit Type"),
				)
			cost_unit_type = getattr(row, "cost_unit_type", None)
			if cost_unit_type and cost_unit_type not in CUSTOMS_ALLOWED_UNIT_TYPES:
				frappe.throw(
					_("Row #{0} (Customs): Cost Unit Type cannot be \"{1}\". It should be one of: {2}.").format(
						idx,
						cost_unit_type,
						", ".join(f'"{u}"' for u in CUSTOMS_ALLOWED_UNIT_TYPES_DISPLAY),
					),
					title=_("Invalid Cost Unit Type"),
				)

	def validate_vehicle_type_load_type(self):
		"""Validate that the selected vehicle_type is allowed for the selected load_type in each Transport charge"""
		transport_rows = [c for c in (getattr(self, "charges") or []) if _sq_charge_row_matches_service(c, "Transport")]
		if getattr(self, "main_service", None) != "Transport" or not transport_rows:
			return

		for transport_row in transport_rows:
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
		"""Validate vehicle type capacity when vehicle_type is assigned. Uses Transport charges."""
		if getattr(self, "main_service", None) != "Transport":
			return

		transport_rows = [c for c in (getattr(self, "charges") or []) if _sq_charge_row_matches_service(c, "Transport")]
		has_vehicle_type = any(getattr(r, "vehicle_type", None) for r in transport_rows)
		if not has_vehicle_type:
			return

		try:
			from logistics.transport.capacity.vehicle_type_capacity import get_vehicle_type_capacity_info
			from logistics.transport.capacity.uom_conversion import convert_weight, convert_volume, get_default_uoms
			from logistics.utils.default_uom import get_default_uoms_for_domain

			required_weight = flt(getattr(self, "transport_weight", None) or getattr(self, "weight", 0))
			required_weight_uom = getattr(self, "transport_weight_uom", None) or getattr(self, "weight_uom", None)
			required_volume = flt(getattr(self, "transport_volume", None) or getattr(self, "volume", 0))
			required_volume_uom = getattr(self, "transport_volume_uom", None) or getattr(self, "volume_uom", None)
			if not required_weight_uom or not required_volume_uom:
				defaults = get_default_uoms_for_domain("transport")
				required_weight_uom = required_weight_uom or defaults.get("weight_uom")
				required_volume_uom = required_volume_uom or defaults.get("volume_uom")
			default_uoms = get_default_uoms(self.company)
			required_weight_uom = required_weight_uom or default_uoms.get("weight")
			required_volume_uom = required_volume_uom or default_uoms.get("volume")

			if required_weight == 0 and required_volume == 0:
				return

			required_weight_std = convert_weight(required_weight, required_weight_uom, default_uoms["weight"], self.company)
			required_volume_std = convert_volume(required_volume, required_volume_uom, default_uoms["volume"], self.company)

			for transport_row in transport_rows:
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
			throw_if_sales_quote_expired_for_creation(self)
			throw_if_additional_charge_sales_quote_blocks_booking_order_creation(self)
			# Check if Sales Quote has air charges (new) or air freight (legacy)
			air_charge_count = count_sales_quote_charges_for_service(self.name, "Air")
			air_freight_count = frappe.db.count("Sales Quote Air Freight", {
				"parent": self.name,
				"parenttype": "Sales Quote"
			}) if frappe.db.table_exists("Sales Quote Air Freight") else 0
			if air_charge_count == 0 and air_freight_count == 0:
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
			air_shipment.total_weight = weight if weight and flt(weight) > 0 else None
			volume = getattr(self, 'air_volume', None) or getattr(self, 'volume', None)
			air_shipment.total_volume = volume if volume and flt(volume) > 0 else None
			chargeable = getattr(self, 'air_chargeable', None) or getattr(self, 'chargeable', None)
			air_shipment.chargeable = chargeable if chargeable and flt(chargeable) > 0 else None
			air_shipment.service_level = getattr(self, 'service_level', None)
			air_shipment.incoterm = getattr(self, 'incoterm', None)
			air_shipment.additional_terms = getattr(self, 'additional_terms', None)
			air_shipment.company = self.company
			air_shipment.branch = self.branch
			air_shipment.cost_center = self.cost_center
			air_shipment.profit_center = self.profit_center
			air_shipment.is_main_service = 1
			copy_sales_quote_fields_to_target(self, air_shipment)

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
		Create a Sea Booking from Sales Quote, then convert it to Sea Shipment.
		Shipments can only be created by converting a Sea Booking.
		
		Returns:
			dict: Result with created Sea Shipment name and status
		"""
		try:
			throw_if_sales_quote_expired_for_creation(self)
			throw_if_additional_charge_sales_quote_blocks_booking_order_creation(self)
			# First create the Sea Booking from Sales Quote
			booking_result = _create_sea_booking_from_sales_quote(self)
			booking_name = booking_result.get("sea_booking")
			
			if not booking_name:
				frappe.throw(_("Failed to create Sea Booking from Sales Quote"))
			
			# Get the booking and convert it to shipment
			booking = frappe.get_doc("Sea Booking", booking_name)
			shipment_result = booking.convert_to_shipment()
			
			return shipment_result
			
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
			throw_if_additional_charge_sales_quote_blocks_booking_order_creation(self)

			# Check if Sales Quote has warehousing details (legacy table or unified Warehousing charges)
			if not _sales_quote_has_warehousing_for_contract(self):
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


def _get_contributors_for_leg(leg):
	"""Return list of (contributor_job_type, contributor_job_no) for this routing leg (cross-module billing)."""
	contributors = []
	# Nested child table: load from DB if not on leg
	contrib_list = getattr(leg, "bill_with_contributors", None)
	if contrib_list:
		for c in contrib_list:
			ct = getattr(c, "contributor_job_type", None)
			cn = getattr(c, "contributor_job_no", None)
			if ct and cn:
				contributors.append((ct, cn))
	else:
		leg_name = getattr(leg, "name", None)
		if leg_name and frappe.db.exists("Sales Quote Routing Leg Contributor", {"parent": leg_name, "parenttype": "Sales Quote Routing Leg"}):
			for c in frappe.get_all(
				"Sales Quote Routing Leg Contributor",
				filters={"parent": leg_name, "parenttype": "Sales Quote Routing Leg"},
				fields=["contributor_job_type", "contributor_job_no"],
			):
				if c.get("contributor_job_type") and c.get("contributor_job_no"):
					contributors.append((c["contributor_job_type"], c["contributor_job_no"]))
	return contributors


def _create_consolidated_invoice(sales_quote, legs, main_leg, posting_date):
	"""Create one Sales Invoice aggregating charges from Main Job + all Sub-Jobs (anchor + contributors per leg)."""
	from logistics.billing.cross_module_billing import get_billing_set_items

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

	# Collect invoice items from all legs: each leg = anchor + contributors (billing set)
	all_items = []
	for leg in legs:
		job_type = getattr(leg, "job_type", None)
		job_no = getattr(leg, "job_no", None)
		if not job_type or not job_no:
			continue
		contributors = _get_contributors_for_leg(leg)
		leg_prefix = _("Leg {0}").format(getattr(leg, "idx", ""))
		items = get_billing_set_items(job_type, job_no, contributors, customer=customer, description_prefix=leg_prefix)
		for item in items:
			if not item.get("description"):
				item["description"] = f"{job_type} {job_no} ({leg_prefix})"
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
	if getattr(main_doc, "job_number", None):
		si.job_number = main_doc.job_number

	base_remarks = _("Auto-created from Sales Quote {0} (Consolidated - Main Job: {1})").format(sales_quote.name, main_job_no)
	si.remarks = base_remarks

	for item in all_items:
		si.append("items", {
			"item_code": item.get("item_code"),
			"item_name": item.get("item_name"),
			"qty": flt(item.get("qty"), 2) or 1,
			"rate": flt(item.get("rate"), 2),
			"uom": item.get("uom"),
			"description": item.get("description"),
		})

	si.set_missing_values()
	si.insert(ignore_permissions=True)

	return {"success": True, "sales_invoice": si.name, "message": _("Sales Invoice {0} created (Consolidated).").format(si.name)}


def _create_separate_invoices_per_leg(sales_quote, legs, posting_date):
	"""Create separate Sales Invoice per routing leg (billing set = anchor + contributors)."""
	from logistics.billing.cross_module_billing import get_billing_set_items

	invoices_created = []
	for leg in legs:
		job_type = getattr(leg, "job_type", None)
		job_no = getattr(leg, "job_no", None)
		if not job_type or not job_no:
			continue
		try:
			contributors = _get_contributors_for_leg(leg)
			anchor_doc = frappe.get_doc(job_type, job_no)
			customer = getattr(anchor_doc, "customer", None) or getattr(anchor_doc, "local_customer", None) or sales_quote.customer
			company = getattr(anchor_doc, "company", None) or sales_quote.company
			if not customer or not company:
				frappe.msgprint(_("Skipping leg {0}: missing customer/company on {1} {2}.").format(getattr(leg, "idx", ""), job_type, job_no), indicator="orange")
				continue
			items = get_billing_set_items(job_type, job_no, contributors, customer=customer)
			if not items:
				frappe.msgprint(_("No charges for leg {0} ({1} {2}). Add charges or contributors.").format(getattr(leg, "idx", ""), job_type, job_no), indicator="orange")
				continue
			si = _create_sales_invoice_from_items(
				items=items,
				customer=customer,
				company=company,
				posting_date=posting_date,
				sales_quote_name=sales_quote.name,
				anchor_doc=anchor_doc,
				sales_quote=sales_quote,
				remarks_suffix=_("Per Product - {0} {1}").format(job_type, job_no),
			)
			if si:
				invoices_created.append(si.name)
		except Exception as e:
			frappe.log_error(str(e), "Multimodal Per-Product Invoice")
			frappe.msgprint(_("Could not create invoice for {0} {1}: {2}").format(job_type, job_no, str(e)), indicator="orange")

	if not invoices_created:
		frappe.throw(_("No invoices could be created. Ensure jobs have charges and are in a billable state."))

	return {"success": True, "sales_invoices": invoices_created, "message": _("Created {0} Sales Invoice(s).").format(len(invoices_created))}


def _create_sales_invoice_from_items(
	items,
	customer,
	company,
	posting_date,
	sales_quote_name,
	anchor_doc,
	sales_quote,
	remarks_suffix,
):
	"""Create one Sales Invoice from item list and header from anchor_doc/sales_quote. Returns the SI doc."""
	si = frappe.new_doc("Sales Invoice")
	si.customer = customer
	si.company = company
	si.posting_date = posting_date
	si.quotation_no = sales_quote_name
	si.branch = getattr(anchor_doc, "branch", None) or sales_quote.branch
	si.cost_center = getattr(anchor_doc, "cost_center", None) or sales_quote.cost_center
	si.profit_center = getattr(anchor_doc, "profit_center", None) or sales_quote.profit_center
	si.job_number = getattr(anchor_doc, "job_number", None)
	si.remarks = _("Auto-created from Sales Quote {0} ({1})").format(sales_quote_name, remarks_suffix)
	for item in items:
		si.append("items", {
			"item_code": item.get("item_code"),
			"item_name": item.get("item_name"),
			"qty": flt(item.get("qty"), 2) or 1,
			"rate": flt(item.get("rate"), 2),
			"uom": item.get("uom"),
			"description": item.get("description"),
		})
	si.set_missing_values()
	si.insert(ignore_permissions=True)
	return si


def _get_invoice_items_from_job(job_type, job_name, customer):
	"""Extract Sales Invoice items from a job/shipment (unified API). Returns list of item dicts."""
	from logistics.billing.cross_module_billing import get_invoice_items_from_job as billing_get_items
	return billing_get_items(job_type, job_name, customer=customer)


def _get_service_params(sales_quote, service_type):
	"""Get params from first charge with the given service_type."""
	charges = [c for c in (getattr(sales_quote, "charges") or []) if _sq_charge_row_matches_service(c, service_type)]
	return charges[0] if charges else None


def _create_transport_order_from_sales_quote(sales_quote):
	"""Create Transport Order from Sales Quote and update routing leg job_no if multimodal."""
	throw_if_sales_quote_expired_for_creation(sales_quote)
	throw_if_additional_charge_sales_quote_blocks_booking_order_creation(sales_quote)
	transport_charges = [c for c in (getattr(sales_quote, "charges") or []) if _sq_charge_row_matches_service(c, "Transport")]
	legacy_transport = getattr(sales_quote, "transport", None) or []
	main_ok = getattr(sales_quote, "main_service", None) == "Transport"
	has_transport = bool(transport_charges) or bool(legacy_transport)
	if not main_ok and not has_transport:
		frappe.throw(_("Only Sales Quotes with Transport as main service or Transport charges can create Transport Orders."))
	if not transport_charges and not legacy_transport:
		frappe.throw(_("No transport lines found in this Sales Quote."))

	from logistics.transport.doctype.transport_order.transport_order import _sync_quote_and_sales_quote

	# Use service params (preferred) or first transport charge/row
	first = _get_service_params(sales_quote, "Transport") or (legacy_transport[0] if legacy_transport else transport_charges[0])
	location_from = getattr(first, "location_from", None) or getattr(sales_quote, "location_from", None)
	location_to = getattr(first, "location_to", None) or getattr(sales_quote, "location_to", None)
	# Fallback: scan all Transport charges for location_from/location_to
	if not location_from or not location_to:
		for ch in transport_charges:
			if not location_from and getattr(ch, "location_from", None):
				location_from = ch.location_from
			if not location_to and getattr(ch, "location_to", None):
				location_to = ch.location_to
			if location_from and location_to:
				break
	# Fallback: use origin_port/destination_port (One-off params) with location_type UNLOCO
	if (not location_from or not location_to) and (getattr(sales_quote, "origin_port", None) or getattr(sales_quote, "destination_port", None)):
		if not location_from:
			location_from = getattr(sales_quote, "origin_port", None)
		if not location_to:
			location_to = getattr(sales_quote, "destination_port", None)
		if location_from and location_to:
			# Will set location_type="UNLOCO" below when using this fallback
			pass
	# Fallback: routing leg with mode Road
	if (not location_from or not location_to) and getattr(sales_quote, "routing_legs", None):
		for leg in sales_quote.routing_legs:
			mode = getattr(leg, "mode", None)
			if mode in ("Road", "Transport") or (mode and str(mode).lower() in ("road", "transport")):
				if not location_from and getattr(leg, "origin", None):
					location_from = leg.origin
				if not location_to and getattr(leg, "destination", None):
					location_to = leg.destination
				if location_from and location_to:
					break
	if not location_from or not location_to:
		frappe.throw(_(
			"Location From and Location To are required for Transport. Set them in Transport charges (location_from, location_to), "
			"in One-off Parameters (Origin Port, Destination Port), or in the Routing leg with mode Road."
		))

	transport_order = frappe.new_doc("Transport Order")
	transport_order.customer = sales_quote.customer
	transport_order.shipper = getattr(sales_quote, "shipper", None)
	transport_order.consignee = getattr(sales_quote, "consignee", None)
	transport_order.booking_date = today()
	transport_order.scheduled_date = today()
	transport_order.quote_type = "Sales Quote"
	transport_order.quote = sales_quote.name
	transport_order.sales_quote = sales_quote.name
	_sync_quote_and_sales_quote(transport_order)

	transport_order.transport_template = getattr(first, "transport_template", None) or getattr(sales_quote, "transport_template", None)
	transport_order.load_type = getattr(first, "load_type", None) or getattr(sales_quote, "load_type", None)
	transport_order.vehicle_type = getattr(first, "vehicle_type", None) or getattr(sales_quote, "vehicle_type", None)
	transport_order.container_type = getattr(first, "container_type", None) or getattr(sales_quote, "container_type", None)
	transport_order.company = sales_quote.company
	transport_order.branch = sales_quote.branch
	transport_order.cost_center = sales_quote.cost_center
	transport_order.profit_center = sales_quote.profit_center
	# location_type: from first charge, header (One-off Transport params), or UNLOCO when using origin_port/destination_port or routing leg fallback
	transport_order.location_type = (
		getattr(first, "location_type", None)
		or getattr(sales_quote, "location_type", None)
	)
	if not transport_order.location_type and (location_from or location_to):
		# Values from origin_port/destination_port or routing leg are UNLOCO
		transport_order.location_type = "UNLOCO"
	transport_order.location_from = location_from
	transport_order.location_to = location_to

	transport_order.transport_job_type = sales_quote._determine_transport_job_type(
		current_job_type=None,
		load_type=transport_order.load_type,
		container_type=transport_order.container_type,
	)
	transport_order.is_main_service = 1
	copy_sales_quote_fields_to_target(sales_quote, transport_order)
	append_transport_order_door_leg_from_party_masters(transport_order)
	apply_shipper_consignee_defaults(transport_order)

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
	# Use Transport Order's implementation (separate_billings_per_service_type, main job, legacy tables).
	transport_order._populate_charges_from_sales_quote()
	transport_order.save(ignore_permissions=True)

	_update_routing_leg_job(
		sales_quote.name,
		mode="Road",
		job_type="Transport Order",
		job_no=transport_order.name,
	)
	frappe.db.commit()
	return {"success": True, "transport_order": transport_order.name, "message": _("Transport Order {0} created.").format(transport_order.name)}


def _get_air_weight_volume_from_sales_quote(sales_quote):
	"""Derive total weight and volume from Sales Quote Air charges (quantity where unit_type is Weight/Volume)."""
	total_weight = flt(getattr(sales_quote, "air_weight", None) or getattr(sales_quote, "weight", None) or 0)
	total_volume = flt(getattr(sales_quote, "air_volume", None) or getattr(sales_quote, "volume", None) or 0)
	air_rows = [c for c in (getattr(sales_quote, "charges") or []) if _sq_charge_row_matches_service(c, "Air")]
	if not air_rows and getattr(sales_quote, "air_freight", None):
		air_rows = sales_quote.air_freight
	for row in (air_rows or []):
		ut = getattr(row, "unit_type", None) or ""
		qty = flt(getattr(row, "quantity", 0) or 0)
		if ut == "Weight" and qty > 0:
			total_weight += qty
		elif ut == "Volume" and qty > 0:
			total_volume += qty
		# Cost side
		cut = getattr(row, "cost_unit_type", None) or ""
		cq = flt(getattr(row, "cost_quantity", 0) or 0)
		if cut == "Weight" and cq > 0:
			total_weight = max(total_weight, cq)
		elif cut == "Volume" and cq > 0:
			total_volume = max(total_volume, cq)
	return total_weight, total_volume


def _create_air_booking_from_sales_quote(sales_quote):
	"""Create Air Booking from Sales Quote and update routing leg job_no if multimodal."""
	throw_if_sales_quote_expired_for_creation(sales_quote)
	throw_if_additional_charge_sales_quote_blocks_booking_order_creation(sales_quote)
	air_charges = [c for c in (getattr(sales_quote, "charges") or []) if _sq_charge_row_matches_service(c, "Air")]
	legacy_air = getattr(sales_quote, "air_freight", None) or []
	main_ok = getattr(sales_quote, "main_service", None) == "Air"
	has_air = bool(air_charges) or bool(legacy_air)
	if not main_ok and not has_air:
		frappe.throw(_("Only Sales Quotes with Air as main service or Air charges can create Air Bookings."))
	if not air_charges and not legacy_air:
		frappe.throw(_("No air freight lines found in this Sales Quote."))

	first = _get_service_params(sales_quote, "Air") or (legacy_air[0] if legacy_air else air_charges[0])
	origin = getattr(first, "origin_port", None) or getattr(sales_quote, "origin_port", None)
	dest = getattr(first, "destination_port", None) or getattr(sales_quote, "destination_port", None)
	# Fallback: scan all Air charges for origin/destination
	if not origin or not dest:
		for ch in air_charges:
			if not origin and getattr(ch, "origin_port", None):
				origin = ch.origin_port
			if not dest and getattr(ch, "destination_port", None):
				dest = ch.destination_port
			if origin and dest:
				break
	# Fallback: get from routing leg with mode Air
	if (not origin or not dest) and getattr(sales_quote, "routing_legs", None):
		for leg in sales_quote.routing_legs:
			if getattr(leg, "mode", None) == "Air" and (getattr(leg, "origin", None) or getattr(leg, "destination", None)):
				if not origin and getattr(leg, "origin", None):
					origin = leg.origin
				if not dest and getattr(leg, "destination", None):
					dest = leg.destination
				if origin and dest:
					break
	if not origin or not dest:
		frappe.throw(_("Origin Port and Destination Port are required for Air mode. Set them in the Air charge parameters (Origin Port, Destination Port) or in the Routing leg with mode Air."))
	if not sales_quote.shipper or not sales_quote.consignee:
		frappe.throw(_("Shipper and Consignee are required for Air mode."))

	air_booking = frappe.new_doc("Air Booking")
	air_booking.booking_date = sales_quote.date or today()
	air_booking.local_customer = sales_quote.customer
	air_booking.quote_type = "Sales Quote"
	air_booking.quote = sales_quote.name
	air_booking.sales_quote = sales_quote.name
	air_booking.origin_port = origin
	air_booking.destination_port = dest
	air_booking.direction = getattr(first, "direction", None) or getattr(sales_quote, "direction", None) or "Export"
	air_booking.shipper = sales_quote.shipper
	air_booking.consignee = sales_quote.consignee
	air_booking.airline = getattr(first, "airline", None) or getattr(sales_quote, "airline", None)
	air_booking.freight_agent = getattr(first, "freight_agent", None) or getattr(sales_quote, "freight_agent", None)
	air_booking.house_type = getattr(first, "air_house_type", None) or getattr(first, "house_type", None)
	# Normalize legacy house_type values
	if air_booking.house_type == "Direct":
		air_booking.house_type = "Standard House"
	elif air_booking.house_type == "Consolidation":
		air_booking.house_type = "Co-load Master"
	air_booking.company = sales_quote.company
	air_booking.branch = sales_quote.branch
	air_booking.cost_center = sales_quote.cost_center
	air_booking.profit_center = sales_quote.profit_center
	air_booking.is_main_service = 1
	copy_sales_quote_fields_to_target(sales_quote, air_booking)

	# Set weight/volume from Sales Quote so charge quantities can be calculated when populating
	weight = getattr(first, "weight", None) or getattr(sales_quote, "weight", None)
	volume = getattr(first, "volume", None) or getattr(sales_quote, "volume", None)
	if weight is not None and flt(weight) > 0:
		air_booking.weight = weight
	if volume is not None and flt(volume) > 0:
		air_booking.volume = volume

	apply_sales_quote_routing_to_booking(air_booking, sales_quote)
	populate_air_sea_booking_party_fields_from_masters(air_booking)
	apply_shipper_consignee_defaults(air_booking)

	# Populate charges before insert so they are saved with the document (avoids insert+reload clearing them)
	from logistics.air_freight.doctype.air_booking.air_booking import _sync_quote_and_sales_quote
	_sync_quote_and_sales_quote(air_booking)
	air_booking._populate_charges_from_sales_quote(sales_quote.name)
	air_booking._normalize_charges_before_save()

	air_booking.insert(ignore_permissions=True)

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
	throw_if_sales_quote_expired_for_creation(sales_quote)
	throw_if_additional_charge_sales_quote_blocks_booking_order_creation(sales_quote)
	sea_charges = [c for c in (getattr(sales_quote, "charges") or []) if _sq_charge_row_matches_service(c, "Sea")]
	legacy_sea = getattr(sales_quote, "sea_freight", None) or []
	main_ok = getattr(sales_quote, "main_service", None) == "Sea"
	has_sea = bool(sea_charges) or bool(legacy_sea)
	if not main_ok and not has_sea:
		frappe.throw(_("Only Sales Quotes with Sea as main service or Sea charges can create Sea Bookings."))
	if not sea_charges and not legacy_sea:
		frappe.throw(_("No sea freight lines found in this Sales Quote."))

	first = _get_service_params(sales_quote, "Sea") or (legacy_sea[0] if legacy_sea else sea_charges[0])
	origin = (
		getattr(first, "origin_port", None)
		or getattr(sales_quote, "origin_port_sea", None)
		or getattr(sales_quote, "origin_port", None)
		or getattr(sales_quote, "location_from", None)
	)
	dest = (
		getattr(first, "destination_port", None)
		or getattr(sales_quote, "destination_port_sea", None)
		or getattr(sales_quote, "destination_port", None)
		or getattr(sales_quote, "location_to", None)
	)
	if not origin or not dest:
		frappe.throw(_("Origin Port and Destination Port are required for Sea mode."))
	if not sales_quote.shipper or not sales_quote.consignee:
		frappe.throw(_("Shipper and Consignee are required for Sea mode."))

	sea_booking = frappe.new_doc("Sea Booking")
	sea_booking.booking_date = sales_quote.date or today()
	sea_booking.local_customer = sales_quote.customer
	sea_booking.quote_type = "Sales Quote"
	sea_booking.quote = sales_quote.name
	sea_booking.sales_quote = sales_quote.name
	sea_booking.origin_port = origin
	sea_booking.destination_port = dest
	sea_booking.direction = getattr(first, "direction", None) or getattr(sales_quote, "direction", None) or "Export"
	sea_booking.shipping_line = getattr(first, "shipping_line", None) or getattr(sales_quote, "shipping_line", None)
	sea_booking.freight_agent = (
		getattr(first, "freight_agent_sea", None) or getattr(first, "freight_agent", None)
		or getattr(sales_quote, "freight_agent_sea", None)
	)
	sea_booking.transport_mode = getattr(first, "transport_mode", None) or getattr(sales_quote, "transport_mode", None) or "FCL"
	sea_booking.shipper = sales_quote.shipper
	sea_booking.consignee = sales_quote.consignee
	sea_booking.company = sales_quote.company
	sea_booking.branch = sales_quote.branch
	sea_booking.cost_center = sales_quote.cost_center
	sea_booking.profit_center = sales_quote.profit_center
	sea_booking.is_main_service = 1
	copy_sales_quote_fields_to_target(sales_quote, sea_booking)

	apply_sales_quote_routing_to_booking(sea_booking, sales_quote)
	populate_air_sea_booking_party_fields_from_masters(sea_booking)
	apply_shipper_consignee_defaults(sea_booking)

	sea_booking.insert(ignore_permissions=True)
	sea_booking.reload()
	sea_booking.quote_type = "Sales Quote"
	sea_booking.quote = sales_quote.name
	sea_booking.sales_quote = sales_quote.name
	from logistics.sea_freight.doctype.sea_booking.sea_booking import _sync_quote_and_sales_quote
	_sync_quote_and_sales_quote(sea_booking)
	# Populate charges from Sales Quote (same as Fetch Quotations)
	sea_booking._populate_charges_from_sales_quote(sales_quote)
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
		order_by="idx asc",
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
def get_load_type_service_flags(load_types=None):
	"""Return mode flags for Load Type names (client sanitization vs service_type)."""
	import json

	if isinstance(load_types, str):
		load_types = json.loads(load_types)
	if not load_types:
		return {}
	out = {}
	for name in load_types:
		if not name:
			continue
		row = frappe.db.get_value(
			"Load Type",
			name,
			["air", "sea", "transport", "customs", "warehousing"],
			as_dict=True,
		)
		if row:
			out[name] = row
	return out


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
		
		filters = sales_quote_charge_filters(air_shipment, sales_quote)

		# Get from Sales Quote Charge (filtered) or Sales Quote Air Freight (legacy)
		from logistics.utils.sales_quote_charge_parameters import (
			SALES_QUOTE_CHARGE_PARAMETER_FIELDS,
			filter_fields_existing_in_doctype,
		)

		charge_fields = [
			"item_code", "item_name", "revenue_calculation_method", "calculation_method", "uom", "currency",
			"unit_rate", "unit_type", "minimum_quantity", "minimum_charge",
			"maximum_charge", "base_amount", "estimated_revenue",
			"charge_type", "charge_category",
			"apply_95_5_rule", "taxable_freight_item", "taxable_freight_item_tax_template",
			"use_tariff_in_revenue", "use_tariff_in_cost", "tariff",
			"revenue_tariff", "cost_tariff", "bill_to_exchange_rate", "pay_to_exchange_rate",
			"bill_to_exchange_rate_source", "pay_to_exchange_rate_source", "service_type",
		] + list(SALES_QUOTE_CHARGE_PARAMETER_FIELDS)
		sqc_fields = filter_fields_existing_in_doctype("Sales Quote Charge", charge_fields)
		legacy_air_fields = filter_fields_existing_in_doctype("Sales Quote Air Freight", charge_fields)
		sales_quote_air_freight_records = frappe.get_all(
			"Sales Quote Charge",
			filters=filters,
			fields=sqc_fields,
			order_by="idx"
		)
		if not sales_quote_air_freight_records and frappe.db.table_exists("Sales Quote Air Freight"):
			sales_quote_air_freight_records = frappe.get_all(
				"Sales Quote Air Freight",
				filters={"parent": sales_quote.name, "parenttype": "Sales Quote"},
				fields=legacy_air_fields,
				order_by="idx"
			)
		sales_quote_air_freight_records = filter_sales_quote_charge_rows_for_operational_doc(
			air_shipment, sales_quote_air_freight_records
		)

		# Map and populate charges
		charges_added = 0
		for sqaf_record in sales_quote_air_freight_records:
			charge_row = _map_sales_quote_air_freight_to_charge(sqaf_record, air_shipment)
			if charge_row:
				air_shipment.append("charges", charge_row)
				charges_added += 1

		from logistics.utils.operational_exchange_rates import sync_operational_exchange_rates_from_charge_rows

		sync_operational_exchange_rates_from_charge_rows(air_shipment, air_shipment.charges)
		
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
		if unit_type in ("Weight", "Chargeable Weight"):
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
		if unit_type in ("Weight", "Chargeable Weight"):
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
		def _af_r(key, default=None):
			return sqaf_record.get(key, default) if isinstance(sqaf_record, dict) else getattr(sqaf_record, key, default)

		# Get the item details to fetch additional required fields
		item_doc = frappe.get_doc("Item", _af_r("item_code"))
		
		# Get default currency from system settings
		default_currency = frappe.get_system_settings("currency") or "USD"
		
		# Map unit_type to calculation_method and quantity
		unit_type_to_calc = {
			"Weight": "Per Unit",
			"Chargeable Weight": "Per Unit",
			"Volume": "Per Unit",
			"Package": "Per Unit",
			"Piece": "Per Unit",
			"Shipment": "Flat Rate"
		}
		calculation_method = unit_type_to_calc.get(_af_r("unit_type"), "Flat Rate")
		
		# Get quantity based on unit_type
		quantity = 0
		if _af_r("unit_type") == "Chargeable Weight":
			quantity = flt(
				air_shipment.get("chargeable", 0)
				or air_shipment.get("chargeable_weight", 0)
			)
		elif _af_r("unit_type") == "Weight":
			quantity = flt(air_shipment.get("total_weight") or air_shipment.get("weight")) or 0
		elif _af_r("unit_type") == "Volume":
			quantity = flt(air_shipment.get("total_volume") or air_shipment.get("volume")) or 0
		elif _af_r("unit_type") in ("Package", "Piece"):
			if hasattr(air_shipment, 'packages') and air_shipment.packages:
				quantity = len(air_shipment.packages)
			else:
				quantity = 1
		elif _af_r("unit_type") == "Shipment" or calculation_method == "Flat Rate":
			quantity = 1
		
		charge_type = _af_r("charge_type") or (
			item_doc.custom_charge_type if hasattr(item_doc, "custom_charge_type") and item_doc.custom_charge_type else None
		) or "Other"
		charge_category = _af_r("charge_category") or (
			item_doc.custom_charge_category if hasattr(item_doc, "custom_charge_category") and item_doc.custom_charge_category else None
		) or "Other"
		
		normalized_uom = _normalize_uom_for_air_booking_charges(
			_af_r("uom"),
			_af_r("unit_type"),
		)
		
		_sq_st = (
			sqaf_record.get("service_type")
			if isinstance(sqaf_record, dict)
			else getattr(sqaf_record, "service_type", None)
		) or "Air"
		charge_data = {
			"service_type": _sq_st,
			"item_code": _af_r("item_code"),
			"item_name": _af_r("item_name") or item_doc.item_name,
			"charge_type": charge_type,
			"charge_category": charge_category,
			"revenue_calculation_method": _af_r("revenue_calculation_method") or _af_r("calculation_method") or calculation_method,
			"rate": _af_r("unit_rate") or 0,
			"currency": _af_r("currency") or default_currency,
			"quantity": quantity,
			"unit_of_measure": normalized_uom,
			"billing_status": "To Bill",
			"bill_to": getattr(sqaf_record, "bill_to", None),
			"pay_to": getattr(sqaf_record, "pay_to", None),
			"use_tariff_in_revenue": getattr(sqaf_record, "use_tariff_in_revenue", False),
			"use_tariff_in_cost": getattr(sqaf_record, "use_tariff_in_cost", False),
			"tariff": getattr(sqaf_record, "tariff", None),
			"revenue_tariff": getattr(sqaf_record, "revenue_tariff", None),
			"cost_tariff": getattr(sqaf_record, "cost_tariff", None),
			"bill_to_exchange_rate": _af_r("bill_to_exchange_rate"),
			"pay_to_exchange_rate": _af_r("pay_to_exchange_rate"),
			"bill_to_exchange_rate_source": _af_r("bill_to_exchange_rate_source"),
			"pay_to_exchange_rate_source": _af_r("pay_to_exchange_rate_source"),
		}
		
		# Add minimum/maximum charge if available
		if _af_r("minimum_charge"):
			charge_data["minimum_charge"] = _af_r("minimum_charge")
		if _af_r("maximum_charge"):
			charge_data["maximum_charge"] = _af_r("maximum_charge")

		if _af_r("apply_95_5_rule") is not None:
			charge_data["apply_95_5_rule"] = cint(_af_r("apply_95_5_rule"))
		if _af_r("taxable_freight_item"):
			charge_data["taxable_freight_item"] = _af_r("taxable_freight_item")
		if _af_r("taxable_freight_item_tax_template"):
			charge_data["taxable_freight_item_tax_template"] = _af_r("taxable_freight_item_tax_template")

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
		
		filters = sales_quote_charge_filters(sea_shipment, sales_quote)

		# Get from Sales Quote Charge (filtered) or Sales Quote Sea Freight (legacy)
		from logistics.utils.sales_quote_charge_parameters import (
			SALES_QUOTE_CHARGE_PARAMETER_FIELDS,
			filter_fields_existing_in_doctype,
		)

		charge_fields = [
			"item_code", "item_name", "revenue_calculation_method", "calculation_method", "uom", "currency",
			"unit_rate", "unit_type", "minimum_quantity", "minimum_charge",
			"maximum_charge", "base_amount", "estimated_revenue",
			"charge_type", "charge_category",
			"apply_95_5_rule", "taxable_freight_item", "taxable_freight_item_tax_template",
			"use_tariff_in_revenue", "use_tariff_in_cost", "tariff",
			"revenue_tariff", "cost_tariff", "bill_to_exchange_rate", "pay_to_exchange_rate",
			"bill_to_exchange_rate_source", "pay_to_exchange_rate_source", "service_type",
		] + list(SALES_QUOTE_CHARGE_PARAMETER_FIELDS)
		sqc_fields = filter_fields_existing_in_doctype("Sales Quote Charge", charge_fields)
		legacy_sea_fields = filter_fields_existing_in_doctype("Sales Quote Sea Freight", charge_fields)
		sales_quote_sea_freight_records = frappe.get_all(
			"Sales Quote Charge",
			filters=filters,
			fields=sqc_fields,
			order_by="idx"
		)
		if not sales_quote_sea_freight_records and frappe.db.table_exists("Sales Quote Sea Freight"):
			sales_quote_sea_freight_records = frappe.get_all(
				"Sales Quote Sea Freight",
				filters={"parent": sales_quote.name, "parenttype": "Sales Quote"},
				fields=legacy_sea_fields,
				order_by="idx"
			)
		sales_quote_sea_freight_records = filter_sales_quote_charge_rows_for_operational_doc(
			sea_shipment, sales_quote_sea_freight_records
		)

		# Map and populate charges
		charges_added = 0
		for sqsf_record in sales_quote_sea_freight_records:
			charge_row = _map_sales_quote_sea_freight_to_charge(sqsf_record, sea_shipment)
			if charge_row:
				sea_shipment.append("charges", charge_row)
				charges_added += 1

		from logistics.utils.operational_exchange_rates import sync_operational_exchange_rates_from_charge_rows

		sync_operational_exchange_rates_from_charge_rows(sea_shipment, sea_shipment.charges)
		
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
		def _sf_r(key, default=None):
			return sqsf_record.get(key, default) if isinstance(sqsf_record, dict) else getattr(sqsf_record, key, default)

		# Get the item details to fetch additional required fields
		item_doc = frappe.get_doc("Item", _sf_r("item_code"))
		
		# Get default currency from system settings
		default_currency = frappe.get_system_settings("currency") or "USD"
		
		# Map unit_type to determine quantity
		unit_type_to_unit = {
			"Weight": "kg",
			"Chargeable Weight": "kg",
			"Volume": "m³",
			"Package": "package",
			"Piece": "package",
			"Shipment": "shipment",
			"Container": "container"
		}
		unit = unit_type_to_unit.get(_sf_r("unit_type"), "shipment")
		
		# Get quantity based on unit type
		quantity = 0
		if _sf_r("unit_type") == "Chargeable Weight":
			quantity = flt(
				sea_shipment.get("chargeable", 0)
				or sea_shipment.get("chargeable_weight", 0)
			)
		elif _sf_r("unit_type") == "Weight":
			quantity = flt(sea_shipment.get("total_weight")) or 0
		elif _sf_r("unit_type") == "Volume":
			quantity = flt(sea_shipment.get("total_volume")) or 0
		elif _sf_r("unit_type") == "Package":
			# Get package count from Sea Shipment if available
			if hasattr(sea_shipment, 'packages') and sea_shipment.packages:
				quantity = len(sea_shipment.packages)
			else:
				quantity = 1
		elif _sf_r("unit_type") == "Container":
			# Get container count from Sea Shipment if available
			if hasattr(sea_shipment, 'containers') and sea_shipment.containers:
				quantity = len(sea_shipment.containers)
			else:
				quantity = 1
		elif _sf_r("unit_type") == "Shipment":
			quantity = 1
		else:
			quantity = 1
		
		# Calculate selling amount based on calculation method
		_sf_rev = (_sf_r("revenue_calculation_method") or _sf_r("calculation_method") or "").strip()
		_sf_ur = flt(_sf_r("unit_rate")) or 0
		selling_amount = 0
		if _sf_rev == "Per Unit":
			selling_amount = _sf_ur * quantity
			# Apply minimum/maximum charge
			if _sf_r("minimum_charge") and selling_amount < flt(_sf_r("minimum_charge")):
				selling_amount = flt(_sf_r("minimum_charge"))
			if _sf_r("maximum_charge") and selling_amount > flt(_sf_r("maximum_charge")):
				selling_amount = flt(_sf_r("maximum_charge"))
		elif _sf_rev == "Fixed Amount":
			selling_amount = _sf_ur
		elif _sf_rev == "Base Plus Additional":
			base = flt(_sf_r("base_amount")) or 0
			additional = _sf_ur * max(0, quantity - 1)
			selling_amount = base + additional
		elif _sf_rev == "First Plus Additional":
			min_qty = flt(_sf_r("minimum_quantity")) or 1
			if quantity <= min_qty:
				selling_amount = _sf_ur
			else:
				additional = _sf_ur * (quantity - min_qty)
				selling_amount = _sf_ur + additional
		else:
			selling_amount = _sf_ur
		
		charge_type = _sf_r("charge_type") or (
			item_doc.custom_charge_type if hasattr(item_doc, "custom_charge_type") and item_doc.custom_charge_type else None
		) or "Other"
		charge_category = _sf_r("charge_category") or (
			item_doc.custom_charge_category if hasattr(item_doc, "custom_charge_category") and item_doc.custom_charge_category else None
		) or "Other"

		_sq_st = (
			sqsf_record.get("service_type")
			if isinstance(sqsf_record, dict)
			else getattr(sqsf_record, "service_type", None)
		) or "Sea"
		# Map the fields from sales_quote_sea_freight to sea_shipment_charges
		charge_data = {
			"service_type": _sq_st,
			"charge_item": _sf_r("item_code"),
			"charge_name": _sf_r("item_name") or item_doc.item_name,
			"charge_type": charge_type,
			"charge_category": charge_category,
			"charge_description": _sf_r("item_name") or item_doc.item_name,
			"bill_to": getattr(sqsf_record, "bill_to", None) or (sea_shipment.local_customer if hasattr(sea_shipment, 'local_customer') else None),
			"pay_to": getattr(sqsf_record, "pay_to", None),
			"selling_currency": _sf_r("currency") or default_currency,
			"selling_amount": selling_amount,
			"per_unit_rate": _sf_r("unit_rate") or 0,
			"unit": unit,
			"revenue_calc_type": _sf_r("revenue_calculation_method") or _sf_r("calculation_method") or "Manual",
			"base_amount": _sf_r("base_amount") or 0,
			"use_tariff_in_revenue": getattr(sqsf_record, "use_tariff_in_revenue", False),
			"use_tariff_in_cost": getattr(sqsf_record, "use_tariff_in_cost", False),
			"tariff": getattr(sqsf_record, "tariff", None),
			"revenue_tariff": getattr(sqsf_record, "revenue_tariff", None),
			"cost_tariff": getattr(sqsf_record, "cost_tariff", None),
			"bill_to_exchange_rate": _sf_r("bill_to_exchange_rate"),
			"pay_to_exchange_rate": _sf_r("pay_to_exchange_rate"),
			"bill_to_exchange_rate_source": _sf_r("bill_to_exchange_rate_source"),
			"pay_to_exchange_rate_source": _sf_r("pay_to_exchange_rate_source"),
		}
		
		# Add minimum charge if available
		if _sf_r("minimum_charge"):
			charge_data["minimum"] = _sf_r("minimum_charge")

		if _sf_r("apply_95_5_rule") is not None:
			charge_data["apply_95_5_rule"] = cint(_sf_r("apply_95_5_rule"))
		if _sf_r("taxable_freight_item"):
			charge_data["taxable_freight_item"] = _sf_r("taxable_freight_item")
		if _sf_r("taxable_freight_item_tax_template"):
			charge_data["taxable_freight_item_tax_template"] = _sf_r("taxable_freight_item_tax_template")

		return charge_data

	except Exception as e:
		frappe.log_error(
			f"Error mapping sales quote sea freight record: {str(e)}",
			"Sales Quote Sea Freight Mapping Error"
		)
		return None


def update_one_off_quote_on_submit(sales_quote_name: str, document_name: str, doctype: str):
	"""
	Update One-off Sales Quote status to Converted when referenced document is submitted.

	Lifecycle contract: Any submittable doctype that calls this on submit (and thus sets
	converted_to_doc on the Sales Quote) MUST call reset_one_off_quote_on_cancel(sales_quote)
	in its on_cancel when the document is cancelled. If the doctype allows clearing the
	sales_quote link on save, it should in validate() (when the link is cleared) call
	reset_one_off_quote_on_cancel(original_sales_quote). Linked doctypes: Transport Order,
	Warehouse Contract, Air Booking, Sea Booking, Declaration Order, Declaration.
	
	Args:
		sales_quote_name: Name of the Sales Quote
		document_name: Name of the document that references the quote
		doctype: DocType of the referencing document
	"""
	if not sales_quote_name:
		return
	
	try:
		# Get the Sales Quote
		sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
		
		# Only update if it's a One-off quote
		if sales_quote.quotation_type != "One-off":
			return
		
		# Update status and converted_to_doc
		sales_quote.db_set("status", "Converted", update_modified=False)
		sales_quote.db_set("converted_to_doc", f"{doctype} {document_name}", update_modified=False)
		frappe.db.commit()
		
	except frappe.DoesNotExistError:
		# Sales Quote doesn't exist, skip
		pass
	except Exception as e:
		frappe.log_error(
			f"Error updating One-off Sales Quote {sales_quote_name} on submit: {str(e)}",
			"One-off Quote Lifecycle Error"
		)


def reset_one_off_quote_on_cancel(sales_quote_name: str):
	"""
	Reset One-off Sales Quote status to Draft and clear converted_to_doc.

	Called in two situations: (1) when a linked document (Order/Booking/Contract/Declaration)
	is cancelled (from that doctype's on_cancel), and (2) when the user clears the
	sales_quote link on an existing document and saves (from that doctype's validate).
	See update_one_off_quote_on_submit docstring for the full lifecycle contract.
	
	Args:
		sales_quote_name: Name of the Sales Quote
	"""
	if not sales_quote_name:
		return
	
	try:
		# Get the Sales Quote
		sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
		
		# Only reset if it's a One-off quote
		if sales_quote.quotation_type != "One-off":
			return
		
		# Reset status and clear converted_to_doc
		sales_quote.db_set("status", "Draft", update_modified=False)
		sales_quote.db_set("converted_to_doc", None, update_modified=False)
		frappe.db.commit()
		
	except frappe.DoesNotExistError:
		# Sales Quote doesn't exist, skip
		pass
	except Exception as e:
		frappe.log_error(
			f"Error resetting One-off Sales Quote {sales_quote_name} on cancel: {str(e)}",
			"One-off Quote Lifecycle Error"
		)


def resolve_allow_linked_freight_bookings_for_internal_job(doc):
	"""For internal-job satellites (e.g. Transport Order) sharing the main job's one-off quote, return
	Sea Booking / Air Booking names that may hold that quote on the main leg — they must not count as a
	separate consumer of the one-off.

	Uses Main Job Type + Main Job (Sea Shipment → parent Sea Booking; Air Shipment → parent Air Booking;
	Transport Job / Declaration → freight links on that job).
	"""
	from frappe.utils import cint

	if not cint(getattr(doc, "is_internal_job", 0)):
		return None, None
	mjt = (getattr(doc, "main_job_type", None) or "").strip()
	mj = (getattr(doc, "main_job", None) or "").strip()
	if not mj:
		return None, None
	allow_sea = None
	allow_air = None
	try:
		if mjt == "Sea Shipment":
			allow_sea = frappe.db.get_value("Sea Shipment", mj, "sea_booking")
		elif mjt == "Air Shipment":
			allow_air = frappe.db.get_value("Air Shipment", mj, "air_booking")
		elif mjt == "Transport Job":
			tj = frappe.db.get_value(
				"Transport Job",
				mj,
				["sea_shipment", "air_shipment"],
				as_dict=True,
			)
			if tj:
				if tj.get("sea_shipment"):
					allow_sea = frappe.db.get_value("Sea Shipment", tj["sea_shipment"], "sea_booking")
				if tj.get("air_shipment"):
					allow_air = frappe.db.get_value("Air Shipment", tj["air_shipment"], "air_booking")
		elif mjt == "Declaration":
			dec = frappe.db.get_value(
				"Declaration",
				mj,
				["sea_shipment", "air_shipment"],
				as_dict=True,
			)
			if dec:
				if dec.get("sea_shipment"):
					allow_sea = frappe.db.get_value("Sea Shipment", dec["sea_shipment"], "sea_booking")
				if dec.get("air_shipment"):
					allow_air = frappe.db.get_value("Air Shipment", dec["air_shipment"], "air_booking")
	except Exception:
		return None, None
	return allow_sea, allow_air


def resolve_single_main_sea_booking_for_sales_quote(sales_quote_name):
	"""If exactly one non-cancelled main Sea Booking references this Sales Quote, return its name.

	Used when a Sea Shipment carries the quote but ``sea_booking`` is not set yet.
	"""
	if not sales_quote_name:
		return None
	cand = frappe.get_all(
		"Sea Booking",
		filters={
			"docstatus": ["!=", 2],
			"is_main_service": 1,
			"sales_quote": sales_quote_name,
		},
		pluck="name",
		limit=2,
	)
	return cand[0] if len(cand) == 1 else None


def resolve_single_main_air_booking_for_sales_quote(sales_quote_name):
	"""If exactly one non-cancelled main Air Booking references this Sales Quote, return its name."""
	if not sales_quote_name:
		return None
	cand = frappe.get_all(
		"Air Booking",
		filters={
			"docstatus": ["!=", 2],
			"is_main_service": 1,
			"sales_quote": sales_quote_name,
		},
		pluck="name",
		limit=2,
	)
	return cand[0] if len(cand) == 1 else None


# Main-service ops docs allowed to share a one-off quote already converted to a Declaration Order (same job chain).
_DOCTYPES_MAIN_SERVICE_WITH_DECLARATION_ORDER_CONVERSION = frozenset(
	(
		"Transport Order",
		"Sea Shipment",
		"Air Shipment",
		"Sea Booking",
		"Air Booking",
	)
)


def validate_one_off_quote_not_converted(
	sales_quote_name: str,
	current_doctype: str = None,
	current_docname: str = None,
	allow_if_quote_converted_to: str = None,
	allow_linked_sea_booking: str = None,
	allow_linked_air_booking: str = None,
		allow_main_transport_if_converted_to_declaration_order: bool = False,
):
	"""
	Validate that One-off Sales Quote is not already converted or linked to another document.
	Raises exception if converted or already in use.
	
	Args:
		sales_quote_name: Name of the Sales Quote
		current_doctype: Doctype of the current document (to exclude from check)
		current_docname: Name of the current document (to exclude from check)
		allow_if_quote_converted_to: If the quote was converted to this doc ref (e.g. "Declaration Order DCO-001"),
			allow use — used when the current document is the next step in the same chain (e.g. Declaration from that Order).
		allow_linked_sea_booking: Sea Booking name that may hold the same quote as this doc (e.g. Sea Shipment's parent booking, or main Sea leg for an internal-job Transport Order).
		allow_linked_air_booking: Air Booking name for the same job chain (e.g. Air Shipment's parent booking).
		allow_main_transport_if_converted_to_declaration_order: If True and current doc is a main-service Transport Order,
			Sea/Air Shipment, or Sea/Air Booking, allow when the quote is already marked converted to a Declaration Order
			(customs leg submitted first; freight main leg is part of the same job chain). For Transport Order, this
			may also be True for an internal-job order when it is tied to the same chain (caller passes True only if
			linked Sea/Air booking resolution succeeded).
		
	Raises:
		frappe.ValidationError: If quote is already converted or linked to another document
	"""
	if not sales_quote_name:
		return
	
	try:
		# Get the Sales Quote
		sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
		
		# Only validate if it's a One-off quote
		if sales_quote.quotation_type != "One-off":
			return
		
		# Check if already converted (but allow if converted to *this* document — e.g. re-saving the same order)
		if sales_quote.status == "Converted" or sales_quote.converted_to_doc:
			current_doc_ref = f"{current_doctype or ''} {current_docname or ''}".strip()
			converted_ref = (sales_quote.converted_to_doc or "").strip()
			if current_doc_ref and converted_ref and current_doc_ref == converted_ref:
				return  # Same document that converted the quote — allow save
			# Same conversion chain: e.g. quote was converted to Declaration Order X, current doc is Declaration from that Order
			if allow_if_quote_converted_to and converted_ref and converted_ref == allow_if_quote_converted_to.strip():
				return
			# Main freight/transport leg alongside a submitted Declaration Order (one-off quote covers customs + freight)
			if (
				allow_main_transport_if_converted_to_declaration_order
				and (current_doctype or "") in _DOCTYPES_MAIN_SERVICE_WITH_DECLARATION_ORDER_CONVERSION
				and converted_ref
				and converted_ref.startswith("Declaration Order ")
			):
				return
			converted_info = sales_quote.converted_to_doc or _("Unknown document")
			frappe.throw(
				_("One-off Sales Quote '{0}' has already been converted ({1}) and cannot be used with another document.").format(
					sales_quote_name,
					converted_info
				),
				title=_("Quote Already Converted")
			)
		
		# Check if already linked to another document (even if not yet converted)
		# This prevents the same quote from being used in multiple documents
		linked_documents = []
		
		# Check Air Booking — main-service bookings "consume" the one-off link.
		air_bookings = frappe.get_all(
			"Air Booking",
			filters={
				"name": ["!=", current_docname or ""],
				"docstatus": ["!=", 2],  # Exclude cancelled documents
				"is_main_service": 1,
				"sales_quote": sales_quote_name,
			},
			fields=["name", "docstatus"],
			limit=1
		)
		if air_bookings:
			abn = (air_bookings[0].name or "").strip()
			if allow_linked_air_booking and abn == (allow_linked_air_booking or "").strip():
				pass  # Same quote on parent booking + shipment is one job chain
			else:
				linked_documents.append(f"Air Booking: {abn}")
		
		# Check Sea Booking — main-service bookings "consume" the one-off link.
		sea_bookings = frappe.get_all(
			"Sea Booking",
			filters={
				"name": ["!=", current_docname or ""],
				"docstatus": ["!=", 2],  # Exclude cancelled documents
				"is_main_service": 1,
				"sales_quote": sales_quote_name,
			},
			fields=["name", "docstatus"],
			limit=1
		)
		if sea_bookings:
			sbn = (sea_bookings[0].name or "").strip()
			if allow_linked_sea_booking and sbn == (allow_linked_sea_booking or "").strip():
				pass  # Same quote on parent booking + shipment is one job chain
			else:
				linked_documents.append(f"Sea Booking: {sbn}")
		
		# Check Transport Order (main service only — same one-off exclusivity rule as freight bookings)
		transport_orders = frappe.get_all(
			"Transport Order",
			filters={
				"sales_quote": sales_quote_name,
				"name": ["!=", current_docname or ""],
				"docstatus": ["!=", 2],  # Exclude cancelled documents
				"is_main_service": 1,
			},
			fields=["name", "docstatus"],
			limit=1
		)
		if transport_orders:
			linked_documents.append(f"Transport Order: {transport_orders[0].name}")
		
		# Check Warehouse Contract
		warehouse_contracts = frappe.get_all(
			"Warehouse Contract",
			filters={
				"sales_quote": sales_quote_name,
				"name": ["!=", current_docname or ""],
				"docstatus": ["!=", 2]  # Exclude cancelled documents
			},
			fields=["name", "docstatus"],
			limit=1
		)
		if warehouse_contracts:
			linked_documents.append(f"Warehouse Contract: {warehouse_contracts[0].name}")
		
		# Check Declaration (main service only)
		declarations = frappe.get_all(
			"Declaration",
			filters={
				"sales_quote": sales_quote_name,
				"name": ["!=", current_docname or ""],
				"docstatus": ["!=", 2],  # Exclude cancelled documents
				"is_main_service": 1,
			},
			fields=["name", "docstatus"],
			limit=1
		)
		if declarations:
			linked_documents.append(f"Declaration: {declarations[0].name}")
		
		# If quote is already linked to another document, throw error
		if linked_documents:
			doc_list = ", ".join(linked_documents)
			frappe.throw(
				_("One-off Sales Quote '{0}' is already linked to another document ({1}) and cannot be used again. Each One-off quote can only be used once.").format(
					sales_quote_name,
					doc_list
				),
				title=_("Quote Already In Use")
			)
		
	except frappe.DoesNotExistError:
		# Sales Quote doesn't exist, skip validation
		pass
	except frappe.ValidationError:
		# Re-raise validation errors
		raise
	except Exception as e:
		frappe.log_error(
			f"Error validating One-off Sales Quote {sales_quote_name}: {str(e)}",
			"One-off Quote Validation Error"
		)


@frappe.whitelist()
def extend_sales_quote_validity(sales_quote, valid_until):
	"""
	Extend Sales Quote Valid Until. Draft quotes are saved; submitted quotes get a direct DB update
	so the field can change without amending the full document.
	"""
	if not sales_quote:
		frappe.throw(_("Sales Quote is required."))
	frappe.has_permission("Sales Quote", "write", doc=sales_quote, throw=True)

	doc = frappe.get_doc("Sales Quote", sales_quote)
	if doc.docstatus == 2:
		frappe.throw(_("Cannot extend validity of a cancelled Sales Quote."))

	new_vu = getdate(valid_until)
	today_d = getdate(today())
	if new_vu < today_d:
		frappe.throw(_("New Valid Until cannot be before today."), title=_("Invalid Date"))

	old_vu = getattr(doc, "valid_until", None)
	if old_vu:
		old_d = getdate(old_vu)
		if new_vu <= old_d:
			frappe.throw(
				_("New Valid Until must be after the current Valid Until ({0}).").format(format_date(old_d)),
				title=_("Invalid Extension"),
			)

	if doc.docstatus == 0:
		doc.valid_until = new_vu
		doc.save()
	else:
		frappe.db.set_value("Sales Quote", doc.name, "valid_until", new_vu, update_modified=True)

	return {
		"success": True,
		"valid_until": str(new_vu),
		"message": _("Valid Until extended to {0}.").format(format_date(new_vu)),
	}


@frappe.whitelist()
def recalculate_charges(docname):
	"""Recalculate all charges in Sales Quote charges table using RateCalculationEngine."""
	doc = frappe.get_doc("Sales Quote", docname)
	lines_recalculated = 0

	for row in doc.charges or []:
		if hasattr(row, "calculate_quantities"):
			row.calculate_quantities()
		if hasattr(row, "calculate_estimated_revenue"):
			row.calculate_estimated_revenue()
		if hasattr(row, "calculate_estimated_cost"):
			row.calculate_estimated_cost()
		lines_recalculated += 1

	doc.save()
	return {
		"success": True,
		"message": _("Successfully recalculated {0} charge line(s)").format(lines_recalculated),
		"lines_recalculated": lines_recalculated,
	}


@frappe.whitelist()
def get_cost_sheet_charges_for_selection(
	sales_quote,
	cost_sheet=None,
	service_type=None,
	charge_group=None,
	origin_port=None,
	destination_port=None,
	load_type=None,
	transport_mode=None,
):
	"""
	Return Cost Sheet charges for user selection, filtered by charge parameters.
	Cost Sheet is optional; when omitted, queries across all submitted Cost Sheets.
	"""
	if not sales_quote:
		frappe.throw(_("Sales Quote is required."))

	# Build filters for Cost Sheet Charge
	filters = [["parenttype", "=", "Cost Sheet"]]
	if cost_sheet:
		filters.append(["parent", "=", cost_sheet])
	else:
		# Only submitted Cost Sheets
		submitted = frappe.get_all("Cost Sheet", filters={"docstatus": 1}, pluck="name")
		if not submitted:
			return {"charges": []}
		filters.append(["parent", "in", submitted])

	if service_type:
		filters.append(["service_type", "=", service_type])
	if charge_group:
		filters.append(["charge_group", "=", charge_group])
	if origin_port:
		filters.append(["origin_port", "=", origin_port])
	if destination_port:
		filters.append(["destination_port", "=", destination_port])
	if load_type:
		filters.append(["load_type", "=", load_type])
	if transport_mode:
		filters.append(["transport_mode", "=", transport_mode])

	rows = frappe.get_all(
		"Cost Sheet Charge",
		filters=filters,
		fields=["name", "parent", "item_code", "item_name", "service_type", "charge_group", "charge_category",
			"unit_cost", "cost_currency", "cost_calculation_method", "cost_unit_type", "cost_minimum_quantity",
			"cost_minimum_charge", "cost_maximum_charge", "cost_base_amount", "cost_uom",
			"origin_port", "destination_port", "load_type", "transport_mode", "direction",
			"airline", "freight_agent", "shipping_line", "freight_agent_sea",
			"vehicle_type", "container_type", "location_type", "location_from", "location_to",
			"customs_authority", "declaration_type", "customs_broker", "pay_to"]
	)

	# Get Cost Sheet header details for each unique parent
	cs_names = list({r.get("parent") for r in rows if r.get("parent")})
	cs_headers = {}
	if cs_names:
		for cs in frappe.get_all(
			"Cost Sheet",
			filters={"name": ["in", cs_names]},
			fields=["name", "provider_type", "provider_name", "valid_from", "valid_to", "currency", "description"]
		):
			cs_headers[cs["name"]] = cs

	charges = []
	for idx, row in enumerate(rows):
		if not row.get("item_code") or not row.get("service_type"):
			continue
		parent = row.get("parent")
		cs_header = cs_headers.get(parent) or {}
		cs_currency = row.get("cost_currency") or (cs_header.get("currency") if cs_header else None)
		charges.append({
			"name": row.get("name"),
			"cost_sheet": parent,
			"provider_type": cs_header.get("provider_type"),
			"provider_name": cs_header.get("provider_name"),
			"valid_from": cs_header.get("valid_from"),
			"valid_to": cs_header.get("valid_to"),
			"cost_sheet_description": cs_header.get("description"),
			"idx": idx + 1,
			"item_code": row.get("item_code"),
			"item_name": row.get("item_name"),
			"service_type": row.get("service_type"),
			"charge_group": row.get("charge_group") or "",
			"charge_category": row.get("charge_category") or "",
			"unit_cost": flt(row.get("unit_cost")),
			"cost_currency": cs_currency,
			"cost_calculation_method": row.get("cost_calculation_method"),
			"cost_unit_type": row.get("cost_unit_type"),
			"cost_minimum_quantity": row.get("cost_minimum_quantity"),
			"cost_minimum_charge": row.get("cost_minimum_charge"),
			"cost_maximum_charge": row.get("cost_maximum_charge"),
			"cost_base_amount": row.get("cost_base_amount"),
			"cost_uom": row.get("cost_uom"),
			"origin_port": row.get("origin_port"),
			"destination_port": row.get("destination_port"),
			"load_type": row.get("load_type"),
			"transport_mode": row.get("transport_mode"),
			"direction": row.get("direction"),
			"airline": row.get("airline"),
			"freight_agent": row.get("freight_agent"),
			"shipping_line": row.get("shipping_line"),
			"freight_agent_sea": row.get("freight_agent_sea"),
			"vehicle_type": row.get("vehicle_type"),
			"container_type": row.get("container_type"),
			"location_type": row.get("location_type"),
			"location_from": row.get("location_from"),
			"location_to": row.get("location_to"),
			"customs_authority": row.get("customs_authority"),
			"declaration_type": row.get("declaration_type"),
			"customs_broker": row.get("customs_broker"),
			"pay_to": row.get("pay_to"),
		})
	return {"charges": charges}


@frappe.whitelist()
def get_rates_from_cost_sheet(sales_quote, selected_charge_names=None):
	"""
	Populate cost fields in Sales Quote charges from selected Cost Sheet charges.
	selected_charge_names: list of Cost Sheet Charge docnames to fetch. Each charge's parent is the Cost Sheet.
	"""
	if not sales_quote:
		frappe.throw(_("Sales Quote is required."))
	if not selected_charge_names:
		frappe.throw(_("Please select at least one charge to fetch."))

	if isinstance(selected_charge_names, str):
		selected_charge_names = frappe.parse_json(selected_charge_names)
	if not selected_charge_names:
		frappe.throw(_("Please select at least one charge to fetch."))

	sq_doc = frappe.get_doc("Sales Quote", sales_quote)
	selected = set(selected_charge_names)

	# Load selected Cost Sheet Charge rows (each has parent = Cost Sheet)
	rows = frappe.get_all(
		"Cost Sheet Charge",
		filters={"name": ["in", list(selected)]},
		fields=["name", "parent", "item_code", "item_name", "service_type", "charge_group", "charge_category",
			"cost_calculation_method", "unit_cost", "cost_unit_type", "cost_currency", "cost_minimum_quantity",
			"cost_minimum_charge", "cost_maximum_charge", "cost_base_amount", "cost_uom",
			"origin_port", "destination_port", "load_type", "transport_mode", "direction",
			"airline", "freight_agent", "shipping_line", "freight_agent_sea",
			"vehicle_type", "container_type", "location_type", "location_from", "location_to",
			"customs_authority", "declaration_type", "customs_broker", "pay_to"]
	)

	# Get Cost Sheet currency for rows missing cost_currency
	cs_currencies = {}
	for row in rows:
		cs = row.get("parent")
		if cs and cs not in cs_currencies:
			cs_currencies[cs] = frappe.db.get_value("Cost Sheet", cs, "currency")

	# Add each selected charge as a new row (do not update existing)
	added = 0
	for cs_row in rows:
		item = cs_row.get("item_code")
		svc = cs_row.get("service_type")
		if not item or not svc:
			continue
		cs_currency = cs_currencies.get(cs_row.get("parent"))
		new_row = sq_doc.append("charges", {
			"service_type": svc,
			"charge_group": cs_row.get("charge_group"),
			"item_code": item,
			"charge_category": cs_row.get("charge_category"),
			"charge_type": "Cost",
			"cost_calculation_method": cs_row.get("cost_calculation_method"),
			"unit_cost": flt(cs_row.get("unit_cost")),
			"cost_unit_type": cs_row.get("cost_unit_type"),
			"cost_currency": cs_row.get("cost_currency") or cs_currency,
			"cost_minimum_quantity": flt(cs_row.get("cost_minimum_quantity")),
			"cost_minimum_charge": flt(cs_row.get("cost_minimum_charge")),
			"cost_maximum_charge": flt(cs_row.get("cost_maximum_charge")),
			"cost_base_amount": flt(cs_row.get("cost_base_amount")),
			"cost_uom": cs_row.get("cost_uom"),
			"cost_sheet_source": cs_row.get("parent"),
		})
		# Populate all parameters (from Cost Sheet charge, or from Sales Quote header for One-off)
		header_params = {}
		if sq_doc.quotation_type == "One-off":
			header_params = {
				"origin_port": getattr(sq_doc, "origin_port", None),
				"destination_port": getattr(sq_doc, "destination_port", None),
				"load_type": getattr(sq_doc, "load_type", None),
				"transport_mode": getattr(sq_doc, "transport_mode", None),
				"direction": getattr(sq_doc, "direction", None),
				"airline": getattr(sq_doc, "airline", None),
				"freight_agent": getattr(sq_doc, "freight_agent", None),
				"shipping_line": getattr(sq_doc, "shipping_line", None),
				"freight_agent_sea": getattr(sq_doc, "freight_agent_sea", None),
				"location_type": getattr(sq_doc, "location_type", None),
				"location_from": getattr(sq_doc, "location_from", None),
				"location_to": getattr(sq_doc, "location_to", None),
				"transport_template": getattr(sq_doc, "transport_template", None),
				"vehicle_type": getattr(sq_doc, "vehicle_type", None),
				"container_type": getattr(sq_doc, "container_type", None),
			}
		for f in ("origin_port", "destination_port", "load_type", "transport_mode", "direction",
			"airline", "freight_agent", "shipping_line", "freight_agent_sea",
			"vehicle_type", "container_type", "location_type", "location_from", "location_to",
			"customs_authority", "declaration_type", "customs_broker", "pay_to"):
			val = cs_row.get(f) or header_params.get(f)
			if val:
				new_row.set(f, val)
		added += 1

	sq_doc.save()
	msg = _("Added {0} charge line(s) from Cost Sheet.").format(added)
	return {
		"success": True,
		"message": msg,
		"added": added,
	}
