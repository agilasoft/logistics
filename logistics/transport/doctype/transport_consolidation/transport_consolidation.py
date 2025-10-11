# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class TransportConsolidation(Document):
	def validate(self):
		"""Validate consolidation rules and calculate totals"""
		self.validate_consolidation_rules()
		self.calculate_totals()
		self.validate_accounts()
	
	def validate_consolidation_rules(self):
		"""Validate that jobs can be consolidated based on load type rules"""
		# Get load type from transport jobs
		load_types = set()
		for job in self.transport_jobs:
			if job.transport_job:
				job_doc = frappe.get_doc("Transport Job", job.transport_job)
				if job_doc.load_type:
					load_types.add(job_doc.load_type)
		
		# All jobs must have the same load type
		if len(load_types) > 1:
			frappe.throw(_("All transport jobs must have the same Load Type"))
		
		if load_types:
			load_type = list(load_types)[0]
			load_type_doc = frappe.get_doc("Load Type", load_type)
			
			# Check if load type allows consolidation
			if not load_type_doc.can_consolidate:
				frappe.throw(_("Load Type {0} does not allow consolidation").format(load_type))
			
			# Check max consolidation jobs limit
			if load_type_doc.max_consolidation_jobs and len(self.transport_jobs) > load_type_doc.max_consolidation_jobs:
				frappe.throw(_("Cannot consolidate more than {0} jobs for Load Type {1}").format(
					load_type_doc.max_consolidation_jobs, load_type))
			
			# Check weight and volume limits
			if load_type_doc.max_weight and self.total_weight > load_type_doc.max_weight:
				frappe.throw(_("Total weight {0} kg exceeds maximum allowed weight {1} kg for Load Type {2}").format(
					self.total_weight, load_type_doc.max_weight, load_type))
			
			if load_type_doc.max_volume and self.total_volume > load_type_doc.max_volume:
				frappe.throw(_("Total volume {0} m³ exceeds maximum allowed volume {1} m³ for Load Type {2}").format(
					self.total_volume, load_type_doc.max_volume, load_type))
	
	def calculate_totals(self):
		"""Calculate total weight and volume from transport jobs"""
		total_weight = 0
		total_volume = 0
		
		for job in self.transport_jobs:
			if job.transport_job:
				job_doc = frappe.get_doc("Transport Job", job.transport_job)
				
				# Calculate weight and volume from packages
				for package in job_doc.packages:
					if package.weight:
						total_weight += package.weight
					
					# Use the calculated volume field
					if package.volume:
						total_volume += package.volume
		
		self.total_weight = total_weight
		self.total_volume = total_volume
	
	def validate_accounts(self):
		"""Validate accounting fields"""
		if not self.company:
			frappe.throw(_("Company is required"))
		
		# Validate cost center belongs to company
		if self.cost_center:
			cost_center_company = frappe.db.get_value("Cost Center", self.cost_center, "company")
			if cost_center_company and cost_center_company != self.company:
				frappe.throw(_("Cost Center {0} does not belong to Company {1}").format(
					self.cost_center, self.company))
		
		# Validate profit center belongs to company
		if self.profit_center:
			profit_center_company = frappe.db.get_value("Profit Center", self.profit_center, "company")
			if profit_center_company and profit_center_company != self.company:
				frappe.throw(_("Profit Center {0} does not belong to Company {1}").format(
					self.profit_center, self.company))
		
		# Validate branch belongs to company
		if self.branch:
			branch_company = frappe.db.get_value("Branch", self.branch, "company")
			if branch_company and branch_company != self.company:
				frappe.throw(_("Branch {0} does not belong to Company {1}").format(
					self.branch, self.company))
