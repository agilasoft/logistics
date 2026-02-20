# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Vehicle Type Capacity Helper

Provides functions to get aggregated capacity information for vehicle types.
"""

import frappe
from frappe import _
from frappe.utils import flt
from typing import Dict, Any, Optional

from .uom_conversion import get_default_uoms, convert_weight, convert_volume
from logistics.utils.measurements import get_aggregation_volume_uom


def get_vehicle_type_capacity_info(vehicle_type: str, company: Optional[str] = None) -> Dict[str, Any]:
	"""
	Get aggregated capacity information for a vehicle type.
	Uses Logistics Settings: default weight UOM and aggregation volume UOM (base or default).
	"""
	default_uoms = get_default_uoms(company)
	volume_uom_std = get_aggregation_volume_uom(company) or default_uoms.get('volume')

	# Get all vehicles of this type
	vehicles = frappe.get_all(
		"Transport Vehicle",
		filters={'vehicle_type': vehicle_type},
		fields=['name', 'capacity_weight', 'capacity_weight_uom', 'capacity_volume', 'capacity_volume_uom', 'capacity_pallets']
	)

	if not vehicles:
		return {
			'max_weight': 0,
			'max_volume': 0,
			'max_pallets': 0,
			'avg_weight': 0,
			'min_weight': 0,
			'vehicle_count': 0,
			'weight_uom': default_uoms['weight'],
			'volume_uom': volume_uom_std
		}

	weights = []
	volumes = []
	pallets = []

	for vehicle in vehicles:
		# Weight
		weight = flt(vehicle.get('capacity_weight', 0))
		if weight > 0:
			weight_uom = vehicle.get('capacity_weight_uom') or default_uoms['weight']
			weight_std = convert_weight(weight, weight_uom, default_uoms['weight'], company)
			weights.append(weight_std)

		# Volume - convert to aggregation volume UOM
		volume = flt(vehicle.get('capacity_volume', 0))
		if volume > 0 and volume_uom_std:
			v_uom = vehicle.get('capacity_volume_uom') or default_uoms['volume']
			volume_std = convert_volume(volume, v_uom, volume_uom_std, company)
			volumes.append(volume_std)

		# Pallets
		pallet = flt(vehicle.get('capacity_pallets', 0))
		if pallet > 0:
			pallets.append(pallet)

	# Calculate statistics
	max_weight = max(weights) if weights else 0
	min_weight = min(weights) if weights else 0
	avg_weight = sum(weights) / len(weights) if weights else 0

	max_volume = max(volumes) if volumes else 0
	max_pallets = max(pallets) if pallets else 0

	return {
		'max_weight': max_weight,
		'max_volume': max_volume,
		'max_pallets': max_pallets,
		'avg_weight': avg_weight,
		'min_weight': min_weight,
		'vehicle_count': len(vehicles),
		'weight_uom': default_uoms['weight'],
		'volume_uom': volume_uom_std
	}


def check_vehicle_type_capacity(
	vehicle_type: str,
	requirements: Dict[str, float],
	company: Optional[str] = None
) -> Dict[str, Any]:
	"""
	Check if vehicle type can accommodate requirements.
	
	Args:
		vehicle_type: Vehicle Type name
		requirements: Dict with 'weight', 'volume', 'pallets' (in standard UOMs)
		company: Optional company for UOM defaults
	
	Returns:
		{
			'sufficient': bool,
			'available_vehicles': list of vehicles with sufficient capacity,
			'warnings': list of warning messages
		}
	"""
	capacity_info = get_vehicle_type_capacity_info(vehicle_type, company)
	
	required_weight = flt(requirements.get('weight', 0))
	required_volume = flt(requirements.get('volume', 0))
	required_pallets = flt(requirements.get('pallets', 0))
	
	sufficient = True
	warnings = []
	
	# Check against maximum capacity
	if required_weight > 0 and required_weight > capacity_info['max_weight']:
		sufficient = False
		warnings.append(_("Required weight ({0} {1}) exceeds maximum capacity ({2} {1}) for vehicle type {3}").format(
			required_weight, capacity_info['weight_uom'], capacity_info['max_weight'], vehicle_type
		))
	
	if required_volume > 0 and required_volume > capacity_info['max_volume']:
		sufficient = False
		warnings.append(_("Required volume ({0} {1}) exceeds maximum capacity ({2} {1}) for vehicle type {3}").format(
			required_volume, capacity_info['volume_uom'], capacity_info['max_volume'], vehicle_type
		))
	
	if required_pallets > 0 and required_pallets > capacity_info['max_pallets']:
		sufficient = False
		warnings.append(_("Required pallets ({0}) exceeds maximum capacity ({1}) for vehicle type {2}").format(
			required_pallets, capacity_info['max_pallets'], vehicle_type
		))
	
	# Find available vehicles
	available_vehicles = []
	if sufficient:
		from .capacity_manager import CapacityManager
		manager = CapacityManager(company)
		available_vehicles = manager.find_suitable_vehicles(
			requirements,
			filters={'vehicle_type': vehicle_type}
		)
	
	return {
		'sufficient': sufficient,
		'available_vehicles': available_vehicles,
		'warnings': warnings
	}
