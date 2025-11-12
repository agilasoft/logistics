# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate, nowdate, now_datetime
import re


class CAeManifestForwarder(Document):
	def validate(self):
		"""Validate CA eManifest data"""
		# Validate CBSA carrier code format (alphanumeric, typically 4-6 characters)
		if self.carrier_code:
			if not re.match(r'^[A-Z0-9]{4,6}$', self.carrier_code.upper()):
				frappe.throw(_("CBSA Carrier Code must be 4-6 alphanumeric characters."))
		
		# Validate CRN format if provided (alphanumeric)
		if self.conveyance_reference_number:
			if not re.match(r'^[A-Z0-9]+$', self.conveyance_reference_number.upper()):
				frappe.throw(_("Conveyance Reference Number (CRN) must be alphanumeric."))
		
		# Validate submission type rules
		if self.submission_type == "Cancellation" and self.status != "Draft":
			frappe.throw(_("Only Draft eManifest can be cancelled."))
		
		if self.submission_type == "Amendment" and self.status not in ["Draft", "Accepted", "Amended"]:
			frappe.throw(_("Amendment can only be made to Draft, Accepted, or Amended eManifest."))
		
		# Validate required fields for submission
		if self.status == "Submitted":
			if not self.port_of_entry:
				frappe.throw(_("Port of Entry is required for submission."))
			if not self.carrier_code:
				frappe.throw(_("CBSA Carrier Code is required for submission."))
			if not self.conveyance_type:
				frappe.throw(_("Conveyance Type is required for submission."))
			if not self.conveyance_name:
				frappe.throw(_("Conveyance Name is required for submission."))
	
	def before_save(self):
		"""Auto-update dates and populate from Global Manifest"""
		self.update_status_dates()
		self.populate_from_global_manifest()
	
	def update_status_dates(self):
		"""Update submission and acceptance dates based on status"""
		if self.status == "Submitted" and not self.submission_date:
			self.submission_date = nowdate()
			if not self.submission_time:
				self.submission_time = now_datetime().strftime("%H:%M:%S")
		elif self.status == "Accepted" and not self.acceptance_date:
			self.acceptance_date = nowdate()
		elif self.status == "Amended":
			# Track amendment date
			pass
	
	def populate_from_global_manifest(self):
		"""Auto-populate fields from linked Global Manifest if not already set"""
		if self.global_manifest and not self.conveyance_name:
			try:
				manifest = frappe.get_doc("Global Manifest", self.global_manifest)
				
				if not self.conveyance_name and manifest.vessel_flight_number:
					self.conveyance_name = manifest.vessel_flight_number
				
				if not self.voyage_number and manifest.voyage_number:
					self.voyage_number = manifest.voyage_number
				
				if not self.port_of_entry and manifest.port_of_discharge:
					self.port_of_entry = manifest.port_of_discharge
				
				if not self.eta and manifest.eta:
					self.eta = manifest.eta
				
				if not self.company and manifest.company:
					self.company = manifest.company
				
				# Determine conveyance type from manifest
				if not self.conveyance_type:
					if manifest.sea_shipment:
						self.conveyance_type = "Vessel"
					elif manifest.air_shipment:
						self.conveyance_type = "Aircraft"
					elif manifest.transport_order:
						# Could be Rail or Truck, default to Truck
						self.conveyance_type = "Truck"
				
				# Get carrier code from settings
				if not self.carrier_code:
					try:
						settings = frappe.get_doc("Manifest Settings", manifest.company)
						if settings.enable_ca_emanifest and settings.cbsa_carrier_code:
							self.carrier_code = settings.cbsa_carrier_code
					except frappe.DoesNotExistError:
						pass
			except frappe.DoesNotExistError:
				pass


