# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from typing import List, Dict, Any, Optional


@frappe.whitelist()
def get_consolidatable_jobs(load_type: str, date: str = None) -> Dict[str, Any]:
	"""
	Get transport jobs that can be consolidated based on load type and date.
	
	Args:
		load_type: Load Type to filter by
		date: Optional date filter (defaults to today)
	
	Returns:
		Dict containing list of consolidatable jobs
	"""
	if not date:
		date = frappe.utils.today()
	
	# Get load type details
	load_type_doc = frappe.get_doc("Load Type", load_type)
	
	if not load_type_doc.can_consolidate:
		return {"jobs": [], "message": "Load Type does not allow consolidation"}
	
	# Get transport jobs with same load type and date
	jobs = frappe.get_all(
		"Transport Job",
		filters={
			"load_type": load_type,
			"booking_date": date,
			"docstatus": 1  # Only submitted jobs
		},
		fields=["name", "customer", "vehicle_type", "booking_date", "load_type"],
		order_by="creation asc"
	)
	
	return {"jobs": jobs, "load_type": load_type, "date": date}


@frappe.whitelist()
def create_consolidation_from_jobs(job_names: List[str], consolidation_date: str = None) -> Dict[str, Any]:
	"""
	Create a Transport Consolidation from a list of Transport Jobs.
	
	Args:
		job_names: List of Transport Job names to consolidate
		consolidation_date: Date for consolidation (defaults to today)
	
	Returns:
		Dict containing consolidation details
	"""
	if not consolidation_date:
		consolidation_date = frappe.utils.today()
	
	if not job_names:
		frappe.throw(_("Please select at least one Transport Job to consolidate"))
	
	# Validate all jobs have the same load type
	load_types = set()
	for job_name in job_names:
		job = frappe.get_doc("Transport Job", job_name)
		if job.load_type:
			load_types.add(job.load_type)
	
	if len(load_types) > 1:
		frappe.throw(_("All transport jobs must have the same Load Type"))
	
	if not load_types:
		frappe.throw(_("Transport Jobs must have a Load Type to be consolidated"))
	
	# Create consolidation
	consolidation = frappe.new_doc("Transport Consolidation")
	consolidation.consolidation_date = consolidation_date
	consolidation.status = "Draft"
	# consolidation_type will be auto-determined in validate() based on addresses
	
	# Add transport jobs
	for job_name in job_names:
		job = frappe.get_doc("Transport Job", job_name)
		
		# Validate load type matches
		if job.load_type != load_type:
			frappe.throw(_("All jobs must have the same Load Type. Job {0} has Load Type {1}, expected {2}").format(
				job.name, job.load_type, load_type))
		
		consolidation.append("transport_jobs", {
			"transport_job": job.name,
			"weight": 0,  # Will be calculated from packages
			"volume": 0    # Will be calculated from packages
		})
	
	consolidation.save()
	
	return {
		"name": consolidation.name,
		"load_type": list(load_types)[0] if load_types else None,
		"jobs_count": len(job_names),
		"status": "Draft"
	}


@frappe.whitelist()
def assign_consolidation_to_run_sheet(consolidation_name: str, run_sheet_name: str) -> Dict[str, Any]:
	"""
	Assign a Transport Consolidation to a Run Sheet.
	
	Args:
		consolidation_name: Name of Transport Consolidation
		run_sheet_name: Name of Run Sheet
	
	Returns:
		Dict containing assignment details
	"""
	# Update consolidation
	consolidation = frappe.get_doc("Transport Consolidation", consolidation_name)
	consolidation.run_sheet = run_sheet_name
	consolidation.status = "Planned"
	consolidation.save()
	
	# Update run sheet
	run_sheet = frappe.get_doc("Run Sheet", run_sheet_name)
	run_sheet.transport_consolidation = consolidation_name
	run_sheet.save()
	
	return {
		"consolidation": consolidation_name,
		"run_sheet": run_sheet_name,
		"status": "Assigned"
	}
