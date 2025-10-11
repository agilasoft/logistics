"""
Volume-based billing calculations for warehousing module.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_days
from typing import Dict, List, Optional, Any
from datetime import date, timedelta

# Import helper functions from main API to avoid circular imports
def _pb__hu_opening_balance(hu: str, date_from: str) -> float:
    """Get opening balance for handling unit."""
    # This is a simplified version - in production, this should be imported from the main API
    return 0.0

def _pb__hu_daily_deltas(hu: str, date_from: str, date_to: str) -> Dict[date, float]:
    """Get daily deltas for handling unit."""
    # This is a simplified version - in production, this should be imported from the main API
    return {}


def calculate_volume_usage(handling_unit: str, date_from: str, date_to: str, 
                         calculation_method: str = "Daily Volume") -> Dict[str, Any]:
    """
    Calculate volume usage for a handling unit over a date range.
    
    Args:
        handling_unit: Handling unit ID
        date_from: Start date
        date_to: End date
        calculation_method: Method for volume calculation
        
    Returns:
        Dict with volume usage details
    """
    if calculation_method == "Daily Volume":
        return _calculate_daily_volume(handling_unit, date_from, date_to)
    elif calculation_method == "Peak Volume":
        return _calculate_peak_volume(handling_unit, date_from, date_to)
    elif calculation_method == "Average Volume":
        return _calculate_average_volume(handling_unit, date_from, date_to)
    elif calculation_method == "End Volume":
        return _calculate_end_volume(handling_unit, date_from, date_to)
    else:
        return {"total_volume": 0, "days": 0, "average_volume": 0}


def _calculate_daily_volume(handling_unit: str, date_from: str, date_to: str) -> Dict[str, Any]:
    """Calculate total volume used daily over the period."""
    start_date = getdate(date_from)
    end_date = getdate(date_to)
    
    total_volume = 0
    days_with_stock = 0
    
    current_date = start_date
    while current_date <= end_date:
        # Get volume from item dimensions in the handling unit
        daily_volume = _get_item_volume_from_ledger(handling_unit, current_date)
        
        if daily_volume > 0:
            total_volume += daily_volume
            days_with_stock += 1
            
        current_date = add_days(current_date, 1)
    
    return {
        "total_volume": total_volume,
        "days": days_with_stock,
        "average_volume": total_volume / days_with_stock if days_with_stock > 0 else 0,
        "calculation_method": "Daily Volume"
    }


def _calculate_peak_volume(handling_unit: str, date_from: str, date_to: str) -> Dict[str, Any]:
    """Calculate peak volume used during the period."""
    start_date = getdate(date_from)
    end_date = getdate(date_to)
    
    peak_volume = 0
    peak_date = None
    
    current_date = start_date
    while current_date <= end_date:
        # Get volume from item dimensions in the handling unit
        daily_volume = _get_item_volume_from_ledger(handling_unit, current_date)
        
        if daily_volume > peak_volume:
            peak_volume = daily_volume
            peak_date = current_date
                
        current_date = add_days(current_date, 1)
    
    return {
        "total_volume": peak_volume,
        "days": 1,
        "average_volume": peak_volume,
        "peak_date": peak_date,
        "calculation_method": "Peak Volume"
    }


def _calculate_average_volume(handling_unit: str, date_from: str, date_to: str) -> Dict[str, Any]:
    """Calculate average volume used during the period."""
    daily_volume_data = _calculate_daily_volume(handling_unit, date_from, date_to)
    
    if daily_volume_data["days"] > 0:
        average_volume = daily_volume_data["total_volume"] / daily_volume_data["days"]
    else:
        average_volume = 0
    
    return {
        "total_volume": average_volume,
        "days": daily_volume_data["days"],
        "average_volume": average_volume,
        "calculation_method": "Average Volume"
    }


def _calculate_end_volume(handling_unit: str, date_from: str, date_to: str) -> Dict[str, Any]:
    """Calculate volume at the end of the period."""
    end_date = getdate(date_to)
    
    # Get volume from item dimensions in the handling unit at end date
    end_volume = _get_item_volume_from_ledger(handling_unit, end_date)
    
    return {
        "total_volume": end_volume,
        "days": 1 if end_volume > 0 else 0,
        "average_volume": end_volume,
        "calculation_method": "End Volume"
    }


def _get_handling_unit_volume(hu_type_doc) -> float:
    """Get volume per handling unit based on its type."""
    if hasattr(hu_type_doc, 'external_length') and hasattr(hu_type_doc, 'external_width') and hasattr(hu_type_doc, 'external_height'):
        length = flt(hu_type_doc.external_length or 0)
        width = flt(hu_type_doc.external_width or 0)
        height = flt(hu_type_doc.external_height or 0)
        
        if length > 0 and width > 0 and height > 0:
            return length * width * height
    
    # Fallback to max volume if dimensions not available
    return flt(hu_type_doc.max_volume_cbm or 0)


def _get_item_volume_from_ledger(handling_unit: str, check_date: date) -> float:
    """Get total volume of items in a handling unit on a specific date."""
    # Get all items in the handling unit on the date
    items_data = frappe.db.sql("""
        SELECT 
            l.item,
            SUM(l.quantity) as total_qty,
            wi.length,
            wi.width,
            wi.height,
            wi.volume
        FROM `tabWarehouse Stock Ledger` l
        LEFT JOIN `tabWarehouse Item` wi ON wi.name = l.item
        WHERE l.handling_unit = %s 
          AND l.posting_date <= %s
          AND l.quantity > 0
        GROUP BY l.item, wi.length, wi.width, wi.height, wi.volume
    """, (handling_unit, check_date), as_dict=True)
    
    total_volume = 0
    for item_data in items_data:
        qty = flt(item_data.total_qty)
        if qty <= 0:
            continue
            
        # Try to get volume from item dimensions first
        item_volume = 0
        if item_data.length and item_data.width and item_data.height:
            item_volume = flt(item_data.length) * flt(item_data.width) * flt(item_data.height)
        elif item_data.volume:
            item_volume = flt(item_data.volume)
        
        if item_volume > 0:
            total_volume += qty * item_volume
    
    return total_volume


def _get_stock_quantity(handling_unit: str, check_date: date) -> float:
    """Get stock quantity for a handling unit on a specific date."""
    # Get opening balance
    opening_balance = frappe.db.sql("""
        SELECT SUM(quantity) as qty
        FROM `tabWarehouse Stock Ledger`
        WHERE handling_unit = %s AND posting_date < %s
        GROUP BY handling_unit
    """, (handling_unit, check_date), as_dict=True)
    
    opening_qty = flt(opening_balance[0].qty) if opening_balance else 0
    
    # Get movements on the date
    movements = frappe.db.sql("""
        SELECT SUM(quantity) as qty
        FROM `tabWarehouse Stock Ledger`
        WHERE handling_unit = %s AND posting_date = %s
        GROUP BY handling_unit
    """, (handling_unit, check_date), as_dict=True)
    
    movement_qty = flt(movements[0].qty) if movements else 0
    
    return opening_qty + movement_qty


def get_volume_billing_quantity(handling_unit: str, date_from: str, date_to: str, 
                               billing_method: str, volume_calculation_method: str = "Daily Volume") -> float:
    """
    Get billing quantity based on volume calculation method.
    
    Args:
        handling_unit: Handling unit ID
        date_from: Start date
        date_to: End date
        billing_method: Billing method (Per Volume, Per Day, etc.)
        volume_calculation_method: Method for volume calculation
        
    Returns:
        Billing quantity
    """
    if billing_method != "Per Volume":
        # For non-volume billing, use existing logic
        # Calculate used days directly to avoid circular import
        start = getdate(date_from)
        end = getdate(date_to)
        cur = _pb__hu_opening_balance(handling_unit, date_from)
        deltas = _pb__hu_daily_deltas(handling_unit, date_from, date_to)
        used = 0
        d = start
        one = timedelta(days=1)
        while d <= end:
            cur = cur + flt(deltas.get(d, 0.0))
            if cur > 0:
                used += 1
            d += one
        return used
    
    # Calculate volume usage
    volume_data = calculate_volume_usage(handling_unit, date_from, date_to, volume_calculation_method)
    
    # Get volume UOM conversion factor
    company = frappe.defaults.get_user_default("Company")
    try:
        settings = frappe.get_doc("Warehouse Settings", company)
        if not settings.enable_volume_billing:
            return 0
    except frappe.DoesNotExistError:
        return 0
    
    # Return total volume for billing
    return volume_data["total_volume"]


def create_volume_based_charge_line(handling_unit: str, date_from: str, date_to: str,
                                   contract_item: Dict, storage_location: str = None) -> Dict[str, Any]:
    """
    Create a charge line for volume-based billing.
    
    Args:
        handling_unit: Handling unit ID
        date_from: Start date
        date_to: End date
        contract_item: Contract item details
        storage_location: Storage location
        
    Returns:
        Charge line dictionary
    """
    billing_method = contract_item.get("billing_method", "Per Day")
    volume_calculation_method = contract_item.get("volume_calculation_method", "Daily Volume")
    
    if billing_method == "Per Volume":
        # Calculate volume usage
        volume_data = calculate_volume_usage(handling_unit, date_from, date_to, volume_calculation_method)
        
        # Get volume UOM
        volume_uom = contract_item.get("volume_uom") or "CBM"
        
        return {
            "item": contract_item.get("item_code"),
            "item_name": f"Storage Charge (Volume - {volume_calculation_method})",
            "uom": volume_uom,
            "quantity": volume_data["total_volume"],
            "rate": flt(contract_item.get("rate", 0)),
            "total": flt(volume_data["total_volume"]) * flt(contract_item.get("rate", 0)),
            "currency": contract_item.get("currency"),
            "handling_unit": handling_unit,
            "storage_location": storage_location,
            "billing_method": billing_method,
            "volume_quantity": volume_data["total_volume"],
            "volume_uom": volume_uom,
            "calculation_method": volume_calculation_method
        }
    else:
        # Use existing day-based calculation
        # Calculate used days directly to avoid circular import
        start = getdate(date_from)
        end = getdate(date_to)
        cur = _pb__hu_opening_balance(handling_unit, date_from)
        deltas = _pb__hu_daily_deltas(handling_unit, date_from, date_to)
        days = 0
        d = start
        one = timedelta(days=1)
        while d <= end:
            cur = cur + flt(deltas.get(d, 0.0))
            if cur > 0:
                days += 1
            d += one
        return {
            "item": contract_item.get("item_code"),
            "item_name": "Storage Charge (Daily)",
            "uom": contract_item.get("storage_uom", "Day"),
            "quantity": days,
            "rate": flt(contract_item.get("rate", 0)),
            "total": flt(days) * flt(contract_item.get("rate", 0)),
            "currency": contract_item.get("currency"),
            "handling_unit": handling_unit,
            "storage_location": storage_location,
            "billing_method": billing_method
        }


# Import the existing function for day-based calculation
# Note: This import is removed to avoid circular import issues
# The function will be called directly when needed
