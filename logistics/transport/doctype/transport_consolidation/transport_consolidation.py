# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt


class TransportConsolidation(Document):
	def validate(self):
		"""Validate consolidation rules and calculate totals"""
		# Clear consolidation flags for removed jobs (must be done before other validations)
		self.clear_consolidation_flags_for_removed_jobs()
		self.auto_determine_load_type()
		self.validate_consolidation_rules()
		self.determine_consolidation_type()
		self.calculate_totals()
		self.validate_capacity_limits()
		self.validate_date_alignment()
		self.validate_vehicle_type_compatibility()
		self.validate_status_workflow()
		self.validate_accounts()
	
	def clear_consolidation_flags_for_removed_jobs(self):
		"""
		Clear consolidation flags (pick_consolidated, drop_consolidated, transport_consolidation)
		from Transport Legs when jobs are removed from the consolidation.
		This ensures that deleted jobs can appear again in the consolidation suggestion dialog.
		"""
		if self.is_new():
			# New document, nothing to clear
			return
		
		try:
			# Get current job names in the consolidation
			current_job_names = set()
			for job_row in (self.transport_jobs or []):
				if job_row.transport_job:
					current_job_names.add(job_row.transport_job)
			
			# Get previous job names from database
			previous_job_rows = frappe.get_all(
				"Transport Consolidation Job",
				filters={"parent": self.name},
				fields=["transport_job"]
			)
			previous_job_names = {row.transport_job for row in previous_job_rows if row.transport_job}
			
			# Find jobs that were removed
			removed_job_names = previous_job_names - current_job_names
			
			if not removed_job_names:
				# No jobs were removed
				return
			
			# Clear consolidation flags for legs of removed jobs
			for job_name in removed_job_names:
				try:
					# Check if job is in any other consolidation
					other_consolidations = frappe.get_all(
						"Transport Consolidation Job",
						filters={
							"transport_job": job_name,
							"parent": ["!=", self.name]
						},
						fields=["parent"],
						limit=1
					)
					
					# If job is in another consolidation, don't clear flags
					if other_consolidations:
						continue
					
					# Get all legs for this job
					leg_fields = ["name", "transport_consolidation"]
					if frappe.db.has_column("Transport Leg", "pick_consolidated"):
						leg_fields.append("pick_consolidated")
					if frappe.db.has_column("Transport Leg", "drop_consolidated"):
						leg_fields.append("drop_consolidated")
					
					job_legs = frappe.get_all(
						"Transport Leg",
						filters={"transport_job": job_name},
						fields=leg_fields
					)
					
					for leg in job_legs:
						leg_consolidation = leg.get("transport_consolidation")
						has_pick_flag = leg.get("pick_consolidated") == 1
						has_drop_flag = leg.get("drop_consolidated") == 1
						
						# Clear flags if:
						# 1. Leg is linked to this consolidation, OR
						# 2. Leg has flags set but no consolidation link (orphaned flags from this job)
						should_clear = False
						if leg_consolidation == self.name:
							# Leg is linked to this consolidation - definitely clear
							should_clear = True
						elif not leg_consolidation and (has_pick_flag or has_drop_flag):
							# Leg has flags but no consolidation link - might be orphaned flags
							# Only clear if the job was only in this consolidation (which we already checked above)
							should_clear = True
						
						if should_clear:
							leg_doc = frappe.get_doc("Transport Leg", leg.name)
							# Clear consolidation flags
							if frappe.db.has_column("Transport Leg", "pick_consolidated"):
								leg_doc.pick_consolidated = 0
							if frappe.db.has_column("Transport Leg", "drop_consolidated"):
								leg_doc.drop_consolidated = 0
							leg_doc.transport_consolidation = None
							leg_doc.save(ignore_permissions=True)
				except Exception as e:
					# Log error but don't fail validation
					frappe.log_error(
						f"Error clearing consolidation flags for job {job_name}: {str(e)}",
						"Clear Consolidation Flags Error"
					)
		except Exception as e:
			# Log error but don't fail validation
			frappe.log_error(
				f"Error in clear_consolidation_flags_for_removed_jobs: {str(e)}",
				"Clear Consolidation Flags Error"
			)
	
	def determine_consolidation_type(self):
		"""Auto-determine consolidation type based on pick and drop addresses"""
		if not self.transport_jobs:
			return
		
		# Collect all unique pick and drop addresses from transport legs
		pick_addresses = set()
		drop_addresses = set()
		
		for job_row in self.transport_jobs:
			if not job_row.transport_job:
				continue
			
			# Get Transport Legs for this job
			job_legs = frappe.get_all(
				"Transport Leg",
				filters={"transport_job": job_row.transport_job},
				fields=["pick_address", "drop_address"]
			)
			
			for leg in job_legs:
				if leg.get("pick_address"):
					pick_addresses.add(leg.get("pick_address"))
				if leg.get("drop_address"):
					drop_addresses.add(leg.get("drop_address"))
		
		# Determine consolidation type based on address patterns
		# Pick: One pick address, multiple drop addresses
		# Drop: Multiple pick addresses, one drop address
		# Both: One pick address, one drop address (all jobs same origin and destination)
		# Route: Multiple pick addresses, multiple drop addresses (milk run)
		
		num_pick = len(pick_addresses)
		num_drop = len(drop_addresses)
		
		if num_pick == 1 and num_drop == 1:
			# All jobs have same pick and drop - Both/Full Consolidated
			self.consolidation_type = "Both"
		elif num_pick == 1 and num_drop > 1:
			# One pick, multiple drops - Pick Consolidated
			self.consolidation_type = "Pick"
		elif num_pick > 1 and num_drop == 1:
			# Multiple picks, one drop - Drop Consolidated
			self.consolidation_type = "Drop"
		elif num_pick > 1 and num_drop > 1:
			# Multiple picks and drops - Route Consolidated (milk run)
			self.consolidation_type = "Route"
		else:
			# Default to Route if unable to determine
			if not self.consolidation_type:
				self.consolidation_type = "Route"
	
	def auto_determine_load_type(self):
		"""Auto-determine and set Load Type from first job when jobs are added"""
		if not self.transport_jobs:
			return
		
		# If load_type is already set, don't override
		if self.load_type:
			return
		
		# Get load type from first job
		for job in self.transport_jobs:
			if job.transport_job:
				try:
					job_doc = frappe.get_doc("Transport Job", job.transport_job)
					if job_doc.load_type:
						self.load_type = job_doc.load_type
						break
				except Exception:
					continue
	
	def validate_consolidation_rules(self):
		"""Validate that jobs can be consolidated based on load type rules"""
		# Require at least one Transport Job
		if not self.transport_jobs:
			return  # Allow empty consolidations in draft state
		
		# Load Type Required: If consolidation has jobs, Load Type must be set
		if not self.load_type:
			frappe.throw(_("Load Type is required when consolidation has jobs"))
		
		# Get load type and company from transport jobs
		load_types = set()
		companies = set()
		vehicle_types = set()
		transport_templates = set()
		transport_job_types = set()
		
		for job in self.transport_jobs:
			if not job.transport_job:
				continue
			
			job_doc = frappe.get_doc("Transport Job", job.transport_job)
			
			# Ensure all linked Transport Jobs are submitted
			if job_doc.docstatus != 1:
				frappe.throw(_("Transport Job {0} must be submitted to be included in consolidation").format(
					job_doc.name
				))
			
			# Collect load types, companies, vehicle types, templates, and job types
			if job_doc.load_type:
				load_types.add(job_doc.load_type)
			if job_doc.company:
				companies.add(job_doc.company)
			if job_doc.vehicle_type:
				vehicle_types.add(job_doc.vehicle_type)
			if job_doc.transport_template:
				transport_templates.add(job_doc.transport_template)
			if job_doc.transport_job_type:
				transport_job_types.add(job_doc.transport_job_type)
		
		# All jobs must have the same load type
		if len(load_types) > 1:
			frappe.throw(_("All transport jobs must have the same Load Type"))
		
		# Load Type Mismatch: Prevent adding jobs with different Load Types
		if load_types and self.load_type:
			if list(load_types)[0] != self.load_type:
				frappe.throw(_("Transport Job has Load Type {0} which does not match consolidation Load Type {1}").format(
					list(load_types)[0], self.load_type))
		
		# All jobs must have the same company
		if len(companies) > 1:
			frappe.throw(_("All transport jobs must belong to the same Company"))
		
		# Warn if jobs have different vehicle types
		if len(vehicle_types) > 1:
			frappe.msgprint(_("Warning: Transport Jobs have different vehicle types ({0}). This may cause issues.").format(
				", ".join(vehicle_types)
			), indicator="orange")
		
		if self.load_type:
			try:
				load_type_doc = frappe.get_doc("Load Type", self.load_type)
				
				# Check if load type allows consolidation (use can_handle_consolidation field)
				can_handle_consolidation = getattr(load_type_doc, "can_handle_consolidation", 0)
				if not (can_handle_consolidation == 1 or can_handle_consolidation == True):
					frappe.throw(_("Load Type {0} does not allow consolidation").format(self.load_type))
				
				# Check max consolidation jobs limit
				if load_type_doc.max_consolidation_jobs and len(self.transport_jobs) > load_type_doc.max_consolidation_jobs:
					frappe.throw(_("Cannot consolidate more than {0} jobs for Load Type {1}").format(
						load_type_doc.max_consolidation_jobs, self.load_type))
			except frappe.DoesNotExistError:
				frappe.throw(_("Load Type {0} does not exist").format(self.load_type))
	
	def validate_capacity_limits(self):
		"""Validate total weight and volume against Load Type limits"""
		if not self.transport_jobs or not self.load_type:
			return
		
		try:
			load_type_doc = frappe.get_doc("Load Type", self.load_type)
			
			# Check weight and volume limits after totals are calculated
			if load_type_doc.max_weight and flt(self.total_weight) > flt(load_type_doc.max_weight):
				frappe.throw(_("Total weight {0} kg exceeds maximum allowed weight {1} kg for Load Type {2}").format(
					flt(self.total_weight), flt(load_type_doc.max_weight), self.load_type))
			
			if load_type_doc.max_volume and flt(self.total_volume) > flt(load_type_doc.max_volume):
				frappe.throw(_("Total volume {0} m³ exceeds maximum allowed volume {1} m³ for Load Type {2}").format(
					flt(self.total_volume), flt(load_type_doc.max_volume), self.load_type))
		except frappe.DoesNotExistError:
			pass  # Load type validation already handled in validate_consolidation_rules
	
	def validate_date_alignment(self):
		"""Validate that all jobs have compatible delivery dates (within acceptable range)"""
		if not self.transport_jobs or len(self.transport_jobs) < 2:
			return
		
		from frappe.utils import getdate, date_diff
		
		dates = []
		for job in self.transport_jobs:
			if not job.transport_job:
				continue
			
			job_doc = frappe.get_doc("Transport Job", job.transport_job)
			# Get scheduled_date or booking_date as fallback
			job_date = job_doc.scheduled_date or job_doc.booking_date
			if job_date:
				dates.append(getdate(job_date))
		
		if not dates or len(dates) < 2:
			return
		
		# Check if dates are within acceptable range (7 days by default)
		min_date = min(dates)
		max_date = max(dates)
		date_range = date_diff(max_date, min_date)
		
		if date_range > 7:
			frappe.msgprint(_("Warning: Transport Jobs have delivery dates spanning {0} days. This may affect consolidation efficiency.").format(
				date_range), indicator="orange")
	
	def validate_vehicle_type_compatibility(self):
		"""Validate that all jobs use compatible vehicle types (if specified)"""
		if not self.transport_jobs:
			return
		
		vehicle_types = set()
		for job in self.transport_jobs:
			if not job.transport_job:
				continue
			
			job_doc = frappe.get_doc("Transport Job", job.transport_job)
			if job_doc.vehicle_type:
				vehicle_types.add(job_doc.vehicle_type)
		
		# If multiple vehicle types, check compatibility
		if len(vehicle_types) > 1:
			# Check if vehicle types are compatible (same base type or compatible)
			# This is a basic check - can be enhanced with Vehicle Type compatibility rules
			frappe.msgprint(_("Warning: Multiple vehicle types detected. Ensure they are compatible for consolidation."), 
				indicator="orange")
	
	def validate_status_workflow(self):
		"""Ensure status transitions are properly validated"""
		# Check if status field exists in the doctype
		meta = frappe.get_meta(self.doctype)
		if not meta.has_field("status"):
			return  # Skip validation if status field doesn't exist
		
		if self.is_new():
			return
		
		old_status = frappe.db.get_value(self.doctype, self.name, "status")
		new_status = self.status
		
		if old_status == new_status:
			return
		
		# Define allowed transitions
		allowed_transitions = {
			"Draft": ["Planned", "Cancelled"],
			"Planned": ["In Progress", "Cancelled"],
			"In Progress": ["Completed", "Cancelled"],
			"Completed": [],  # Cannot change from Completed
			"Cancelled": []  # Cannot change from Cancelled
		}
		
		if old_status and new_status not in allowed_transitions.get(old_status, []):
			frappe.throw(_("Cannot change status from {0} to {1}").format(old_status, new_status))
		
		# Status-specific validations
		if new_status == "Planned":
			# Planned: Consolidation is finalized, ready for Run Sheet assignment
			if not self.transport_jobs or len(self.transport_jobs) == 0:
				frappe.throw(_("Cannot set status to Planned without Transport Jobs"))
		
		if new_status in ["In Progress", "Completed"]:
			# In Progress/Completed: Must have Run Sheet
			if not self.run_sheet:
				frappe.throw(_("Cannot set status to {0} without Run Sheet").format(new_status))
	
	def calculate_totals(self):
		"""Calculate total weight and volume from transport consolidation job rows"""
		total_weight = 0
		total_volume = 0
		
		for job in self.transport_jobs:
			if job.weight:
				total_weight += flt(job.weight)
			if job.volume:
				total_volume += flt(job.volume)
		
		self.total_weight = total_weight
		self.total_volume = total_volume
	
	def validate_accounts(self):
		"""Validate accounting fields"""
		if not self.company:
			frappe.throw(_("Company is required"))
		
		# Validate cost center belongs to company
		if self.cost_center:
			# Check if Cost Center doctype has a company field before validating
			# Cost Center may not have a company field in this installation
			try:
				cost_center_meta = frappe.get_meta("Cost Center")
				if cost_center_meta.has_field("company"):
					try:
						cost_center_company = frappe.db.get_value("Cost Center", self.cost_center, "company")
						if cost_center_company and cost_center_company != self.company:
							frappe.throw(_("Cost Center {0} does not belong to Company {1}").format(
								self.cost_center, self.company))
					except Exception:
						# If database query fails (e.g., column doesn't exist), skip validation
						pass
			except Exception:
				# If Cost Center doctype doesn't exist or any other error, skip validation
				pass
		
		# Validate profit center belongs to company
		if self.profit_center:
			# Check if Profit Center doctype has a company field before validating
			# Profit Center may not have a company field in this installation
			try:
				profit_center_meta = frappe.get_meta("Profit Center")
				if profit_center_meta.has_field("company"):
					try:
						profit_center_company = frappe.db.get_value("Profit Center", self.profit_center, "company")
						if profit_center_company and profit_center_company != self.company:
							frappe.throw(_("Profit Center {0} does not belong to Company {1}").format(
								self.profit_center, self.company))
					except Exception:
						# If database query fails (e.g., column doesn't exist), skip validation
						pass
			except Exception:
				# If Profit Center doctype doesn't exist or any other error, skip validation
				pass
		
		# Validate branch belongs to company
		if self.branch:
			# Check if Branch doctype has a company field before validating
			# Branch may not have a company field in this installation
			try:
				branch_meta = frappe.get_meta("Branch")
				if branch_meta.has_field("company"):
					try:
						branch_company = frappe.db.get_value("Branch", self.branch, "company")
						if branch_company and branch_company != self.company:
							frappe.throw(_("Branch {0} does not belong to Company {1}").format(
								self.branch, self.company))
					except Exception:
						# If database query fails (e.g., column doesn't exist), skip validation
						pass
			except Exception:
				# If Branch doctype doesn't exist or any other error, skip validation
				pass
	
	def on_trash(self):
		"""
		Clear consolidation flags (pick_consolidated, drop_consolidated, transport_consolidation)
		from Transport Legs when the Transport Consolidation document is deleted.
		Only clears if the job isn't in another consolidation.
		For TRJs with no runsheets, all legs are cleared automatically so they can appear
		in consolidation suggestions again.
		"""
		try:
			# Get all jobs in this consolidation from the database
			# We need to query the database because the child table might already be deleted
			job_rows = frappe.get_all(
				"Transport Consolidation Job",
				filters={"parent": self.name},
				fields=["transport_job"]
			)
			
			if not job_rows:
				# No jobs in this consolidation, nothing to clear
				return
			
			# Clear consolidation flags for legs of all jobs
			for job_row in job_rows:
				job_name = job_row.get("transport_job")
				if not job_name:
					continue
				
				try:
					# Check if job is in any other consolidation
					other_consolidations = frappe.get_all(
						"Transport Consolidation Job",
						filters={
							"transport_job": job_name,
							"parent": ["!=", self.name]
						},
						fields=["parent"],
						limit=1
					)
					
					# If job is in another consolidation, don't clear flags
					if other_consolidations:
						continue
					
					# Get all legs for this job, including run_sheet field
					leg_fields = ["name", "transport_consolidation"]
					if frappe.db.has_column("Transport Leg", "pick_consolidated"):
						leg_fields.append("pick_consolidated")
					if frappe.db.has_column("Transport Leg", "drop_consolidated"):
						leg_fields.append("drop_consolidated")
					if frappe.db.has_column("Transport Leg", "run_sheet"):
						leg_fields.append("run_sheet")
					
					job_legs = frappe.get_all(
						"Transport Leg",
						filters={"transport_job": job_name},
						fields=leg_fields
					)
					
					# Check if this TRJ has any legs with run_sheet assigned
					has_runsheet = False
					if frappe.db.has_column("Transport Leg", "run_sheet"):
						has_runsheet = any(leg.get("run_sheet") for leg in job_legs)
					
					# If TRJ has no runsheets, clear ALL legs for this TRJ automatically
					# This allows the TRJ to appear in consolidation suggestions again
					if not has_runsheet:
						for leg in job_legs:
							leg_consolidation = leg.get("transport_consolidation")
							
							# Clear flags for all legs linked to this consolidation
							# Since TRJ has no runsheets, all legs should be cleared
							if leg_consolidation == self.name:
								# Use db_set for direct database update during deletion
								update_fields = {}
								if frappe.db.has_column("Transport Leg", "pick_consolidated"):
									update_fields["pick_consolidated"] = 0
								if frappe.db.has_column("Transport Leg", "drop_consolidated"):
									update_fields["drop_consolidated"] = 0
								update_fields["transport_consolidation"] = None
								
								# Update directly in database
								for field, value in update_fields.items():
									frappe.db.set_value("Transport Leg", leg.name, field, value, update_modified=False)
					else:
						# If TRJ has runsheets, only clear legs linked to this consolidation
						# that don't have run_sheet assigned (existing behavior)
						for leg in job_legs:
							leg_consolidation = leg.get("transport_consolidation")
							leg_run_sheet = leg.get("run_sheet")
							
							# Only clear flags if leg is linked to this consolidation AND has no run_sheet
							if leg_consolidation == self.name and not leg_run_sheet:
								# Use db_set for direct database update during deletion
								update_fields = {}
								if frappe.db.has_column("Transport Leg", "pick_consolidated"):
									update_fields["pick_consolidated"] = 0
								if frappe.db.has_column("Transport Leg", "drop_consolidated"):
									update_fields["drop_consolidated"] = 0
								update_fields["transport_consolidation"] = None
								
								# Update directly in database
								for field, value in update_fields.items():
									frappe.db.set_value("Transport Leg", leg.name, field, value, update_modified=False)
				
					# Commit changes for this job
					frappe.db.commit()
				except Exception as e:
					# Log error but don't fail deletion
					frappe.log_error(
						f"Error clearing consolidation flags for job {job_name} when deleting consolidation {self.name}: {str(e)}",
						"Clear Consolidation Flags on Delete Error"
					)
		except Exception as e:
			# Log error but don't fail deletion
			frappe.log_error(
				f"Error in on_trash for Transport Consolidation {self.name}: {str(e)}",
				"Transport Consolidation on_trash Error"
			)


