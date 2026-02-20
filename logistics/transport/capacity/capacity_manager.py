# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Capacity Manager - Core Engine for Transport Capacity Management

Provides centralized capacity management functionality including:
- Capacity tracking and calculation
- Capacity reservation and release
- Capacity validation
- Vehicle selection based on capacity
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, get_datetime
from typing import Optional, Dict, List, Any
from datetime import datetime, date, time as dt_time

from .uom_conversion import (
	convert_weight,
	convert_volume,
	standardize_capacity_value,
	get_default_uoms
)
from logistics.utils.measurements import get_aggregation_volume_uom


class CapacityManager:
	"""Core capacity management engine"""
	
	def __init__(self, company: Optional[str] = None):
		"""
		Initialize Capacity Manager.
		
		Args:
			company: Optional company for company-specific settings
		"""
		self.company = company
		self.settings = self._get_settings()
		self.default_uoms = get_default_uoms(company)
		# Use aggregation volume UOM (base or default from Logistics Settings) for capacity volume
		self.volume_uom = get_aggregation_volume_uom(company) or self.default_uoms.get('volume')
	
	def _get_settings(self) -> Dict[str, Any]:
		"""Get Transport Capacity Settings"""
		try:
			settings = frappe.get_single("Transport Capacity Settings")
			return {
				'enabled': getattr(settings, 'enable_capacity_management', True),
				'reservation_enabled': getattr(settings, 'enable_capacity_reservation', True),
				'auto_reserve': getattr(settings, 'auto_reserve_capacity', True),
				'strict_validation': getattr(settings, 'capacity_validation_strict', True),
				'default_buffer': flt(getattr(settings, 'default_capacity_buffer', 10)),
				'alert_threshold': flt(getattr(settings, 'capacity_alert_threshold', 80)),
				'uom_conversion_enabled': getattr(settings, 'enable_uom_conversion', True)
			}
		except Exception:
			# Return defaults if settings don't exist
			return {
				'enabled': True,
				'reservation_enabled': True,
				'auto_reserve': True,
				'strict_validation': True,
				'default_buffer': 10.0,
				'alert_threshold': 80.0,
				'uom_conversion_enabled': True
			}
	
	def is_enabled(self) -> bool:
		"""Check if capacity management is enabled"""
		return self.settings.get('enabled', True)
	
	def get_vehicle_capacity(self, vehicle: str) -> Dict[str, float]:
		"""
		Get vehicle capacity in standard UOMs.
		
		Args:
			vehicle: Transport Vehicle name
		
		Returns:
			Dictionary with 'weight', 'volume', 'pallets' in standard UOMs
		"""
		if not self.is_enabled():
			return {'weight': 0, 'volume': 0, 'pallets': 0}
		
		try:
			vehicle_doc = frappe.get_doc("Transport Vehicle", vehicle)
			
			# Get capacity values
			weight = flt(getattr(vehicle_doc, 'capacity_weight', 0))
			volume = flt(getattr(vehicle_doc, 'capacity_volume', 0))
			pallets = flt(getattr(vehicle_doc, 'capacity_pallets', 0))
			
			# Get UOMs
			weight_uom = getattr(vehicle_doc, 'capacity_weight_uom', None) or self.default_uoms['weight']
			volume_uom = getattr(vehicle_doc, 'capacity_volume_uom', None) or self.default_uoms['volume']
			
			# Convert to standard UOMs (Logistics Settings: weight = default, volume = aggregation)
			if self.settings.get('uom_conversion_enabled') and self.volume_uom:
				weight = convert_weight(weight, weight_uom, self.default_uoms['weight'], self.company)
				volume = convert_volume(volume, volume_uom, self.volume_uom, self.company)
			
			return {
				'weight': weight,
				'volume': volume,
				'pallets': pallets,
				'weight_uom': self.default_uoms['weight'],
				'volume_uom': self.volume_uom
			}
		except Exception as e:
			frappe.log_error(f"Error getting vehicle capacity: {str(e)}", "Capacity Manager")
			return {'weight': 0, 'volume': 0, 'pallets': 0}
	
	def get_available_capacity(
		self,
		vehicle: str,
		reservation_date: Optional[date] = None,
		time_slot: Optional[Dict[str, Any]] = None
	) -> Dict[str, float]:
		"""
		Get available capacity for a vehicle on a specific date/time.
		
		Args:
			vehicle: Transport Vehicle name
			reservation_date: Date to check (defaults to today)
			time_slot: Optional time slot dict with 'start_time' and 'end_time'
		
		Returns:
			Dictionary with available 'weight', 'volume', 'pallets'
		"""
		if not self.is_enabled():
			return {'weight': 0, 'volume': 0, 'pallets': 0}
		
		# Get total capacity
		total_capacity = self.get_vehicle_capacity(vehicle)
		
		# Get reserved capacity
		reserved = self.get_reserved_capacity(vehicle, reservation_date, time_slot)
		
		# Calculate available
		return {
			'weight': max(0, total_capacity['weight'] - reserved['weight']),
			'volume': max(0, total_capacity['volume'] - reserved['volume']),
			'pallets': max(0, total_capacity['pallets'] - reserved['pallets']),
			'weight_uom': total_capacity.get('weight_uom', self.default_uoms['weight']),
			'volume_uom': total_capacity.get('volume_uom') or self.volume_uom
		}
	
	def get_reserved_capacity(
		self,
		vehicle: str,
		reservation_date: Optional[date] = None,
		time_slot: Optional[Dict[str, Any]] = None
	) -> Dict[str, float]:
		"""
		Get reserved capacity for a vehicle.
		
		Args:
			vehicle: Transport Vehicle name
			reservation_date: Date to check (defaults to today)
			time_slot: Optional time slot dict
		
		Returns:
			Dictionary with reserved 'weight', 'volume', 'pallets'
		"""
		if not self.is_enabled() or not self.settings.get('reservation_enabled'):
			return {'weight': 0, 'volume': 0, 'pallets': 0}
		
		if not reservation_date:
			reservation_date = getdate()
		
		# Query active reservations
		filters = {
			'vehicle': vehicle,
			'reservation_date': reservation_date,
			'status': ['in', ['Reserved', 'Active']]
		}

		reservations = frappe.get_all(
			"Capacity Reservation",
			filters=filters,
			fields=[
				'reserved_weight', 'reserved_weight_uom', 'reserved_volume', 'reserved_volume_uom',
				'reserved_pallets', 'reservation_start_time', 'reservation_end_time'
			]
		)

		# Time slot overlap: when time_slot is provided, only sum reservations that overlap
		if time_slot and time_slot.get('start_time') is not None and time_slot.get('end_time') is not None:
			def _to_time(v):
				if v is None:
					return None
				if isinstance(v, dt_time):
					return v
				if isinstance(v, datetime):
					return v.time()
				if isinstance(v, str):
					try:
						return get_datetime(v).time()
					except Exception:
						return None
				return None

			slot_start = _to_time(time_slot['start_time'])
			slot_end = _to_time(time_slot['end_time'])
			if slot_start is not None and slot_end is not None:

				def _overlaps(r_start, r_end):
					if r_start is None and r_end is None:
						return True  # All-day reservation overlaps any slot
					r_s = _to_time(r_start) or dt_time(0, 0)
					r_e = _to_time(r_end) or dt_time(23, 59, 59)
					return (r_s < slot_end) and (slot_start < r_e)

				reservations = [
					r for r in reservations
					if _overlaps(r.get('reservation_start_time'), r.get('reservation_end_time'))
				]

		total_weight = 0
		total_volume = 0
		total_pallets = 0

		for res in reservations:
			# Convert to standard UOMs
			weight = flt(res.get('reserved_weight', 0))
			if weight > 0:
				weight_uom = res.get('reserved_weight_uom') or self.default_uoms['weight']
				total_weight += convert_weight(weight, weight_uom, self.default_uoms['weight'], self.company)
			
			volume = flt(res.get('reserved_volume', 0))
			if volume > 0 and self.volume_uom:
				volume_uom = res.get('reserved_volume_uom') or self.default_uoms['volume']
				total_volume += convert_volume(volume, volume_uom, self.volume_uom, self.company)
			
			total_pallets += flt(res.get('reserved_pallets', 0))
		
		return {
			'weight': total_weight,
			'volume': total_volume,
			'pallets': total_pallets
		}
	
	def check_capacity_sufficient(
		self,
		vehicle: str,
		requirements: Dict[str, float],
		consider_buffer: bool = True
	) -> Dict[str, Any]:
		"""
		Check if vehicle has sufficient capacity for requirements.
		
		Args:
			vehicle: Transport Vehicle name
			requirements: Dict with 'weight', 'volume', 'pallets' (in standard UOMs)
			consider_buffer: Whether to consider capacity buffer
		
		Returns:
			Dict with 'sufficient': bool, 'available': dict, 'required': dict, 'warnings': list
		"""
		if not self.is_enabled():
			return {
				'sufficient': True,
				'available': {'weight': 0, 'volume': 0, 'pallets': 0},
				'required': requirements,
				'warnings': []
			}
		
		# Get available capacity
		available = self.get_available_capacity(vehicle)
		
		# Apply buffer if needed
		if consider_buffer:
			buffer = self.settings.get('default_buffer', 10) / 100.0
			available['weight'] = available['weight'] * (1 - buffer)
			available['volume'] = available['volume'] * (1 - buffer)
			available['pallets'] = available['pallets'] * (1 - buffer)
		
		# Check each dimension
		sufficient = True
		warnings = []
		
		required_weight = flt(requirements.get('weight', 0))
		required_volume = flt(requirements.get('volume', 0))
		required_pallets = flt(requirements.get('pallets', 0))
		
		if required_weight > 0:
			if required_weight > available['weight']:
				sufficient = False
				weight_uom = available.get('weight_uom') or self.default_uoms.get('weight', '')
				warnings.append(_("Insufficient weight capacity: Required {0} {1}, Available {2} {1}").format(
					required_weight, weight_uom, available['weight']
				))
			elif required_weight > available['weight'] * (self.settings.get('alert_threshold', 80) / 100.0):
				warnings.append(_("Weight capacity approaching limit: {0}% utilized").format(
					(required_weight / available['weight'] * 100) if available['weight'] > 0 else 0
				))
		
		if required_volume > 0:
			if required_volume > available['volume']:
				sufficient = False
				volume_uom = available.get('volume_uom') or self.default_uoms.get('volume', '')
				warnings.append(_("Insufficient volume capacity: Required {0} {1}, Available {2} {1}").format(
					required_volume, volume_uom, available['volume']
				))
			elif required_volume > available['volume'] * (self.settings.get('alert_threshold', 80) / 100.0):
				warnings.append(_("Volume capacity approaching limit: {0}% utilized").format(
					(required_volume / available['volume'] * 100) if available['volume'] > 0 else 0
				))
		
		if required_pallets > 0:
			if required_pallets > available['pallets']:
				sufficient = False
				warnings.append(_("Insufficient pallet capacity: Required {0}, Available {1}").format(
					required_pallets, available['pallets']
				))
		
		return {
			'sufficient': sufficient,
			'available': available,
			'required': requirements,
			'warnings': warnings
		}
	
	def find_suitable_vehicles(
		self,
		requirements: Dict[str, float],
		filters: Optional[Dict[str, Any]] = None
	) -> List[Dict[str, Any]]:
		"""
		Find vehicles that can accommodate the capacity requirements.
		
		Args:
			requirements: Dict with 'weight', 'volume', 'pallets' (in standard UOMs)
			filters: Additional filters for vehicle selection (vehicle_type, company_owned, etc.)
		
		Returns:
			List of suitable vehicles with capacity info, sorted by best fit
		"""
		if not self.is_enabled():
			return []
		
		# Build vehicle filters
		vehicle_filters = filters or {}
		if 'company_owned' not in vehicle_filters:
			vehicle_filters['company_owned'] = 1  # Default to company-owned vehicles
		
		# Get vehicles
		vehicles = frappe.get_all(
			"Transport Vehicle",
			filters=vehicle_filters,
			fields=['name', 'vehicle_name', 'vehicle_type', 'capacity_weight', 'capacity_volume', 'capacity_pallets']
		)
		
		suitable_vehicles = []
		
		for vehicle in vehicles:
			# Check capacity
			check_result = self.check_capacity_sufficient(vehicle['name'], requirements)
			
			if check_result['sufficient']:
				# Calculate utilization percentage
				available = check_result['available']
				utilization = {
					'weight': (requirements.get('weight', 0) / available['weight'] * 100) if available['weight'] > 0 else 0,
					'volume': (requirements.get('volume', 0) / available['volume'] * 100) if available['volume'] > 0 else 0,
					'pallets': (requirements.get('pallets', 0) / available['pallets'] * 100) if available['pallets'] > 0 else 0
				}
				
				# Calculate fit score (lower is better - closer to 100% without exceeding)
				max_utilization = max(utilization.values())
				fit_score = 100 - max_utilization  # Lower utilization = better fit
				
				suitable_vehicles.append({
					'vehicle': vehicle['name'],
					'vehicle_name': vehicle.get('vehicle_name'),
					'vehicle_type': vehicle.get('vehicle_type'),
					'available_capacity': available,
					'utilization': utilization,
					'fit_score': fit_score,
					'warnings': check_result['warnings']
				})
		
		# Sort by fit score (best fit first)
		suitable_vehicles.sort(key=lambda x: x['fit_score'], reverse=True)
		
		return suitable_vehicles
