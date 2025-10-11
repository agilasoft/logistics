#!/usr/bin/env python3
"""
Comprehensive Periodic Billing Implementation

This module provides complete periodic billing functionality supporting all billing methods:
- Per Day, Per Volume, Per Weight, Per Piece, Per Container, Per Hour, Per Handling Unit, High Water Mark
"""

from __future__ import annotations
import frappe
from frappe import _
from frappe.utils import flt, getdate, get_datetime, now_datetime, add_days
from typing import Dict, List, Any, Optional, Tuple
from datetime import date, datetime, timedelta
import json

# Import billing methods
from .billing_methods import get_billing_quantity, create_charge_line, _get_billing_method_from_contract

# =============================================================================
# Comprehensive Periodic Billing
# =============================================================================

@frappe.whitelist()
def periodic_billing_get_comprehensive_charges(periodic_billing: str, clear_existing: int = 1) -> Dict[str, Any]:
    """
    Comprehensive periodic billing function that supports all billing methods.
    
    Args:
        periodic_billing: Periodic Billing document name
        clear_existing: Clear existing charges before creating new ones
    
    Returns:
        Dict with billing results
    """
    try:
        # Get periodic billing document
        pb_doc = frappe.get_doc("Periodic Billing", periodic_billing)
        if not pb_doc:
            return {"error": "Periodic Billing not found"}
        
        # Clear existing charges if requested
        if clear_existing:
            pb_doc.set("charges", [])
        
        # Get billing parameters
        customer = pb_doc.customer
        date_from = pb_doc.date_from
        date_to = pb_doc.date_to
        company = pb_doc.company
        branch = pb_doc.branch
        
        if not customer:
            return {"error": "Customer is required"}
        
        # Get customer contract
        contract = _get_customer_contract(customer, company, branch)
        if not contract:
            return {"error": f"No contract found for customer {customer}"}
        
        # Get all handling units for the customer
        hu_list = _get_customer_handling_units(customer, date_to, company, branch)
        
        if not hu_list:
            return {"message": "No handling units found for this customer"}
        
        created_charges = 0
        total_amount = 0.0
        warnings = []
        
        # Process each handling unit
        for hu in hu_list:
            hu_charges = _calculate_handling_unit_charges(
                contract=contract,
                handling_unit=hu,
                date_from=date_from,
                date_to=date_to,
                company=company,
                branch=branch
            )
            
            if hu_charges:
                for charge in hu_charges:
                    pb_doc.append("charges", charge)
                    created_charges += 1
                    total_amount += flt(charge.get("total", 0))
        
        # Save the document
        if created_charges > 0:
            pb_doc.save()
            frappe.db.commit()
        
        return {
            "ok": True,
            "message": f"Created {created_charges} charge(s). Total: {total_amount}",
            "created_charges": created_charges,
            "total_amount": total_amount,
            "warnings": warnings
        }
        
    except Exception as e:
        frappe.log_error(f"Error in periodic_billing_get_comprehensive_charges: {str(e)}")
        return {"error": str(e)}


def _get_customer_contract(customer: str, company: str = None, branch: str = None) -> Optional[str]:
    """Get customer's warehouse contract."""
    filters = {
        "customer": customer,
        "status": "Active"
    }
    
    if company:
        filters["company"] = company
    if branch:
        filters["branch"] = branch
    
    contracts = frappe.get_all(
        "Warehouse Contract",
        filters=filters,
        fields=["name"],
        order_by="creation desc",
        limit=1
    )
    
    return contracts[0].name if contracts else None


def _get_customer_handling_units(customer: str, date_to: str, company: str = None, branch: str = None) -> List[str]:
    """Get all handling units for a customer."""
    # Get handling units from stock ledger
    hu_data = frappe.db.sql("""
        SELECT DISTINCT l.handling_unit
        FROM `tabWarehouse Stock Ledger` l
        LEFT JOIN `tabHandling Unit` hu ON hu.name = l.handling_unit
        WHERE l.posting_date <= %s
          AND l.handling_unit IS NOT NULL
          AND hu.customer = %s
    """, (date_to, customer), as_dict=True)
    
    return [row.handling_unit for row in hu_data if row.handling_unit]


