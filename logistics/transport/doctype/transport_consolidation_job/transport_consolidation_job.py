# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt


class TransportConsolidationJob(Document):
	def validate(self):
		"""Calculate weight and volume from transport job packages"""
		if self.transport_job:
			# Check if transport job has any legs with run_sheet assigned
			self.check_run_sheet_assignment()
			self.calculate_weight_and_volume()
	
	def check_run_sheet_assignment(self):
		"""
		Check if the transport job has any legs with a run_sheet assigned.
		If so, prevent adding it to consolidation.
		"""
		if not self.transport_job:
			return
		
		# Check if Transport Leg table has run_sheet field
		if not frappe.db.has_column("Transport Leg", "run_sheet"):
			return
		
		# Get all legs for this transport job
		legs = frappe.get_all(
			"Transport Leg",
			filters={"transport_job": self.transport_job},
			fields=["name", "run_sheet"]
		)
		
		# Check if any leg has a run_sheet assigned
		legs_with_runsheet = [leg for leg in legs if leg.get("run_sheet")]
		
		if legs_with_runsheet:
			leg_names = [leg["name"] for leg in legs_with_runsheet]
			leg_list = ", ".join(leg_names[:5])
			if len(leg_names) > 5:
				leg_list += f" and {len(leg_names) - 5} more"
			
			frappe.throw(
				frappe._("Cannot add Transport Job {0} to consolidation. "
					"The following Transport Leg(s) already have a Run Sheet assigned: {1}").format(
					self.transport_job, leg_list
				)
			)
	
	def calculate_weight_and_volume(self):
		"""
		Calculate total weight and volume from all packages in the transport job.
		If transport job has multiple packages, it sums all volumes and weights from all packages.
		Example: package 1(volume=1) + package 2(volume=1) = transport_consolidation_job volume=2
		Uses UOM conversion to ensure consistent units (KG for weight, CBM for volume).
		"""
		if not self.transport_job:
			self.weight = 0
			self.volume = 0
			return
		
		try:
			# Get the transport job document
			job_doc = frappe.get_doc("Transport Job", self.transport_job)
			
			# Get company from parent consolidation or from transport job
			company = None
			# Try to get company from parent consolidation
			# self.parent contains the parent document name
			if hasattr(self, 'parent') and self.parent:
				try:
					# Check if parent document exists (might not be saved yet)
					if frappe.db.exists("Transport Consolidation", self.parent):
						parent_doc = frappe.get_doc("Transport Consolidation", self.parent)
						company = parent_doc.company
				except Exception:
					pass
			
			# Fallback to transport job's company
			if not company and hasattr(job_doc, 'company') and job_doc.company:
				company = job_doc.company
			
			# Import UOM conversion utilities
			from logistics.transport.capacity.uom_conversion import (
				convert_weight, convert_volume, calculate_volume_from_dimensions,
				get_default_uoms
			)
			
			# Get default UOMs
			default_uoms = get_default_uoms(company)
			weight_uom = default_uoms['weight']  # Typically 'KG'
			volume_uom = default_uoms['volume']   # Typically 'CBM'
			
			total_weight = 0
			total_volume = 0
			
			# Get all packages from transport job
			# If transport job has multiple packages, sum all volumes and weights
			packages = getattr(job_doc, 'packages', []) or []
			
			# Loop through all packages and sum their weight and volume
			for pkg in packages:
				# Sum weight from each package
				pkg_weight = flt(getattr(pkg, 'weight', 0))
				if pkg_weight > 0:
					pkg_weight_uom = getattr(pkg, 'weight_uom', None) or weight_uom
					total_weight += convert_weight(pkg_weight, pkg_weight_uom, weight_uom, company)
				
				# Sum volume from each package - prefer direct volume, calculate from dimensions if not available
				pkg_volume = flt(getattr(pkg, 'volume', 0))
				if pkg_volume > 0:
					pkg_volume_uom = getattr(pkg, 'volume_uom', None) or volume_uom
					total_volume += convert_volume(pkg_volume, pkg_volume_uom, volume_uom, company)
				elif hasattr(pkg, 'length') and hasattr(pkg, 'width') and hasattr(pkg, 'height'):
					# Calculate from dimensions if volume is not directly set
					length = flt(getattr(pkg, 'length', 0))
					width = flt(getattr(pkg, 'width', 0))
					height = flt(getattr(pkg, 'height', 0))
					if length > 0 and width > 0 and height > 0:
						dim_uom = getattr(pkg, 'dimension_uom', None) or default_uoms['dimension']
						pkg_volume = calculate_volume_from_dimensions(
							length, width, height,
							dimension_uom=dim_uom,
							volume_uom=volume_uom,
							company=company
						)
						total_volume += pkg_volume
			
			# Set calculated values (sum of all packages)
			self.weight = total_weight
			self.volume = total_volume
			
		except frappe.DoesNotExistError:
			# Transport job doesn't exist
			self.weight = 0
			self.volume = 0
		except Exception as e:
			# Log error but don't fail validation
			frappe.log_error(
				f"Error calculating weight and volume for transport job {self.transport_job}: {str(e)}",
				"Transport Consolidation Job Calculation Error"
			)
			# Set to 0 on error to avoid breaking the form
			self.weight = 0
			self.volume = 0


