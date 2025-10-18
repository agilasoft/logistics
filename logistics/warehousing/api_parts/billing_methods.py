#!/usr/bin/env python3
"""
Comprehensive Billing Methods Implementation

This module provides complete billing method calculations for all warehouse operations:
- Per Day, Per Volume, Per Weight, Per Piece, Per Container, Per Hour, Per Handling Unit, High Water Mark
"""

from __future__ import annotations
import frappe
from frappe import _
from frappe.utils import flt, getdate, get_datetime, now_datetime, add_days
from typing import Dict, List, Any, Optional, Tuple
from datetime import date, datetime, timedelta
import json

# =============================================================================
# Billing Method Calculation Functions
# =============================================================================

def get_billing_quantity(
    context: str,
    billing_method: str,
    reference_doc: str,
    date_from: str = None,
    date_to: str = None,
    **kwargs
) -> float:
    """
    Get billing quantity based on the specified billing method.
    
    Args:
        context: Charge context (storage, inbound, outbound, transfer, vas, stocktake)
        billing_method: Billing method (Per Day, Per Volume, Per Weight, etc.)
        reference_doc: Reference document (handling_unit, warehouse_job, order, etc.)
        date_from: Start date for calculation
        date_to: End date for calculation
        **kwargs: Additional parameters for specific billing methods
    
    Returns:
        Billing quantity for the specified method
    """
    if not billing_method or billing_method == "Per Day":
        return get_per_day_quantity(reference_doc, date_from, date_to, context)
    
    elif billing_method == "Per Week":
        return get_per_week_quantity(reference_doc, date_from, date_to, context, **kwargs)
    
    elif billing_method == "Per Volume":
        return get_per_volume_quantity(reference_doc, date_from, date_to, context, **kwargs)
    
    elif billing_method == "Per Weight":
        return get_per_weight_quantity(reference_doc, date_from, date_to, context, **kwargs)
    
    elif billing_method == "Per Piece":
        return get_per_piece_quantity(reference_doc, date_from, date_to, context, **kwargs)
    
    elif billing_method == "Per Container":
        return get_per_container_quantity(reference_doc, date_from, date_to, context, **kwargs)
    
    elif billing_method == "Per Hour":
        return get_per_hour_quantity(reference_doc, date_from, date_to, context, **kwargs)
    
    elif billing_method == "Per Handling Unit":
        return get_per_handling_unit_quantity(reference_doc, date_from, date_to, context, **kwargs)
    
    elif billing_method == "High Water Mark":
        return get_high_water_mark_quantity(reference_doc, date_from, date_to, context, **kwargs)
    
    else:
        frappe.throw(f"Unsupported billing method: {billing_method}")


def get_per_day_quantity(reference_doc: str, date_from: str, date_to: str, context: str) -> float:
    """Calculate Per Day billing quantity."""
    if not date_from or not date_to:
        return 1.0
    
    start_date = getdate(date_from)
    end_date = getdate(date_to)
    days = (end_date - start_date).days + 1
    
    # For storage context, count actual days with stock
    if context == "storage":
        return _count_storage_days(reference_doc, date_from, date_to)
    
    return float(days)


def get_per_week_quantity(reference_doc: str, date_from: str, date_to: str, context: str, **kwargs) -> float:
    """Calculate Per Week billing quantity."""
    if not date_from or not date_to:
        return 1.0
    
    start_date = getdate(date_from)
    end_date = getdate(date_to)
    days = (end_date - start_date).days + 1
    weeks = days / 7.0
    
    # Apply billing time settings
    billing_time_multiplier = kwargs.get('billing_time_multiplier', 1.0)
    minimum_billing_time = kwargs.get('minimum_billing_time', 1.0)
    
    # Apply minimum billing time
    weeks = max(weeks, minimum_billing_time)
    
    # Apply multiplier
    weeks *= billing_time_multiplier
    
    # For storage context, count actual weeks with stock
    if context == "storage":
        storage_days = _count_storage_days(reference_doc, date_from, date_to)
        storage_weeks = storage_days / 7.0
        storage_weeks = max(storage_weeks, minimum_billing_time)
        return storage_weeks * billing_time_multiplier
    
    return weeks