def _calculate_handling_unit_charges(
    contract: str,
    handling_unit: str,
    date_from: str,
    date_to: str,
    company: str = None,
    branch: str = None
) -> List[Dict[str, Any]]:
    """Calculate charges for a handling unit using all applicable billing methods."""
    charges = []
    
    # Get contract items for storage charges
    storage_contract_items = _get_storage_contract_items(contract, handling_unit)
    
    for contract_item in storage_contract_items:
        billing_method = contract_item.get("billing_method", "Per Volume")
        
        # Get billing quantity based on method
        billing_quantity = get_billing_quantity(
            context="storage",
            billing_method=billing_method,
            reference_doc=handling_unit,
            date_from=date_from,
            date_to=date_to,
            volume_calculation_method=contract_item.get("volume_calculation_method", "Daily Volume")
        )
        
        if billing_quantity > 0:
            # Create charge line
            charge_line = create_charge_line(
                contract_item=contract_item,
                billing_quantity=billing_quantity,
                context="storage",
                reference_doc=handling_unit
            )
            
            if charge_line:
                charges.append(charge_line)
    
    return charges


def _get_storage_contract_items(contract: str, handling_unit: str) -> List[Dict[str, Any]]:
    """Get storage contract items for a handling unit."""
    # Get handling unit type and storage type
    hu_type = frappe.db.get_value("Handling Unit", handling_unit, "type")
    storage_location = _get_handling_unit_storage_location(handling_unit)
    storage_type = frappe.db.get_value("Storage Location", storage_location, "storage_type") if storage_location else None
    
    # Build filters
    base_filters = {
        "parent": contract,
        "parenttype": "Warehouse Contract",
        "storage_charge": 1
    }
    
    fields = [
        "item_charge", "description", "rate", "currency",
        "storage_uom", "handling_uom", "time_uom",
        "billing_method", "volume_uom", "volume_calculation_method",
        "handling_unit_type", "storage_type"
    ]
    
    # Try to find exact match first (both handling_unit_type and storage_type)
    if hu_type and storage_type:
        filters = dict(base_filters)
        filters["handling_unit_type"] = hu_type
        filters["storage_type"] = storage_type
        rows = frappe.get_all(
            "Warehouse Contract Item",
            filters=filters,
            fields=fields,
            limit=1,
            ignore_permissions=True
        )
        if rows:
            return rows
    
    # Try handling_unit_type only
    if hu_type:
        filters = dict(base_filters)
        filters["handling_unit_type"] = hu_type
        rows = frappe.get_all(
            "Warehouse Contract Item",
            filters=filters,
            fields=fields,
            limit=1,
            ignore_permissions=True
        )
        if rows:
            return rows
    
    # Try storage_type only
    if storage_type:
        filters = dict(base_filters)
        filters["storage_type"] = storage_type
        rows = frappe.get_all(
            "Warehouse Contract Item",
            filters=filters,
            fields=fields,
            limit=1,
            ignore_permissions=True
        )
        if rows:
            return rows
    
    # Fallback to any storage contract item
    rows = frappe.get_all(
        "Warehouse Contract Item",
        filters=base_filters,
        fields=fields,
        limit=1,
        ignore_permissions=True
    )
    
    return rows


