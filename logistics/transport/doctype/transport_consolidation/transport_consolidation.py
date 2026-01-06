# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt


class TransportConsolidation(Document):
	def validate(self):
		"""Validate consolidation rules and calculate totals"""
		self.validate_consolidation_rules()
		self.determine_consolidation_type()
		self.calculate_totals()
		self.validate_capacity_limits()
		self.validate_accounts()
	
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
	
	def validate_consolidation_rules(self):
		"""Validate that jobs can be consolidated based on load type rules"""
		# Require at least one Transport Job
		if not self.transport_jobs:
			frappe.throw(_("At least one Transport Job is required"))
		
		# Get load type and company from transport jobs
		load_types = set()
		companies = set()
		vehicle_types = set()
		
		for job in self.transport_jobs:
			if not job.transport_job:
				continue
			
			job_doc = frappe.get_doc("Transport Job", job.transport_job)
			
			# Ensure all linked Transport Jobs are submitted
			if job_doc.docstatus != 1:
				frappe.throw(_("Transport Job {0} must be submitted to be included in consolidation").format(
					job_doc.name
				))
			
			# Collect load types, companies, and vehicle types
			if job_doc.load_type:
				load_types.add(job_doc.load_type)
			if job_doc.company:
				companies.add(job_doc.company)
			if job_doc.vehicle_type:
				vehicle_types.add(job_doc.vehicle_type)
		
		# All jobs must have the same load type
		if len(load_types) > 1:
			frappe.throw(_("All transport jobs must have the same Load Type"))
		
		# All jobs must have the same company
		if len(companies) > 1:
			frappe.throw(_("All transport jobs must belong to the same Company"))
		
		# Warn if jobs have different vehicle types
		if len(vehicle_types) > 1:
			frappe.msgprint(_("Warning: Transport Jobs have different vehicle types ({0}). This may cause issues.").format(
				", ".join(vehicle_types)
			), indicator="orange")
		
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
	
	def validate_capacity_limits(self):
		"""Validate total weight and volume against Load Type limits"""
		if not self.transport_jobs:
			return
		
		# Get load type from first job
		load_type = None
		for job in self.transport_jobs:
			if job.transport_job:
				job_doc = frappe.get_doc("Transport Job", job.transport_job)
				if job_doc.load_type:
					load_type = job_doc.load_type
					break
		
		if not load_type:
			return
		
		load_type_doc = frappe.get_doc("Load Type", load_type)
		
		# Check weight and volume limits after totals are calculated
		if load_type_doc.max_weight and flt(self.total_weight) > flt(load_type_doc.max_weight):
			frappe.throw(_("Total weight {0} kg exceeds maximum allowed weight {1} kg for Load Type {2}").format(
				flt(self.total_weight), flt(load_type_doc.max_weight), load_type))
		
		if load_type_doc.max_volume and flt(self.total_volume) > flt(load_type_doc.max_volume):
			frappe.throw(_("Total volume {0} m³ exceeds maximum allowed volume {1} m³ for Load Type {2}").format(
				flt(self.total_volume), flt(load_type_doc.max_volume), load_type))
	
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