def get_per_hour_quantity(reference_doc: str, date_from: str, date_to: str, context: str, **kwargs) -> float:
    """Calculate Per Hour billing quantity."""
    if not date_from or not date_to:
        return 1.0
    
    start_datetime = get_datetime(date_from)
    end_datetime = get_datetime(date_to)
    hours = (end_datetime - start_datetime).total_seconds() / 3600.0
    
    # Apply billing time settings
    billing_time_multiplier = kwargs.get('billing_time_multiplier', 1.0)
    minimum_billing_time = kwargs.get('minimum_billing_time', 1.0)
    
    # Apply minimum billing time
    hours = max(hours, minimum_billing_time)
    
    # Apply multiplier
    hours *= billing_time_multiplier
    
    # For storage context, count actual hours with stock
    if context == "storage":
        storage_days = _count_storage_days(reference_doc, date_from, date_to)
        storage_hours = storage_days * 24.0
        storage_hours = max(storage_hours, minimum_billing_time)
        return storage_hours * billing_time_multiplier
    
    return hours


def get_per_volume_quantity(reference_doc: str, date_from: str, date_to: str, context: str, **kwargs) -> float:
    """Calculate Per Volume billing quantity."""
    volume_calculation_method = kwargs.get('volume_calculation_method', 'Daily Volume')
    
    if context == "storage":
        return _get_storage_volume_quantity(reference_doc, date_from, date_to, volume_calculation_method)
    else:
        return _get_operation_volume_quantity(reference_doc, date_from, date_to, context, volume_calculation_method)


def get_per_weight_quantity(reference_doc: str, date_from: str, date_to: str, context: str, **kwargs) -> float:
    """Calculate Per Weight billing quantity."""
    if context == "storage":
        return _get_storage_weight_quantity(reference_doc, date_from, date_to)
    else:
        return _get_operation_weight_quantity(reference_doc, date_from, date_to, context)


def get_per_piece_quantity(reference_doc: str, date_from: str, date_to: str, context: str, **kwargs) -> float:
    """Calculate Per Piece billing quantity."""
    if context == "storage":
        return _get_storage_piece_quantity(reference_doc, date_from, date_to)
    else:
        return _get_operation_piece_quantity(reference_doc, date_from, date_to, context)


def get_per_container_quantity(reference_doc: str, date_from: str, date_to: str, context: str, **kwargs) -> float:
    """Calculate Per Container billing quantity."""
    return _get_container_quantity(reference_doc, date_from, date_to, context)


# Removed duplicate function - using the enhanced version above


def get_per_handling_unit_quantity(reference_doc: str, date_from: str, date_to: str, context: str, **kwargs) -> float:
    """Calculate Per Handling Unit billing quantity."""
    if context == "storage":
        return _get_storage_handling_unit_quantity(reference_doc, date_from, date_to)
    else:
        return _get_operation_handling_unit_quantity(reference_doc, date_from, date_to, context)


def get_high_water_mark_quantity(reference_doc: str, date_from: str, date_to: str, context: str, **kwargs) -> float:
    """Calculate High Water Mark billing quantity."""
    if context == "storage":
        return _get_storage_high_water_mark_quantity(reference_doc, date_from, date_to)
    else:
        return _get_operation_high_water_mark_quantity(reference_doc, date_from, date_to, context)


# =============================================================================
# Storage Billing Calculations
# =============================================================================

def _count_storage_days(handling_unit: str, date_from: str, date_to: str) -> float:
    """Count actual days with stock in storage."""
    if not handling_unit:
        return 0.0
    
    # Get days with positive stock
    days_data = frappe.db.sql("""
        SELECT COUNT(DISTINCT posting_date) as days
        FROM `tabWarehouse Stock Ledger`
        WHERE handling_unit = %s
          AND posting_date BETWEEN %s AND %s
          AND quantity > 0
    """, (handling_unit, date_from, date_to), as_dict=True)
    
    return flt(days_data[0].days) if days_data else 0.0