@frappe.whitelist()
def create_run_sheet_from_consolidation(consolidation_name: str):
	"""
	Create a Run Sheet from a Transport Consolidation.
	Determines if it's Pick Consolidated or Drop Consolidated and sets appropriate checkboxes.
	Populates routing correctly based on consolidation type.
	"""
	try:
		# Check if consolidation_name is a temporary name (unsaved document)
		if consolidation_name and (consolidation_name.startswith("new-") or not frappe.db.exists("Transport Consolidation", consolidation_name)):
			return {
				"status": "error",
				"message": _("Please save the Transport Consolidation first before creating a Run Sheet. The document must be saved to the database.")
			}
		
		consolidation = frappe.get_doc("Transport Consolidation", consolidation_name)
		
		# Validate consolidation has jobs
		if not consolidation.transport_jobs or len(consolidation.transport_jobs) == 0:
			return {
				"status": "error",
				"message": _("Transport Consolidation must have at least one Transport Job")
			}
		
		# Check if Run Sheet already exists
		if consolidation.run_sheet:
			return {
				"status": "error",
				"message": _("Run Sheet {0} already exists for this consolidation").format(consolidation.run_sheet)
			}
		
		# Get all Transport Jobs and their Transport Legs
		transport_jobs = []
		all_legs = []
		
		for job_row in consolidation.transport_jobs:
			if not job_row.transport_job:
				continue
			
			job_doc = frappe.get_doc("Transport Job", job_row.transport_job)
			transport_jobs.append(job_doc)
			
			# Get all Transport Legs for this job
			job_legs = frappe.get_all(
				"Transport Leg",
				filters={"transport_job": job_doc.name},
				fields=["name", "pick_address", "drop_address", "facility_type_from", "facility_from",
				        "facility_type_to", "facility_to", "pick_mode", "drop_mode", "order"],
				order_by="`order` asc, creation asc"
			)
			
			for leg in job_legs:
				leg_doc = frappe.get_doc("Transport Leg", leg.name)
				all_legs.append(leg_doc)
		
		if not all_legs:
			return {
				"status": "error",
				"message": _("No Transport Legs found for the Transport Jobs in this consolidation")
			}
		
		# Determine consolidation pattern based on addresses
		# This determines how legs are organized in the Run Sheet
		pick_addresses = set()
		drop_addresses = set()
		
		for leg in all_legs:
			if leg.pick_address:
				pick_addresses.add(leg.pick_address)
			if leg.drop_address:
				drop_addresses.add(leg.drop_address)
		
		# Determine if it's pick consolidated or drop consolidated for Run Sheet routing
		is_pick_consolidated = len(pick_addresses) == 1 and len(drop_addresses) > 1
		is_drop_consolidated = len(drop_addresses) == 1 and len(pick_addresses) > 1
		is_both_consolidated = len(pick_addresses) == 1 and len(drop_addresses) == 1
		
		# If neither condition is met, default based on consolidation type
		if not is_pick_consolidated and not is_drop_consolidated and not is_both_consolidated:
			# Use the consolidation_type field to determine routing pattern
			if consolidation.consolidation_type == "Pick":
				is_pick_consolidated = True
			elif consolidation.consolidation_type == "Drop":
				is_drop_consolidated = True
			elif consolidation.consolidation_type == "Both":
				is_both_consolidated = True
			else:
				# Route consolidation - default to pick consolidated for routing
				is_pick_consolidated = True
				frappe.msgprint(
					_("Warning: Route consolidation detected. Using pick-consolidated routing pattern."),
					indicator="orange"
				)
		
		# Create Run Sheet
		run_sheet = frappe.new_doc("Run Sheet")
		run_sheet.transport_consolidation = consolidation_name
		run_sheet.company = consolidation.company
		
		# Set run_date from consolidation_date
		if consolidation.consolidation_date:
			from frappe.utils import get_datetime
			run_sheet.run_date = get_datetime(f"{consolidation.consolidation_date} 00:00:00")
		
		# Get vehicle type from first job
		if transport_jobs and transport_jobs[0].vehicle_type:
			run_sheet.vehicle_type = transport_jobs[0].vehicle_type
		
		# Filter out legs that are already assigned to another Run Sheet
		available_legs = []
		skipped_legs = []
		
		for leg in all_legs:
			if leg.run_sheet and leg.run_sheet != consolidation.run_sheet:
				skipped_legs.append(leg.name)
			else:
				available_legs.append(leg)
		
		if skipped_legs:
			frappe.msgprint(
				_("Warning: {0} Transport Leg(s) are already assigned to another Run Sheet and were skipped: {1}").format(
					len(skipped_legs), ", ".join(skipped_legs[:5])
				),
				indicator="orange"
			)
		
		if not available_legs:
			return {
				"status": "error",
				"message": _("All Transport Legs are already assigned to other Run Sheets")
			}
		
		# Add legs to Run Sheet based on consolidation pattern
		if is_both_consolidated:
			# Both Consolidated: Same pick and drop for all jobs
			# Sort legs by order or name
			sorted_legs = sorted(available_legs, key=lambda l: (l.order or 0, l.name))
			
			for leg in sorted_legs:
				run_sheet.append("legs", {
					"transport_leg": leg.name
				})
				
				# Set both flags for both consolidated
				leg.pick_consolidated = 1
				leg.drop_consolidated = 1
				leg.transport_consolidation = consolidation_name
				leg.save(ignore_permissions=True)
		
		elif is_pick_consolidated:
			# Pick Consolidated: One pick, multiple drops
			# All legs share the same pick address but have different drop addresses
			# Sort legs by drop address for logical routing order
			sorted_legs = sorted(available_legs, key=lambda l: (l.drop_address or "", l.name))
			
			# Add all legs to Run Sheet
			for leg in sorted_legs:
				run_sheet.append("legs", {
					"transport_leg": leg.name
				})
				
				# Set pick_consolidated checkbox on all legs
				leg.pick_consolidated = 1
				leg.drop_consolidated = 0  # Clear drop_consolidated if it was set
				leg.transport_consolidation = consolidation_name
				leg.save(ignore_permissions=True)
		
		elif is_drop_consolidated:
			# Drop Consolidated: Multiple picks, one drop
			# All legs share the same drop address but have different pick addresses
			# Sort legs by pick address for logical routing order
			sorted_legs = sorted(available_legs, key=lambda l: (l.pick_address or "", l.name))
			
			# Add all legs to Run Sheet
			for leg in sorted_legs:
				run_sheet.append("legs", {
					"transport_leg": leg.name
				})
				
				# Set drop_consolidated checkbox on all legs
				leg.drop_consolidated = 1
				leg.pick_consolidated = 0  # Clear pick_consolidated if it was set
				leg.transport_consolidation = consolidation_name
				leg.save(ignore_permissions=True)
		
		else:
			# Route Consolidated: Multiple picks and drops (milk run)
			# Sort by pick address first, then drop address for route optimization
			sorted_legs = sorted(available_legs, key=lambda l: (l.pick_address or "", l.drop_address or "", l.name))
			
			for leg in sorted_legs:
				run_sheet.append("legs", {
					"transport_leg": leg.name
				})
				
				# Route consolidations may have mixed patterns
				leg.transport_consolidation = consolidation_name
				leg.save(ignore_permissions=True)
		
		# Save Run Sheet
		run_sheet.insert(ignore_permissions=True)
		
		# Update consolidation with Run Sheet link
		consolidation.run_sheet = run_sheet.name
		consolidation.save(ignore_permissions=True)
		
		frappe.db.commit()
		
		return {
			"status": "success",
			"run_sheet_name": run_sheet.name,
			"consolidation_type": consolidation.consolidation_type,
			"is_pick_consolidated": is_pick_consolidated,
			"is_drop_consolidated": is_drop_consolidated,
			"is_both_consolidated": is_both_consolidated,
			"legs_count": len(run_sheet.legs)
		}
		
	except Exception as e:
		frappe.log_error(f"Error creating Run Sheet from Transport Consolidation: {str(e)}")
		frappe.db.rollback()
		return {
			"status": "error",
			"message": str(e)
		}


