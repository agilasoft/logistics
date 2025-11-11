# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate, nowdate, now_datetime


class GlobalManifest(Document):
	def validate(self):
		"""Validate global manifest data"""
		if self.etd and self.eta:
			if getdate(self.etd) > getdate(self.eta):
				frappe.throw(_("ETD (Expected Departure) cannot be after ETA (Expected Arrival)."))
		
		# Validate that at least one shipment is linked
		if not self.sea_shipment and not self.air_shipment and not self.transport_order:
			frappe.msgprint(
				_("No shipment linked. Consider linking a Sea Shipment, Air Shipment, or Transport Order."),
				indicator="orange",
				title=_("No Shipment Linked")
			)
	
	def before_save(self):
		"""Auto-update dates and populate from linked shipments"""
		self.update_status_dates()
		self.populate_from_shipment()
	
	def update_status_dates(self):
		"""Update submission and acceptance dates based on status"""
		if self.status == "Submitted" and not self.submission_date:
			self.submission_date = nowdate()
			if not self.submission_time:
				self.submission_time = now_datetime().strftime("%H:%M:%S")
		elif self.status == "Accepted" and not self.acceptance_date:
			self.acceptance_date = nowdate()
	
	def populate_from_shipment(self):
		"""Auto-populate fields from linked shipment if not already set"""
		# Only populate if key fields are not already set
		if self.sea_shipment and not self.vessel_flight_number:
			self._populate_from_sea_shipment()
		elif self.air_shipment and not self.vessel_flight_number:
			self._populate_from_air_shipment()
		elif self.transport_order and not self.port_of_loading:
			self._populate_from_transport_order()
	
	def _populate_from_sea_shipment(self):
		"""Populate from Sea Shipment"""
		try:
			sea_shipment = frappe.get_doc("Sea Shipment", self.sea_shipment)
			
			if not self.vessel_flight_number and sea_shipment.vessel_name:
				self.vessel_flight_number = sea_shipment.vessel_name
			
			if not self.voyage_number and sea_shipment.voyage_number:
				self.voyage_number = sea_shipment.voyage_number
			
			if not self.port_of_loading and sea_shipment.origin_port:
				self.port_of_loading = sea_shipment.origin_port
			
			if not self.port_of_discharge and sea_shipment.destination_port:
				self.port_of_discharge = sea_shipment.destination_port
			
			if not self.etd and sea_shipment.etd:
				self.etd = sea_shipment.etd
			
			if not self.eta and sea_shipment.eta:
				self.eta = sea_shipment.eta
			
			if not self.country and sea_shipment.destination_country:
				self.country = sea_shipment.destination_country
			
			if not self.carrier and sea_shipment.shipping_line:
				# Try to get supplier from shipping line
				carrier = frappe.db.get_value("Shipping Line", sea_shipment.shipping_line, "supplier")
				if carrier:
					self.carrier = carrier
		except frappe.DoesNotExistError:
			pass
	
	def _populate_from_air_shipment(self):
		"""Populate from Air Shipment"""
		try:
			air_shipment = frappe.get_doc("Air Shipment", self.air_shipment)
			
			if not self.vessel_flight_number and air_shipment.flight_number:
				self.vessel_flight_number = air_shipment.flight_number
			
			if not self.voyage_number and air_shipment.flight_number:
				self.voyage_number = air_shipment.flight_number
			
			if not self.port_of_loading and air_shipment.origin_airport:
				self.port_of_loading = air_shipment.origin_airport
			
			if not self.port_of_discharge and air_shipment.destination_airport:
				self.port_of_discharge = air_shipment.destination_airport
			
			if not self.etd and air_shipment.etd:
				self.etd = air_shipment.etd
			
			if not self.eta and air_shipment.eta:
				self.eta = air_shipment.eta
			
			if not self.country and air_shipment.destination_country:
				self.country = air_shipment.destination_country
			
			if not self.carrier and air_shipment.airline:
				# Try to get supplier from airline
				carrier = frappe.db.get_value("Airline", air_shipment.airline, "supplier")
				if carrier:
					self.carrier = carrier
		except frappe.DoesNotExistError:
			pass
	
	def _populate_from_transport_order(self):
		"""Populate from Transport Order"""
		try:
			transport_order = frappe.get_doc("Transport Order", self.transport_order)
			
			if not self.port_of_loading and transport_order.origin:
				self.port_of_loading = transport_order.origin
			
			if not self.port_of_discharge and transport_order.destination:
				self.port_of_discharge = transport_order.destination
			
			if not self.etd and transport_order.etd:
				self.etd = transport_order.etd
			
			if not self.eta and transport_order.eta:
				self.eta = transport_order.eta
		except frappe.DoesNotExistError:
			pass


