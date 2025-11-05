# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class Declaration(Document):
	def before_save(self):
		"""Calculate sustainability metrics before saving"""
		self.calculate_sustainability_metrics()
	
	def after_submit(self):
		"""Record sustainability metrics after declaration submission"""
		self.record_sustainability_metrics()
	
	def calculate_sustainability_metrics(self):
		"""Calculate sustainability metrics for this declaration"""
		try:
			# For customs declarations, we can track compliance-related sustainability metrics
			# This could include paper usage, digital processing efficiency, etc.
			
			# Calculate estimated paper usage (simplified)
			paper_usage = self._calculate_paper_usage()
			self.estimated_paper_usage = paper_usage
			
			# Calculate estimated carbon footprint from processing
			carbon_footprint = self._calculate_processing_carbon_footprint()
			self.estimated_carbon_footprint = carbon_footprint
			
		except Exception as e:
			frappe.log_error(f"Error calculating sustainability metrics for Declaration {self.name}: {e}", "Declaration Sustainability Error")
	
	def record_sustainability_metrics(self):
		"""Record sustainability metrics in the centralized system"""
		try:
			from logistics.sustainability.utils.sustainability_integration import integrate_sustainability
			
			result = integrate_sustainability(
				doctype=self.doctype,
				docname=self.name,
				module="Customs",
				doc=self
			)
			
			if result.get("status") == "success":
				frappe.msgprint(_("Sustainability metrics recorded successfully"))
			elif result.get("status") == "skipped":
				# Don't show message if sustainability is not enabled
				pass
			else:
				frappe.log_error(f"Sustainability recording failed: {result.get('message', 'Unknown error')}", "Declaration Sustainability Error")
				
		except Exception as e:
			frappe.log_error(f"Error recording sustainability metrics for Declaration {self.name}: {e}", "Declaration Sustainability Error")
	
	def _calculate_paper_usage(self) -> float:
		"""Calculate estimated paper usage for customs declaration"""
		# Estimate based on typical customs declaration requirements
		# This is a simplified calculation
		base_pages = 5  # Base pages for standard declaration
		return float(base_pages)
	
	def _calculate_processing_carbon_footprint(self) -> float:
		"""Calculate estimated carbon footprint from processing"""
		# Estimate based on digital processing and office operations
		# This is a simplified calculation
		processing_factor = 0.1  # kg CO2e per declaration
		return processing_factor