# -------------------------------------------------------------------
# ACTION: Create CA eManifest from Global Manifest
# -------------------------------------------------------------------
@frappe.whitelist()
def create_from_global_manifest(global_manifest_name: str) -> dict:
	"""
	Create a CA eManifest Forwarder filing from a Global Manifest.
	
	Args:
		global_manifest_name: Name of the Global Manifest
		
	Returns:
		dict: Result with created CA eManifest name and status
	"""
	try:
		global_manifest = frappe.get_doc("Global Manifest", global_manifest_name)
		
		# Check if CA eManifest already exists
		existing_emanifest = frappe.db.get_value("CA eManifest Forwarder", {"global_manifest": global_manifest_name}, "name")
		if existing_emanifest:
			return {
				"success": False,
				"message": _("CA eManifest Forwarder {0} already exists for this Global Manifest.").format(existing_emanifest),
				"ca_emanifest_forwarder": existing_emanifest
			}
		
		# Validate country is Canada
		# Check both country name and code
		country_code = frappe.db.get_value("Country", global_manifest.country, "code")
		country_name = global_manifest.country
		
		if country_code != "CA" and country_name != "Canada":
			frappe.throw(_("Global Manifest country must be Canada to create CA eManifest."))
		
		# Create new CA eManifest Forwarder
		emanifest = frappe.new_doc("CA eManifest Forwarder")
		
		# Set basic information
		emanifest.global_manifest = global_manifest_name
		emanifest.submission_type = "Original"
		emanifest.status = "Draft"
		emanifest.company = global_manifest.company
		
		# Populate from global manifest
		emanifest.conveyance_name = global_manifest.vessel_flight_number
		emanifest.voyage_number = global_manifest.voyage_number
		emanifest.port_of_entry = global_manifest.port_of_discharge
		emanifest.eta = global_manifest.eta
		
		# Determine conveyance type
		if global_manifest.sea_shipment:
			emanifest.conveyance_type = "Vessel"
		elif global_manifest.air_shipment:
			emanifest.conveyance_type = "Aircraft"
		elif global_manifest.transport_order:
			emanifest.conveyance_type = "Truck"
		else:
			emanifest.conveyance_type = "Vessel"  # Default
		
		# Get carrier code from settings
		try:
			settings = frappe.get_doc("Manifest Settings", global_manifest.company)
			if settings.enable_ca_emanifest and settings.cbsa_carrier_code:
				emanifest.carrier_code = settings.cbsa_carrier_code
		except frappe.DoesNotExistError:
			pass
		
		# Copy bills from global manifest
		if global_manifest.bills:
			for bill in global_manifest.bills:
				emanifest_bill = emanifest.append("bills")
				emanifest_bill.bill_number = bill.bill_number
				emanifest_bill.bill_type = bill.bill_type
				emanifest_bill.shipper = bill.shipper
				emanifest_bill.consignee = bill.consignee
				emanifest_bill.notify_party = bill.notify_party
				emanifest_bill.commodity_description = bill.commodity_description
				emanifest_bill.package_count = bill.package_count
				emanifest_bill.package_type = bill.package_type
				emanifest_bill.weight = bill.weight
				emanifest_bill.weight_uom = bill.weight_uom
				emanifest_bill.volume = bill.volume
				emanifest_bill.volume_uom = bill.volume_uom
				emanifest_bill.container_numbers = bill.container_numbers
				emanifest_bill.seal_numbers = bill.seal_numbers
				emanifest_bill.declaration = bill.declaration
				emanifest_bill.sea_shipment = bill.sea_shipment
				emanifest_bill.air_shipment = bill.air_shipment
		
		# Insert and save
		emanifest.insert(ignore_permissions=True)
		emanifest.save(ignore_permissions=True)
		
		return {
			"success": True,
			"ca_emanifest_forwarder": emanifest.name,
			"message": _("CA eManifest Forwarder {0} created successfully from Global Manifest.").format(emanifest.name)
		}
		
	except frappe.DoesNotExistError:
		frappe.throw(_("Global Manifest {0} does not exist.").format(global_manifest_name))
	except Exception as e:
		frappe.log_error(f"Error creating CA eManifest from Global Manifest: {str(e)}", "CA eManifest Creation Error")
		frappe.throw(_("Error creating CA eManifest: {0}").format(str(e)))

