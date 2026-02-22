# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today, getdate


class OneOffQuote(Document):
	def before_validate(self):
		"""Normalize legacy house_type values before validation"""
		# Normalize legacy house_type values BEFORE validation runs
		if hasattr(self, 'sea_house_type') and self.sea_house_type:
			if self.sea_house_type == "Direct":
				self.sea_house_type = "Standard House"
			elif self.sea_house_type == "Consolidation":
				self.sea_house_type = "Co-load Master"
		
		if hasattr(self, 'air_house_type') and self.air_house_type:
			if self.air_house_type == "Direct":
				self.air_house_type = "Standard House"
			elif self.air_house_type == "Consolidation":
				self.air_house_type = "Co-load Master"
	
	def validate(self):
		"""One-Off Quote: one conversion per quote; when Converted, converted_to_doc must be set."""
		# Normalize legacy house_type values (backup, in case before_validate didn't run)
		if hasattr(self, 'sea_house_type') and self.sea_house_type:
			if self.sea_house_type == "Direct":
				self.sea_house_type = "Standard House"
			elif self.sea_house_type == "Consolidation":
				self.sea_house_type = "Co-load Master"
		
		if hasattr(self, 'air_house_type') and self.air_house_type:
			if self.air_house_type == "Direct":
				self.air_house_type = "Standard House"
			elif self.air_house_type == "Consolidation":
				self.air_house_type = "Co-load Master"
		
		if self.status == "Converted" and not self.converted_to_doc:
			frappe.throw(_("Status is Converted but Converted To is not set."))

	@frappe.whitelist()
	def create_transport_order(self):
		"""Create a Transport Order from this One-Off Quote (is_transport must be set). One conversion per quote."""
		if not getattr(self, "is_transport", False):
			frappe.throw(_("Only One-Off Quotes with Transport enabled can create Transport Orders."))
		if self.status == "Converted" and self.converted_to_doc:
			frappe.throw(_("This One-Off Quote has already been converted to {0}.").format(self.converted_to_doc))

		from logistics.transport.doctype.transport_order.transport_order import _sync_quote_and_sales_quote

		transport_order = frappe.new_doc("Transport Order")
		transport_order.customer = self.customer
		transport_order.booking_date = today()
		transport_order.scheduled_date = today()
		transport_order.quote_type = "One-Off Quote"
		transport_order.quote = self.name
		_sync_quote_and_sales_quote(transport_order)

		transport_order.transport_template = getattr(self, "transport_template", None)
		transport_order.load_type = getattr(self, "load_type", None)
		transport_order.vehicle_type = getattr(self, "vehicle_type", None)
		transport_order.container_type = getattr(self, "container_type", None)
		transport_order.company = self.company
		transport_order.branch = self.branch
		transport_order.cost_center = self.cost_center
		transport_order.profit_center = self.profit_center
		transport_order.location_type = getattr(self, "location_type", None)
		transport_order.location_from = getattr(self, "location_from", None)
		transport_order.location_to = getattr(self, "location_to", None)

		# Determine transport_job_type from load_type to ensure compatibility
		transport_order.transport_job_type = self._determine_transport_job_type(
			current_job_type=None,
			load_type=transport_order.load_type,
			container_type=transport_order.container_type
		)

		transport_order.flags.skip_container_no_validation = True
		transport_order.flags.skip_container_type_validation = True
		transport_order.flags.skip_vehicle_type_validation = True
		transport_order.flags.skip_sales_quote_on_change = True

		transport_order.insert(ignore_permissions=True)
		transport_order.reload()
		transport_order.quote_type = "One-Off Quote"
		transport_order.quote = self.name
		_sync_quote_and_sales_quote(transport_order)
		
		# Populate charges from One-Off Quote Transport
		transport_order._populate_charges_from_one_off_quote()
		
		transport_order.save(ignore_permissions=True)

		self.status = "Converted"
		self.converted_to_doc = f"Transport Order: {transport_order.name}"
		self.db_update()

		frappe.db.commit()
		return {"success": True, "transport_order": transport_order.name, "message": _("Transport Order {0} created.").format(transport_order.name)}

	@frappe.whitelist()
	def create_air_booking(self):
		"""Create an Air Booking from this One-Off Quote (is_air must be set). One conversion per quote."""
		if not getattr(self, "is_air", False):
			frappe.throw(_("Only One-Off Quotes with Air enabled can create Air Bookings."))
		if self.status == "Converted" and self.converted_to_doc:
			frappe.throw(_("This One-Off Quote has already been converted to {0}.").format(self.converted_to_doc))

		origin = getattr(self, "origin_port", None)
		dest = getattr(self, "destination_port", None)
		if not origin or not dest:
			frappe.throw(_("Origin Port and Destination Port are required for Air mode."))
		
		shipper = getattr(self, "shipper", None)
		consignee = getattr(self, "consignee", None)
		if not shipper:
			frappe.throw(_("Shipper is required for Air mode."))
		if not consignee:
			frappe.throw(_("Consignee is required for Air mode."))

		air_booking = frappe.new_doc("Air Booking")
		air_booking.booking_date = today()
		air_booking.local_customer = self.customer
		air_booking.quote_type = "One-Off Quote"
		air_booking.quote = self.name
		air_booking.sales_quote = None
		air_booking.origin_port = origin
		air_booking.destination_port = dest
		air_booking.direction = getattr(self, "air_direction", None) or "Export"
		air_booking.shipper = shipper
		air_booking.consignee = consignee
		
		# Validate and set airline if it exists
		airline = getattr(self, "airline", None)
		if airline and frappe.db.exists("Airline", airline):
			air_booking.airline = airline
		
		# Validate and set freight_agent if it exists
		freight_agent = getattr(self, "freight_agent", None)
		if freight_agent and frappe.db.exists("Freight Agent", freight_agent):
			air_booking.freight_agent = freight_agent
		elif freight_agent:
			# Log warning if freight_agent was set but doesn't exist
			frappe.log_error(
				_("Freight Agent '{0}' from One-Off Quote '{1}' does not exist. Skipping freight_agent on Air Booking.").format(
					freight_agent, self.name
				),
				"One-Off Quote: Invalid Freight Agent"
			)
		
		air_booking.house_type = getattr(self, "air_house_type", None)  # header param
		air_booking.company = self.company
		air_booking.branch = self.branch
		air_booking.cost_center = self.cost_center
		air_booking.profit_center = self.profit_center

		air_booking.insert(ignore_permissions=True)
		air_booking.reload()
		air_booking.quote_type = "One-Off Quote"
		air_booking.quote = self.name
		from logistics.air_freight.doctype.air_booking.air_booking import _sync_quote_and_sales_quote
		_sync_quote_and_sales_quote(air_booking)
		air_booking.save(ignore_permissions=True)

		self.status = "Converted"
		self.converted_to_doc = f"Air Booking: {air_booking.name}"
		self.db_update()

		frappe.db.commit()
		return {"success": True, "air_booking": air_booking.name, "message": _("Air Booking {0} created.").format(air_booking.name)}

	@frappe.whitelist()
	def create_sea_booking(self):
		"""Create a Sea Booking from this One-Off Quote (is_sea must be set). One conversion per quote."""
		if not getattr(self, "is_sea", False):
			frappe.throw(_("Only One-Off Quotes with Sea enabled can create Sea Bookings."))
		if self.status == "Converted" and self.converted_to_doc:
			frappe.throw(_("This One-Off Quote has already been converted to {0}.").format(self.converted_to_doc))

		# Sea tab may not have header origin/dest in same layout as Sales Quote; allow from first leg if needed
		origin = getattr(self, "origin_port_sea", None) or getattr(self, "origin_port", None)
		dest = getattr(self, "destination_port_sea", None) or getattr(self, "destination_port", None)
		if not origin or not dest:
			frappe.throw(_("Origin Port and Destination Port are required for Sea. Add them to the Sea tab or use Air tab ports."))
		
		# Get shipper and consignee (required for Sea Booking)
		shipper = getattr(self, "shipper", None)
		consignee = getattr(self, "consignee", None)
		if not shipper:
			frappe.throw(_("Shipper is required for Sea mode."))
		if not consignee:
			frappe.throw(_("Consignee is required for Sea mode."))

		sea_booking = frappe.new_doc("Sea Booking")
		sea_booking.booking_date = today()
		sea_booking.local_customer = self.customer
		sea_booking.quote_type = "One-Off Quote"
		sea_booking.quote = self.name
		sea_booking.sales_quote = None
		sea_booking.origin_port = origin
		sea_booking.destination_port = dest
		sea_booking.direction = getattr(self, "sea_direction", None) or "Export"
		sea_booking.transport_mode = getattr(self, "sea_transport_mode", None) or "FCL"
		sea_booking.shipper = shipper
		sea_booking.consignee = consignee
		
		# Validate and set shipping_line if it exists
		shipping_line = getattr(self, "shipping_line", None)
		if shipping_line and frappe.db.exists("Shipping Line", shipping_line):
			sea_booking.shipping_line = shipping_line
		
		# Validate and set freight_agent if it exists
		freight_agent_sea = getattr(self, "freight_agent_sea", None)
		if freight_agent_sea and frappe.db.exists("Freight Agent", freight_agent_sea):
			sea_booking.freight_agent = freight_agent_sea
		elif freight_agent_sea:
			# Log warning if freight_agent_sea was set but doesn't exist
			frappe.log_error(
				_("Freight Agent '{0}' from One-Off Quote '{1}' does not exist. Skipping freight_agent on Sea Booking.").format(
					freight_agent_sea, self.name
				),
				"One-Off Quote: Invalid Freight Agent"
			)
		
		# Set house_type from One-Off Quote if available
		sea_house_type = getattr(self, "sea_house_type", None)
		if sea_house_type:
			# Normalize legacy values before setting
			if sea_house_type == "Direct":
				sea_house_type = "Standard House"
			elif sea_house_type == "Consolidation":
				sea_house_type = "Co-load Master"
			sea_booking.house_type = sea_house_type
		
		sea_booking.company = self.company
		sea_booking.branch = self.branch
		sea_booking.cost_center = self.cost_center
		sea_booking.profit_center = self.profit_center

		sea_booking.insert(ignore_permissions=True)
		sea_booking.reload()
		sea_booking.quote_type = "One-Off Quote"
		sea_booking.quote = self.name
		from logistics.sea_freight.doctype.sea_booking.sea_booking import _sync_quote_and_sales_quote
		_sync_quote_and_sales_quote(sea_booking)
		# Populate charges from One-Off Quote Sea Freight (on_update only runs when quote/quote_type change, so we must call explicitly on conversion)
		sea_booking._populate_charges_from_one_off_quote()
		sea_booking.save(ignore_permissions=True)

		self.status = "Converted"
		self.converted_to_doc = f"Sea Booking: {sea_booking.name}"
		self.db_update()

		frappe.db.commit()
		return {"success": True, "sea_booking": sea_booking.name, "message": _("Sea Booking {0} created.").format(sea_booking.name)}

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
				# If only Container is allowed but container_type is missing, default to Non-Container
				# (validation will catch this later if needed)
				return "Non-Container"
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
					# If only Container is allowed but container_type is missing, default to Non-Container
					return "Non-Container"
				return current_job_type
			else:
				# Current job type is not allowed for this load_type, find an alternative
				return find_best_job_type()
		
		# No job type set, determine default based on load_type's allowed job types
		return find_best_job_type()


@frappe.whitelist()
def create_transport_order(one_off_quote_name):
	"""Create Transport Order from One-Off Quote (for use from JS dialog)."""
	doc = frappe.get_doc("One-Off Quote", one_off_quote_name)
	return doc.create_transport_order()


@frappe.whitelist()
def create_air_booking(one_off_quote_name):
	"""Create Air Booking from One-Off Quote (for use from JS dialog)."""
	doc = frappe.get_doc("One-Off Quote", one_off_quote_name)
	return doc.create_air_booking()


@frappe.whitelist()
def create_sea_booking(one_off_quote_name):
	"""Create Sea Booking from One-Off Quote (for use from JS dialog)."""
	doc = frappe.get_doc("One-Off Quote", one_off_quote_name)
	return doc.create_sea_booking()