# -------------------------------------------------------------------
# ACTION: Create Global Manifest from Sea Shipment
# -------------------------------------------------------------------
@frappe.whitelist()
def create_from_sea_shipment(sea_shipment_name: str) -> dict:
	"""
	Create a Global Manifest from a Sea Shipment.
	
	Args:
		sea_shipment_name: Name of the Sea Shipment
		
	Returns:
		dict: Result with created Global Manifest name and status
	"""
	try:
		sea_shipment = frappe.get_doc("Sea Shipment", sea_shipment_name)
		
		# Check if Global Manifest already exists
		existing_manifest = frappe.db.get_value("Global Manifest", {"sea_shipment": sea_shipment_name}, "name")
		if existing_manifest:
			return {
				"success": False,
				"message": _("Global Manifest {0} already exists for this Sea Shipment.").format(existing_manifest),
				"global_manifest": existing_manifest
			}
		
		# Create new Global Manifest
		manifest = frappe.new_doc("Global Manifest")
		
		# Set basic information
		manifest.manifest_type = "Import" if sea_shipment.direction == "Import" else "Export"
		manifest.sea_shipment = sea_shipment_name
		manifest.company = sea_shipment.company
		manifest.branch = getattr(sea_shipment, 'branch', None)
		
		# Populate from sea shipment
		manifest.vessel_flight_number = sea_shipment.vessel_name
		manifest.voyage_number = sea_shipment.voyage_number
		manifest.port_of_loading = sea_shipment.origin_port
		manifest.port_of_discharge = sea_shipment.destination_port
		manifest.etd = sea_shipment.etd
		manifest.eta = sea_shipment.eta
		manifest.country = sea_shipment.destination_country
		
		# Set carrier from shipping line
		if sea_shipment.shipping_line:
			carrier = frappe.db.get_value("Shipping Line", sea_shipment.shipping_line, "supplier")
			if carrier:
				manifest.carrier = carrier
		
		# Insert and save
		manifest.insert(ignore_permissions=True)
		manifest.save(ignore_permissions=True)
		
		return {
			"success": True,
			"global_manifest": manifest.name,
			"message": _("Global Manifest {0} created successfully from Sea Shipment.").format(manifest.name)
		}
		
	except frappe.DoesNotExistError:
		frappe.throw(_("Sea Shipment {0} does not exist.").format(sea_shipment_name))
	except Exception as e:
		frappe.log_error(f"Error creating Global Manifest from Sea Shipment: {str(e)}", "Global Manifest Creation Error")
		frappe.throw(_("Error creating Global Manifest: {0}").format(str(e)))