def _get_storage_volume_quantity(handling_unit: str, date_from: str, date_to: str, calculation_method: str) -> float:
    """Get storage volume quantity based on calculation method."""
    if not handling_unit:
        return 0.0
    
    # Import volume billing functions
    from .volume_billing import calculate_volume_usage
    
    volume_data = calculate_volume_usage(handling_unit, date_from, date_to, calculation_method)
    
    if calculation_method == "Daily Volume":
        return flt(volume_data.get("total_volume", 0))
    elif calculation_method == "Peak Volume":
        return flt(volume_data.get("peak_volume", 0))
    elif calculation_method == "Average Volume":
        return flt(volume_data.get("average_volume", 0))
    elif calculation_method == "End Volume":
        return flt(volume_data.get("end_volume", 0))
    else:
        return flt(volume_data.get("total_volume", 0))


def _get_storage_weight_quantity(handling_unit: str, date_from: str, date_to: str) -> float:
    """Get storage weight quantity."""
    if not handling_unit:
        return 0.0
    
    # Get total weight from stock ledger
    weight_data = frappe.db.sql("""
        SELECT SUM(ABS(quantity) * COALESCE(wi.weight, 0)) as total_weight
        FROM `tabWarehouse Stock Ledger` l
        LEFT JOIN `tabWarehouse Item` wi ON wi.name = l.item
        WHERE l.handling_unit = %s
          AND l.posting_date BETWEEN %s AND %s
          AND l.quantity > 0
    """, (handling_unit, date_from, date_to), as_dict=True)
    
    return flt(weight_data[0].total_weight) if weight_data else 0.0


def _get_storage_piece_quantity(handling_unit: str, date_from: str, date_to: str) -> float:
    """Get storage piece quantity."""
    if not handling_unit:
        return 0.0
    
    # Get total pieces from stock ledger
    piece_data = frappe.db.sql("""
        SELECT SUM(ABS(quantity)) as total_pieces
        FROM `tabWarehouse Stock Ledger`
        WHERE handling_unit = %s
          AND posting_date BETWEEN %s AND %s
          AND quantity > 0
    """, (handling_unit, date_from, date_to), as_dict=True)
    
    return flt(piece_data[0].total_pieces) if piece_data else 0.0


def _get_storage_handling_unit_quantity(handling_unit: str, date_from: str, date_to: str) -> float:
    """Get storage handling unit quantity (always 1 for a single handling unit)."""
    return 1.0 if handling_unit else 0.0


def _get_storage_high_water_mark_quantity(handling_unit: str, date_from: str, date_to: str) -> float:
    """Get storage high water mark quantity (peak volume)."""
    return _get_storage_volume_quantity(handling_unit, date_from, date_to, "Peak Volume")


# =============================================================================
# Operation Billing Calculations
# =============================================================================

def _get_operation_volume_quantity(reference_doc: str, date_from: str, date_to: str, context: str, calculation_method: str) -> float:
    """Get operation volume quantity."""
    # For operations, volume is calculated from order items or job items
    if context in ["inbound", "outbound"]:
        return _get_order_volume_quantity(reference_doc, context)
    elif context == "vas":
        return _get_vas_volume_quantity(reference_doc)
    else:
        return _get_job_volume_quantity(reference_doc, context)


def _get_operation_weight_quantity(reference_doc: str, date_from: str, date_to: str, context: str) -> float:
    """Get operation weight quantity."""
    if context in ["inbound", "outbound"]:
        return _get_order_weight_quantity(reference_doc, context)
    elif context == "vas":
        return _get_vas_weight_quantity(reference_doc)
    else:
        return _get_job_weight_quantity(reference_doc, context)


def _get_operation_piece_quantity(reference_doc: str, date_from: str, date_to: str, context: str) -> float:
    """Get operation piece quantity."""
    if context in ["inbound", "outbound"]:
        return _get_order_piece_quantity(reference_doc, context)
    elif context == "vas":
        return _get_vas_piece_quantity(reference_doc)
    else:
        return _get_job_piece_quantity(reference_doc, context)