@frappe.whitelist()
def fetch_matching_jobs(consolidation_name: str):
	"""
	Automatically find and add matching Transport Jobs to a consolidation.
	When consolidation_type is "Pick", the system will find transport jobs with:
	- Same transport_template
	- Same transport_job_type
	- Same load_type
	- Same date range
	- Within weight/volume limits
	- Compatible vehicle types
	- No conflicting requirements
	- No conflicting checkbox between hazardous and refrigeration
	
	The system will automatically modify pick_consolidated=1 and drop_consolidated=1 on Transport Legs.
	"""
	try:
		# Check if consolidation_name is a temporary name (unsaved document)
		if consolidation_name and (consolidation_name.startswith("new-") or not frappe.db.exists("Transport Consolidation", consolidation_name)):
			return {
				"status": "error",
				"message": _("Please save the Transport Consolidation first before fetching matching jobs. The document must be saved to the database.")
			}
		
		consolidation = frappe.get_doc("Transport Consolidation", consolidation_name)
		
		# Require consolidation_type to be set
		if not consolidation.consolidation_type:
			return {
				"status": "error",
				"message": _("Consolidation Type must be set to fetch matching jobs")
			}
		
		# Require load_type to be set
		if not consolidation.load_type:
			return {
				"status": "error",
				"message": _("Load Type must be set to fetch matching jobs")
			}
		
		# Require company to be set
		if not consolidation.company:
			return {
				"status": "error",
				"message": _("Company must be set to fetch matching jobs")
			}
		
		# Get reference job to match against (if available)
		reference_job = None
		if consolidation.transport_jobs and len(consolidation.transport_jobs) > 0:
			# Use first job as reference
			first_job_row = consolidation.transport_jobs[0]
			if first_job_row.transport_job:
				reference_job = frappe.get_doc("Transport Job", first_job_row.transport_job)
		
		# Build filters based on consolidation type
		filters = {
			"docstatus": 1,  # Only submitted jobs
			"load_type": consolidation.load_type,
			"company": consolidation.company,
		}
		
		# Match transport_template if set (from reference job or can be left optional)
		if reference_job and reference_job.transport_template:
			filters["transport_template"] = reference_job.transport_template
		
		# Match transport_job_type if set (from reference job or can be left optional)
		if reference_job and reference_job.transport_job_type:
			filters["transport_job_type"] = reference_job.transport_job_type
		
		# Exclude jobs already in this consolidation
		existing_job_names = [row.transport_job for row in consolidation.transport_jobs if row.transport_job]
		if existing_job_names:
			filters["name"] = ["not in", existing_job_names]
		
		# Get matching jobs
		matching_jobs = frappe.get_all(
			"Transport Job",
			filters=filters,
			fields=["name", "transport_template", "transport_job_type", "load_type", 
			        "vehicle_type", "hazardous", "refrigeration", "scheduled_date", "booking_date", "company"],
			order_by="creation desc"
		)
		
		if not matching_jobs:
			return {
				"status": "success",
				"message": _("No matching jobs found"),
				"added_count": 0
			}
		
		# Get Load Type limits
		load_type_doc = frappe.get_doc("Load Type", consolidation.load_type)
		max_jobs = load_type_doc.max_consolidation_jobs or 999999
		max_weight = load_type_doc.max_weight or 999999
		max_volume = load_type_doc.max_volume or 999999
		
		# Calculate current totals
		current_weight = flt(consolidation.total_weight or 0)
		current_volume = flt(consolidation.total_volume or 0)
		current_job_count = len(consolidation.transport_jobs)
		
		# Filter and validate matching jobs
		valid_jobs = []
		date_range_days = 7  # Acceptable date range for consolidation
		
		from frappe.utils import getdate, date_diff
		# Get reference date from reference job or consolidation date
		reference_date = None
		if reference_job:
			reference_date = getdate(reference_job.scheduled_date or reference_job.booking_date)
		elif consolidation.consolidation_date:
			reference_date = getdate(consolidation.consolidation_date)
		
		# Track reference hazardous/refrigeration values (from reference job or first valid job)
		reference_hazardous = None
		reference_refrigeration = None
		if reference_job:
			reference_hazardous = reference_job.hazardous
			reference_refrigeration = reference_job.refrigeration
		
		for job_data in matching_jobs:
			# Check max jobs limit
			if current_job_count + len(valid_jobs) >= max_jobs:
				break
			
			# Check date range compatibility (if reference date is available)
			if reference_date:
				job_date = getdate(job_data.scheduled_date or job_data.booking_date)
				if job_date:
					date_diff_days = abs(date_diff(job_date, reference_date))
					if date_diff_days > date_range_days:
						continue
			
			# Check vehicle type compatibility (only if reference job exists)
			if reference_job and reference_job.vehicle_type and job_data.vehicle_type:
				if reference_job.vehicle_type != job_data.vehicle_type:
					# Allow different vehicle types but warn
					pass  # Will be handled by validation
			
			# Check conflicting requirements (hazardous and refrigeration)
			# Jobs with hazardous and refrigeration must match exactly
			if reference_hazardous is None:
				# No reference yet - use first job's values as reference
				# This ensures all fetched jobs have the same hazardous/refrigeration requirements
				reference_hazardous = job_data.hazardous
				reference_refrigeration = job_data.refrigeration
			else:
				# Compare with reference values
				if reference_hazardous != job_data.hazardous:
					continue  # Cannot mix hazardous and non-hazardous
				if reference_refrigeration != job_data.refrigeration:
					continue  # Cannot mix refrigeration and non-refrigeration
			
			# Get job document to calculate weight/volume
			try:
				job_doc = frappe.get_doc("Transport Job", job_data.name)
				
				# Calculate job weight and volume
				job_weight = 0
				job_volume = 0
				for package in job_doc.packages:
					if package.weight:
						job_weight += flt(package.weight)
					if package.volume:
						job_volume += flt(package.volume)
				
				# Check weight and volume limits
				if current_weight + job_weight > max_weight:
					continue
				if current_volume + job_volume > max_volume:
					continue
				
				# Check if job has legs compatible with consolidation type
				leg_fields = ["name", "pick_address", "drop_address", "pick_consolidated", "drop_consolidated", "transport_consolidation"]
				# Add run_sheet field if it exists
				if frappe.db.has_column("Transport Leg", "run_sheet"):
					leg_fields.append("run_sheet")
				
				job_legs = frappe.get_all(
					"Transport Leg",
					filters={"transport_job": job_data.name},
					fields=leg_fields
				)
				
				if not job_legs:
					continue
				
				# Check if any leg has a run_sheet - if so, skip this job
				has_runsheet = False
				for leg in job_legs:
					if leg.get("run_sheet"):
						has_runsheet = True
						break
				
				if has_runsheet:
					continue
				
				# Check if legs are already consolidated
				has_available_legs = False
				for leg in job_legs:
					if not leg.get("transport_consolidation") or leg.get("transport_consolidation") == consolidation_name:
						has_available_legs = True
						break
				
				if not has_available_legs:
					continue
				
				valid_jobs.append({
					"job_name": job_data.name,
					"weight": job_weight,
					"volume": job_volume
				})
				
				current_weight += job_weight
				current_volume += job_volume
				
			except Exception as e:
				frappe.log_error(f"Error processing job {job_data.name}: {str(e)}", "Fetch Matching Jobs Error")
				continue
		
		# Add valid jobs to consolidation
		added_count = 0
		for job_info in valid_jobs:
			try:
				# Check if job already exists
				existing = False
				for existing_job in consolidation.transport_jobs:
					if existing_job.transport_job == job_info["job_name"]:
						existing = True
						break
				
				if existing:
					continue
				
				# Add job to consolidation
				consolidation_job_row = consolidation.append("transport_jobs", {
					"transport_job": job_info["job_name"]
				})
				
				# Explicitly calculate weight and volume from transport job packages
				# This ensures weight and volume are computed when job is added from dialog
				if consolidation_job_row:
					# Set parent reference for the child document (needed for company lookup)
					consolidation_job_row.parent = consolidation_name
					# Calculate weight and volume from packages
					consolidation_job_row.calculate_weight_and_volume()
				
				# Update Transport Legs with consolidation flags
				job_legs = frappe.get_all(
					"Transport Leg",
					filters={"transport_job": job_info["job_name"]},
					fields=["name"]
				)
				
				for leg in job_legs:
					leg_doc = frappe.get_doc("Transport Leg", leg.name)
					
					# Skip if leg is already in another consolidation
					if leg_doc.transport_consolidation and leg_doc.transport_consolidation != consolidation_name:
						continue
					
					# Set consolidation flags based on consolidation_type
					if consolidation.consolidation_type == "Pick":
						leg_doc.pick_consolidated = 1
						leg_doc.drop_consolidated = 0
					elif consolidation.consolidation_type == "Drop":
						leg_doc.pick_consolidated = 0
						leg_doc.drop_consolidated = 1
					elif consolidation.consolidation_type == "Both":
						leg_doc.pick_consolidated = 1
						leg_doc.drop_consolidated = 1
					
					leg_doc.transport_consolidation = consolidation_name
					leg_doc.save(ignore_permissions=True)
				
				added_count += 1
				
			except Exception as e:
				frappe.log_error(f"Error adding job {job_info['job_name']}: {str(e)}", "Fetch Matching Jobs Error")
				continue
		
		# Save consolidation
		if added_count > 0:
			consolidation.save(ignore_permissions=True)
			frappe.db.commit()
		
		return {
			"status": "success",
			"message": _("Added {0} matching job(s)").format(added_count),
			"added_count": added_count,
			"total_jobs": len(consolidation.transport_jobs)
		}
		
	except Exception as e:
		frappe.log_error(f"Error fetching matching jobs: {str(e)}", "Fetch Matching Jobs Error")
		frappe.db.rollback()
		return {
			"status": "error",
			"message": str(e)
		}


