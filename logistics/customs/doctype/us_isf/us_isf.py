# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import getdate, nowdate, now_datetime, date_diff, add_days
from datetime import datetime, timedelta


class USISF(Document):
	def validate(self):
		"""Validate US ISF data"""
		# Validate all ISF-10 elements are present
		isf_10_fields = [
			"importer_of_record",
			"consignee",
			"buyer",
			"seller",
			"ship_to_party",
			"manufacturer",
			"country_of_origin",
			"commodity_hs_code",
			"container_stuffing_location"
		]
		
		missing_fields = []
		for field in isf_10_fields:
			if not self.get(field):
				field_label = self.meta.get_field(field).label
				missing_fields.append(field_label)
		
		if missing_fields:
			frappe.throw(_("The following ISF-10 required fields are missing: {0}").format(", ".join(missing_fields)))
		
		# Validate HS code format (should be numeric, typically 10 digits)
		if self.commodity_hs_code:
			if not self.commodity_hs_code.replace(".", "").isdigit():
				frappe.throw(_("Commodity HTSUS Number must be numeric."))
		
		# Validate 24-hour rule
		self.validate_24_hour_rule()
	
	def before_save(self):
		"""Auto-update dates and populate from Global Manifest/AMS"""
		self.update_status_dates()
		self.populate_from_related_documents()
		self.validate_24_hour_rule()
	
	def update_status_dates(self):
		"""Update submission and acceptance dates based on status"""
		if self.status == "Submitted" and not self.submission_date:
			self.submission_date = nowdate()
			if not self.submission_time:
				self.submission_time = now_datetime().strftime("%H:%M:%S")
		elif self.status == "Accepted" and not self.acceptance_date:
			self.acceptance_date = nowdate()
	
	def populate_from_related_documents(self):
		"""Auto-populate fields from linked Global Manifest or AMS"""
		if self.global_manifest and not self.estimated_arrival_date:
			try:
				manifest = frappe.get_doc("Global Manifest", self.global_manifest)
				if manifest.eta:
					self.estimated_arrival_date = manifest.eta
				if not self.company and manifest.company:
					self.company = manifest.company
			except frappe.DoesNotExistError:
				pass
		
		if self.ams and not self.estimated_arrival_date:
			try:
				ams = frappe.get_doc("US AMS", self.ams)
				if ams.estimated_arrival_date:
					self.estimated_arrival_date = ams.estimated_arrival_date
				if not self.company and ams.company:
					self.company = ams.company
			except frappe.DoesNotExistError:
				pass
	
	def validate_24_hour_rule(self):
		"""
		Validate that ISF is filed at least 24 hours before vessel departure.
		ISF must be filed 24 hours before vessel departure from foreign port.
		"""
		if not self.global_manifest or not self.estimated_arrival_date:
			self.validation_24_hour_rule = ""
			self.validation_status = ""
			return
		
		try:
			manifest = frappe.get_doc("Global Manifest", self.global_manifest)
			
			# Get ETD from manifest (vessel departure)
			if not manifest.etd:
				self.validation_24_hour_rule = "ETD not set in Global Manifest"
				self.validation_status = "Warning"
				return
			
			etd = getdate(manifest.etd)
			current_date = nowdate()
			
			# Calculate hours until departure (approximate)
			days_until_departure = (etd - current_date).days
			hours_until_departure = days_until_departure * 24
			
			# Check if submitted
			if self.status == "Submitted" and self.submission_date:
				submission_date = getdate(self.submission_date)
				days_before_departure = (etd - submission_date).days
				hours_before_departure = days_before_departure * 24
				
				if hours_before_departure < 24:
					self.validation_24_hour_rule = f"ISF filed {hours_before_departure} hours before departure (Required: 24 hours)"
					self.validation_status = "Error"
				else:
					self.validation_24_hour_rule = f"ISF filed {hours_before_departure} hours before departure ✓"
					self.validation_status = "Valid"
			else:
				# Not yet submitted - check if it will meet 24-hour rule
				if hours_until_departure < 24:
					self.validation_24_hour_rule = f"Only {hours_until_departure} hours until departure (Required: 24 hours)"
					self.validation_status = "Error"
				else:
					self.validation_24_hour_rule = f"{hours_until_departure} hours until departure"
					self.validation_status = "Warning"
		
		except frappe.DoesNotExistError:
			self.validation_24_hour_rule = "Global Manifest not found"
			self.validation_status = "Warning"


# -------------------------------------------------------------------
# ACTION: Create US ISF from US AMS
# -------------------------------------------------------------------
@frappe.whitelist()
def create_from_ams(ams_name: str) -> dict:
	"""
	Create a US ISF filing from a US AMS.
	
	Args:
		ams_name: Name of the US AMS
		
	Returns:
		dict: Result with created US ISF name and status
	"""
	try:
		ams = frappe.get_doc("US AMS", ams_name)
		
		# Check if US ISF already exists
		existing_isf = frappe.db.get_value("US ISF", {"ams": ams_name}, "name")
		if existing_isf:
			return {
				"success": False,
				"message": _("US ISF {0} already exists for this US AMS.").format(existing_isf),
				"us_isf": existing_isf
			}
		
		# Create new US ISF
		isf = frappe.new_doc("US ISF")
		
		# Set basic information
		isf.ams = ams_name
		isf.global_manifest = ams.global_manifest
		isf.status = "Draft"
		isf.company = ams.company
		isf.estimated_arrival_date = ams.estimated_arrival_date
		
		# Populate from AMS bills if available
		if ams.bills:
			# Get first bill for initial data
			first_bill = ams.bills[0]
			if first_bill.consignee:
				isf.consignee = first_bill.consignee
			if first_bill.shipper:
				# Try to use shipper as seller
				isf.seller = first_bill.shipper
		
		# Insert and save
		isf.insert(ignore_permissions=True)
		isf.save(ignore_permissions=True)
		
		return {
			"success": True,
			"us_isf": isf.name,
			"message": _("US ISF {0} created successfully from US AMS.").format(isf.name)
		}
		
	except frappe.DoesNotExistError:
		frappe.throw(_("US AMS {0} does not exist.").format(ams_name))
	except Exception as e:
		frappe.log_error(f"Error creating US ISF from US AMS: {str(e)}", "US ISF Creation Error")
		frappe.throw(_("Error creating US ISF: {0}").format(str(e)))


# -------------------------------------------------------------------
# ACTION: Validate 24-Hour Rule
# -------------------------------------------------------------------
@frappe.whitelist()
def validate_24_hour_rule(isf_name: str) -> dict:
	"""
	Validate that ISF meets the 24-hour rule.
	
	Args:
		isf_name: Name of the US ISF
		
	Returns:
		dict: Validation result
	"""
	try:
		isf = frappe.get_doc("US ISF", isf_name)
		isf.validate_24_hour_rule()
		isf.save(ignore_permissions=True)
		
		return {
			"success": True,
			"validation_status": isf.validation_status,
			"validation_message": isf.validation_24_hour_rule
		}
	except frappe.DoesNotExistError:
		frappe.throw(_("US ISF {0} does not exist.").format(isf_name))
	except Exception as e:
		frappe.log_error(f"Error validating 24-hour rule: {str(e)}", "ISF Validation Error")
		frappe.throw(_("Error validating 24-hour rule: {0}").format(str(e)))

