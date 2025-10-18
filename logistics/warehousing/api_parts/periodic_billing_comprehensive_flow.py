#!/usr/bin/env python3
"""
Comprehensive Periodic Billing Flow

This module handles the complete periodic billing flow:
1. Compute storage charges based on handling units
2. Fetch charges from warehouse jobs
3. Combine both for comprehensive billing
"""

from __future__ import annotations
import frappe
from frappe import _
from frappe.utils import flt, getdate, get_datetime, now_datetime, add_days
from typing import Dict, List, Any, Optional, Tuple
from datetime import date, datetime, timedelta

# =============================================================================
# Comprehensive Periodic Billing Functions
# =============================================================================

@frappe.whitelist()
def get_comprehensive_periodic_billing_charges(periodic_billing: str, clear_existing: int = 1) -> Dict[str, Any]:
    """
    Get comprehensive periodic billing charges including:
    1. Storage charges computed from handling units
    2. Charges fetched from warehouse jobs
    
    Args:
        periodic_billing: Periodic Billing document name
        clear_existing: Clear existing charges before creating new ones
    
    Returns:
        Dict with comprehensive billing results
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
        
        created_charges = 0
        total_amount = 0.0
        warnings = []
        
        # 1. COMPUTE STORAGE CHARGES
        storage_charges = _compute_storage_charges(
            contract=contract,
            customer=customer,
            date_from=date_from,
            date_to=date_to,
            company=company,
            branch=branch
        )
        
        for charge in storage_charges:
            pb_doc.append("charges", charge)
            created_charges += 1
            total_amount += flt(charge.get("total", 0))
        
        # 2. FETCH CHARGES FROM WAREHOUSE JOBS
        job_charges = _fetch_warehouse_job_charges(
            customer=customer,
            date_from=date_from,
            date_to=date_to,
            company=company,
            branch=branch
        )
        
        for charge in job_charges:
            pb_doc.append("charges", charge)
            created_charges += 1
            total_amount += flt(charge.get("total", 0))
        
        # Save the document
        if created_charges > 0:
            pb_doc.save()
            frappe.db.commit()
        
        return {
            "ok": True,
            "message": f"Created {created_charges} comprehensive charge(s)",
            "created_charges": created_charges,
            "total_amount": total_amount,
            "storage_charges": len(storage_charges),
            "job_charges": len(job_charges),
            "warnings": warnings
        }
        
    except Exception as e:
        return {"error": str(e)}


def _compute_storage_charges(contract: str, customer: str, date_from: str, date_to: str, 
                           company: str, branch: str) -> List[Dict[str, Any]]:
    """Compute storage charges for handling units with storage type and billing time considerations"""
    try:
        # Get all handling units for the customer
        hu_list = _get_customer_handling_units(customer, date_to, company, branch)
        
        if not hu_list:
            return []
        
        storage_charges = []
        
        # Get contract items for storage
        contract_doc = frappe.get_doc("Warehouse Contract", contract)
        storage_items = [item for item in contract_doc.items if item.charge_type == "Storage"]
        
        for hu in hu_list:
            # Get handling unit details
            hu_doc = frappe.get_doc("Handling Unit", hu)
            storage_type = hu_doc.get("storage_type") or "Dry Storage"  # Default storage type
            
            for contract_item in storage_items:
                billing_method = contract_item.storage_billing_method or "Per Day"
                
                # Use enhanced storage charge computation
                from logistics.warehousing.api_parts.storage_charge_computation import compute_storage_charge_with_type
                
                # Prepare contract item data (only for storage charges)
                contract_item_data = {
                    "volume_uom": contract_item.get("volume_uom", "CBM"),
                    "weight_uom": contract_item.get("weight_uom", "Kg"),
                    "billing_time_unit": contract_item.get("billing_time_unit", "Day")
                }
                
                # Add billing time settings only for storage charges
                if contract_item.get("storage_charge"):
                    contract_item_data.update({
                        "billing_time_unit": contract_item.get("billing_time_unit", "Day"),
                        "billing_time_multiplier": flt(contract_item.get("billing_time_multiplier", 1.0)),
                        "minimum_billing_time": flt(contract_item.get("minimum_billing_time", 1.0))
                    })
                
                # Compute storage charge with type and billing time considerations
                charge_result = compute_storage_charge_with_type(
                    handling_unit=hu,
                    storage_type=storage_type,
                    billing_method=billing_method,
                    date_from=date_from,
                    date_to=date_to,
                    contract_item=contract_item_data
                )
                
                if charge_result.get("ok"):
                    charge_details = charge_result.get("charge_details", {})
                    billing_quantity = charge_details.get("final_quantity", 0)
                    
                    if billing_quantity > 0:
                        # Create enhanced storage charge
                        charge = {
                            "item": contract_item.item_charge,
                            "item_name": contract_item.description or contract_item.item_charge,
                            "uom": _get_billing_uom_for_method(billing_method),
                            "quantity": billing_quantity,
                            "rate": contract_item.rate,
                            "total": billing_quantity * flt(contract_item.rate),
                            "handling_unit": hu,
                            "storage_type": storage_type,
                            "billing_method": billing_method,
                            "currency": contract_item.currency or "USD",
                            "billing_time_unit": charge_details.get("billing_time_unit"),
                            "billing_time_multiplier": charge_details.get("billing_time_multiplier"),
                            "storage_type_multiplier": charge_details.get("storage_type_multiplier")
                        }
                        
                        # Add method-specific fields
                        if billing_method == "Per Volume":
                            charge.update({
                                "volume_quantity": billing_quantity,
                                "volume_uom": contract_item.volume_uom or "CBM"
                            })
                        elif billing_method == "Per Weight":
                            charge.update({
                                "weight_quantity": billing_quantity,
                                "weight_uom": contract_item.weight_uom or "Kg"
                            })
                        elif billing_method == "Per Handling Unit":
                            charge.update({
                                "handling_unit_quantity": billing_quantity,
                                "handling_unit_uom": contract_item.handling_unit_uom or "Nos"
                            })
                        elif billing_method == "High Water Mark":
                            charge.update({
                                "peak_quantity": billing_quantity,
                                "peak_uom": contract_item.volume_uom or "CBM"
                            })
                        elif billing_method in ["Per Day", "Per Week", "Per Hour"]:
                            charge.update({
                                "time_quantity": billing_quantity,
                                "billing_time_unit": contract_item.billing_time_unit or "Day"
                            })
                        
                        # Add computation details
                        charge["computation_details"] = charge_details.get("computation_details", {})
                        
                        storage_charges.append(charge)
                else:
                    # Log error but continue with other charges
                    frappe.log_error(f"Error computing storage charge for {hu}: {charge_result.get('error')}")
        
        return storage_charges
        
    except Exception as e:
        frappe.log_error(f"Error computing storage charges: {str(e)}")
        return []


def _fetch_warehouse_job_charges(customer: str, date_from: str, date_to: str, 
                                company: str, branch: str) -> List[Dict[str, Any]]:
    """Fetch charges from warehouse jobs for the customer"""
    try:
        # Get warehouse jobs for the customer in the date range
        jobs = frappe.get_all("Warehouse Job", 
            filters={
                "customer": customer,
                "company": company,
                "branch": branch,
                "posting_date": ["between", [date_from, date_to]],
                "docstatus": 1
            },
            fields=["name", "posting_date", "job_type"]
        )
        
        if not jobs:
            return []
        
        job_charges = []
        
        for job in jobs:
            # Get charges from warehouse job
            charges = frappe.get_all("Warehouse Job Charges",
                filters={"parent": job.name},
                fields=["*"]
            )
            
            for charge in charges:
                # Create periodic billing charge from warehouse job charge
                job_charge = {
                    "item": charge.item_code,
                    "item_name": charge.item_name,
                    "uom": charge.uom,
                    "quantity": charge.quantity,
                    "rate": charge.rate,
                    "total": charge.total,
                    "warehouse_job": job.name,
                    "billing_method": charge.billing_method,
                    "currency": charge.currency or "USD"
                }
                
                # Copy method-specific fields
                if charge.billing_method == "Per Volume":
                    job_charge.update({
                        "volume_quantity": charge.volume_quantity,
                        "volume_uom": charge.volume_uom
                    })
                elif charge.billing_method == "Per Weight":
                    job_charge.update({
                        "weight_quantity": charge.weight_quantity,
                        "weight_uom": charge.weight_uom
                    })
                elif charge.billing_method == "Per Piece":
                    job_charge.update({
                        "piece_quantity": charge.piece_quantity,
                        "piece_uom": charge.piece_uom
                    })
                elif charge.billing_method == "Per Container":
                    job_charge.update({
                        "container_quantity": charge.container_quantity,
                        "container_uom": charge.container_uom
                    })
                elif charge.billing_method == "Per Hour":
                    job_charge.update({
                        "hour_quantity": charge.hour_quantity,
                        "hour_uom": charge.hour_uom
                    })
                elif charge.billing_method == "Per Handling Unit":
                    job_charge.update({
                        "handling_unit_quantity": charge.handling_unit_quantity,
                        "handling_unit_uom": charge.handling_unit_uom
                    })
                elif charge.billing_method == "High Water Mark":
                    job_charge.update({
                        "peak_quantity": charge.peak_quantity,
                        "peak_uom": charge.peak_uom
                    })
                
                job_charges.append(job_charge)
        
        return job_charges
        
    except Exception as e:
        frappe.log_error(f"Error fetching warehouse job charges: {str(e)}")
        return []


# =============================================================================
# Helper Functions
# =============================================================================

def _get_customer_contract(customer: str, company: str, branch: str) -> Optional[str]:
    """Get customer contract"""
    try:
        contract = frappe.get_value("Warehouse Contract", 
            filters={
                "customer": customer,
                "company": company,
                "branch": branch,
                "docstatus": 1
            },
            fieldname="name"
        )
        return contract
    except:
        return None


def _get_customer_handling_units(customer: str, date_to: str, company: str, branch: str) -> List[str]:
    """Get handling units for customer"""
    try:
        # Get handling units that belong to the customer
        hus = frappe.get_all("Handling Unit",
            filters={
                "customer": customer,
                "company": company,
                "branch": branch,
                "status": ["in", ["Available", "In Use"]]
            },
            fields=["name"]
        )
        
        return [hu.name for hu in hus]
    except:
        return []


def _get_billing_uom_for_method(billing_method: str) -> str:
    """Get appropriate UOM for billing method"""
    uom_map = {
        "Per Day": "Days",
        "Per Volume": "CBM",
        "Per Weight": "Kg",
        "Per Piece": "Nos",
        "Per Container": "Nos",
        "Per Hour": "Hours",
        "Per Handling Unit": "Nos",
        "High Water Mark": "CBM"
    }
    
    return uom_map.get(billing_method, "Nos")
