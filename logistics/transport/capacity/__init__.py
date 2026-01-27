# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Transport Capacity Management Module

Provides capacity tracking, reservation, and validation for transport operations.
"""

from .uom_conversion import (
	convert_weight,
	convert_volume,
	convert_dimension,
	calculate_volume_from_dimensions,
	get_default_uoms,
	standardize_capacity_value
)
from .capacity_manager import CapacityManager
from .vehicle_type_capacity import (
	get_vehicle_type_capacity_info,
	check_vehicle_type_capacity
)

__all__ = [
	"convert_weight",
	"convert_volume",
	"convert_dimension",
	"calculate_volume_from_dimensions",
	"get_default_uoms",
	"standardize_capacity_value",
	"CapacityManager",
	"get_vehicle_type_capacity_info",
	"check_vehicle_type_capacity"
]
