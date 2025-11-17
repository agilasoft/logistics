"""
Warehouse Charges Calculation Module

This module handles the calculation of warehouse job charges based on
contract billing methods and time billing settings.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timedelta
from logistics.warehousing.api_parts.common import _get_default_currency


@frappe.whitelist()
def get_warehouse_job_charges_with_contract(customer: str, date_from: str, date_to: str, warehouse_contract: str, company: Optional[str] = None, branch: Optional[str] = None) -> Tuple[List[Dict], float, List[str]]:
    """
    Get warehouse job charges based on contract billing methods.
    
    This function retrieves warehouse jobs and calculates charges according to
    the billing methods defined in the warehouse contract.
    """
    charges = []
    total = 0.0
    warnings = []
    
    try:
        # Input validation
        if not customer:
            frappe.throw(_("Customer is required"))
        
        if not frappe.db.exists("Customer", customer):
            frappe.throw(_("Invalid Customer: {0}").format(customer))
        
        if not date_from or not date_to:
            frappe.throw(_("Date From and Date To are required"))
        
        if not warehouse_contract:
            frappe.throw(_("Warehouse Contract is required"))
        
        if not frappe.db.exists("Warehouse Contract", warehouse_contract):
            frappe.throw(_("Invalid Warehouse Contract: {0}").format(warehouse_contract))
        
        if company and not frappe.db.exists("Company", company):
            frappe.throw(_("Invalid Company: {0}").format(company))
        
        if branch and not frappe.db.exists("Branch", branch):
            frappe.throw(_("Invalid Branch: {0}").format(branch))
        # Get warehouse jobs for the customer in the date range
        filters = {
            "docstatus": 1, 
            "customer": customer, 
            "job_open_date": ["between", [date_from, date_to]]
        }
        
        if company:
            filters["company"] = company
        if branch:
            filters["branch"] = branch

        jobs = frappe.get_all(
            "Warehouse Job",
            filters=filters,
            fields=["name", "job_open_date"],
            order_by="job_open_date asc, name asc",
            ignore_permissions=True,
        ) or []
        
        if not jobs:
            warnings.append(_("No warehouse jobs found for the specified period."))
            return charges, total, warnings
        
        # Get contract items for job charges
        contract_items = get_contract_job_items(warehouse_contract)
        if not contract_items:
            warnings.append(_("No job charge items found in contract or contract is not valid."))
            return charges, total, warnings
        
        # Process each job
        for job in jobs:
            job_charges = calculate_job_charges_with_contract(job, contract_items, date_from, date_to)
            charges.extend(job_charges)
            total += sum(flt(charge.get("total", 0)) for charge in job_charges)
        
    except Exception as e:
        warnings.append(f"Error processing warehouse job charges: {str(e)}")
        frappe.log_error(f"Error in get_warehouse_job_charges_with_contract: {str(e)}")
    
    return charges, total, warnings


def get_contract_job_items(warehouse_contract: str) -> List[Dict]:
    """Get contract items that are applicable for job charges."""
    try:
        # First check if contract is valid
        contract_info = frappe.db.sql("""
            SELECT name, date, valid_until, customer
            FROM `tabWarehouse Contract`
            WHERE name = %s AND docstatus = 1
        """, (warehouse_contract,), as_dict=True)
        
        if not contract_info:
            frappe.msgprint(_("Warehouse Contract {0} not found or not submitted.").format(warehouse_contract), alert=True)
            return []
        
        contract = contract_info[0]
        today = frappe.utils.today()
        
        # Check contract validity
        if contract.valid_until and contract.valid_until < today:
            frappe.msgprint(
                _("Warehouse Contract {0} has expired on {1}. Please extend the contract validity period to calculate charges.").format(
                    warehouse_contract, contract.valid_until
                ), 
                alert=True
            )
            return []
        
        if contract.date and contract.date > today:
            frappe.msgprint(
                _("Warehouse Contract {0} is not yet active. Contract starts on {1}.").format(
                    warehouse_contract, contract.date
                ), 
                alert=True
            )
            return []
        
        contract_items = frappe.db.sql("""
            SELECT 
                item_charge AS item_code, 
                rate, 
                currency, 
                uom, 
                handling_unit_type, 
                storage_type, 
                unit_type,
                inbound_charge,
                outbound_charge,
                transfer_charge,
                vas_charge,
                stocktake_charge,
                billing_time_unit,
                billing_time_multiplier,
                minimum_billing_time
            FROM `tabWarehouse Contract Item`
            WHERE parent = %s AND parenttype = 'Warehouse Contract'
            AND (inbound_charge = 1 OR outbound_charge = 1 OR transfer_charge = 1 OR vas_charge = 1 OR stocktake_charge = 1)
            ORDER BY handling_unit_type, storage_type
        """, (warehouse_contract,), as_dict=True)
        
        return contract_items or []
        
    except Exception as e:
        frappe.log_error(f"Error getting contract job items: {str(e)}")
        return []


def calculate_job_charges_with_contract(job: Dict, contract_items: List[Dict], date_from: str, date_to: str) -> List[Dict]:
    """Calculate job charges based on contract billing methods."""
    charges = []
    
    try:
        # Get job details
        job_doc = frappe.get_doc("Warehouse Job", job["name"])
        job_type = job.get("type", "Generic")
        
        # Find matching contract items for this job type
        matching_items = find_matching_contract_items_for_job(job_type, contract_items)
        
        if not matching_items:
            # Use generic contract items if no specific match
            matching_items = [item for item in contract_items if not item.get("handling_unit_type")]
        
        # Calculate charges for each matching contract item
        for contract_item in matching_items:
            charge = calculate_single_job_charge(job, job_doc, contract_item, date_from, date_to)
            if charge:
                charges.append(charge)
        
    except Exception as e:
        frappe.log_error(f"Error calculating job charges for {job.get('name')}: {str(e)}")
    
    return charges


def find_matching_contract_items_for_job(job_type: str, contract_items: List[Dict]) -> List[Dict]:
    """Find contract items that match the job type."""
    matching_items = []
    
    # Map job types to contract charge types
    job_type_mapping = {
        "Inbound": "inbound_charge",
        "Outbound": "outbound_charge", 
        "Pick": "outbound_charge",  # Pick operations are outbound
        "Putaway": "inbound_charge",  # Putaway operations are inbound
        "Transfer": "transfer_charge",
        "VAS": "vas_charge",
        "Stocktake": "stocktake_charge"
    }
    
    charge_type = job_type_mapping.get(job_type, "inbound_charge")  # Default to inbound
    
    
    for item in contract_items:
        if item.get(charge_type, 0):
            matching_items.append(item)
    
    return matching_items


def calculate_single_job_charge(job: Dict, job_doc, contract_item: Dict, date_from: str, date_to: str) -> Optional[Dict]:
    """Calculate a single job charge based on contract billing method."""
    try:
        # Get billing method from contract
        unit_type = contract_item.get("unit_type", "Day")
        rate = flt(contract_item.get("rate", 0))
        calculation_method = contract_item.get("calculation_method", "Per Unit")
        
        if rate <= 0:
            return None
        
        # Calculate billing quantity based on method
        billing_quantity = calculate_job_billing_quantity(job, job_doc, unit_type, contract_item, date_from, date_to)
        
        if billing_quantity <= 0:
            return None
        
        # Apply calculation method to get total
        from logistics.warehousing.doctype.warehouse_job.warehouse_job import _apply_calculation_method
        total = _apply_calculation_method(billing_quantity, rate, contract_item)
        
        # For Base Plus Additional and First Plus Additional, simplify display:
        # Qty = 1, Rate = Total, Total = Total
        if calculation_method in ["Base Plus Additional", "First Plus Additional"]:
            display_qty = 1.0
            display_rate = total
        else:
            # For other methods, show actual quantity and rate
            display_qty = billing_quantity
            display_rate = rate
        
        # Create charge
        charge = {
            "item": contract_item.get("item_code"),
            "item_name": f"Job Charge ({job.get('type', 'Generic')})",
            "uom": contract_item.get("uom", "Day"),
            "quantity": display_qty,
            "rate": display_rate,
            "total": total,
            "currency": contract_item.get("currency", _get_default_currency(company)),
            "warehouse_job": job.get("name"),
            "calculation_notes": generate_job_charge_calculation_notes(job, contract_item, billing_quantity, rate, unit_type, date_to)
        }
        
        return charge
        
    except Exception as e:
        frappe.log_error(f"Error calculating single job charge: {str(e)}")
        return None


def calculate_job_billing_quantity(job: Dict, job_doc, unit_type: str, contract_item: Dict, date_from: str, date_to: str) -> float:
    """Calculate billing quantity for job based on unit type."""
    try:
        if unit_type == "Handling Unit":
            return calculate_job_handling_unit_quantity(job_doc)
        elif unit_type == "Volume":
            return calculate_job_volume_quantity(job_doc)
        elif unit_type == "Weight":
            return calculate_job_weight_quantity(job_doc)
        elif unit_type == "Package":
            return calculate_job_container_quantity(job_doc)
        elif unit_type == "Piece":
            return calculate_job_piece_quantity(job_doc)
        elif unit_type == "Operation Time":
            return calculate_job_time_quantity(job_doc, contract_item)
        else:  # Default to Per Day
            return calculate_job_day_quantity(job, date_from, date_to)
            
    except Exception as e:
        frappe.log_error(f"Error calculating job billing quantity: {str(e)}")
        return 0.0


def calculate_job_day_quantity(job: Dict, date_from: str, date_to: str) -> float:
    """Calculate days for job billing based on Warehouse Stock Ledger posting dates."""
    try:
        # Get posting dates from Warehouse Stock Ledger for this job
        posting_dates = frappe.db.sql("""
            SELECT DISTINCT DATE(posting_date) as posting_date
            FROM `tabWarehouse Stock Ledger`
            WHERE warehouse_job = %s
            AND DATE(posting_date) BETWEEN %s AND %s
            ORDER BY posting_date
        """, (job.get("name"), date_from, date_to), as_dict=True)
        
        if not posting_dates:
            # If no ledger entries, use job open date to billing end date
            job_open_date = job.get("job_open_date")
            if job_open_date:
                start_date = datetime.strptime(str(job_open_date), "%Y-%m-%d")
                end_date = datetime.strptime(str(date_to), "%Y-%m-%d")
                days = (end_date - start_date).days + 1
            else:
                days = 1
        else:
            # Calculate days based on actual posting dates
            days = len(posting_dates)
        
        return float(max(1, days))  # Minimum 1 day
        
    except Exception as e:
        frappe.log_error(f"Error calculating job day quantity: {str(e)}")
        return 1.0


def calculate_job_handling_unit_quantity(job_doc) -> float:
    """Calculate handling units for job billing."""
    try:
        # Count handling units in job items
        handling_units = set()
        for item in job_doc.items or []:
            if item.get("handling_unit"):
                handling_units.add(item.get("handling_unit"))
        
        return float(len(handling_units)) if handling_units else 1.0
        
    except Exception as e:
        frappe.log_error(f"Error calculating job handling unit quantity: {str(e)}")
        return 1.0


def calculate_job_volume_quantity(job_doc) -> float:
    """Calculate volume for job billing."""
    try:
        total_volume = 0.0
        for item in job_doc.items or []:
            volume = flt(item.get("volume", 0))
            quantity = flt(item.get("quantity", 0))
            total_volume += volume * quantity
        
        return total_volume
        
    except Exception as e:
        frappe.log_error(f"Error calculating job volume quantity: {str(e)}")
        return 0.0


def calculate_job_weight_quantity(job_doc) -> float:
    """Calculate weight for job billing."""
    try:
        total_weight = 0.0
        for item in job_doc.items or []:
            weight = flt(item.get("weight", 0))
            quantity = flt(item.get("quantity", 0))
            total_weight += weight * quantity
        
        return total_weight
        
    except Exception as e:
        frappe.log_error(f"Error calculating job weight quantity: {str(e)}")
        return 0.0


def calculate_job_container_quantity(job_doc) -> float:
    """Calculate containers for job billing."""
    try:
        # Check if total_teu is available on the job
        if hasattr(job_doc, 'total_teu'):
            total_teu = getattr(job_doc, 'total_teu', 0)
        else:
            total_teu = job_doc.get('total_teu', 0) if isinstance(job_doc, dict) else 0
        
        if total_teu and total_teu > 0:
            return flt(total_teu)
        
        # Count distinct containers or use job items count
        containers = set()
        for item in job_doc.items or []:
            if item.get("container"):
                containers.add(item.get("container"))
        
        return float(len(containers)) if containers else float(len(job_doc.items or []))
        
    except Exception as e:
        frappe.log_error(f"Error calculating job container quantity: {str(e)}")
        return 1.0


def calculate_job_piece_quantity(job_doc) -> float:
    """Calculate pieces for job billing."""
    try:
        total_pieces = 0.0
        
        
        for item in job_doc.items or []:
            # Try both dictionary access and attribute access
            if hasattr(item, 'quantity'):
                quantity = flt(item.quantity)
            else:
                quantity = flt(item.get("quantity", 0))
            
            total_pieces += quantity
        return total_pieces
        
    except Exception as e:
        frappe.log_error(f"Error calculating job piece quantity: {str(e)}")
        return 1.0


def calculate_job_time_quantity(job_doc, contract_item: Dict) -> float:
    """Calculate time for job billing."""
    try:
        # Get time billing settings from contract
        billing_unit = contract_item.get("billing_time_unit", "Hour")
        multiplier = flt(contract_item.get("billing_time_multiplier", 1))
        minimum_time = flt(contract_item.get("minimum_billing_time", 1))
        
        # Calculate actual time (this would need to be implemented based on job tracking)
        # For now, use a default calculation
        actual_time = 1.0  # This should be calculated from job start/end times
        
        # Apply multiplier and minimum time
        calculated_time = max(minimum_time, actual_time * multiplier)
        
        return calculated_time
        
    except Exception as e:
        frappe.log_error(f"Error calculating job time quantity: {str(e)}")
        return 1.0


def generate_job_charge_calculation_notes(job: Dict, contract_item: Dict, billing_quantity: float, rate: float, unit_type: str, date_to: str) -> str:
    """Generate calculation notes for job charges."""
    return f"""Warehouse Job Charge Calculation:
  • Warehouse Job: {job.get('name', 'N/A')}
  • Job Type: {job.get('type', 'N/A')}
  • Period: Based on Warehouse Stock Ledger posting dates
  • Billing Method: {unit_type}
  • UOM: {contract_item.get('uom', 'N/A')}
  • Rate per {contract_item.get('uom', 'N/A')}: {rate}
  • Billing Quantity: {billing_quantity}
  • Calculation: {billing_quantity} × {rate} = {billing_quantity * rate}
  • Currency: {contract_item.get('currency', _get_default_currency(company))}
  • Contract Setup Applied:
    - Rate sourced from Warehouse Contract Item
    - Applied based on actual stock movements in Warehouse Stock Ledger
    - Charge type: {unit_type} billing method
    - Time billing settings: {contract_item.get('billing_time_unit', 'N/A')} unit, {contract_item.get('billing_time_multiplier', 1)} multiplier, {contract_item.get('minimum_billing_time', 1)} minimum"""


# Additional utility functions

@frappe.whitelist()
def test_job_charges_calculation(customer: str, date_from: str, date_to: str, warehouse_contract: str) -> Dict[str, Any]:
    """Test job charges calculation for debugging."""
    try:
        # Get basic info
        info = {
            "customer": customer,
            "date_from": date_from,
            "date_to": date_to,
            "warehouse_contract": warehouse_contract
        }
        
        # Get warehouse jobs
        jobs = frappe.get_all(
            "Warehouse Job",
            filters={
                "docstatus": 1, 
                "customer": customer, 
                "job_open_date": ["between", [date_from, date_to]]
            },
            fields=["name", "job_open_date"],
            order_by="job_open_date asc, name asc",
            ignore_permissions=True,
        ) or []
        
        info["jobs_found"] = len(jobs)
        info["jobs"] = jobs[:5]  # First 5 for testing
        
        # Get contract items
        contract_items = get_contract_job_items(warehouse_contract)
        info["contract_items_found"] = len(contract_items)
        info["contract_items"] = contract_items[:3]  # First 3 for testing
        
        return {"ok": True, "info": info}
        
    except Exception as e:
        frappe.log_error(f"Error testing job charges calculation: {str(e)}")
        return {"ok": False, "error": str(e)}