@frappe.whitelist()
def get_consolidatable_jobs(consolidation_type: str = None, company: str = None, date: str = None, current_consolidation: str = None):
	"""
	Get all Transport Jobs with legs that can be consolidated (same pick or same drop).
	Returns jobs grouped by consolidation type.
	
	Validations performed:
	1. Job must be submitted (docstatus = 1)
	2. Job must belong to specified company (if provided)
	3. Job must have at least one Transport Leg
	4. Transport Legs must have pick_address and drop_address
	5. Load Type must have can_handle_consolidation = 1 (primary requirement)
	   OR Transport Job must have consolidate = 1 (fallback for backward compatibility)
	6. Job must match consolidation_type filter (if provided)
	
	Priority: If Load Type has can_handle_consolidation = 1, the job is included
	regardless of the consolidate flag. If Load Type doesn't have can_handle_consolidation = 1,
	then the consolidate flag is checked as a fallback.
	
	Args:
		consolidation_type: Filter by consolidation type (Pick, Drop, Both, Route)
		company: Filter by company
		date: Filter by date (not currently implemented)
		current_consolidation: Name of current consolidation (to allow jobs from this consolidation)
	
	Returns empty list if no jobs match all criteria.
	"""
	try:
		# Build filters for Transport Jobs
		filters = {"docstatus": 1}  # Only submitted jobs
		
		if company:
			filters["company"] = company
		
		# Note: We don't filter by consolidate in the initial query
		# Instead, we check it in the loop so we can track it in debug info
		# and handle cases where the field might not exist
		
		# Get all submitted Transport Jobs
		# Include group_legs_in_one_runsheet field for filtering
		job_fields = ["name", "customer", "company", "status", "load_type", "vehicle_type"]
		if frappe.db.has_column("Transport Job", "group_legs_in_one_runsheet"):
			job_fields.append("group_legs_in_one_runsheet")
		if frappe.db.has_column("Transport Job", "consolidate"):
			job_fields.append("consolidate")
		
		all_jobs = frappe.get_all(
			"Transport Job",
			filters=filters,
			fields=job_fields,
			order_by="creation desc"
		)
		
		# Initialize variables for diagnostics
		legs_by_job = {}
		existing_consolidation_jobs = set()
		
		# Get Transport Legs for all jobs (if any exist)
		if not all_jobs:
			# No jobs found - return with diagnostics
			debug_info = {
				"total_jobs_found": 0,
				"jobs_without_legs": 0,
				"jobs_without_load_type": 0,
				"jobs_with_invalid_load_type": 0,
				"jobs_without_consolidate_flag": 0,
				"jobs_without_addresses": 0,
				"jobs_already_consolidated": 0,
				"jobs_with_runsheet": 0,
				"consolidatable_jobs_found": 0,
				"consolidation_groups_found": 0,
				"company_filter": company,
				"consolidation_type_filter": consolidation_type,
				"message": "No submitted Transport Jobs found matching the criteria."
			}
			return {
				"status": "success",
				"jobs": [],
				"consolidation_groups": [],
				"debug": debug_info
			}
		
		job_names = [job["name"] for job in all_jobs]
		# Fetch consolidation-related fields to check if legs are already consolidated
		leg_fields = ["name", "transport_job", "pick_address", "drop_address", "status"]
		# Add consolidation fields if they exist
		if frappe.db.has_column("Transport Leg", "pick_consolidated"):
			leg_fields.append("pick_consolidated")
		if frappe.db.has_column("Transport Leg", "drop_consolidated"):
			leg_fields.append("drop_consolidated")
		if frappe.db.has_column("Transport Leg", "transport_consolidation"):
			leg_fields.append("transport_consolidation")
		# Add run_sheet field to check if legs are assigned to run sheets
		if frappe.db.has_column("Transport Leg", "run_sheet"):
			leg_fields.append("run_sheet")
		
		all_legs = frappe.get_all(
			"Transport Leg",
			filters={"transport_job": ["in", job_names]},
			fields=leg_fields,
			order_by="transport_job, creation"
		)
		
		# Group legs by job
		legs_by_job = {}
		for leg in all_legs:
			job_name = leg["transport_job"]
			if job_name not in legs_by_job:
				legs_by_job[job_name] = []
			legs_by_job[job_name].append(leg)
		
		# Analyze each job for consolidation potential
		consolidatable_jobs = []
		pick_groups = {}  # Group by pick address
		drop_groups = {}  # Group by drop address
		
		# Get jobs that are already in consolidations (optional filter)
		# If current_consolidation is provided, exclude jobs that are in OTHER consolidations
		# but allow jobs that are only in the current consolidation
		existing_consolidation_jobs = set()
		jobs_in_current_consolidation = set()
		
		if frappe.db.has_table("Transport Consolidation Job"):
			if current_consolidation:
				# Get jobs in current consolidation (to allow them to be shown)
				current_consolidation_jobs = frappe.get_all(
					"Transport Consolidation Job",
					filters={"parent": current_consolidation},
					fields=["transport_job"]
				)
				jobs_in_current_consolidation = {row["transport_job"] for row in current_consolidation_jobs if row.get("transport_job")}
				
				# Get jobs in OTHER consolidations (to exclude them)
				existing_consolidations = frappe.get_all(
					"Transport Consolidation Job",
					filters={"parent": ["!=", current_consolidation]},
					fields=["transport_job"],
					distinct=True
				)
				existing_consolidation_jobs = {row["transport_job"] for row in existing_consolidations if row.get("transport_job")}
			else:
				# No current consolidation specified - exclude all jobs in any consolidation
				existing_consolidations = frappe.get_all(
					"Transport Consolidation Job",
					fields=["transport_job"],
					distinct=True
				)
				existing_consolidation_jobs = {row["transport_job"] for row in existing_consolidations if row.get("transport_job")}
		
		# Track excluded jobs for diagnostics
		excluded_jobs_reasons = {}
		
		for job in all_jobs:
			job_name = job["name"]
			legs = legs_by_job.get(job_name, [])
			
			if not legs:
				excluded_jobs_reasons[job_name] = "no_legs"
				continue
			
			# Check if job is already in another consolidation (not the current one)
			if job_name in existing_consolidation_jobs:
				# Skip jobs that are already in another consolidation
				excluded_jobs_reasons[job_name] = "in_other_consolidation"
				continue
			
			# Check if legs are already consolidated (have pick_consolidated/drop_consolidated flags or transport_consolidation link)
			# Also check if any leg has a run_sheet assigned - if so, skip this job
			# If current_consolidation is provided, only consider legs consolidated to OTHER consolidations
			already_consolidated_legs = []
			has_runsheet = False
			for leg in legs:
				# Check if leg has a run_sheet
				if leg.get("run_sheet"):
					has_runsheet = True
					break
				
				# Check consolidation flags
				leg_consolidation = leg.get("transport_consolidation")
				has_consolidation_flag = (
					leg.get("pick_consolidated") == 1 or 
					leg.get("drop_consolidated") == 1 or
					leg_consolidation
				)
				
				# If current_consolidation is provided, only count legs consolidated to OTHER consolidations
				if has_consolidation_flag:
					if current_consolidation and leg_consolidation == current_consolidation:
						# Leg is consolidated to current consolidation - don't count it as "already consolidated"
						# This allows jobs that were removed from current consolidation to appear again
						pass
					else:
						# Leg is consolidated to another consolidation or has flags set
						already_consolidated_legs.append(leg.get("name"))
			
			# Skip jobs that have any leg with a run_sheet
			if has_runsheet:
				excluded_jobs_reasons[job_name] = "has_runsheet"
				continue
			
			# If all legs are already consolidated (to other consolidations), skip this job
			if len(already_consolidated_legs) == len(legs):
				excluded_jobs_reasons[job_name] = "all_legs_consolidated"
				continue
			
			# Validate Load Type allows consolidation
			# If Load Type has can_handle_consolidation = 1, include the job (regardless of consolidate flag)
			load_type = job.get("load_type")
			if load_type:
				try:
					# Check can_handle_consolidation field (required)
					can_handle_consolidation = frappe.db.get_value("Load Type", load_type, "can_handle_consolidation")
					# Explicitly check if Load Type allows consolidation (1 or True means allowed)
					if can_handle_consolidation == 1 or can_handle_consolidation == True:
						# Load Type allows consolidation, continue processing this job
						pass  # Continue processing this job
					else:
						# Load Type doesn't allow consolidation (None, 0, False all mean not consolidatable)
						# Check if job has consolidate = 1 as a fallback (for backward compatibility)
						if frappe.db.has_column("Transport Job", "consolidate"):
							if job.get("consolidate") == 1:
								# Job has consolidate flag set, allow it even if Load Type doesn't have can_handle_consolidation
								pass  # Continue processing this job
							else:
								# Skip jobs whose Load Type doesn't allow consolidation AND consolidate flag is not set
								excluded_jobs_reasons[job_name] = "invalid_load_type"
								continue
						else:
							# Skip jobs whose Load Type doesn't allow consolidation (no consolidate field to check)
							excluded_jobs_reasons[job_name] = "invalid_load_type"
							continue
				except Exception:
					# If Load Type doesn't exist or error, skip this job
					frappe.log_error(f"Error checking can_handle_consolidation for Load Type {load_type} in job {job_name}")
					excluded_jobs_reasons[job_name] = "load_type_error"
					continue
			else:
				# If job has no load_type, check if consolidate flag is set (for backward compatibility)
				if frappe.db.has_column("Transport Job", "consolidate"):
					if job.get("consolidate") == 1:
						# Job has consolidate flag set but no load_type, allow it
						pass  # Continue processing this job
					else:
						# Skip jobs without load_type and without consolidate flag
						excluded_jobs_reasons[job_name] = "no_load_type"
						continue
				else:
					# Skip jobs without load_type (load_type is required for consolidation)
					excluded_jobs_reasons[job_name] = "no_load_type"
					continue
			
			# Get unique pick and drop addresses (only from non-consolidated legs)
			pick_addresses = set()
			drop_addresses = set()
			available_legs_count = 0
			
			for leg in legs:
				# Skip legs that have a run_sheet assigned
				if leg.get("run_sheet"):
					continue
				
				# Only consider legs that are not already consolidated
				has_consolidation_flag = (
					leg.get("pick_consolidated") == 1 or 
					leg.get("drop_consolidated") == 1 or
					leg.get("transport_consolidation")
				)
				
				if not has_consolidation_flag:
					available_legs_count += 1
					if leg.get("pick_address"):
						pick_addresses.add(leg["pick_address"])
					if leg.get("drop_address"):
						drop_addresses.add(leg["drop_address"])
			
			# If no available legs (all are already consolidated), skip
			if available_legs_count == 0:
				continue
			
			# Determine consolidation type based on address patterns
			num_pick = len(pick_addresses)
			num_drop = len(drop_addresses)
			total_legs = len(legs)
			
			if num_pick == 1 and num_drop == 1:
				consolidation_type_str = "Both"
			elif num_pick == 1 and num_drop > 1:
				consolidation_type_str = "Pick"
			elif num_pick > 1 and num_drop == 1:
				consolidation_type_str = "Drop"
			elif num_pick > 1 and num_drop > 1:
				consolidation_type_str = "Route"
			else:
				consolidation_type_str = "Route"  # Default
			
			# For Route jobs (multiple legs), include them even if they don't have addresses
			# For other jobs, they must have at least one pick address and one drop address
			if total_legs > 1 or (num_pick > 0 and num_drop > 0):
				# Determine if pick or drop is consolidated for display purposes
				is_pick_consolidated = num_pick == 1
				is_drop_consolidated = num_drop == 1
				
				# Get address names for display
				pick_address_name = None
				drop_address_name = None
				
				# Handle Route jobs (multiple legs) that might not have addresses
				if pick_addresses:
					pick_address_name = frappe.db.get_value("Address", list(pick_addresses)[0], "address_title") or list(pick_addresses)[0]
				elif total_legs > 1:
					# Route job without pick addresses - show as "-" or "N/A"
					pick_address_name = "-"
				
				if drop_addresses:
					drop_address_name = frappe.db.get_value("Address", list(drop_addresses)[0], "address_title") or list(drop_addresses)[0]
				elif total_legs > 1:
					# Route job without drop addresses - show as "-" or "N/A"
					drop_address_name = "-"
				
				# Get all address titles for tooltip display (when there are multiple addresses)
				pick_address_titles = []
				drop_address_titles = []
				# Populate address titles when there are multiple addresses (which would show "X different" in the UI)
				# This allows tooltips to work for Route consolidation type or when consolidation_type filter is blank
				if num_pick > 1 or num_drop > 1:
					# Fetch all pick address titles
					if pick_addresses:
						for addr_id in pick_addresses:
							addr_title = frappe.db.get_value("Address", addr_id, "address_title") or addr_id
							pick_address_titles.append(addr_title)
					# Fetch all drop address titles
					if drop_addresses:
						for addr_id in drop_addresses:
							addr_title = frappe.db.get_value("Address", addr_id, "address_title") or addr_id
							drop_address_titles.append(addr_title)
				
				# Check if some legs are already consolidated
				has_partial_consolidation = len(already_consolidated_legs) > 0 and len(already_consolidated_legs) < len(legs)
				
				job_info = {
					"name": job_name,
					"customer": job.get("customer"),
					"company": job.get("company"),
					"status": job.get("status"),
					"pick_address": pick_address_name if is_pick_consolidated else f"{len(pick_addresses)} different",
					"drop_address": drop_address_name if is_drop_consolidated else f"{len(drop_addresses)} different",
					"consolidation_type": consolidation_type_str,
					"legs_count": total_legs,  # Total legs count for Route filtering
					"available_legs_count": available_legs_count,
					"already_consolidated_legs_count": len(already_consolidated_legs),
					"has_partial_consolidation": has_partial_consolidation,
					"pick_addresses": list(pick_addresses),  # Store all pick addresses for filtering
					"drop_addresses": list(drop_addresses),  # Store all drop addresses for filtering
					"pick_address_titles": pick_address_titles,  # Store pick address titles for Route tooltip
					"drop_address_titles": drop_address_titles  # Store drop address titles for Route tooltip
				}
				
				consolidatable_jobs.append(job_info)
				
				# Group for consolidation suggestions
				# Include jobs in pick_groups if they can participate in Pick consolidation
				# (i.e., they have at least one pick address)
				if num_pick >= 1:
					# For Pick consolidation, we need jobs that share a pick address
					# Add job to pick_groups for each of its pick addresses
					for pick_addr in pick_addresses:
						if pick_addr not in pick_groups:
							pick_groups[pick_addr] = []
						pick_groups[pick_addr].append(job_info)
				
				# Include jobs in drop_groups if they can participate in Drop consolidation
				# (i.e., they have at least one drop address)
				if num_drop >= 1:
					# For Drop consolidation, we need jobs that share a drop address
					# Add job to drop_groups for each of its drop addresses
					for drop_addr in drop_addresses:
						if drop_addr not in drop_groups:
							drop_groups[drop_addr] = []
						drop_groups[drop_addr].append(job_info)
		
		# Build consolidation groups and determine dynamic consolidation_type for each job
		consolidation_groups = []
		
		# Track which jobs can participate in which consolidation types
		job_pick_consolidation = {}  # job_name -> can_participate_in_pick
		job_drop_consolidation = {}  # job_name -> can_participate_in_drop
		job_both_consolidation = {}  # job_name -> can_participate_in_both
		
		# Analyze pick groups to determine Pick consolidation potential
		for pick_addr, jobs in pick_groups.items():
			if len(jobs) > 1:  # Only groups with multiple jobs
				# All jobs in this group share the same pick address (by definition of pick_groups)
				# Check if they also share the same drop address (Both) or have different drop addresses (Pick)
				all_drop_addresses = set()
				for job in jobs:
					drop_addrs = job.get("drop_addresses", [])
					all_drop_addresses.update(drop_addrs)
				
				# If all jobs have the same drop address (and same pick address), it's Both consolidation
				if len(all_drop_addresses) == 1:
					for job in jobs:
						job_both_consolidation[job["name"]] = True
					# Create Both consolidation group
					drop_addr = list(all_drop_addresses)[0]
					consolidation_groups.append({
						"type": "Both",
						"address": f"{frappe.db.get_value('Address', pick_addr, 'address_title') or pick_addr} → {frappe.db.get_value('Address', drop_addr, 'address_title') or drop_addr}",
						"jobs": [j["name"] for j in jobs],
						"count": len(jobs)
					})
				# If multiple drop addresses, jobs can participate in Pick consolidation
				else:
					for job in jobs:
						job_pick_consolidation[job["name"]] = True
					consolidation_groups.append({
						"type": "Pick",
						"address": frappe.db.get_value("Address", pick_addr, "address_title") or pick_addr,
						"jobs": [j["name"] for j in jobs],
						"count": len(jobs)
					})
		
		# Analyze drop groups to determine Drop consolidation potential
		# Note: Both consolidation is already handled in pick groups, so we only check for Drop here
		for drop_addr, jobs in drop_groups.items():
			if len(jobs) > 1:  # Only groups with multiple jobs
				# All jobs in this group share the same drop address (by definition of drop_groups)
				# Check if they have different pick addresses (Drop consolidation)
				# (Both consolidation is already handled in pick groups above)
				all_pick_addresses = set()
				for job in jobs:
					pick_addrs = job.get("pick_addresses", [])
					all_pick_addresses.update(pick_addrs)
				
				# If multiple pick addresses, jobs can participate in Drop consolidation
				# (Skip if already marked as Both - Both takes priority)
				if len(all_pick_addresses) > 1:
					# Only mark as Drop if not already marked as Both
					has_both = any(job_both_consolidation.get(job["name"], False) for job in jobs)
					if not has_both:
						for job in jobs:
							job_drop_consolidation[job["name"]] = True
						consolidation_groups.append({
							"type": "Drop",
							"address": frappe.db.get_value("Address", drop_addr, "address_title") or drop_addr,
							"jobs": [j["name"] for j in jobs],
							"count": len(jobs)
						})
		
		# Set dynamic consolidation_type for each job based on consolidation potential
		# Priority: Both > Pick > Drop > Route (if multiple legs)
		for job in consolidatable_jobs:
			job_name = job["name"]
			dynamic_type = None
			
			# Check if job is Route type (jobs with multiple legs)
			if job.get("legs_count", 0) > 1:
				dynamic_type = "Route"
			# Check if job can participate in Both consolidation
			elif job_both_consolidation.get(job_name, False):
				dynamic_type = "Both"
			# Check if job can participate in Pick consolidation
			elif job_pick_consolidation.get(job_name, False):
				dynamic_type = "Pick"
			# Check if job can participate in Drop consolidation
			elif job_drop_consolidation.get(job_name, False):
				dynamic_type = "Drop"
			
			# Update job's consolidation_type (will be set to blank if no filter and no consolidation potential)
			job["consolidation_type"] = dynamic_type
		
		# Filter by date if provided
		if date:
			# This would require checking job dates, which may not be available in Transport Job
			# For now, we'll skip date filtering or implement it based on available date fields
			pass
		
		# Filter by consolidation_type (type_filter) if provided
		# Apply enhanced filtering logic based on type_filter requirements
		if consolidation_type:
			if consolidation_type == "Pick":
				# Pick: List jobs with same Pick Address but different Drop addresses
				# Exclude jobs with multiple legs (Route jobs)
				# Exclude jobs if they have identical Drop Address (when grouped by Pick Address)
				
				# First, exclude jobs with multiple legs (Route jobs)
				filtered_jobs = [
					j for j in consolidatable_jobs 
					if j.get("legs_count", 0) <= 1
				]
				
				# Group jobs by Pick Address
				pick_addr_groups = {}
				for job in filtered_jobs:
					pick_addrs = job.get("pick_addresses", [])
					for pick_addr in pick_addrs:
						if pick_addr not in pick_addr_groups:
							pick_addr_groups[pick_addr] = []
						pick_addr_groups[pick_addr].append(job)
				
				# Filter: Only include jobs that share a Pick Address with other jobs
				# AND have different Drop addresses (exclude groups where all jobs have identical Drop Address)
				valid_jobs = []
				for pick_addr, jobs_in_group in pick_addr_groups.items():
					if len(jobs_in_group) > 1:  # Multiple jobs share this Pick Address
						# Collect all unique drop addresses for jobs in this group
						# A job might have multiple drop addresses, so we need to check all of them
						all_drop_addresses = set()
						for job in jobs_in_group:
							drop_addrs = job.get("drop_addresses", [])
							all_drop_addresses.update(drop_addrs)
						
						# Only include this group if there are multiple different drop addresses
						# (meaning jobs have different drop addresses for the same pick address)
						if len(all_drop_addresses) > 1:
							# All jobs in this group are valid (they share pick address but have different drop addresses)
							valid_jobs.extend(jobs_in_group)
						# If all jobs have the same drop address(es), exclude the entire group
				
				# Remove duplicates (a job might be added multiple times if it has multiple pick addresses)
				# consolidation_type is already set dynamically above
				seen_job_names = set()
				consolidatable_jobs = []
				for job in valid_jobs:
					if job["name"] not in seen_job_names:
						seen_job_names.add(job["name"])
						# Ensure consolidation_type is set to "Pick" for filtered results
						job["consolidation_type"] = "Pick"
						consolidatable_jobs.append(job)
						
			elif consolidation_type == "Drop":
				# Drop: List jobs with same Drop Address but different Pick addresses
				# Exclude jobs with multiple legs (Route jobs)
				# Exclude jobs if they have identical Pick Address (when grouped by Drop Address)
				
				# First, exclude jobs with multiple legs (Route jobs)
				filtered_jobs = [
					j for j in consolidatable_jobs 
					if j.get("legs_count", 0) <= 1
				]
				
				# Group jobs by Drop Address
				drop_addr_groups = {}
				for job in filtered_jobs:
					drop_addrs = job.get("drop_addresses", [])
					for drop_addr in drop_addrs:
						if drop_addr not in drop_addr_groups:
							drop_addr_groups[drop_addr] = []
						drop_addr_groups[drop_addr].append(job)
				
				# Filter: Only include jobs that share a Drop Address with other jobs
				# AND have different Pick addresses (exclude groups where all jobs have identical Pick Address)
				valid_jobs = []
				for drop_addr, jobs_in_group in drop_addr_groups.items():
					if len(jobs_in_group) > 1:  # Multiple jobs share this Drop Address
						# Collect all unique pick addresses for jobs in this group
						# A job might have multiple pick addresses, so we need to check all of them
						all_pick_addresses = set()
						for job in jobs_in_group:
							pick_addrs = job.get("pick_addresses", [])
							all_pick_addresses.update(pick_addrs)
						
						# Only include this group if there are multiple different pick addresses
						# (meaning jobs have different pick addresses for the same drop address)
						if len(all_pick_addresses) > 1:
							# All jobs in this group are valid (they share drop address but have different pick addresses)
							valid_jobs.extend(jobs_in_group)
						# If all jobs have the same pick address(es), exclude the entire group
				
				# Remove duplicates (a job might be added multiple times if it has multiple drop addresses)
				# consolidation_type is already set dynamically above
				seen_job_names = set()
				consolidatable_jobs = []
				for job in valid_jobs:
					if job["name"] not in seen_job_names:
						seen_job_names.add(job["name"])
						# Ensure consolidation_type is set to "Drop" for filtered results
						job["consolidation_type"] = "Drop"
						consolidatable_jobs.append(job)
						
			elif consolidation_type == "Both":
				# Both: List jobs with identical Pick/Drop Address
				# Exclude jobs with multiple legs (Route jobs)
				# Exclude jobs that don't have identical Pick/Drop address
				
				# First, exclude jobs with multiple legs (Route jobs)
				# Then filter for jobs that can participate in Both consolidation
				consolidatable_jobs = [
					j for j in consolidatable_jobs 
					if j.get("legs_count", 0) <= 1
					and j.get("consolidation_type") == "Both"
				]
				# Ensure consolidation_type is set to "Both" for filtered results
				for job in consolidatable_jobs:
					job["consolidation_type"] = "Both"
				
			elif consolidation_type == "Route":
				# Route: Show all consolidatable jobs (same as blank filter)
				# Set consolidation_type to "Route" for all jobs for display purposes
				for job in consolidatable_jobs:
					job["consolidation_type"] = "Route"
				# No filtering - show all consolidatable jobs (same behavior as blank)
			else:
				# Fallback to exact match for any other consolidation type
				consolidatable_jobs = [
					j for j in consolidatable_jobs 
					if j.get("consolidation_type") == consolidation_type
				]
		else:
			# No type filter applied - set consolidation_type to blank/empty for all jobs
			for job in consolidatable_jobs:
				job["consolidation_type"] = ""
		
		# Always generate debug information for diagnostics
		debug_info = {}
		# Try to diagnose why no jobs were found (or provide statistics even if jobs were found)
		jobs_without_legs = sum(1 for job in all_jobs if not legs_by_job.get(job["name"], []))
		jobs_without_load_type = sum(1 for job in all_jobs if not job.get("load_type"))
		jobs_with_invalid_load_type = 0
		jobs_without_consolidate_flag = 0
		jobs_without_addresses = 0
		jobs_already_consolidated = 0
		jobs_with_runsheet = 0
		
		for job in all_jobs:
			job_name = job["name"]
			legs = legs_by_job.get(job_name, [])
			if not legs:
				continue
			
			# Check if job is already in a consolidation
			if job_name in existing_consolidation_jobs:
				jobs_already_consolidated += 1
				continue
			
			# Check if all legs are already consolidated or have run_sheet
			all_legs_consolidated = True
			has_runsheet = False
			for leg in legs:
				# Check if leg has a run_sheet
				if leg.get("run_sheet"):
					has_runsheet = True
					break
				
				has_consolidation_flag = (
					leg.get("pick_consolidated") == 1 or 
					leg.get("drop_consolidated") == 1 or
					leg.get("transport_consolidation")
				)
				if not has_consolidation_flag:
					all_legs_consolidated = False
					break
			
			if has_runsheet:
				jobs_with_runsheet += 1
				continue
			
			if all_legs_consolidated:
				jobs_already_consolidated += 1
				continue
			
			# Check Load Type consolidation eligibility
			load_type = job.get("load_type")
			has_valid_load_type = False
			has_consolidate_flag = False
			
			if load_type:
				try:
					# Check can_handle_consolidation field
					can_handle_consolidation = frappe.db.get_value("Load Type", load_type, "can_handle_consolidation")
					if can_handle_consolidation == 1 or can_handle_consolidation == True:
						has_valid_load_type = True
					else:
						# Load Type doesn't have can_handle_consolidation = 1
						# Check if job has consolidate flag as fallback
						if frappe.db.has_column("Transport Job", "consolidate"):
							if job.get("consolidate") == 1:
								has_consolidate_flag = True
								has_valid_load_type = True  # Allow through consolidate flag
							else:
								jobs_with_invalid_load_type += 1
						else:
							jobs_with_invalid_load_type += 1
				except Exception:
					jobs_with_invalid_load_type += 1
			else:
				# No load_type, check consolidate flag
				if frappe.db.has_column("Transport Job", "consolidate"):
					if job.get("consolidate") == 1:
						has_consolidate_flag = True
						has_valid_load_type = True  # Allow through consolidate flag
					else:
						jobs_without_load_type += 1
				else:
					jobs_without_load_type += 1
			
			# Track jobs without consolidate flag (only if they also don't have valid load type)
			if not has_valid_load_type:
				if frappe.db.has_column("Transport Job", "consolidate"):
					if job.get("consolidate") != 1:
						jobs_without_consolidate_flag += 1
			
			# Check addresses (only from non-consolidated legs without run_sheet)
			pick_addresses = set()
			drop_addresses = set()
			for leg in legs:
				# Skip legs that have a run_sheet assigned
				if leg.get("run_sheet"):
					continue
				
				has_consolidation_flag = (
					leg.get("pick_consolidated") == 1 or 
					leg.get("drop_consolidated") == 1 or
					leg.get("transport_consolidation")
				)
				if not has_consolidation_flag:
					if leg.get("pick_address"):
						pick_addresses.add(leg["pick_address"])
					if leg.get("drop_address"):
						drop_addresses.add(leg["drop_address"])
			
			if len(pick_addresses) == 0 or len(drop_addresses) == 0:
				jobs_without_addresses += 1
		
		# Count excluded jobs by reason
		excluded_by_reason = {}
		for reason in excluded_jobs_reasons.values():
			excluded_by_reason[reason] = excluded_by_reason.get(reason, 0) + 1
		
		# Build detailed exclusion info for sample jobs (first 20)
		excluded_jobs_detailed = {}
		sample_excluded = list(excluded_jobs_reasons.items())[:20]
		for job_name, reason in sample_excluded:
			job_info = {
				"reason": reason,
				"details": {}
			}
			
			# Get job details
			job_doc = None
			try:
				job_doc = frappe.get_doc("Transport Job", job_name)
				job_info["details"]["docstatus"] = job_doc.docstatus
				job_info["details"]["company"] = job_doc.company
				job_info["details"]["load_type"] = job_doc.load_type
				if frappe.db.has_column("Transport Job", "consolidate"):
					job_info["details"]["consolidate_flag"] = job_doc.consolidate
			except Exception:
				pass
			
			# Get leg details
			legs = legs_by_job.get(job_name, [])
			job_info["details"]["legs_count"] = len(legs)
			
			if legs:
				legs_with_runsheet = [leg for leg in legs if leg.get("run_sheet")]
				legs_consolidated = []
				legs_consolidation_links = []
				
				for leg in legs:
					leg_consolidation = leg.get("transport_consolidation")
					has_flag = (
						leg.get("pick_consolidated") == 1 or 
						leg.get("drop_consolidated") == 1 or
						leg_consolidation
					)
					if has_flag:
						legs_consolidated.append(leg.get("name"))
						if leg_consolidation:
							legs_consolidation_links.append({
								"leg": leg.get("name"),
								"consolidation": leg_consolidation,
								"pick_consolidated": leg.get("pick_consolidated"),
								"drop_consolidated": leg.get("drop_consolidated")
							})
				
				job_info["details"]["legs_with_runsheet"] = len(legs_with_runsheet)
				job_info["details"]["legs_with_runsheet_names"] = [leg.get("run_sheet") for leg in legs_with_runsheet if leg.get("run_sheet")]
				job_info["details"]["legs_consolidated_count"] = len(legs_consolidated)
				job_info["details"]["legs_consolidation_links"] = legs_consolidation_links
			
			# Check if in consolidation table
			if frappe.db.has_table("Transport Consolidation Job"):
				in_consolidations = frappe.get_all(
					"Transport Consolidation Job",
					filters={"transport_job": job_name},
					fields=["parent"]
				)
				job_info["details"]["in_consolidations"] = [row["parent"] for row in in_consolidations]
			
			excluded_jobs_detailed[job_name] = job_info
		
		debug_info = {
			"total_jobs_found": len(all_jobs),
			"jobs_without_legs": jobs_without_legs,
			"jobs_without_load_type": jobs_without_load_type,
			"jobs_with_invalid_load_type": jobs_with_invalid_load_type,
			"jobs_without_consolidate_flag": jobs_without_consolidate_flag,
			"jobs_without_addresses": jobs_without_addresses,
			"jobs_already_consolidated": jobs_already_consolidated,
			"jobs_with_runsheet": jobs_with_runsheet,
			"consolidatable_jobs_found": len(consolidatable_jobs),
			"consolidation_groups_found": len(consolidation_groups),
			"company_filter": company,
			"consolidation_type_filter": consolidation_type,
			"current_consolidation": current_consolidation,
			"excluded_jobs_count": len(excluded_jobs_reasons),
			"excluded_by_reason": excluded_by_reason,
			"excluded_jobs_sample": dict(list(excluded_jobs_reasons.items())[:10]),  # First 10 for debugging
			"excluded_jobs_detailed": excluded_jobs_detailed  # Detailed info for first 20
		}
		
		return {
			"status": "success",
			"jobs": consolidatable_jobs,
			"consolidation_groups": consolidation_groups,
			"debug": debug_info
		}
		
	except Exception as e:
		frappe.log_error(f"Error fetching consolidatable jobs: {str(e)}")
		return {
			"status": "error",
			"message": str(e),
			"jobs": [],
			"consolidation_groups": []
		}