def _get_operation_handling_unit_quantity(reference_doc: str, date_from: str, date_to: str, context: str) -> float:
    """Get operation handling unit quantity."""
    if context in ["inbound", "outbound"]:
        return _get_order_handling_unit_quantity(reference_doc, context)
    elif context == "vas":
        return _get_vas_handling_unit_quantity(reference_doc)
    else:
        return _get_job_handling_unit_quantity(reference_doc, context)


def _get_operation_high_water_mark_quantity(reference_doc: str, date_from: str, date_to: str, context: str) -> float:
    """Get operation high water mark quantity."""
    # For operations, high water mark is typically the peak volume during the operation
    return _get_operation_volume_quantity(reference_doc, date_from, date_to, context, "Peak Volume")


# =============================================================================
# Order-based Calculations
# =============================================================================

def _get_order_volume_quantity(order_name: str, context: str) -> float:
    """Get volume quantity from order items."""
    if context == "inbound":
        table_name = "Inbound Order Item"
    elif context == "outbound":
        table_name = "Outbound Order Item"
    else:
        return 0.0
    
    volume_data = frappe.db.sql(f"""
        SELECT SUM(quantity * COALESCE(volume, 0)) as total_volume
        FROM `tab{table_name}`
        WHERE parent = %s
    """, (order_name,), as_dict=True)
    
    return flt(volume_data[0].total_volume) if volume_data else 0.0


def _get_order_weight_quantity(order_name: str, context: str) -> float:
    """Get weight quantity from order items."""
    if context == "inbound":
        table_name = "Inbound Order Item"
    elif context == "outbound":
        table_name = "Outbound Order Item"
    else:
        return 0.0
    
    weight_data = frappe.db.sql(f"""
        SELECT SUM(quantity * COALESCE(weight, 0)) as total_weight
        FROM `tab{table_name}`
        WHERE parent = %s
    """, (order_name,), as_dict=True)
    
    return flt(weight_data[0].total_weight) if weight_data else 0.0


def _get_order_piece_quantity(order_name: str, context: str) -> float:
    """Get piece quantity from order items."""
    if context == "inbound":
        table_name = "Inbound Order Item"
    elif context == "outbound":
        table_name = "Outbound Order Item"
    else:
        return 0.0
    
    piece_data = frappe.db.sql(f"""
        SELECT SUM(quantity) as total_pieces
        FROM `tab{table_name}`
        WHERE parent = %s
    """, (order_name,), as_dict=True)
    
    return flt(piece_data[0].total_pieces) if piece_data else 0.0


def _get_order_handling_unit_quantity(order_name: str, context: str) -> float:
    """Get handling unit quantity from order."""
    # Count unique handling units in the order
    if context == "inbound":
        table_name = "Inbound Order Item"
    elif context == "outbound":
        table_name = "Outbound Order Item"
    else:
        return 0.0
    
    hu_data = frappe.db.sql(f"""
        SELECT COUNT(DISTINCT handling_unit) as total_hus
        FROM `tab{table_name}`
        WHERE parent = %s AND handling_unit IS NOT NULL
    """, (order_name,), as_dict=True)
    
    return flt(hu_data[0].total_hus) if hu_data else 0.0


# =============================================================================
# VAS Calculations
# =============================================================================

def _get_vas_volume_quantity(vas_order: str) -> float:
    """Get VAS volume quantity."""
    volume_data = frappe.db.sql("""
        SELECT SUM(quantity * COALESCE(volume, 0)) as total_volume
        FROM `tabVAS Order Item`
        WHERE parent = %s
    """, (vas_order,), as_dict=True)
    
    return flt(volume_data[0].total_volume) if volume_data else 0.0


def _get_vas_weight_quantity(vas_order: str) -> float:
    """Get VAS weight quantity."""
    weight_data = frappe.db.sql("""
        SELECT SUM(quantity * COALESCE(weight, 0)) as total_weight
        FROM `tabVAS Order Item`
        WHERE parent = %s
    """, (vas_order,), as_dict=True)
    
    return flt(weight_data[0].total_weight) if weight_data else 0.0