# -------------------------------------------------------------------
# ACTION: Create Global Manifest from Air Shipment
# -------------------------------------------------------------------
@frappe.whitelist()
def create_from_air_shipment(air_shipment_name: str) -> dict:
	"""
	Create a Global Manifest from an Air Shipment.
	
	Args:
		air_shipment_name: Name of the Air Shipment
		
	Returns:
		dict: Result with created Global Manifest name and status
	"""
	try:
		air_shipment = frappe.get_doc("Air Shipment", air_shipment_name)
		
		# Check if Global Manifest already exists
		existing_manifest = frappe.db.get_value("Global Manifest", {"air_shipment": air_shipment_name}, "name")
		if existing_manifest:
			return {
				"success": False,
				"message": _("Global Manifest {0} already exists for this Air Shipment.").format(existing_manifest),
				"global_manifest": existing_manifest
			}
		
		# Create new Global Manifest
		manifest = frappe.new_doc("Global Manifest")
		
		# Set basic information
		manifest.manifest_type = "Import" if air_shipment.direction == "Import" else "Export"
		manifest.air_shipment = air_shipment_name
		manifest.company = air_shipment.company
		manifest.branch = getattr(air_shipment, 'branch', None)
		
		# Populate from air shipment
		manifest.vessel_flight_number = air_shipment.flight_number
		manifest.voyage_number = air_shipment.flight_number
		manifest.port_of_loading = air_shipment.origin_airport
		manifest.port_of_discharge = air_shipment.destination_airport
		manifest.etd = air_shipment.etd
		manifest.eta = air_shipment.eta
		manifest.country = air_shipment.destination_country
		
		# Set carrier from airline
		if air_shipment.airline:
			carrier = frappe.db.get_value("Airline", air_shipment.airline, "supplier")
			if carrier:
				manifest.carrier = carrier
		
		# Insert and save
		manifest.insert(ignore_permissions=True)
		manifest.save(ignore_permissions=True)
		
		return {
			"success": True,
			"global_manifest": manifest.name,
			"message": _("Global Manifest {0} created successfully from Air Shipment.").format(manifest.name)
		}
		
	except frappe.DoesNotExistError:
		frappe.throw(_("Air Shipment {0} does not exist.").format(air_shipment_name))
	except Exception as e:
		frappe.log_error(f"Error creating Global Manifest from Air Shipment: {str(e)}", "Global Manifest Creation Error")
		frappe.throw(_("Error creating Global Manifest: {0}").format(str(e)))


# -------------------------------------------------------------------
# ACTION: Create Global Manifest from Transport Order
# -------------------------------------------------------------------
@frappe.whitelist()
def create_from_transport_order(transport_order_name: str) -> dict:
	"""
	Create a Global Manifest from a Transport Order.
	
	Args:
		transport_order_name: Name of the Transport Order
		
	Returns:
		dict: Result with created Global Manifest name and status
	"""
	try:
		transport_order = frappe.get_doc("Transport Order", transport_order_name)
		
		# Check if Global Manifest already exists
		existing_manifest = frappe.db.get_value("Global Manifest", {"transport_order": transport_order_name}, "name")
		if existing_manifest:
			return {
				"success": False,
				"message": _("Global Manifest {0} already exists for this Transport Order.").format(existing_manifest),
				"global_manifest": existing_manifest
			}
		
		# Create new Global Manifest
		manifest = frappe.new_doc("Global Manifest")
		
		# Set basic information
		manifest.manifest_type = "Transit"
		manifest.transport_order = transport_order_name
		manifest.company = transport_order.company
		manifest.branch = getattr(transport_order, 'branch', None)
		
		# Populate from transport order
		manifest.port_of_loading = transport_order.origin
		manifest.port_of_discharge = transport_order.destination
		manifest.etd = transport_order.etd
		manifest.eta = transport_order.eta
		
		# Insert and save
		manifest.insert(ignore_permissions=True)
		manifest.save(ignore_permissions=True)
		
		return {
			"success": True,
			"global_manifest": manifest.name,
			"message": _("Global Manifest {0} created successfully from Transport Order.").format(manifest.name)
		}
		
	except frappe.DoesNotExistError:
		frappe.throw(_("Transport Order {0} does not exist.").format(transport_order_name))
	except Exception as e:
		frappe.log_error(f"Error creating Global Manifest from Transport Order: {str(e)}", "Global Manifest Creation Error")
		frappe.throw(_("Error creating Global Manifest: {0}").format(str(e)))

