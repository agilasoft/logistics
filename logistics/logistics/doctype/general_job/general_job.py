# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class GeneralJob(Document):
	def before_save(self):
		"""Calculate sustainability metrics and create job costing number before saving"""
		self.calculate_sustainability_metrics()
		self.create_job_costing_number_if_needed()

	def after_insert(self):
		"""Create job costing number for new documents"""
		self.create_job_costing_number_if_needed()
	
	def after_submit(self):
		"""Record sustainability metrics after job submission"""
		self.record_sustainability_metrics()
	
	def calculate_sustainability_metrics(self):
		"""Calculate sustainability metrics for this general job"""
		try:
			# For general jobs, we can track general sustainability metrics
			# This could include office operations, general energy usage, etc.
			
			# Calculate estimated energy consumption
			energy_consumption = self._calculate_energy_consumption()
			self.estimated_energy_consumption = energy_consumption
			
			# Calculate estimated carbon footprint
			carbon_footprint = self._calculate_carbon_footprint()
			self.estimated_carbon_footprint = carbon_footprint
			
		except Exception as e:
			frappe.log_error(f"Error calculating sustainability metrics for General Job {self.name}: {e}", "General Job Sustainability Error")
	
	def record_sustainability_metrics(self):
		"""Record sustainability metrics in the centralized system"""
		try:
			from logistics.sustainability.utils.sustainability_integration import integrate_sustainability
			
			result = integrate_sustainability(
				doctype=self.doctype,
				docname=self.name,
				module="Job Management",
				doc=self
			)
			
			if result.get("status") == "success":
				frappe.msgprint(_("Sustainability metrics recorded successfully"))
			elif result.get("status") == "skipped":
				# Don't show message if sustainability is not enabled
				pass
			else:
				frappe.log_error(f"Sustainability recording failed: {result.get('message', 'Unknown error')}", "General Job Sustainability Error")
				
		except Exception as e:
			frappe.log_error(f"Error recording sustainability metrics for General Job {self.name}: {e}", "General Job Sustainability Error")
	
	def _calculate_energy_consumption(self) -> float:
		"""Calculate estimated energy consumption for general job"""
		# Estimate based on typical office operations
		# This is a simplified calculation
		base_energy = 10.0  # kWh per job
		return base_energy
	
	def _calculate_carbon_footprint(self) -> float:
		"""Calculate estimated carbon footprint"""
		# Estimate based on energy consumption
		energy_factor = 0.4  # kg CO2e per kWh
		return self.estimated_energy_consumption * energy_factor

	def create_job_costing_number_if_needed(self):
		"""Create Job Costing Number if it doesn't exist"""
		if self.job_costing_number:
			return

		if not self.company:
			return

		try:
			# Check if Job Costing Number already exists for this job
			existing_jcn = frappe.db.exists("Job Costing Number", {"job_no": self.name})
			if existing_jcn:
				self.job_costing_number = existing_jcn
				return

			# Create new Job Costing Number
			jcn = frappe.new_doc("Job Costing Number")
			jcn.job_type = "General Job"
			jcn.job_no = self.name
			jcn.company = self.company
			jcn.branch = getattr(self, "branch", None)
			jcn.cost_center = getattr(self, "cost_center", None)
			jcn.profit_center = getattr(self, "profit_center", None)
			jcn.insert(ignore_permissions=True)
			self.job_costing_number = jcn.name
		except Exception as e:
			frappe.log_error(f"Error creating Job Costing Number for General Job {self.name}: {str(e)}", "Job Costing Number Creation Error")


@frappe.whitelist()
def create_job_costing_number(docname):
	"""Create Job Costing Number for a General Job via button action"""
	doc = frappe.get_doc("General Job", docname)
	doc.create_job_costing_number_if_needed()
	if doc.job_costing_number:
		doc.save()
		return doc.job_costing_number
	return None