def _apply_consolidation_automation(consolidation_name: str, consolidation_type: str, job_names: list):
	"""
	Apply automation logic to set consolidation checkboxes based on consolidation type.
	
	Consolidation Type = Pick:
	- Check if all selected Transport Job legs have the same Pick Address
	- If true, automatically check pick_consolidated checkbox
	- One pick address, multiple drop addresses
	
	Consolidation Type = Drop:
	- Check if all selected Transport Job legs have the same Drop Address
	- If true, automatically check drop_consolidated checkbox
	- Multiple pick addresses, one drop address
	
	Consolidation Type = Both:
	- Check if all selected Transport Job legs have the same Pick AND Drop Address
	- If true, automatically check both pick_consolidated and drop_consolidated checkboxes
	- Same pick and drop for all jobs
	
	Consolidation Type = Route:
	- Multiple picks and drops (milk run)
	- No automatic checkbox setting
	"""
	try:
		if not consolidation_type or not job_names:
			return
		
		# Get all legs from all selected jobs
		all_legs = frappe.get_all(
			"Transport Leg",
			filters={"transport_job": ["in", job_names]},
			fields=["name", "pick_address", "drop_address", "pick_consolidated", "drop_consolidated", "transport_consolidation", "run_sheet"]
		)
		
		if not all_legs:
			return
		
		# Filter out legs that are already assigned to a run sheet or another consolidation
		available_legs = []
		for leg in all_legs:
			# Skip if leg has a run_sheet assigned
			if leg.get("run_sheet"):
				continue
			# Skip if leg is already in another consolidation
			if leg.get("transport_consolidation") and leg.get("transport_consolidation") != consolidation_name:
				continue
			available_legs.append(leg)
		
		if not available_legs:
			return
		
		# Collect unique pick and drop addresses from available legs (selected jobs only)
		pick_addresses = set()
		drop_addresses = set()
		
		for leg in available_legs:
			if leg.get("pick_address"):
				pick_addresses.add(leg["pick_address"])
			if leg.get("drop_address"):
				drop_addresses.add(leg["drop_address"])
		
		# Apply automation based on consolidation_type
		# Check if the selected jobs' legs match the consolidation_type pattern
		if consolidation_type == "Pick":
			# Pick Consolidation: Check if all selected jobs' legs have the same pick address
			# One pick address, multiple drop addresses
			if len(pick_addresses) == 1:
				# All selected legs have the same pick address - auto-check pick_consolidated
				for leg in available_legs:
					leg_doc = frappe.get_doc("Transport Leg", leg["name"])
					leg_doc.pick_consolidated = 1
					leg_doc.drop_consolidated = 0  # Clear drop_consolidated
					leg_doc.transport_consolidation = consolidation_name
					leg_doc.save(ignore_permissions=True)
		
		elif consolidation_type == "Drop":
			# Drop Consolidation: Check if all selected jobs' legs have the same drop address
			# Multiple pick addresses, one drop address
			if len(drop_addresses) == 1:
				# All selected legs have the same drop address - auto-check drop_consolidated
				for leg in available_legs:
					leg_doc = frappe.get_doc("Transport Leg", leg["name"])
					leg_doc.drop_consolidated = 1
					leg_doc.pick_consolidated = 0  # Clear pick_consolidated
					leg_doc.transport_consolidation = consolidation_name
					leg_doc.save(ignore_permissions=True)
		
		elif consolidation_type == "Both":
			# Both Consolidation: Check if all selected jobs' legs have the same pick AND drop address
			# Same pick and drop for all selected jobs
			if len(pick_addresses) == 1 and len(drop_addresses) == 1:
				# All selected legs have the same pick and drop address - auto-check both
				for leg in available_legs:
					leg_doc = frappe.get_doc("Transport Leg", leg["name"])
					leg_doc.pick_consolidated = 1
					leg_doc.drop_consolidated = 1
					leg_doc.transport_consolidation = consolidation_name
					leg_doc.save(ignore_permissions=True)
		
		# Route consolidation: Multiple picks and drops (milk run)
		# No automatic checkbox setting, but still set transport_consolidation link
		elif consolidation_type == "Route":
			for leg in available_legs:
				leg_doc = frappe.get_doc("Transport Leg", leg["name"])
				leg_doc.transport_consolidation = consolidation_name
				leg_doc.save(ignore_permissions=True)
		
		frappe.db.commit()
		
	except Exception as e:
		frappe.log_error(f"Error applying consolidation automation: {str(e)}", "Consolidation Automation Error")
		# Don't throw - allow the job addition to succeed even if automation fails