def _get_handling_unit_storage_location(handling_unit: str) -> Optional[str]:
    """Get the primary storage location for a handling unit."""
    if not handling_unit:
        return None
    
    # Get the most frequently used storage location (excluding staging)
    location_data = frappe.db.sql("""
        SELECT 
            l.storage_location,
            COUNT(*) as day_count,
            SUM(ABS(l.quantity)) as total_movement
        FROM `tabWarehouse Stock Ledger` l
        LEFT JOIN `tabStorage Location` sl ON sl.name = l.storage_location
        WHERE l.handling_unit = %s 
          AND l.storage_location IS NOT NULL
          AND (sl.staging_area = 0 OR sl.staging_area IS NULL)
        GROUP BY l.storage_location
        ORDER BY day_count DESC, total_movement DESC
        LIMIT 1
    """, (handling_unit,), as_dict=True)
    
    return location_data[0].storage_location if location_data else None


# =============================================================================
# Order-based Billing
# =============================================================================

@frappe.whitelist()
def calculate_order_charges(
    contract: str,
    order_name: str,
    order_type: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Calculate charges for warehouse orders using appropriate billing methods.
    
    Args:
        contract: Warehouse Contract name
        order_name: Order document name
        order_type: Order type (inbound, outbound, vas)
        **kwargs: Additional parameters
    
    Returns:
        Dict with charge calculation results
    """
    try:
        # Get contract items for the order type
        context = order_type.lower()
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
                reference_doc=order_name,
                **kwargs
            )
            
            if billing_quantity > 0:
                # Create charge line
                charge_line = create_charge_line(
                    contract_item=contract_item,
                    billing_quantity=billing_quantity,
                    context=context,
                    reference_doc=order_name,
                    **kwargs
                )
                
                if charge_line:
                    charges.append(charge_line)
                    created_charges += 1
                    total_amount += flt(charge_line.get("total", 0))
        
        return {
            "ok": True,
            "message": f"Created {created_charges} charge(s) for {order_type} order",
            "created_charges": created_charges,
            "total_amount": total_amount,
            "charges": charges
        }
        
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# Job-based Billing
# =============================================================================

@frappe.whitelist()
def calculate_job_charges(
    contract: str,
    warehouse_job: str,
    **kwargs
) -> Dict[str, Any]:
    """
    Calculate charges for warehouse jobs using appropriate billing methods.
    
    Args:
        contract: Warehouse Contract name
        warehouse_job: Warehouse Job name
        **kwargs: Additional parameters
    
    Returns:
        Dict with charge calculation results
    """
    try:
        # Get job document
        job_doc = frappe.get_doc("Warehouse Job", warehouse_job)
        if not job_doc:
            return {"error": "Warehouse Job not found"}
        
        # Determine job context
        context = _get_job_context(job_doc)
        
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
                reference_doc=warehouse_job,
                **kwargs
            )
            
            if billing_quantity > 0:
                # Create charge line
                charge_line = create_charge_line(
                    contract_item=contract_item,
                    billing_quantity=billing_quantity,
                    context=context,
                    reference_doc=warehouse_job,
                    **kwargs
                )
                
                if charge_line:
                    charges.append(charge_line)
                    created_charges += 1
                    total_amount += flt(charge_line.get("total", 0))
        
        return {
            "ok": True,
            "message": f"Created {created_charges} charge(s) for {context} job",
            "created_charges": created_charges,
            "total_amount": total_amount,
            "charges": charges
        }
        
    except Exception as e:
        return {"error": str(e)}


def _get_job_context(job_doc) -> str:
    """Determine the context for a warehouse job."""
    job_type = job_doc.type
    
    if job_type == "Inbound":
        return "inbound"
    elif job_type == "Outbound":
        return "outbound"
    elif job_type == "Transfer":
        return "transfer"
    elif job_type == "VAS":
        return "vas"
    elif job_type == "Stocktake":
        return "stocktake"
    else:
        return "storage"


# =============================================================================
# Helper Functions
# =============================================================================

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
        "storage_uom", "handling_uom", "time_uom",
        "billing_method",
        "volume_uom", "volume_calculation_method"
    ]
    
    return frappe.get_all("Warehouse Contract Item", filters=filters, fields=fields, ignore_permissions=True)
