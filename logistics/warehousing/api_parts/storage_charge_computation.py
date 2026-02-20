#!/usr/bin/env python3
"""
Storage Charge Computation with Storage Type, Billing Method, and Billing Time

This module provides comprehensive storage charge computation considering:
- Storage Type (Cold Storage, Dry Storage, Hazardous Storage, etc.)
- Billing Method (Per Day, Per Week, Per Hour, Per Volume, Per Weight, etc.)
- Billing Time (per day, per week, per hour, etc.)
"""

from __future__ import annotations
import frappe
from frappe import _
from frappe.utils import flt, getdate, get_datetime, now_datetime, add_days
from typing import Dict, List, Any, Optional, Tuple
from datetime import date, datetime, timedelta
from logistics.warehousing.api_parts.billing_methods import get_billing_quantity

# =============================================================================
# Storage Charge Computation Functions
# =============================================================================

@frappe.whitelist()
def compute_storage_charge_with_type(
    handling_unit: str,
    storage_type: str,
    billing_method: str,
    date_from: str,
    date_to: str,
    contract_item: Dict[str, Any] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Compute storage charge considering storage type, billing method, and billing time.
    
    Args:
        handling_unit: Handling unit reference
        storage_type: Storage type (Cold Storage, Dry Storage, etc.)
        billing_method: Billing method (Per Day, Per Week, Per Hour, Per Volume, etc.)
        date_from: Start date
        date_to: End date
        contract_item: Contract item with billing settings
        **kwargs: Additional parameters
    
    Returns:
        Dict with computed charge details
    """
    try:
        # Get storage type details
        storage_type_doc = frappe.get_doc("Storage Type", storage_type)
        
        # Get handling unit details
        hu_doc = frappe.get_doc("Handling Unit", handling_unit)
        
        # Get contract item billing settings
        billing_settings = _get_billing_settings(contract_item, storage_type_doc)
        
        # Compute base quantity based on billing method
        base_quantity = _compute_base_quantity(
            handling_unit=handling_unit,
            storage_type=storage_type,
            billing_method=billing_method,
            date_from=date_from,
            date_to=date_to,
            billing_settings=billing_settings,
            **kwargs
        )
        
        # Apply storage type multipliers
        adjusted_quantity = _apply_storage_type_multipliers(
            base_quantity=base_quantity,
            storage_type=storage_type,
            billing_method=billing_method,
            billing_settings=billing_settings
        )
        
        # Apply billing time settings
        final_quantity = _apply_billing_time_settings(
            quantity=adjusted_quantity,
            billing_method=billing_method,
            billing_settings=billing_settings
        )
        
        # Compute charge details
        charge_details = {
            "handling_unit": handling_unit,
            "storage_type": storage_type,
            "billing_method": billing_method,
            "base_quantity": base_quantity,
            "adjusted_quantity": adjusted_quantity,
            "final_quantity": final_quantity,
            "billing_time_unit": billing_settings.get("billing_time_unit"),
            "billing_time_multiplier": billing_settings.get("billing_time_multiplier", 1.0),
            "minimum_billing_time": billing_settings.get("minimum_billing_time", 1.0),
            "storage_type_multiplier": billing_settings.get("storage_type_multiplier", 1.0),
            "computation_details": _get_computation_details(
                handling_unit, storage_type, billing_method, billing_settings
            )
        }
        
        return {
            "ok": True,
            "charge_details": charge_details,
            "message": f"Storage charge computed: {final_quantity:.2f} {billing_settings.get('billing_time_unit', 'units')}"
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "message": f"Error computing storage charge: {str(e)}"
        }


def _get_billing_settings(contract_item: Dict[str, Any], storage_type_doc) -> Dict[str, Any]:
    """Get billing settings from contract item and storage type."""
    settings = {
        "billing_time_unit": "Day",
        "billing_time_multiplier": 1.0,
        "minimum_billing_time": 1.0,
        "storage_type_multiplier": 1.0,
        "volume_uom": "CBM",
        "weight_uom": "Kg",
        "billing_time_unit": "Day"
    }
    
    # Get settings from contract item
    if contract_item:
        settings.update({
            "billing_time_unit": contract_item.get("billing_time_unit", "Day"),
            "billing_time_multiplier": flt(contract_item.get("billing_time_multiplier", 1.0)),
            "minimum_billing_time": flt(contract_item.get("minimum_billing_time", 1.0)),
            "volume_uom": contract_item.get("volume_uom", "CBM"),
            "weight_uom": contract_item.get("weight_uom", "Kg"),
            "billing_time_unit": contract_item.get("billing_time_unit", "Day")
        })
    
    # Get settings from storage type
    if storage_type_doc:
        settings.update({
            "storage_type_multiplier": _get_storage_type_multiplier(storage_type_doc),
            "billing_time_unit": storage_type_doc.get("time_unit", "Day")
        })
    
    return settings


def _compute_base_quantity(
    handling_unit: str,
    storage_type: str,
    billing_method: str,
    date_from: str,
    date_to: str,
    billing_settings: Dict[str, Any],
    **kwargs
) -> float:
    """Compute base quantity based on billing method."""
    
    # Get billing quantity using existing billing methods
    base_quantity = get_billing_quantity(
        context="storage",
        billing_method=billing_method,
        reference_doc=handling_unit,
        date_from=date_from,
        date_to=date_to,
        **kwargs
    )
    
    return flt(base_quantity)


def _apply_storage_type_multipliers(
    base_quantity: float,
    storage_type: str,
    billing_method: str,
    billing_settings: Dict[str, Any]
) -> float:
    """Apply storage type specific multipliers."""
    
    # Get storage type multiplier
    storage_multiplier = billing_settings.get("storage_type_multiplier", 1.0)
    
    # Apply storage type specific logic
    if storage_type == "Cold Storage":
        # Cold storage typically has higher rates
        storage_multiplier *= 1.5
    elif storage_type == "Hazardous Storage":
        # Hazardous storage has premium rates
        storage_multiplier *= 2.0
    elif storage_type == "Dry Storage":
        # Standard dry storage
        storage_multiplier *= 1.0
    
    # Apply storage type multiplier
    adjusted_quantity = base_quantity * storage_multiplier
    
    return flt(adjusted_quantity)


def _apply_billing_time_settings(
    quantity: float,
    billing_method: str,
    billing_settings: Dict[str, Any]
) -> float:
    """Apply billing time settings (multiplier, minimum time) for storage charges only."""
    
    # Only apply billing time settings for time-based storage billing methods
    if billing_method not in ["Per Day", "Per Week", "Per Hour"]:
        return quantity
    
    # Get billing time settings
    multiplier = billing_settings.get("billing_time_multiplier", 1.0)
    minimum_time = billing_settings.get("minimum_billing_time", 1.0)
    
    # Apply minimum billing time
    final_quantity = max(quantity, minimum_time)
    
    # Apply multiplier
    final_quantity *= multiplier
    
    return flt(final_quantity)


def _get_storage_type_multiplier(storage_type_doc) -> float:
    """Get storage type specific multiplier."""
    
    # Default multiplier
    multiplier = 1.0
    
    # Get multiplier based on storage type characteristics
    if hasattr(storage_type_doc, 'billing_uom'):
        # Use billing UOM to determine multiplier
        billing_uom = storage_type_doc.get("billing_uom")
        if billing_uom:
            # Different UOMs may have different multipliers
            if "Hour" in billing_uom:
                multiplier = 1.0  # Hourly billing
            elif "Week" in billing_uom:
                multiplier = 7.0  # Weekly billing
            elif "Month" in billing_uom:
                multiplier = 30.0  # Monthly billing
    
    # Get multiplier from storage type environment
    if hasattr(storage_type_doc, 'environment'):
        environment = storage_type_doc.get("environment")
        if environment:
            if "Cold" in environment:
                multiplier *= 1.5
            elif "Hazardous" in environment:
                multiplier *= 2.0
            elif "Controlled" in environment:
                multiplier *= 1.2
    
    return flt(multiplier)


def _get_computation_details(
    handling_unit: str,
    storage_type: str,
    billing_method: str,
    billing_settings: Dict[str, Any]
) -> Dict[str, Any]:
    """Get detailed computation information."""
    
    return {
        "handling_unit_details": _get_handling_unit_details(handling_unit),
        "storage_type_details": _get_storage_type_details(storage_type),
        "billing_method_details": _get_billing_method_details(billing_method),
        "billing_settings": billing_settings,
        "computation_timestamp": now_datetime().isoformat()
    }


def _get_handling_unit_details(handling_unit: str) -> Dict[str, Any]:
    """Get handling unit details."""
    try:
        hu_doc = frappe.get_doc("Handling Unit", handling_unit)
        return {
            "name": hu_doc.name,
            "volume": hu_doc.volume,
            "weight": hu_doc.weight,
            "status": hu_doc.status,
            "customer": hu_doc.customer,
            "handling_unit_type": hu_doc.handling_unit_type
        }
    except Exception:
        return {"error": "Handling unit not found"}


def _get_storage_type_details(storage_type: str) -> Dict[str, Any]:
    """Get storage type details."""
    try:
        st_doc = frappe.get_doc("Storage Type", storage_type)
        return {
            "name": st_doc.name,
            "description": st_doc.description,
            "environment": st_doc.environment,
            "billing_uom": st_doc.billing_uom,
            "time_unit": st_doc.time_unit,
            "max_capacity": st_doc.max_capacity,
            "capacity_uom": st_doc.capacity_uom
        }
    except Exception:
        return {"error": "Storage type not found"}


def _get_billing_method_details(billing_method: str) -> Dict[str, Any]:
    """Get billing method details."""
    return {
        "method": billing_method,
        "is_time_based": billing_method in ["Per Day", "Per Week", "Per Hour"],
        "is_volume_based": billing_method == "Per Volume",
        "is_weight_based": billing_method == "Per Weight",
        "is_handling_unit_based": billing_method == "Per Handling Unit",
        "is_peak_based": billing_method == "High Water Mark"
    }


# =============================================================================
# Batch Storage Charge Computation
# =============================================================================

@frappe.whitelist()
def compute_batch_storage_charges(
    handling_units: List[str],
    storage_types: List[str],
    billing_methods: List[str],
    date_from: str,
    date_to: str,
    contract_items: List[Dict[str, Any]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Compute storage charges for multiple handling units with different storage types and billing methods.
    
    Args:
        handling_units: List of handling unit names
        storage_types: List of storage types
        billing_methods: List of billing methods
        date_from: Start date
        date_to: End date
        contract_items: List of contract items
        **kwargs: Additional parameters
    
    Returns:
        Dict with batch computation results
    """
    try:
        results = []
        total_charges = 0.0
        
        for i, handling_unit in enumerate(handling_units):
            storage_type = storage_types[i] if i < len(storage_types) else storage_types[0]
            billing_method = billing_methods[i] if i < len(billing_methods) else billing_methods[0]
            contract_item = contract_items[i] if contract_items and i < len(contract_items) else None
            
            # Compute charge for this handling unit
            result = compute_storage_charge_with_type(
                handling_unit=handling_unit,
                storage_type=storage_type,
                billing_method=billing_method,
                date_from=date_from,
                date_to=date_to,
                contract_item=contract_item,
                **kwargs
            )
            
            if result.get("ok"):
                charge_details = result.get("charge_details", {})
                total_charges += flt(charge_details.get("final_quantity", 0))
                results.append({
                    "handling_unit": handling_unit,
                    "storage_type": storage_type,
                    "billing_method": billing_method,
                    "quantity": charge_details.get("final_quantity", 0),
                    "details": charge_details
                })
            else:
                results.append({
                    "handling_unit": handling_unit,
                    "error": result.get("error", "Unknown error"),
                    "quantity": 0
                })
        
        return {
            "ok": True,
            "results": results,
            "total_handling_units": len(handling_units),
            "successful_computations": len([r for r in results if "error" not in r]),
            "total_charges": total_charges,
            "message": f"Batch computation completed: {len(results)} handling units processed"
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "message": f"Error in batch computation: {str(e)}"
        }


# =============================================================================
# Storage Type Analysis
# =============================================================================

@frappe.whitelist()
def analyze_storage_type_billing(
    storage_type: str,
    date_from: str,
    date_to: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Analyze billing patterns for a specific storage type.
    
    Args:
        storage_type: Storage type to analyze
        date_from: Start date
        date_to: End date
        **kwargs: Additional parameters
    
    Returns:
        Dict with analysis results
    """
    try:
        # Get all handling units of this storage type
        handling_units = frappe.get_all("Handling Unit",
            filters={
                "storage_type": storage_type,
                "status": ["in", ["Available", "In Use"]]
            },
            fields=["name", "volume", "weight", "customer"]
        )
        
        if not handling_units:
            return {
                "ok": False,
                "message": f"No handling units found for storage type: {storage_type}"
            }
        
        # Analyze billing patterns
        analysis = {
            "storage_type": storage_type,
            "total_handling_units": len(handling_units),
            "total_volume": sum(flt(hu.get("volume", 0)) for hu in handling_units),
            "total_weight": sum(flt(hu.get("weight", 0)) for hu in handling_units),
            "customers": list(set(hu.get("customer") for hu in handling_units if hu.get("customer"))),
            "date_range": {
                "from": date_from,
                "to": date_to
            },
            "billing_recommendations": _get_billing_recommendations(storage_type, handling_units)
        }
        
        return {
            "ok": True,
            "analysis": analysis,
            "message": f"Storage type analysis completed for {storage_type}"
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": str(e),
            "message": f"Error analyzing storage type: {str(e)}"
        }


def _get_billing_recommendations(storage_type: str, handling_units: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Get billing recommendations based on storage type and handling units."""
    
    recommendations = {
        "recommended_billing_methods": [],
        "billing_considerations": [],
        "rate_suggestions": {}
    }
    
    # Analyze handling units
    total_volume = sum(flt(hu.get("volume", 0)) for hu in handling_units)
    total_weight = sum(flt(hu.get("weight", 0)) for hu in handling_units)
    avg_volume = total_volume / len(handling_units) if handling_units else 0
    avg_weight = total_weight / len(handling_units) if handling_units else 0
    
    # Storage type specific recommendations
    if "Cold" in storage_type:
        recommendations["recommended_billing_methods"] = ["Per Day", "Per Week", "Per Volume"]
        recommendations["billing_considerations"] = [
            "Cold storage requires continuous energy consumption",
            "Consider higher rates for temperature-sensitive items",
            "Weekly billing may be more cost-effective for long-term storage"
        ]
    elif "Hazardous" in storage_type:
        recommendations["recommended_billing_methods"] = ["Per Day", "Per Week", "Per Volume"]
        recommendations["billing_considerations"] = [
            "Hazardous storage requires special handling and compliance",
            "Consider premium rates for safety requirements",
            "Daily billing for short-term hazardous storage"
        ]
    else:
        recommendations["recommended_billing_methods"] = ["Per Day", "Per Week", "Per Volume", "Per Weight"]
        recommendations["billing_considerations"] = [
            "Standard storage rates apply",
            "Consider volume-based billing for large items",
            "Weight-based billing for heavy items"
        ]
    
    # Rate suggestions based on analysis
    if avg_volume > 10:  # Large volume items
        recommendations["rate_suggestions"]["volume_based"] = "Consider volume-based rates for large items"
    if avg_weight > 100:  # Heavy items
        recommendations["rate_suggestions"]["weight_based"] = "Consider weight-based rates for heavy items"
    
    return recommendations
