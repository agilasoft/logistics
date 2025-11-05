# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, getdate, add_days
from frappe import _


class SustainabilityCompliance(Document):
	def before_save(self):
		"""Update status and validate data before saving"""
		self.update_status()
		self.validate_data()
	
	def update_status(self):
		"""Update compliance and certification status based on dates"""
		today = getdate()
		
		# Update certification status based on expiry date
		if self.expiry_date:
			if self.expiry_date < today:
				self.certification_status = "Expired"
			elif self.certification_date and self.certification_date <= today:
				self.certification_status = "Certified"
			else:
				self.certification_status = "Pending"
		elif self.certification_date and self.certification_date <= today:
			self.certification_status = "Certified"
		else:
			self.certification_status = "Pending"
		
		# Update compliance status based on audit status
		if self.audit_status == "Passed":
			self.compliance_status = "Compliant"
		elif self.audit_status == "Failed":
			self.compliance_status = "Non-Compliant"
		elif self.audit_status == "Pending":
			self.compliance_status = "Under Review"
		else:
			self.compliance_status = "Not Applicable"
	
	def validate_data(self):
		"""Validate compliance data"""
		# Validate certification date is not in the future
		if self.certification_date and self.certification_date > getdate():
			frappe.throw(_("Certification date cannot be in the future"))
		
		# Validate expiry date is after certification date
		if self.certification_date and self.expiry_date and self.expiry_date <= self.certification_date:
			frappe.throw(_("Expiry date must be after certification date"))
		
		# Validate audit dates
		if self.last_audit_date and self.last_audit_date > getdate():
			frappe.throw(_("Last audit date cannot be in the future"))
		
		if self.next_audit_date and self.next_audit_date < getdate():
			frappe.throw(_("Next audit date cannot be in the past"))
	
	def get_days_until_expiry(self):
		"""Get days until certification expires"""
		if not self.expiry_date:
			return None
		
		today = getdate()
		if self.expiry_date < today:
			return 0
		
		return (self.expiry_date - today).days
	
	def get_days_until_next_audit(self):
		"""Get days until next audit"""
		if not self.next_audit_date:
			return None
		
		today = getdate()
		if self.next_audit_date < today:
			return 0
		
		return (self.next_audit_date - today).days
	
	def is_expiring_soon(self, days=30):
		"""Check if certification is expiring soon"""
		days_until_expiry = self.get_days_until_expiry()
		return days_until_expiry is not None and days_until_expiry <= days
	
	def is_audit_due_soon(self, days=30):
		"""Check if audit is due soon"""
		days_until_audit = self.get_days_until_next_audit()
		return days_until_audit is not None and days_until_audit <= days
	
	def get_compliance_rating(self):
		"""Get overall compliance rating"""
		rating = 0
		
		# Base rating on certification status
		if self.certification_status == "Certified":
			rating += 40
		elif self.certification_status == "Pending":
			rating += 20
		
		# Add rating based on compliance status
		if self.compliance_status == "Compliant":
			rating += 40
		elif self.compliance_status == "Under Review":
			rating += 20
		
		# Add rating based on audit status
		if self.audit_status == "Passed":
			rating += 20
		elif self.audit_status == "Pending":
			rating += 10
		
		return min(100, rating)


@frappe.whitelist()
def get_sustainability_compliance_summary(module=None, branch=None, facility=None):
	"""Get sustainability compliance summary for a specific module or all modules"""
	
	filters = {}
	if module:
		filters["module"] = module
	if branch:
		filters["branch"] = branch
	if facility:
		filters["facility"] = facility
	
	# Get compliance data
	compliance_data = frappe.get_all("Sustainability Compliance",
		filters=filters,
		fields=["*"],
		order_by="expiry_date asc"
	)
	
	# Calculate summary statistics
	summary = {
		"total_compliance": len(compliance_data),
		"certified_count": 0,
		"expired_count": 0,
		"expiring_soon_count": 0,
		"compliant_count": 0,
		"non_compliant_count": 0,
		"audit_due_soon_count": 0,
		"compliance_by_type": {},
		"compliance_by_status": {}
	}
	
	if compliance_data:
		# Count by certification status
		for data in compliance_data:
			cert_status = data.certification_status or "Not Certified"
			if cert_status not in summary["compliance_by_status"]:
				summary["compliance_by_status"][cert_status] = 0
			summary["compliance_by_status"][cert_status] += 1
			
			# Count by type
			compliance_type = data.compliance_type or "Other"
			if compliance_type not in summary["compliance_by_type"]:
				summary["compliance_by_type"][compliance_type] = 0
			summary["compliance_by_type"][compliance_type] += 1
		
		# Calculate specific counts
		summary["certified_count"] = summary["compliance_by_status"].get("Certified", 0)
		summary["expired_count"] = summary["compliance_by_status"].get("Expired", 0)
		summary["compliant_count"] = summary["compliance_by_status"].get("Compliant", 0)
		summary["non_compliant_count"] = summary["compliance_by_status"].get("Non-Compliant", 0)
		
		# Count expiring soon and audit due soon
		for data in compliance_data:
			doc = frappe.get_doc("Sustainability Compliance", data.name)
			if doc.is_expiring_soon():
				summary["expiring_soon_count"] += 1
			if doc.is_audit_due_soon():
				summary["audit_due_soon_count"] += 1
	
	return {
		"compliance_data": compliance_data,
		"summary": summary
	}


@frappe.whitelist()
def create_sustainability_compliance(compliance_name, compliance_type, **kwargs):
	"""Create a new sustainability compliance record"""
	
	doc = frappe.new_doc("Sustainability Compliance")
	doc.compliance_name = compliance_name
	doc.compliance_type = compliance_type
	doc.module = kwargs.get("module", "All")
	doc.branch = kwargs.get("branch")
	doc.facility = kwargs.get("facility")
	doc.company = kwargs.get("company", frappe.defaults.get_user_default("Company"))
	doc.standard_name = kwargs.get("standard_name")
	doc.standard_version = kwargs.get("standard_version")
	doc.certification_body = kwargs.get("certification_body")
	doc.certification_number = kwargs.get("certification_number")
	doc.certification_date = kwargs.get("certification_date")
	doc.expiry_date = kwargs.get("expiry_date")
	doc.last_audit_date = kwargs.get("last_audit_date")
	doc.next_audit_date = kwargs.get("next_audit_date")
	doc.compliance_status = kwargs.get("compliance_status", "Not Applicable")
	doc.certification_status = kwargs.get("certification_status", "Pending")
	doc.audit_status = kwargs.get("audit_status", "Not Required")
	doc.description = kwargs.get("description")
	doc.requirements = kwargs.get("requirements")
	doc.responsible_person = kwargs.get("responsible_person")
	doc.notes = kwargs.get("notes")
	
	doc.insert(ignore_permissions=True)
	return doc.name
