# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate, nowdate, now_datetime
import re


class JPAFR(Document):
	def validate(self):
		"""Validate JP AFR data"""
		# Validate filer code format (alphanumeric, typically 8-12 characters)
		if self.filer_code:
			if not re.match(r'^[A-Z0-9]{8,12}$', self.filer_code.upper()):
				frappe.throw(_("Japan Customs Filer Code must be 8-12 alphanumeric characters."))
		
		# Validate submission type rules
		if self.submission_type == "Cancellation" and self.status != "Draft":
			frappe.throw(_("Only Draft AFR can be cancelled."))
		
		if self.submission_type == "Amendment" and self.status not in ["Draft", "Accepted"]:
			frappe.throw(_("Amendment can only be made to Draft or Accepted AFR."))
		
		# Validate required fields for submission
		if self.status == "Submitted":
			if not self.port_of_loading:
				frappe.throw(_("Port of Loading is required for submission."))
			if not self.port_of_discharge:
				frappe.throw(_("Port of Discharge is required for submission."))
			if not self.vessel_name:
				frappe.throw(_("Vessel Name is required for submission."))
			if not self.eta:
				frappe.throw(_("ETA is required for submission."))
		
		# Validate submission timing (must be before vessel departure)
		if self.status == "Submitted" and self.eta and self.submission_date:
			# AFR must be filed before vessel departure (before ETA)
			if getdate(self.submission_date) >= getdate(self.eta):
				frappe.msgprint(
					_("Warning: AFR should be filed before vessel departure (before ETA)."),
					indicator="orange",
					title=_("Submission Timing Warning")
				)
	
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
	
	def populate_from_global_manifest(self):
		"""Auto-populate fields from linked Global Manifest if not already set"""
		if self.global_manifest and not self.vessel_name:
			try:
				manifest = frappe.get_doc("Global Manifest", self.global_manifest)
				
				if not self.vessel_name and manifest.vessel_flight_number:
					self.vessel_name = manifest.vessel_flight_number
				
				if not self.voyage_number and manifest.voyage_number:
					self.voyage_number = manifest.voyage_number
				
				if not self.port_of_loading and manifest.port_of_loading:
					self.port_of_loading = manifest.port_of_loading
				
				if not self.port_of_discharge and manifest.port_of_discharge:
					self.port_of_discharge = manifest.port_of_discharge
				
				if not self.eta and manifest.eta:
					self.eta = manifest.eta
				
				if not self.company and manifest.company:
					self.company = manifest.company
				
				# Get filer code from settings
				if not self.filer_code:
					try:
						settings = frappe.get_doc("Manifest Settings", manifest.company)
						if settings.enable_jp_afr and settings.japan_customs_filer_code:
							self.filer_code = settings.japan_customs_filer_code
					except frappe.DoesNotExistError:
						pass
			except frappe.DoesNotExistError:
				pass


# -------------------------------------------------------------------
# ACTION: Create JP AFR from Global Manifest
# -------------------------------------------------------------------
@frappe.whitelist()
def create_from_global_manifest(global_manifest_name: str) -> dict:
	"""
	Create a JP AFR filing from a Global Manifest.
	
	Args:
		global_manifest_name: Name of the Global Manifest
		
	Returns:
		dict: Result with created JP AFR name and status
	"""
	try:
		global_manifest = frappe.get_doc("Global Manifest", global_manifest_name)
		
		# Check if JP AFR already exists
		existing_afr = frappe.db.get_value("JP AFR", {"global_manifest": global_manifest_name}, "name")
		if existing_afr:
			return {
				"success": False,
				"message": _("JP AFR {0} already exists for this Global Manifest.").format(existing_afr),
				"jp_afr": existing_afr
			}
		
		# Validate country is Japan
		# Check both country name and code
		country_code = frappe.db.get_value("Country", global_manifest.country, "code")
		country_name = global_manifest.country
		
		if country_code != "JP" and country_name != "Japan":
			frappe.throw(_("Global Manifest country must be Japan to create JP AFR."))
		
		# Create new JP AFR
		afr = frappe.new_doc("JP AFR")
		
		# Set basic information
		afr.global_manifest = global_manifest_name
		afr.submission_type = "Original"
		afr.status = "Draft"
		afr.company = global_manifest.company
		
		# Populate from global manifest
		afr.vessel_name = global_manifest.vessel_flight_number
		afr.voyage_number = global_manifest.voyage_number
		afr.port_of_loading = global_manifest.port_of_loading
		afr.port_of_discharge = global_manifest.port_of_discharge
		afr.eta = global_manifest.eta
		
		# Get filer code from settings
		try:
			settings = frappe.get_doc("Manifest Settings", global_manifest.company)
			if settings.enable_jp_afr and settings.japan_customs_filer_code:
				afr.filer_code = settings.japan_customs_filer_code
		except frappe.DoesNotExistError:
			pass
		
		# Copy bills from global manifest
		if global_manifest.bills:
			for bill in global_manifest.bills:
				afr_bill = afr.append("bills")
				afr_bill.bill_number = bill.bill_number
				afr_bill.bill_type = bill.bill_type
				afr_bill.shipper = bill.shipper
				afr_bill.consignee = bill.consignee
				afr_bill.notify_party = bill.notify_party
				afr_bill.commodity_description = bill.commodity_description
				afr_bill.package_count = bill.package_count
				afr_bill.package_type = bill.package_type
				afr_bill.weight = bill.weight
				afr_bill.weight_uom = bill.weight_uom
				afr_bill.volume = bill.volume
				afr_bill.volume_uom = bill.volume_uom
				afr_bill.container_numbers = bill.container_numbers
				afr_bill.seal_numbers = bill.seal_numbers
				afr_bill.declaration = bill.declaration
				afr_bill.sea_shipment = bill.sea_shipment
				afr_bill.air_shipment = bill.air_shipment
		
		# Insert and save
		afr.insert(ignore_permissions=True)
		afr.save(ignore_permissions=True)
		
		return {
			"success": True,
			"jp_afr": afr.name,
			"message": _("JP AFR {0} created successfully from Global Manifest.").format(afr.name)
		}
		
	except frappe.DoesNotExistError:
		frappe.throw(_("Global Manifest {0} does not exist.").format(global_manifest_name))
	except Exception as e:
		frappe.log_error(f"Error creating JP AFR from Global Manifest: {str(e)}", "JP AFR Creation Error")
		frappe.throw(_("Error creating JP AFR: {0}").format(str(e)))

