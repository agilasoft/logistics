# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate, nowdate, now_datetime
import re


class USAMS(Document):
	def validate(self):
		"""Validate US AMS data"""
		# Validate SCAC code format (4 uppercase letters)
		if self.carrier_code:
			if not re.match(r'^[A-Z]{4}$', self.carrier_code):
				frappe.throw(_("Carrier Code (SCAC) must be exactly 4 uppercase letters."))
		
		# Validate submission type rules
		if self.submission_type == "Cancel" and self.status != "Draft":
			frappe.throw(_("Only Draft AMS can be cancelled."))
		
		# Validate required fields for submission
		if self.status == "Submitted":
			if not self.port_of_unlading:
				frappe.throw(_("Port of Unlading is required for submission."))
			if not self.carrier_code:
				frappe.throw(_("Carrier Code (SCAC) is required for submission."))
	
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
		elif self.status == "Released" and not self.release_date:
			self.release_date = nowdate()
	
	def populate_from_global_manifest(self):
		"""Auto-populate fields from linked Global Manifest if not already set"""
		if self.global_manifest and not self.vessel_name:
			try:
				manifest = frappe.get_doc("Global Manifest", self.global_manifest)
				
				if not self.vessel_name and manifest.vessel_flight_number:
					self.vessel_name = manifest.vessel_flight_number
				
				if not self.voyage_number and manifest.voyage_number:
					self.voyage_number = manifest.voyage_number
				
				if not self.port_of_unlading and manifest.port_of_discharge:
					self.port_of_unlading = manifest.port_of_discharge
				
				if not self.estimated_arrival_date and manifest.eta:
					self.estimated_arrival_date = manifest.eta
				
				if not self.company and manifest.company:
					self.company = manifest.company
				
				# Get filer code from settings
				if not self.filer_code:
					try:
						settings = frappe.get_doc("Manifest Settings", manifest.company)
						if settings.enable_us_ams and settings.ams_filer_code:
							self.filer_code = settings.ams_filer_code
					except frappe.DoesNotExistError:
						pass
			except frappe.DoesNotExistError:
				pass


# -------------------------------------------------------------------
# ACTION: Create US AMS from Global Manifest
# -------------------------------------------------------------------
@frappe.whitelist()
def create_from_global_manifest(global_manifest_name: str) -> dict:
	"""
	Create a US AMS filing from a Global Manifest.
	
	Args:
		global_manifest_name: Name of the Global Manifest
		
	Returns:
		dict: Result with created US AMS name and status
	"""
	try:
		global_manifest = frappe.get_doc("Global Manifest", global_manifest_name)
		
		# Check if US AMS already exists
		existing_ams = frappe.db.get_value("US AMS", {"global_manifest": global_manifest_name}, "name")
		if existing_ams:
			return {
				"success": False,
				"message": _("US AMS {0} already exists for this Global Manifest.").format(existing_ams),
				"us_ams": existing_ams
			}
		
		# Validate country is US
		if global_manifest.country != "United States":
			frappe.throw(_("Global Manifest country must be United States to create US AMS."))
		
		# Create new US AMS
		ams = frappe.new_doc("US AMS")
		
		# Set basic information
		ams.global_manifest = global_manifest_name
		ams.submission_type = "Original"
		ams.status = "Draft"
		ams.company = global_manifest.company
		
		# Populate from global manifest
		ams.vessel_name = global_manifest.vessel_flight_number
		ams.voyage_number = global_manifest.voyage_number
		ams.port_of_unlading = global_manifest.port_of_discharge
		ams.estimated_arrival_date = global_manifest.eta
		
		# Get filer code from settings
		try:
			settings = frappe.get_doc("Manifest Settings", global_manifest.company)
			if settings.enable_us_ams and settings.ams_filer_code:
				ams.filer_code = settings.ams_filer_code
		except frappe.DoesNotExistError:
			pass
		
		# Copy bills from global manifest
		if global_manifest.bills:
			for bill in global_manifest.bills:
				ams_bill = ams.append("bills")
				ams_bill.bill_number = bill.bill_number
				ams_bill.bill_type = bill.bill_type
				ams_bill.shipper = bill.shipper
				ams_bill.consignee = bill.consignee
				ams_bill.notify_party = bill.notify_party
				ams_bill.commodity_description = bill.commodity_description
				ams_bill.package_count = bill.package_count
				ams_bill.weight = bill.weight
				ams_bill.container_numbers = bill.container_numbers
				ams_bill.seal_numbers = bill.seal_numbers
				ams_bill.declaration = bill.declaration
				ams_bill.sea_shipment = bill.sea_shipment
				ams_bill.air_shipment = bill.air_shipment
				ams_bill.status = "Pending"
		
		# Insert and save
		ams.insert(ignore_permissions=True)
		ams.save(ignore_permissions=True)
		
		return {
			"success": True,
			"us_ams": ams.name,
			"message": _("US AMS {0} created successfully from Global Manifest.").format(ams.name)
		}
		
	except frappe.DoesNotExistError:
		frappe.throw(_("Global Manifest {0} does not exist.").format(global_manifest_name))
	except Exception as e:
		frappe.log_error(f"Error creating US AMS from Global Manifest: {str(e)}", "US AMS Creation Error")
		frappe.throw(_("Error creating US AMS: {0}").format(str(e)))