@frappe.whitelist()
def add_jobs_to_consolidation(consolidation_name: str, job_names):
	"""
	Add selected Transport Jobs to a Transport Consolidation.
	"""
	try:
		# Handle case where job_names is received as a JSON string instead of a list
		# This can happen when data is passed through form data
		if isinstance(job_names, str):
			job_names = frappe.parse_json(job_names)
		
		# Ensure job_names is a list
		if not isinstance(job_names, list):
			job_names = [job_names] if job_names else []
		
		# Check if consolidation_name is a temporary name (unsaved document)
		if consolidation_name and (consolidation_name.startswith("new-") or not frappe.db.exists("Transport Consolidation", consolidation_name)):
			return {
				"status": "error",
				"message": _("Please save the Transport Consolidation first before adding jobs. The document must be saved to the database.")
			}
		
		consolidation = frappe.get_doc("Transport Consolidation", consolidation_name)
		
		if not job_names or len(job_names) == 0:
			return {
				"status": "error",
				"message": _("No jobs selected")
			}
		
		added_count = 0
		skipped_count = 0
		errors = []
		added_job_names = []  # Track successfully added jobs for consolidation logic
		
		for job_name in job_names:
			try:
				# Check if job already exists in consolidation
				existing = False
				for existing_job in consolidation.transport_jobs:
					if existing_job.transport_job == job_name:
						existing = True
						skipped_count += 1
						break
				
				if existing:
					continue
				
				# Get Transport Job
				job_doc = frappe.get_doc("Transport Job", job_name)
				
				# Validate job is submitted
				if job_doc.docstatus != 1:
					errors.append(_("Transport Job {0} is not submitted").format(job_name))
					continue
				
				# Get Transport Legs for this job
				job_legs = frappe.get_all(
					"Transport Leg",
					filters={"transport_job": job_name},
					fields=["name", "pick_address", "drop_address"],
					limit=1
				)
				
				if not job_legs:
					errors.append(_("Transport Job {0} has no Transport Legs").format(job_name))
					continue
				
				# Get first leg for address info
				first_leg = job_legs[0]
				
				# Add job to consolidation
				consolidation_job_row = consolidation.append("transport_jobs", {
					"transport_job": job_name
				})
				
				# Explicitly calculate weight and volume from transport job packages
				# This ensures weight and volume are computed when job is added from dialog
				if consolidation_job_row:
					# Set parent reference for the child document (needed for company lookup)
					consolidation_job_row.parent = consolidation_name
					# Calculate weight and volume from packages
					consolidation_job_row.calculate_weight_and_volume()
				
				added_job_names.append(job_name)
				added_count += 1
				
			except Exception as e:
				errors.append(_("Error adding job {0}: {1}").format(job_name, str(e)))
				frappe.log_error(f"Error adding job {job_name} to consolidation: {str(e)}")
		
		# Save consolidation first (needed before updating legs)
		if added_count > 0:
			consolidation.save(ignore_permissions=True)
			frappe.db.commit()
			
			# Reload consolidation to get updated consolidation_type (determined by validate())
			consolidation.reload()
			
			# Apply automation logic: Auto-check consolidation checkboxes based on consolidation_type
			# This happens after jobs are added to the consolidation
			if consolidation.consolidation_type and added_job_names:
				_apply_consolidation_automation(consolidation_name, consolidation.consolidation_type, added_job_names)
		
		message = _("Added {0} job(s)").format(added_count)
		if skipped_count > 0:
			message += _(", {0} already existed").format(skipped_count)
		if errors:
			message += _(", {0} had errors").format(len(errors))
		
		return {
			"status": "success",
			"added_count": added_count,
			"skipped_count": skipped_count,
			"errors": errors,
			"message": message
		}
		
	except Exception as e:
		frappe.log_error(f"Error adding jobs to consolidation: {str(e)}")
		frappe.db.rollback()
		return {
			"status": "error",
			"message": str(e)
		}