def _get_vas_piece_quantity(vas_order: str) -> float:
    """Get VAS piece quantity."""
    piece_data = frappe.db.sql("""
        SELECT SUM(quantity) as total_pieces
        FROM `tabVAS Order Item`
        WHERE parent = %s
    """, (vas_order,), as_dict=True)
    
    return flt(piece_data[0].total_pieces) if piece_data else 0.0


def _get_vas_handling_unit_quantity(vas_order: str) -> float:
    """Get VAS handling unit quantity."""
    hu_data = frappe.db.sql("""
        SELECT COUNT(DISTINCT handling_unit) as total_hus
        FROM `tabVAS Order Item`
        WHERE parent = %s AND handling_unit IS NOT NULL
    """, (vas_order,), as_dict=True)
    
    return flt(hu_data[0].total_hus) if hu_data else 0.0


# =============================================================================
# Job Calculations
# =============================================================================

def _get_job_volume_quantity(job_name: str, context: str) -> float:
    """Get job volume quantity."""
    volume_data = frappe.db.sql("""
        SELECT SUM(quantity * COALESCE(volume, 0)) as total_volume
        FROM `tabWarehouse Job Item`
        WHERE parent = %s
    """, (job_name,), as_dict=True)
    
    return flt(volume_data[0].total_volume) if volume_data else 0.0


def _get_job_weight_quantity(job_name: str, context: str) -> float:
    """Get job weight quantity."""
    weight_data = frappe.db.sql("""
        SELECT SUM(quantity * COALESCE(weight, 0)) as total_weight
        FROM `tabWarehouse Job Item`
        WHERE parent = %s
    """, (job_name,), as_dict=True)
    
    return flt(weight_data[0].total_weight) if weight_data else 0.0


def _get_job_piece_quantity(job_name: str, context: str) -> float:
    """Get job piece quantity."""
    piece_data = frappe.db.sql("""
        SELECT SUM(quantity) as total_pieces
        FROM `tabWarehouse Job Item`
        WHERE parent = %s
    """, (job_name,), as_dict=True)
    
    return flt(piece_data[0].total_pieces) if piece_data else 0.0


def _get_job_handling_unit_quantity(job_name: str, context: str) -> float:
    """Get job handling unit quantity."""
    hu_data = frappe.db.sql("""
        SELECT COUNT(DISTINCT handling_unit) as total_hus
        FROM `tabWarehouse Job Item`
        WHERE parent = %s AND handling_unit IS NOT NULL
    """, (job_name,), as_dict=True)
    
    return flt(hu_data[0].total_hus) if hu_data else 0.0


# =============================================================================
# Container and Hour Calculations
# =============================================================================

def _get_container_quantity(reference_doc: str, date_from: str, date_to: str, context: str) -> float:
    """Get container quantity."""
    # This would depend on how containers are tracked in your system
    # For now, return 1 as a placeholder
    return 1.0


def _get_hour_quantity(reference_doc: str, date_from: str, date_to: str, context: str) -> float:
    """Get hour quantity."""
    # Calculate hours based on operation duration
    if not date_from or not date_to:
        return 1.0
    
    start_time = get_datetime(date_from)
    end_time = get_datetime(date_to)
    hours = (end_time - start_time).total_seconds() / 3600
    
    return max(1.0, flt(hours))


# =============================================================================
# Charge Line Creation
# =============================================================================

