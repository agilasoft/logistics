# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Capacity Reserver

Handles capacity reservation and release for transport jobs and legs.
"""

import frappe
from frappe import _
from frappe.utils import getdate, now
from typing import Optional, Dict, Any
from frappe.model.document import Document

from .capacity_manager import CapacityManager
from .uom_conversion import get_default_uoms


def reserve_job_capacity(job_doc: Document):
	"""
	Reserve capacity for a transport job.
	
	Args:
		job_doc: Transport Job document
	"""
	if not job_doc.vehicle:
		return
	
	try:
		manager = CapacityManager(job_doc.company)
		
		if not manager.is_enabled() or not manager.settings.get('reservation_enabled'):
			return
		
		# Calculate requirements
		requirements = job_doc.calculate_capacity_requirements()
		
		if requirements['weight'] == 0 and requirements['volume'] == 0 and requirements['pallets'] == 0:
			return  # No capacity to reserve
		
		# Check if reservation already exists
		existing = frappe.db.exists(
			"Capacity Reservation",
			{
				'transport_job': job_doc.name,
				'status': ['in', ['Reserved', 'Active']]
			}
		)
		
		if existing:
			return  # Already reserved
		
		# Get scheduled date from job
		reservation_date = getattr(job_doc, 'scheduled_date', None) or getdate()
		
		# Create reservation
		reservation = frappe.new_doc("Capacity Reservation")
		reservation.vehicle = job_doc.vehicle
		reservation.reservation_date = reservation_date
		reservation.reserved_weight = requirements['weight']
		reservation.reserved_weight_uom = requirements['weight_uom']
		reservation.reserved_volume = requirements['volume']
		reservation.reserved_volume_uom = requirements['volume_uom']
		reservation.reserved_pallets = requirements['pallets']
		reservation.transport_job = job_doc.name
		reservation.status = "Reserved"
		reservation.reserved_by = frappe.session.user
		reservation.insert(ignore_permissions=True)
		
	except Exception as e:
		frappe.log_error(f"Error reserving capacity for job {job_doc.name}: {str(e)}", "Capacity Reservation Error")


def release_job_capacity(job_doc: Document):
	"""
	Release capacity for a transport job.
	
	Args:
		job_doc: Transport Job document
	"""
	if not job_doc.vehicle:
		return
	
	try:
		# Find and release reservations
		reservations = frappe.get_all(
			"Capacity Reservation",
			filters={
				'transport_job': job_doc.name,
				'status': ['in', ['Reserved', 'Active']]
			}
		)
		
		for res in reservations:
			res_doc = frappe.get_doc("Capacity Reservation", res.name)
			res_doc.status = "Released"
			res_doc.released_at = now()
			res_doc.save(ignore_permissions=True)
		
	except Exception as e:
		frappe.log_error(f"Error releasing capacity for job {job_doc.name}: {str(e)}", "Capacity Release Error")


def reserve_leg_capacity(leg_doc: Document, vehicle: str, requirements: Dict[str, Any]):
	"""
	Reserve capacity for a transport leg.
	
	Args:
		leg_doc: Transport Leg document
		vehicle: Vehicle name
		requirements: Dict with capacity requirements
	"""
	if not vehicle:
		return
	
	try:
		manager = CapacityManager()
		
		if not manager.is_enabled() or not manager.settings.get('reservation_enabled'):
			return
		
		# Get scheduled date
		reservation_date = getattr(leg_doc, 'date', None) or getdate()
		
		# Get default UOMs from settings
		from logistics.transport.capacity.uom_conversion import get_default_uoms
		default_uoms = get_default_uoms(company=getattr(leg_doc, 'company', None))
		
		# Create reservation
		reservation = frappe.new_doc("Capacity Reservation")
		reservation.vehicle = vehicle
		reservation.reservation_date = reservation_date
		reservation.reserved_weight = flt(requirements.get('weight', 0))
		reservation.reserved_weight_uom = requirements.get('weight_uom') or default_uoms.get('weight', '')
		reservation.reserved_volume = flt(requirements.get('volume', 0))
		reservation.reserved_volume_uom = requirements.get('volume_uom') or default_uoms.get('volume', '')
		reservation.reserved_pallets = flt(requirements.get('pallets', 0))
		reservation.transport_leg = leg_doc.name
		reservation.status = "Reserved"
		reservation.reserved_by = frappe.session.user
		reservation.insert(ignore_permissions=True)
		
	except Exception as e:
		frappe.log_error(f"Error reserving capacity for leg {leg_doc.name}: {str(e)}", "Capacity Reservation Error")


def release_leg_capacity(leg_doc: Document):
	"""
	Release capacity for a transport leg.
	
	Args:
		leg_doc: Transport Leg document
	"""
	try:
		# Find and release reservations
		reservations = frappe.get_all(
			"Capacity Reservation",
			filters={
				'transport_leg': leg_doc.name,
				'status': ['in', ['Reserved', 'Active']]
			}
		)
		
		for res in reservations:
			res_doc = frappe.get_doc("Capacity Reservation", res.name)
			res_doc.status = "Released"
			res_doc.released_at = now()
			res_doc.save(ignore_permissions=True)
		
	except Exception as e:
		frappe.log_error(f"Error releasing capacity for leg {leg_doc.name}: {str(e)}", "Capacity Release Error")