@frappe.whitelist()
def create_run_sheet_from_consolidation(consolidation_name: str):
	"""
	Create a Run Sheet from a Transport Consolidation.
	Determines if it's Pick Consolidated or Drop Consolidated and sets appropriate checkboxes.
	Populates routing correctly based on consolidation type.
	"""
	try:
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
def get_consolidatable_jobs(consolidation_type: str = None, company: str = None, date: str = None):
	"""
	Get all Transport Jobs with legs that can be consolidated (same pick or same drop).
	Returns jobs grouped by consolidation type.
	"""
	try:
		# Build filters for Transport Jobs
		filters = {"docstatus": 1}  # Only submitted jobs
		
		if company:
			filters["company"] = company
		
		# Get all submitted Transport Jobs
		all_jobs = frappe.get_all(
			"Transport Job",
			filters=filters,
			fields=["name", "customer", "company", "status", "load_type", "vehicle_type"],
			order_by="creation desc"
		)
		
		if not all_jobs:
			return {
				"status": "success",
				"jobs": [],
				"consolidation_groups": []
			}
		
		# Get Transport Legs for all jobs
		job_names = [job["name"] for job in all_jobs]
		all_legs = frappe.get_all(
			"Transport Leg",
			filters={"transport_job": ["in", job_names]},
			fields=["name", "transport_job", "pick_address", "drop_address", "status"],
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
		
		for job in all_jobs:
			job_name = job["name"]
			legs = legs_by_job.get(job_name, [])
			
			if not legs:
				continue
			
			# Get unique pick and drop addresses
			pick_addresses = set()
			drop_addresses = set()
			
			for leg in legs:
				if leg["pick_address"]:
					pick_addresses.add(leg["pick_address"])
				if leg["drop_address"]:
					drop_addresses.add(leg["drop_address"])
			
			# Determine consolidation type based on address patterns
			num_pick = len(pick_addresses)
			num_drop = len(drop_addresses)
			
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
			
			# Only include jobs that can be consolidated (have clear pattern)
			if num_pick > 0 and num_drop > 0:
				# Get address names for display
				pick_address_name = None
				drop_address_name = None
				
				if pick_addresses:
					pick_address_name = frappe.db.get_value("Address", list(pick_addresses)[0], "address_title") or list(pick_addresses)[0]
				if drop_addresses:
					drop_address_name = frappe.db.get_value("Address", list(drop_addresses)[0], "address_title") or list(drop_addresses)[0]
				
				job_info = {
					"name": job_name,
					"customer": job.get("customer"),
					"company": job.get("company"),
					"status": job.get("status"),
					"pick_address": pick_address_name if is_pick_consolidated else f"{len(pick_addresses)} different",
					"drop_address": drop_address_name if is_drop_consolidated else f"{len(drop_addresses)} different",
					"consolidation_type": consolidation_type_str,
					"legs_count": len(legs)
				}
				
				consolidatable_jobs.append(job_info)
				
				# Group for consolidation suggestions
				if consolidation_type_str == "Pick" or consolidation_type_str == "Both":
					pick_addr = list(pick_addresses)[0]
					if pick_addr not in pick_groups:
						pick_groups[pick_addr] = []
					pick_groups[pick_addr].append(job_info)
				
				if consolidation_type_str == "Drop" or consolidation_type_str == "Both":
					drop_addr = list(drop_addresses)[0]
					if drop_addr not in drop_groups:
						drop_groups[drop_addr] = []
					drop_groups[drop_addr].append(job_info)
		
		# Build consolidation groups
		consolidation_groups = []
		for pick_addr, jobs in pick_groups.items():
			if len(jobs) > 1:  # Only groups with multiple jobs
				consolidation_groups.append({
					"type": "Pick",
					"address": frappe.db.get_value("Address", pick_addr, "address_title") or pick_addr,
					"jobs": [j["name"] for j in jobs],
					"count": len(jobs)
				})
		
		for drop_addr, jobs in drop_groups.items():
			if len(jobs) > 1:  # Only groups with multiple jobs
				consolidation_groups.append({
					"type": "Drop",
					"address": frappe.db.get_value("Address", drop_addr, "address_title") or drop_addr,
					"jobs": [j["name"] for j in jobs],
					"count": len(jobs)
				})
		
		# Filter by date if provided
		if date:
			# This would require checking job dates, which may not be available in Transport Job
			# For now, we'll skip date filtering or implement it based on available date fields
			pass
		
		# Filter by consolidation_type if provided
		if consolidation_type:
			consolidatable_jobs = [
				j for j in consolidatable_jobs 
				if j["consolidation_type"] == consolidation_type
			]
		
		return {
			"status": "success",
			"jobs": consolidatable_jobs,
			"consolidation_groups": consolidation_groups
		}
		
	except Exception as e:
		frappe.log_error(f"Error fetching consolidatable jobs: {str(e)}")
		return {
			"status": "error",
			"message": str(e),
			"jobs": [],
			"consolidation_groups": []
		}


@frappe.whitelist()
def add_jobs_to_consolidation(consolidation_name: str, job_names: list):
	"""
	Add selected Transport Jobs to a Transport Consolidation.
	"""
	try:
		consolidation = frappe.get_doc("Transport Consolidation", consolidation_name)
		
		if not job_names or len(job_names) == 0:
			return {
				"status": "error",
				"message": _("No jobs selected")
			}
		
		added_count = 0
		skipped_count = 0
		errors = []
		
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
				consolidation.append("transport_jobs", {
					"transport_job": job_name
				})
				
				added_count += 1
				
			except Exception as e:
				errors.append(_("Error adding job {0}: {1}").format(job_name, str(e)))
				frappe.log_error(f"Error adding job {job_name} to consolidation: {str(e)}")
		
		# Save consolidation
		if added_count > 0:
			consolidation.save(ignore_permissions=True)
			frappe.db.commit()
		
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