def create_charge_line(
    contract_item: Dict[str, Any],
    billing_quantity: float,
    context: str,
    reference_doc: str = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Create a charge line based on contract item and billing quantity.
    
    Args:
        contract_item: Contract item data
        billing_quantity: Calculated billing quantity
        context: Charge context
        reference_doc: Reference document
        **kwargs: Additional parameters
    
    Returns:
        Charge line data
    """
    if not contract_item or billing_quantity <= 0:
        return {}
    
    rate = flt(contract_item.get("rate", 0))
    currency = contract_item.get("currency", "USD")
    total = billing_quantity * rate
    
    charge_line = {
        "item_code": contract_item.get("item_charge"),
        "item_name": contract_item.get("description", ""),
        "uom": _get_billing_uom(contract_item, context),
        "quantity": billing_quantity,
        "currency": currency,
        "rate": rate,
        "total": total,
        "billing_method": _get_billing_method_from_contract(contract_item, context),
    }
    
    # Add method-specific fields
    if _get_billing_method_from_contract(contract_item, context) == "Per Volume":
        charge_line.update({
            "volume_quantity": billing_quantity,
            "volume_uom": contract_item.get("volume_uom")
        })
    
    return charge_line


def _get_billing_uom(contract_item: Dict[str, Any], context: str) -> str:
    """Get appropriate UOM for billing."""
    billing_method = _get_billing_method_from_contract(contract_item, context)
    
    if billing_method == "Per Volume":
        return contract_item.get("volume_uom", "CBM")
    elif context == "storage":
        return contract_item.get("billing_time_unit", "Day")
    else:
        return contract_item.get("uom", "Nos")


def _get_billing_method_from_contract(contract_item: Dict[str, Any], context: str) -> str:
    """Get billing method from contract item based on context."""
    # Use the single billing_method field for all contexts
    return contract_item.get("billing_method", "Per Volume")


# =============================================================================
# API Functions
# =============================================================================

@frappe.whitelist()
def calculate_charges_by_billing_method(
    contract: str,
    context: str,
    reference_doc: str,
    date_from: str = None,
    date_to: str = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Calculate charges using the appropriate billing method.
    
    Args:
        contract: Warehouse Contract name
        context: Charge context (storage, inbound, outbound, etc.)
        reference_doc: Reference document
        date_from: Start date
        date_to: End date
        **kwargs: Additional parameters
    
    Returns:
        Dict with charge calculation results
    """
    try:
        # Get contract items for the context
        contract_items = _get_contract_items_for_context(contract, context)
        
        if not contract_items:
            return {"error": f"No contract items found for {context} charges"}
        
        created_charges = 0
        total_amount = 0.0
        charges = []
        
        for contract_item in contract_items:
            billing_method = _get_billing_method_from_contract(contract_item, context)
            
            # Get billing quantity
            billing_quantity = get_billing_quantity(
                context=context,
                billing_method=billing_method,
                reference_doc=reference_doc,
                date_from=date_from,
                date_to=date_to,
                **kwargs
            )
            
            if billing_quantity > 0:
                # Create charge line
                charge_line = create_charge_line(
                    contract_item=contract_item,
                    billing_quantity=billing_quantity,
                    context=context,
                    reference_doc=reference_doc,
                    **kwargs
                )
                
                if charge_line:
                    charges.append(charge_line)
                    created_charges += 1
                    total_amount += flt(charge_line.get("total", 0))
        
        return {
            "ok": True,
            "message": f"Created {created_charges} charge(s) using {billing_method} billing",
            "created_charges": created_charges,
            "total_amount": total_amount,
            "charges": charges
        }
        
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)
        }


def _get_contract_items_for_context(contract: str, context: str) -> List[Dict[str, Any]]:
    """Get contract items for the specified context."""
    context_flag = {
        "storage": "storage_charge",
        "inbound": "inbound_charge", 
        "outbound": "outbound_charge",
        "transfer": "transfer_charge",
        "vas": "vas_charge",
        "stocktake": "stocktake_charge"
    }
    
    flag = context_flag.get(context)
    if not flag:
        return []
    
    filters = {
        "parent": contract,
        "parenttype": "Warehouse Contract",
        flag: 1
    }
    
    fields = [
        "item_charge", "description", "rate", "currency",
        "billing_time_unit", "uom", "billing_time_multiplier", "minimum_billing_time",
        "billing_method",
        "volume_uom", "volume_calculation_method"
    ]
    
    return frappe.get_all("Warehouse Contract Item", filters=filters, fields=fields, ignore_permissions=True)