@frappe.whitelist()
def get_transport_job_filter():
	"""
	Get filter query for transport_job field to exclude jobs with run_sheets.
	This is used in frm.set_query to filter the transport_job dropdown.
	
	Returns:
		Dictionary with filters to exclude jobs that have any leg with run_sheet assigned
	"""
	filters = {
		"docstatus": 1  # Only submitted jobs
	}
	
	# Check if Transport Leg table has run_sheet field
	if frappe.db.has_column("Transport Leg", "run_sheet"):
		# Get all transport jobs that have legs with run_sheet assigned
		# Use a query to find jobs where any leg has a run_sheet
		legs_with_runsheet = frappe.db.sql("""
			SELECT DISTINCT transport_job
			FROM `tabTransport Leg`
			WHERE run_sheet IS NOT NULL
			AND run_sheet != ''
			AND transport_job IS NOT NULL
		""", as_dict=True)
		
		# Extract unique transport job names
		job_names_with_runsheet = [leg["transport_job"] for leg in legs_with_runsheet if leg.get("transport_job")]
		
		# Exclude jobs that have any leg with run_sheet
		if job_names_with_runsheet:
			filters["name"] = ["not in", job_names_with_runsheet]
	
	return filters


@frappe.whitelist()
def calculate_weight_volume_from_job(transport_job: str, company: str = None) -> dict:
	"""
	Calculate weight and volume from transport job packages.
	If transport job has multiple packages, it sums all volumes and weights from all packages.
	This is called from client-side when transport_job is selected.
	
	Args:
		transport_job: Name of the Transport Job
		company: Optional company for UOM conversion settings
		
	Returns:
		Dictionary with 'weight' and 'volume' keys (sum of all packages)
	"""
	if not transport_job:
		return {'weight': 0, 'volume': 0}
	
	try:
		# Get the transport job document
		job_doc = frappe.get_doc("Transport Job", transport_job)
		
		# Get company from parameter or from transport job
		if not company and hasattr(job_doc, 'company') and job_doc.company:
			company = job_doc.company
		
		# Import UOM conversion utilities
		from logistics.transport.capacity.uom_conversion import (
			convert_weight, convert_volume, calculate_volume_from_dimensions,
			get_default_uoms
		)
		
		# Get default UOMs
		default_uoms = get_default_uoms(company)
		weight_uom = default_uoms['weight']  # Typically 'KG'
		volume_uom = default_uoms['volume']   # Typically 'CBM'
		
		total_weight = 0
		total_volume = 0
		
		# Get all packages from transport job
		# If transport job has multiple packages, sum all volumes and weights
		packages = getattr(job_doc, 'packages', []) or []
		
		# Loop through all packages and sum their weight and volume
		for pkg in packages:
			# Sum weight from each package
			pkg_weight = flt(getattr(pkg, 'weight', 0))
			if pkg_weight > 0:
				pkg_weight_uom = getattr(pkg, 'weight_uom', None) or weight_uom
				total_weight += convert_weight(pkg_weight, pkg_weight_uom, weight_uom, company)
			
			# Sum volume from each package - prefer direct volume, calculate from dimensions if not available
			pkg_volume = flt(getattr(pkg, 'volume', 0))
			if pkg_volume > 0:
				pkg_volume_uom = getattr(pkg, 'volume_uom', None) or volume_uom
				total_volume += convert_volume(pkg_volume, pkg_volume_uom, volume_uom, company)
			elif hasattr(pkg, 'length') and hasattr(pkg, 'width') and hasattr(pkg, 'height'):
				# Calculate from dimensions if volume is not directly set
				length = flt(getattr(pkg, 'length', 0))
				width = flt(getattr(pkg, 'width', 0))
				height = flt(getattr(pkg, 'height', 0))
				if length > 0 and width > 0 and height > 0:
					dim_uom = getattr(pkg, 'dimension_uom', None) or default_uoms['dimension']
					pkg_volume = calculate_volume_from_dimensions(
						length, width, height,
						dimension_uom=dim_uom,
						volume_uom=volume_uom,
						company=company
					)
					total_volume += pkg_volume
		
		return {
			'weight': total_weight,
			'volume': total_volume
		}
		
	except frappe.DoesNotExistError:
		# Transport job doesn't exist
		return {'weight': 0, 'volume': 0}
	except Exception as e:
		# Log error and return 0
		frappe.log_error(
			f"Error calculating weight and volume for transport job {transport_job}: {str(e)}",
			"Transport Consolidation Job Calculation Error"
		)
		return {'weight': 0, 'volume': 0}
