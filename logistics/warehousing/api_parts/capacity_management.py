# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Comprehensive Capacity Management System
=======================================

This module provides advanced capacity planning, validation, and optimization
for warehouse storage locations and handling units, aligning with industry
best practices for warehouse management.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple, Any
import frappe
from frappe import _
from frappe.utils import flt, now_datetime, get_datetime, getdate
from frappe.model.document import Document


class CapacityValidationError(Exception):
    """Custom exception for capacity validation errors"""
    pass


class CapacityManager:
    """Comprehensive capacity management for warehouse operations"""
    
    def __init__(self):
        self.capacity_cache = {}
        self.alert_thresholds = self._get_alert_thresholds()
    
    def validate_storage_capacity(
        self, 
        location: str, 
        item: str, 
        quantity: float,
        handling_unit: Optional[str] = None,
        batch_no: Optional[str] = None,
        serial_no: Optional[str] = None,
        tolerance_percentage: float = 0.0
    ) -> Dict[str, Any]:
        """
        Comprehensive capacity validation for storage locations
        
        Args:
            location: Storage location name
            item: Item being stored
            quantity: Quantity to be stored
            handling_unit: Handling unit (optional)
            batch_no: Batch number (optional)
            serial_no: Serial number (optional)
            tolerance_percentage: Allowable percentage by which capacity can be exceeded (default: 0.0)
            
        Returns:
            Dict with validation results and capacity information
            
        Raises:
            CapacityValidationError: If capacity constraints are violated
        """
        try:
            # Get location capacity data
            location_data = self._get_location_capacity_data(location)
            if not location_data:
                raise CapacityValidationError(f"Location {location} not found or has no capacity data")
            
            # Get item dimensions and weight
            item_data = self._get_item_capacity_data(item)
            
            # Calculate required capacity
            required_capacity = self._calculate_required_capacity(
                item_data, quantity, handling_unit
            )
            
            # Get current capacity usage
            current_usage = self._get_current_capacity_usage(location, handling_unit)
            
            # Validate capacity constraints
            validation_results = self._validate_capacity_constraints(
                location_data, required_capacity, current_usage, tolerance_percentage
            )
            
            # Check handling unit capacity if specified
            if handling_unit:
                hu_validation = self._validate_handling_unit_capacity(
                    handling_unit, item_data, quantity, tolerance_percentage
                )
                validation_results.update(hu_validation)
            
            # Generate capacity alerts if needed
            alerts = self._generate_capacity_alerts(
                location_data, current_usage, required_capacity
            )
            
            return {
                "valid": validation_results["valid"],
                "location_capacity": location_data,
                "required_capacity": required_capacity,
                "current_usage": current_usage,
                "validation_results": validation_results,
                "alerts": alerts,
                "recommendations": self._generate_capacity_recommendations(
                    location_data, current_usage, required_capacity
                )
            }
            
        except Exception as e:
            frappe.log_error(f"Capacity validation error: {str(e)}")
            raise CapacityValidationError(f"Capacity validation failed: {str(e)}")
    
    def _get_location_capacity_data(self, location: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive capacity data for a storage location"""
        try:
            location_doc = frappe.get_doc("Storage Location", location)
            
            # Get storage type capacity data
            storage_type_data = {}
            if location_doc.storage_type:
                st_doc = frappe.get_doc("Storage Type", location_doc.storage_type)
                storage_type_data = {
                    "max_volume": flt(st_doc.max_capacity),
                    "max_weight": flt(st_doc.max_weight),
                    "max_height": flt(st_doc.max_height),
                    "max_width": flt(st_doc.max_width),
                    "max_length": flt(st_doc.max_length),
                    "capacity_uom": st_doc.capacity_uom,
                    "weight_uom": st_doc.billing_uom
                }
            
            return {
                "name": location_doc.name,
                "max_hu_slot": flt(location_doc.max_hu_slot),
                "max_volume": flt(location_doc.max_volume) or storage_type_data.get("max_volume", 0),
                "max_weight": flt(location_doc.max_weight) or storage_type_data.get("max_weight", 0),
                "max_height": flt(location_doc.max_height) or storage_type_data.get("max_height", 0),
                "max_width": flt(location_doc.max_width) or storage_type_data.get("max_width", 0),
                "max_length": flt(location_doc.max_length) or storage_type_data.get("max_length", 0),
                "capacity_uom": location_doc.capacity_uom or storage_type_data.get("capacity_uom"),
                "weight_uom": location_doc.weight_uom or storage_type_data.get("weight_uom"),
                "enable_capacity_alerts": location_doc.enable_capacity_alerts,
                "volume_alert_threshold": flt(location_doc.volume_alert_threshold),
                "weight_alert_threshold": flt(location_doc.weight_alert_threshold),
                "utilization_alert_threshold": flt(location_doc.utilization_alert_threshold)
            }
        except Exception as e:
            frappe.log_error(f"Error getting location capacity data: {str(e)}")
            return None
    
    def _get_item_capacity_data(self, item: str) -> Dict[str, Any]:
        """Get capacity-related data for an item"""
        try:
            item_doc = frappe.get_doc("Warehouse Item", item)
            return {
                "name": item_doc.name,
                "volume": flt(item_doc.volume),
                "weight": flt(item_doc.weight),
                "length": flt(item_doc.length),
                "width": flt(item_doc.width),
                "height": flt(item_doc.height),
                "volume_uom": item_doc.volume_uom,
                "weight_uom": item_doc.weight_uom
            }
        except Exception as e:
            frappe.log_error(f"Error getting item capacity data: {str(e)}")
            return {
                "name": item,
                "volume": 0,
                "weight": 0,
                "length": 0,
                "width": 0,
                "height": 0,
                "volume_uom": None,
                "weight_uom": None
            }
    
    def _calculate_required_capacity(
        self, 
        item_data: Dict[str, Any], 
        quantity: float,
        handling_unit: Optional[str] = None
    ) -> Dict[str, Any]:
        """Calculate required capacity for storing items"""
        # Calculate volume
        if item_data.get("volume"):
            volume = flt(item_data["volume"]) * flt(quantity)
        elif all([item_data.get("length"), item_data.get("width"), item_data.get("height")]):
            volume = flt(item_data["length"]) * flt(item_data["width"]) * flt(item_data["height"]) * flt(quantity)
        else:
            volume = 0
        
        # Calculate weight
        weight = flt(item_data.get("weight", 0)) * flt(quantity)
        
        # Get handling unit capacity if specified
        hu_capacity = {}
        if handling_unit:
            hu_capacity = self._get_handling_unit_capacity_data(handling_unit)
        
        return {
            "volume": volume,
            "weight": weight,
            "length": flt(item_data.get("length", 0)),
            "width": flt(item_data.get("width", 0)),
            "height": flt(item_data.get("height", 0)),
            "quantity": quantity,
            "handling_unit_capacity": hu_capacity
        }
    
    def _get_current_capacity_usage(self, location: str, handling_unit: Optional[str] = None) -> Dict[str, Any]:
        """Get current capacity usage for a location"""
        try:
            # Build filters
            filters = {"storage_location": location, "quantity": [">", 0]}
            if handling_unit:
                filters["handling_unit"] = handling_unit
            
            # Get current stock data
            stock_data = frappe.db.sql("""
                SELECT 
                    l.item,
                    l.quantity,
                    l.handling_unit,
                    wi.volume,
                    wi.weight,
                    wi.length,
                    wi.width,
                    wi.height
                FROM `tabWarehouse Stock Ledger` l
                LEFT JOIN `tabWarehouse Item` wi ON wi.name = l.item
                WHERE l.storage_location = %s AND l.quantity > 0
            """, (location,), as_dict=True)
            
            # Calculate current usage
            current_volume = 0
            current_weight = 0
            current_hu_count = 0
            unique_hus = set()
            
            for stock in stock_data:
                # Calculate volume
                if stock.get("volume"):
                    current_volume += flt(stock["volume"]) * flt(stock["quantity"])
                elif all([stock.get("length"), stock.get("width"), stock.get("height")]):
                    current_volume += flt(stock["length"]) * flt(stock["width"]) * flt(stock["height"]) * flt(stock["quantity"])
                
                # Calculate weight
                current_weight += flt(stock.get("weight", 0)) * flt(stock["quantity"])
                
                # Count handling units
                if stock.get("handling_unit"):
                    unique_hus.add(stock["handling_unit"])
            
            current_hu_count = len(unique_hus)
            
            return {
                "volume": current_volume,
                "weight": current_weight,
                "hu_count": current_hu_count,
                "stock_items": len(stock_data)
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting current capacity usage: {str(e)}")
            return {"volume": 0, "weight": 0, "hu_count": 0, "stock_items": 0}
    
    def _validate_capacity_constraints(
        self, 
        location_data: Dict[str, Any], 
        required_capacity: Dict[str, Any],
        current_usage: Dict[str, Any],
        tolerance_percentage: float = 0.0
    ) -> Dict[str, Any]:
        """Validate capacity constraints against location limits
        
        Args:
            location_data: Location capacity data
            required_capacity: Required capacity for the operation
            current_usage: Current capacity usage
            tolerance_percentage: Allowable percentage by which capacity can be exceeded (default: 0.0)
        """
        validation_results = {
            "valid": True,
            "violations": [],
            "warnings": [],
            "capacity_utilization": {}
        }
        
        # Calculate projected usage
        projected_volume = current_usage["volume"] + required_capacity["volume"]
        projected_weight = current_usage["weight"] + required_capacity["weight"]
        projected_hu_count = current_usage["hu_count"] + (1 if required_capacity.get("handling_unit_capacity") else 0)
        
        # Calculate allowed capacity with tolerance (e.g., 5% tolerance: max * 1.05)
        tolerance_multiplier = 1.0 + (flt(tolerance_percentage) / 100.0)
        
        # Validate volume capacity
        if location_data["max_volume"] > 0:
            allowed_volume = location_data["max_volume"] * tolerance_multiplier
            # Also use small epsilon for floating point precision
            epsilon = 1e-5
            if projected_volume > allowed_volume + epsilon:
                validation_results["valid"] = False
                tolerance_msg = f" (tolerance: {tolerance_percentage:.1f}%)" if tolerance_percentage > 0 else ""
                validation_results["violations"].append(
                    f"Volume capacity exceeded: {projected_volume:.3f} > {location_data['max_volume']:.3f}{tolerance_msg}"
                )
            else:
                utilization = (projected_volume / location_data["max_volume"]) * 100
                validation_results["capacity_utilization"]["volume"] = utilization
                if utilization > location_data.get("volume_alert_threshold", 80):
                    validation_results["warnings"].append(
                        f"Volume utilization high: {utilization:.1f}%"
                    )
        
        # Validate weight capacity
        if location_data["max_weight"] > 0:
            allowed_weight = location_data["max_weight"] * tolerance_multiplier
            # Also use small epsilon for floating point precision
            epsilon = 1e-5
            if projected_weight > allowed_weight + epsilon:
                validation_results["valid"] = False
                tolerance_msg = f" (tolerance: {tolerance_percentage:.1f}%)" if tolerance_percentage > 0 else ""
                validation_results["violations"].append(
                    f"Weight capacity exceeded: {projected_weight:.2f} > {location_data['max_weight']:.2f}{tolerance_msg}"
                )
            else:
                utilization = (projected_weight / location_data["max_weight"]) * 100
                validation_results["capacity_utilization"]["weight"] = utilization
                if utilization > location_data.get("weight_alert_threshold", 80):
                    validation_results["warnings"].append(
                        f"Weight utilization high: {utilization:.1f}%"
                    )
        
        # Validate handling unit capacity
        if location_data["max_hu_slot"] > 0:
            if projected_hu_count > location_data["max_hu_slot"]:
                validation_results["valid"] = False
                validation_results["violations"].append(
                    f"Handling unit capacity exceeded: {projected_hu_count} > {location_data['max_hu_slot']}"
                )
            else:
                utilization = (projected_hu_count / location_data["max_hu_slot"]) * 100
                validation_results["capacity_utilization"]["handling_units"] = utilization
                if utilization > location_data.get("utilization_alert_threshold", 90):
                    validation_results["warnings"].append(
                        f"Handling unit utilization high: {utilization:.1f}%"
                    )
        
        return validation_results
    
    def _validate_handling_unit_capacity(
        self, 
        handling_unit: str, 
        item_data: Dict[str, Any], 
        quantity: float,
        tolerance_percentage: float = 0.0
    ) -> Dict[str, Any]:
        """Validate handling unit capacity constraints
        
        Args:
            handling_unit: Handling unit name
            item_data: Item capacity data
            quantity: Quantity to validate
            tolerance_percentage: Allowable percentage by which capacity can be exceeded (default: 0.0)
        """
        try:
            hu_data = self._get_handling_unit_capacity_data(handling_unit)
            if not hu_data:
                return {"valid": True, "warnings": ["No capacity data for handling unit"]}
            
            # Calculate required capacity for handling unit
            required_volume = flt(item_data.get("volume", 0)) * flt(quantity)
            required_weight = flt(item_data.get("weight", 0)) * flt(quantity)
            
            # Get current usage in handling unit
            current_usage = self._get_handling_unit_current_usage(handling_unit)
            
            # Validate constraints
            hu_validation = {
                "valid": True,
                "violations": [],
                "warnings": []
            }
            
            # Calculate allowed capacity with tolerance (e.g., 5% tolerance: max * 1.05)
            tolerance_multiplier = 1.0 + (flt(tolerance_percentage) / 100.0)
            
            # Check volume capacity
            if hu_data.get("max_volume", 0) > 0:
                projected_volume = current_usage["volume"] + required_volume
                allowed_volume = hu_data["max_volume"] * tolerance_multiplier
                # Also use small epsilon for floating point precision
                epsilon = 1e-5
                if projected_volume > allowed_volume + epsilon:
                    hu_validation["valid"] = False
                    tolerance_msg = f" (tolerance: {tolerance_percentage:.1f}%)" if tolerance_percentage > 0 else ""
                    hu_validation["violations"].append(
                        f"Handling unit volume capacity exceeded: {projected_volume:.3f} > {hu_data['max_volume']:.3f}{tolerance_msg}"
                    )
            
            # Check weight capacity
            if hu_data.get("max_weight", 0) > 0:
                projected_weight = current_usage["weight"] + required_weight
                allowed_weight = hu_data["max_weight"] * tolerance_multiplier
                # Also use small epsilon for floating point precision
                epsilon = 1e-5
                if projected_weight > allowed_weight + epsilon:
                    hu_validation["valid"] = False
                    tolerance_msg = f" (tolerance: {tolerance_percentage:.1f}%)" if tolerance_percentage > 0 else ""
                    hu_validation["violations"].append(
                        f"Handling unit weight capacity exceeded: {projected_weight:.2f} > {hu_data['max_weight']:.2f}{tolerance_msg}"
                    )
            
            return hu_validation
            
        except Exception as e:
            frappe.log_error(f"Error validating handling unit capacity: {str(e)}")
            return {"valid": True, "warnings": [f"Handling unit validation error: {str(e)}"]}
    
    def _get_handling_unit_capacity_data(self, handling_unit: str) -> Optional[Dict[str, Any]]:
        """Get capacity data for a handling unit"""
        try:
            hu_doc = frappe.get_doc("Handling Unit", handling_unit)
            return {
                "name": hu_doc.name,
                "max_volume": flt(hu_doc.max_volume),
                "max_weight": flt(hu_doc.max_weight),
                "max_height": flt(hu_doc.max_height),
                "max_width": flt(hu_doc.max_width),
                "max_length": flt(hu_doc.max_length),
                "capacity_uom": hu_doc.capacity_uom,
                "weight_uom": hu_doc.weight_uom
            }
        except Exception as e:
            frappe.log_error(f"Error getting handling unit capacity data: {str(e)}")
            return None
    
    def _get_handling_unit_current_usage(self, handling_unit: str) -> Dict[str, Any]:
        """Get current capacity usage for a handling unit"""
        try:
            stock_data = frappe.db.sql("""
                SELECT 
                    l.quantity,
                    wi.volume,
                    wi.weight
                FROM `tabWarehouse Stock Ledger` l
                LEFT JOIN `tabWarehouse Item` wi ON wi.name = l.item
                WHERE l.handling_unit = %s AND l.quantity > 0
            """, (handling_unit,), as_dict=True)
            
            current_volume = 0
            current_weight = 0
            
            for stock in stock_data:
                if stock.get("volume"):
                    current_volume += flt(stock["volume"]) * flt(stock["quantity"])
                current_weight += flt(stock.get("weight", 0)) * flt(stock["quantity"])
            
            return {
                "volume": current_volume,
                "weight": current_weight,
                "stock_items": len(stock_data)
            }
            
        except Exception as e:
            frappe.log_error(f"Error getting handling unit current usage: {str(e)}")
            return {"volume": 0, "weight": 0, "stock_items": 0}
    
    def _generate_capacity_alerts(
        self, 
        location_data: Dict[str, Any], 
        current_usage: Dict[str, Any],
        required_capacity: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate capacity alerts based on thresholds"""
        alerts = []
        
        if not location_data.get("enable_capacity_alerts"):
            return alerts
        
        # Volume alerts
        if location_data.get("max_volume", 0) > 0:
            current_utilization = (current_usage["volume"] / location_data["max_volume"]) * 100
            if current_utilization > location_data.get("volume_alert_threshold", 80):
                alerts.append({
                    "type": "volume_alert",
                    "message": f"Volume utilization at {current_utilization:.1f}%",
                    "severity": "warning" if current_utilization < 95 else "critical"
                })
        
        # Weight alerts
        if location_data.get("max_weight", 0) > 0:
            current_utilization = (current_usage["weight"] / location_data["max_weight"]) * 100
            if current_utilization > location_data.get("weight_alert_threshold", 80):
                alerts.append({
                    "type": "weight_alert",
                    "message": f"Weight utilization at {current_utilization:.1f}%",
                    "severity": "warning" if current_utilization < 95 else "critical"
                })
        
        # Handling unit alerts
        if location_data.get("max_hu_slot", 0) > 0:
            current_utilization = (current_usage["hu_count"] / location_data["max_hu_slot"]) * 100
            if current_utilization > location_data.get("utilization_alert_threshold", 90):
                alerts.append({
                    "type": "hu_alert",
                    "message": f"Handling unit utilization at {current_utilization:.1f}%",
                    "severity": "warning" if current_utilization < 95 else "critical"
                })
        
        return alerts
    
    def _generate_capacity_recommendations(
        self, 
        location_data: Dict[str, Any], 
        current_usage: Dict[str, Any],
        required_capacity: Dict[str, Any]
    ) -> List[str]:
        """Generate capacity optimization recommendations"""
        recommendations = []
        
        # Volume recommendations
        if location_data.get("max_volume", 0) > 0:
            utilization = (current_usage["volume"] / location_data["max_volume"]) * 100
            if utilization > 80:
                recommendations.append("Consider redistributing items to optimize volume utilization")
        
        # Weight recommendations
        if location_data.get("max_weight", 0) > 0:
            utilization = (current_usage["weight"] / location_data["max_weight"]) * 100
            if utilization > 80:
                recommendations.append("Consider redistributing items to optimize weight distribution")
        
        # Handling unit recommendations
        if location_data.get("max_hu_slot", 0) > 0:
            utilization = (current_usage["hu_count"] / location_data["max_hu_slot"]) * 100
            if utilization > 80:
                recommendations.append("Consider consolidating handling units or adding more storage slots")
        
        return recommendations
    
    def _get_alert_thresholds(self) -> Dict[str, float]:
        """Get default alert thresholds"""
        return {
            "volume_alert": 80.0,
            "weight_alert": 80.0,
            "utilization_alert": 90.0
        }
    
    def update_capacity_metrics(self, location: str) -> Dict[str, Any]:
        """Update real-time capacity metrics for a location"""
        try:
            # Get current usage
            current_usage = self._get_current_capacity_usage(location)
            
            # Get location capacity data
            location_data = self._get_location_capacity_data(location)
            if not location_data:
                return {"error": "Location not found"}
            
            # Calculate utilization percentages
            volume_utilization = 0
            weight_utilization = 0
            hu_utilization = 0
            
            if location_data.get("max_volume", 0) > 0:
                volume_utilization = (current_usage["volume"] / location_data["max_volume"]) * 100
            
            if location_data.get("max_weight", 0) > 0:
                weight_utilization = (current_usage["weight"] / location_data["max_weight"]) * 100
            
            if location_data.get("max_hu_slot", 0) > 0:
                hu_utilization = (current_usage["hu_count"] / location_data["max_hu_slot"]) * 100
            
            # Update the location document
            location_doc = frappe.get_doc("Storage Location", location)
            location_doc.current_volume = current_usage["volume"]
            location_doc.current_weight = current_usage["weight"]
            location_doc.utilization_percentage = max(volume_utilization, weight_utilization, hu_utilization)
            location_doc.save(ignore_permissions=True)
            
            return {
                "current_volume": current_usage["volume"],
                "current_weight": current_usage["weight"],
                "current_hu_count": current_usage["hu_count"],
                "volume_utilization": volume_utilization,
                "weight_utilization": weight_utilization,
                "hu_utilization": hu_utilization,
                "overall_utilization": location_doc.utilization_percentage
            }
            
        except Exception as e:
            frappe.log_error(f"Error updating capacity metrics: {str(e)}")
            return {"error": str(e)}


# Helper function to validate capacity limits for warehouse jobs
def validate_warehouse_job_capacity(warehouse_job, company=None):
    """
    Validate capacity limits for all items in a warehouse job.
    Throws an error if capacity limits are exceeded and the setting is enabled.
    
    Args:
        warehouse_job: Warehouse Job document or name
        company: Company name (optional, will be extracted from job if not provided)
    
    Raises:
        frappe.ValidationError: If capacity limits are exceeded
    """
    try:
        # Get warehouse job document
        if isinstance(warehouse_job, str):
            job = frappe.get_doc("Warehouse Job", warehouse_job)
        else:
            job = warehouse_job
        
        # Get company from job if not provided
        if not company:
            company = getattr(job, "company", None)
        
        if not company:
            return  # No company, skip validation
        
        # Get warehouse settings
        try:
            settings = frappe.get_doc("Warehouse Settings", company)
        except frappe.DoesNotExistError:
            return  # No settings, skip validation
        
        # Check if the setting is enabled
        if not getattr(settings, "prevent_exceeding_capacity_limit", False):
            return  # Setting not enabled, skip validation
        
        # Check if capacity management is enabled
        if not getattr(settings, "enable_capacity_management", False):
            return  # Capacity management not enabled, skip validation
        
        # Get capacity tolerance percentage from settings (default: 0.0 for strict enforcement)
        tolerance_percentage = flt(getattr(settings, "capacity_tolerance_percentage", 0.0))
        
        # Initialize capacity manager
        capacity_manager = CapacityManager()
        
        # Validate each item in the job
        violations = []
        
        for item_row in (job.items or []):
            location = getattr(item_row, "location", None)
            to_location = getattr(item_row, "to_location", None)
            item = getattr(item_row, "item", None)
            quantity = flt(getattr(item_row, "quantity", 0))
            handling_unit = getattr(item_row, "handling_unit", None)
            batch_no = getattr(item_row, "batch_no", None)
            serial_no = getattr(item_row, "serial_no", None)
            
            if not item or not quantity:
                continue
            
            # Determine which location to validate based on job type
            # IMPORTANT: Only check capacity for positive quantities (putaway items) that add items to locations
            # Negative quantities (pick items) remove items, so no capacity validation needed
            # NOTE: VAS Action (Pick/Putaway) only applies to VAS job types, not Move or other job types
            job_type = (getattr(job, "type", "") or "").strip()
            
            # For Putaway jobs, validate destination location (to_location or location)
            # For Pick jobs, we're removing items, so no capacity validation needed
            # For Move jobs, only validate destination location for positive qty (putaway items)
            #   - Move jobs do NOT use VAS Action field
            # For Receiving/Inbound, validate staging area
            # For Stocktake, validate location only if adding items (positive qty)
            # For VAS jobs, validate quantity sign matches vas_action, then validate capacity when vas_action = Putaway
            #   - VAS Action field only applies to VAS job types
            # For Release, we're removing items, so no capacity validation needed
            
            target_location = None
            if job_type == "Putaway":
                # Validate destination location (always adding items)
                target_location = to_location or location
            elif job_type == "Move":
                # Only validate capacity for positive quantities (putaway items going to destination)
                # Negative quantities remove items from source, so skip capacity validation
                if quantity > 0:
                    target_location = to_location or location
                else:
                    # Negative qty means we're removing from this location, skip validation
                    continue
            elif job_type in ("Receiving", "Inbound"):
                # Validate staging area (always adding items)
                target_location = location
            elif job_type == "Stocktake":
                # Only validate capacity if adding items (positive qty)
                if quantity > 0:
                    target_location = location
                else:
                    # Negative qty means we're removing from this location, skip validation
                    continue
            elif job_type == "VAS":
                # VAS Action validation: Only applies to VAS job types
                # For VAS jobs, validate that quantity sign matches vas_action
                # Negative quantities should have vas_action = Pick
                # Positive quantities should have vas_action = Putaway
                vas_action = getattr(item_row, "vas_action", None)
                
                # Validate quantity sign matches vas_action
                if quantity < 0:
                    if vas_action != "Pick":
                        violations.append({
                            "row": getattr(item_row, "idx", "?"),
                            "item": item,
                            "location": location,
                            "handling_unit": handling_unit,
                            "violations": [f"Negative quantity requires vas_action = 'Pick', but found '{vas_action or '(empty)'}'"]
                        })
                        continue
                    # Negative qty with Pick action - skip capacity validation (removing items)
                    continue
                elif quantity > 0:
                    if vas_action != "Putaway":
                        violations.append({
                            "row": getattr(item_row, "idx", "?"),
                            "item": item,
                            "location": location,
                            "handling_unit": handling_unit,
                            "violations": [f"Positive quantity requires vas_action = 'Putaway', but found '{vas_action or '(empty)'}'"]
                        })
                        continue
                    # Positive qty with Putaway action - validate capacity
                    target_location = to_location or location
                else:
                    # Zero quantity, skip validation
                    continue
            else:
                # For Pick, Release, and other outbound operations, skip validation
                continue
            
            if not target_location:
                continue
            
            # Validate location capacity
            try:
                validation_result = capacity_manager.validate_storage_capacity(
                    location=target_location,
                    item=item,
                    quantity=abs(quantity),
                    handling_unit=handling_unit,
                    batch_no=batch_no,
                    serial_no=serial_no,
                    tolerance_percentage=tolerance_percentage
                )
                
                # Check if validation failed
                is_valid = validation_result.get("valid", True)
                violations_info = validation_result.get("validation_results", {}).get("violations", [])
                
                if not is_valid:
                    # If valid is False, there should be violations, but handle edge cases
                    if violations_info:
                        violations.append({
                            "row": getattr(item_row, "idx", "?"),
                            "item": item,
                            "location": target_location,
                            "handling_unit": handling_unit,
                            "violations": violations_info
                        })
                    else:
                        # Edge case: valid is False but no violations listed - add a generic violation
                        violations.append({
                            "row": getattr(item_row, "idx", "?"),
                            "item": item,
                            "location": target_location,
                            "handling_unit": handling_unit,
                            "violations": ["Capacity limit exceeded (validation failed but no specific violation details)"]
                        })
                
                # Also validate handling unit capacity if specified
                if handling_unit:
                    hu_validation = capacity_manager._validate_handling_unit_capacity(
                        handling_unit=handling_unit,
                        item_data=capacity_manager._get_item_capacity_data(item),
                        quantity=abs(quantity),
                        tolerance_percentage=tolerance_percentage
                    )
                    
                    hu_is_valid = hu_validation.get("valid", True)
                    hu_violations = hu_validation.get("violations", [])
                    
                    if not hu_is_valid:
                        # If valid is False, there should be violations, but handle edge cases
                        if hu_violations:
                            violations.append({
                                "row": getattr(item_row, "idx", "?"),
                                "item": item,
                                "location": target_location,
                                "handling_unit": handling_unit,
                                "violations": hu_violations
                            })
                        else:
                            # Edge case: valid is False but no violations listed
                            violations.append({
                                "row": getattr(item_row, "idx", "?"),
                                "item": item,
                                "location": target_location,
                                "handling_unit": handling_unit,
                                "violations": ["Handling unit capacity limit exceeded (validation failed but no specific violation details)"]
                            })
                            
            except CapacityValidationError as e:
                violations.append({
                    "row": getattr(item_row, "idx", "?"),
                    "item": item,
                    "location": target_location,
                    "handling_unit": handling_unit,
                    "violations": [str(e)]
                })
            except Exception as e:
                frappe.log_error(f"Error validating capacity for row {getattr(item_row, 'idx', '?')}: {str(e)}")
                # Continue with other items even if one fails
        
        # If there are violations, throw an error
        if violations:
            error_messages = []
            for violation in violations:
                row_msg = _("Row #{0}: Item {1}").format(violation["row"], violation["item"])
                if violation.get("location"):
                    row_msg += _(" at Location {0}").format(violation["location"])
                if violation.get("handling_unit"):
                    row_msg += _(" in Handling Unit {0}").format(violation["handling_unit"])
                row_msg += ":\n"
                for v in violation["violations"]:
                    row_msg += f"  - {v}\n"
                error_messages.append(row_msg)
            
            error_msg = _("Capacity limits exceeded. Cannot process warehouse job:\n\n{0}").format(
                "\n".join(error_messages)
            )
            frappe.throw(
                error_msg,
                title=_("Capacity Limit Exceeded")
            )
    
    except frappe.ValidationError:
        # Re-raise validation errors (these should block submission)
        raise
    except Exception as e:
        # Log other errors but still block submission to be safe
        frappe.log_error(f"Error in validate_warehouse_job_capacity: {str(e)}")
        frappe.throw(
            _("Error validating capacity limits. Please check the error log for details. Submission blocked for safety."),
            title=_("Capacity Validation Error")
        )


# API Functions for external use
@frappe.whitelist()
def validate_storage_capacity(
    location: str, 
    item: str, 
    quantity: float,
    handling_unit: Optional[str] = None,
    batch_no: Optional[str] = None,
    serial_no: Optional[str] = None
) -> Dict[str, Any]:
    """API function to validate storage capacity"""
    try:
        capacity_manager = CapacityManager()
        return capacity_manager.validate_storage_capacity(
            location, item, quantity, handling_unit, batch_no, serial_no
        )
    except CapacityValidationError as e:
        return {"valid": False, "error": str(e)}
    except Exception as e:
        frappe.log_error(f"Capacity validation API error: {str(e)}")
        return {"valid": False, "error": "Internal error occurred"}


@frappe.whitelist()
def update_location_capacity_metrics(location: str) -> Dict[str, Any]:
    """API function to update capacity metrics for a location"""
    try:
        capacity_manager = CapacityManager()
        return capacity_manager.update_capacity_metrics(location)
    except Exception as e:
        frappe.log_error(f"Capacity metrics update error: {str(e)}")
        return {"error": str(e)}


@frappe.whitelist()
def get_capacity_utilization_report(
    company: Optional[str] = None,
    branch: Optional[str] = None,
    site: Optional[str] = None,
    building: Optional[str] = None,
    zone: Optional[str] = None
) -> Dict[str, Any]:
    """Generate comprehensive capacity utilization report"""
    try:
        # Build filters
        filters = {}
        if company:
            filters["company"] = company
        if branch:
            filters["branch"] = branch
        if site:
            filters["site"] = site
        if building:
            filters["building"] = building
        if zone:
            filters["zone"] = zone
        
        # Get locations with capacity data
        locations = frappe.get_all(
            "Storage Location",
            filters=filters,
            fields=[
                "name", "site", "building", "zone", "aisle", "bay", "level",
                "max_volume", "max_weight", "max_hu_slot",
                "current_volume", "current_weight", "utilization_percentage"
            ]
        )
        
        # Calculate summary statistics
        total_locations = len(locations)
        high_utilization_locations = [loc for loc in locations if flt(loc.utilization_percentage) > 80]
        critical_locations = [loc for loc in locations if flt(loc.utilization_percentage) > 95]
        
        # Calculate average utilization
        avg_utilization = sum(flt(loc.utilization_percentage) for loc in locations) / total_locations if total_locations > 0 else 0
        
        return {
            "total_locations": total_locations,
            "high_utilization_count": len(high_utilization_locations),
            "critical_utilization_count": len(critical_locations),
            "average_utilization": avg_utilization,
            "locations": locations,
            "high_utilization_locations": high_utilization_locations,
            "critical_locations": critical_locations
        }
        
    except Exception as e:
        frappe.log_error(f"Capacity utilization report error: {str(e)}")
        return {"error": str(e)}


@frappe.whitelist()
def refresh_capacity_data():
    """Refresh capacity data for all handling units and storage locations"""
    try:
        updated_count = 0
        
        # Refresh handling unit capacity data
        handling_units = frappe.get_all(
            "Handling Unit",
            filters={"docstatus": ["!=", 2]},
            fields=["name"]
        )
        
        for hu in handling_units:
            try:
                hu_doc = frappe.get_doc("Handling Unit", hu.name)
                
                # Calculate current capacity usage
                current_volume = calculate_handling_unit_current_volume(hu.name)
                current_weight = calculate_handling_unit_current_weight(hu.name)
                
                # Calculate utilization percentage
                max_volume = flt(hu_doc.max_volume)
                max_weight = flt(hu_doc.max_weight)
                
                volume_utilization = (current_volume / max_volume * 100) if max_volume > 0 else 0
                weight_utilization = (current_weight / max_weight * 100) if max_weight > 0 else 0
                
                # Use the higher of volume or weight utilization
                utilization_percentage = max(volume_utilization, weight_utilization)
                
                # Update the handling unit
                hu_doc.current_volume = current_volume
                hu_doc.current_weight = current_weight
                hu_doc.utilization_percentage = utilization_percentage
                hu_doc.save(ignore_permissions=True)
                
                updated_count += 1
                
            except Exception as e:
                frappe.log_error(f"Error updating handling unit {hu.name}: {str(e)}")
                continue
        
        # Refresh storage location capacity data
        storage_locations = frappe.get_all(
            "Storage Location",
            filters={"docstatus": ["!=", 2]},
            fields=["name"]
        )
        
        for sl in storage_locations:
            try:
                sl_doc = frappe.get_doc("Storage Location", sl.name)
                
                # Calculate current capacity usage
                current_volume = calculate_storage_location_current_volume(sl.name)
                current_weight = calculate_storage_location_current_weight(sl.name)
                
                # Calculate utilization percentage
                max_volume = flt(sl_doc.max_volume)
                max_weight = flt(sl_doc.max_weight)
                
                volume_utilization = (current_volume / max_volume * 100) if max_volume > 0 else 0
                weight_utilization = (current_weight / max_weight * 100) if max_weight > 0 else 0
                
                # Use the higher of volume or weight utilization
                utilization_percentage = max(volume_utilization, weight_utilization)
                
                # Update the storage location
                sl_doc.current_volume = current_volume
                sl_doc.current_weight = current_weight
                sl_doc.utilization_percentage = utilization_percentage
                sl_doc.save(ignore_permissions=True)
                
                updated_count += 1
                
            except Exception as e:
                frappe.log_error(f"Error updating storage location {sl.name}: {str(e)}")
                continue
        
        frappe.db.commit()
        
        return {
            "success": True,
            "message": f"Capacity data refreshed successfully for {updated_count} units",
            "updated_count": updated_count
        }
        
    except Exception as e:
        frappe.db.rollback()
        frappe.log_error(f"Capacity data refresh error: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }


def calculate_handling_unit_current_volume(handling_unit_name):
    """Calculate current volume usage for a handling unit"""
    try:
        # Get stock ledger entries for this handling unit
        stock_entries = frappe.db.sql("""
            SELECT 
                SUM(COALESCE(quantity, 0) * COALESCE(wi.volume, 0)) as total_volume
            FROM `tabWarehouse Stock Ledger` wsl
            LEFT JOIN `tabWarehouse Item` wi ON wsl.item = wi.name
            WHERE wsl.handling_unit = %s
        """, (handling_unit_name,), as_dict=True)
        
        return flt(stock_entries[0].total_volume) if stock_entries else 0
        
    except Exception as e:
        frappe.log_error(f"Error calculating handling unit volume: {str(e)}")
        return 0


def calculate_handling_unit_current_weight(handling_unit_name):
    """Calculate current weight usage for a handling unit"""
    try:
        # Get stock ledger entries for this handling unit
        stock_entries = frappe.db.sql("""
            SELECT 
                SUM(COALESCE(quantity, 0) * COALESCE(wi.weight, 0)) as total_weight
            FROM `tabWarehouse Stock Ledger` wsl
            LEFT JOIN `tabWarehouse Item` wi ON wsl.item = wi.name
            WHERE wsl.handling_unit = %s
        """, (handling_unit_name,), as_dict=True)
        
        return flt(stock_entries[0].total_weight) if stock_entries else 0
        
    except Exception as e:
        frappe.log_error(f"Error calculating handling unit weight: {str(e)}")
        return 0


def calculate_storage_location_current_volume(storage_location_name):
    """Calculate current volume usage for a storage location"""
    try:
        # Get stock ledger entries for this storage location
        stock_entries = frappe.db.sql("""
            SELECT 
                SUM(COALESCE(quantity, 0) * COALESCE(wi.volume, 0)) as total_volume
            FROM `tabWarehouse Stock Ledger` wsl
            LEFT JOIN `tabWarehouse Item` wi ON wsl.item = wi.name
            WHERE wsl.storage_location = %s
        """, (storage_location_name,), as_dict=True)
        
        return flt(stock_entries[0].total_volume) if stock_entries else 0
        
    except Exception as e:
        frappe.log_error(f"Error calculating storage location volume: {str(e)}")
        return 0


def calculate_storage_location_current_weight(storage_location_name):
    """Calculate current weight usage for a storage location"""
    try:
        # Get stock ledger entries for this storage location
        stock_entries = frappe.db.sql("""
            SELECT 
                SUM(COALESCE(quantity, 0) * COALESCE(wi.weight, 0)) as total_weight
            FROM `tabWarehouse Stock Ledger` wsl
            LEFT JOIN `tabWarehouse Item` wi ON wsl.item = wi.name
            WHERE wsl.storage_location = %s
        """, (storage_location_name,), as_dict=True)
        
        return flt(stock_entries[0].total_weight) if stock_entries else 0
        
    except Exception as e:
        frappe.log_error(f"Error calculating storage location weight: {str(e)}")
        return 0
