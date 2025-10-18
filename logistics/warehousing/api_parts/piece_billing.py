"""
Piece-based billing for VAS (Value Added Services).
This module handles billing VAS services based on the number of pieces processed.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, add_days
from typing import Dict, Any, List, Optional
from datetime import date, timedelta


def calculate_piece_usage(vas_order: str, date_from: str, date_to: str, 
                         billing_method: str = "Per Piece") -> Dict[str, Any]:
    """
    Calculate piece usage for VAS billing.
    
    Args:
        vas_order: VAS Order name
        date_from: Start date for calculation
        date_to: End date for calculation
        billing_method: Billing method (Per Piece, Per Day, etc.)
    
    Returns:
        Dict with piece usage data
    """
    if billing_method != "Per Piece":
        return {"total_pieces": 0, "days": 0, "average_pieces": 0, "calculation_method": "Not Per Piece"}
    
    start_date = getdate(date_from)
    end_date = getdate(date_to)
    
    # Get VAS order details
    vas_doc = frappe.get_doc("VAS Order", vas_order)
    if not vas_doc:
        return {"total_pieces": 0, "days": 0, "average_pieces": 0, "calculation_method": "VAS Order Not Found"}
    
    # Calculate total pieces from VAS order items
    total_pieces = 0
    for item in vas_doc.items:
        if item.quantity:
            total_pieces += flt(item.quantity)
    
    # Calculate days
    days = (end_date - start_date).days + 1
    
    return {
        "total_pieces": total_pieces,
        "days": days,
        "average_pieces": total_pieces / days if days > 0 else 0,
        "calculation_method": "Per Piece"
    }


def get_piece_billing_quantity(vas_order: str, date_from: str, date_to: str, 
                              billing_method: str = "Per Piece") -> float:
    """
    Get piece billing quantity for VAS order.
    
    Args:
        vas_order: VAS Order name
        date_from: Start date
        date_to: End date
        billing_method: Billing method
    
    Returns:
        Piece quantity for billing
    """
    if billing_method != "Per Piece":
        return 0.0
    
    piece_data = calculate_piece_usage(vas_order, date_from, date_to, billing_method)
    return flt(piece_data.get("total_pieces", 0))


def create_piece_based_charge_line(vas_order: str, date_from: str, date_to: str,
                                  contract_item: Dict, warehouse_job: str = None) -> Dict[str, Any]:
    """
    Create charge line for piece-based VAS billing.
    
    Args:
        vas_order: VAS Order name
        date_from: Start date
        date_to: End date
        contract_item: Contract item details
        warehouse_job: Associated warehouse job
    
    Returns:
        Charge line data
    """
    billing_method = contract_item.get("billing_method", "Per Day")
    
    if billing_method != "Per Piece":
        return {}
    
    # Get piece quantity
    piece_quantity = get_piece_billing_quantity(vas_order, date_from, date_to, billing_method)
    
    if piece_quantity <= 0:
        return {}
    
    # Get rate from contract
    rate = flt(contract_item.get("rate", 0))
    currency = contract_item.get("currency", "USD")
    
    # Calculate total
    total = piece_quantity * rate
    
    charge_line = {
        "item_code": contract_item.get("item_charge"),
        "item_name": contract_item.get("description", ""),
        "uom": contract_item.get("uom", "Nos"),
        "quantity": piece_quantity,
        "currency": currency,
        "rate": rate,
        "total": total,
        "billing_method": billing_method,
        "piece_quantity": piece_quantity,
        "piece_uom": contract_item.get("uom", "Nos")
    }
    
    return charge_line


def get_vas_piece_charges(vas_order: str, clear_existing: int = 1) -> Dict[str, Any]:
    """
    Get piece-based charges for VAS order.
    
    Args:
        vas_order: VAS Order name
        clear_existing: Clear existing charges
    
    Returns:
        Dict with charge data
    """
    vas_doc = frappe.get_doc("VAS Order", vas_order)
    if not vas_doc:
        return {"error": "VAS Order not found"}
    
    # Clear existing charges if requested
    if clear_existing:
        vas_doc.set("charges", [])
    
    # Get contract for customer
    contract = vas_doc.contract
    if not contract:
        return {"error": "No contract found for VAS order"}
    
    # Get contract items with piece billing
    contract_items = frappe.get_all("Warehouse Contract Item",
                                   filters={
                                       "parent": contract,
                                       "billing_method": "Per Piece",
                                       "vas_charge": 1
                                   },
                                   fields=["*"])
    
    if not contract_items:
        return {"message": "No piece-based VAS charges found in contract"}
    
    created_charges = 0
    total_amount = 0.0
    
    # Create charges for each contract item
    for contract_item in contract_items:
        charge_line = create_piece_based_charge_line(
            vas_order=vas_order,
            date_from=vas_doc.order_date,
            date_to=vas_doc.due_date or vas_doc.order_date,
            contract_item=contract_item,
            warehouse_job=None
        )
        
        if charge_line:
            vas_doc.append("charges", charge_line)
            created_charges += 1
            total_amount += flt(charge_line.get("total", 0))
    
    # Save the VAS order
    if created_charges > 0:
        vas_doc.save()
        frappe.db.commit()
    
    return {
        "ok": True,
        "message": f"Created {created_charges} piece-based charge(s). Total: {total_amount}",
        "created_charges": created_charges,
        "total_amount": total_amount
    }


def calculate_vas_job_piece_charges(warehouse_job: str, clear_existing: int = 1) -> Dict[str, Any]:
    """
    Calculate piece-based charges for VAS warehouse job.
    
    Args:
        warehouse_job: Warehouse Job name
        clear_existing: Clear existing charges
    
    Returns:
        Dict with charge data
    """
    job_doc = frappe.get_doc("Warehouse Job", warehouse_job)
    if not job_doc:
        return {"error": "Warehouse Job not found"}
    
    if job_doc.type != "VAS":
        return {"error": "Job must be of type VAS"}
    
    if not job_doc.reference_order:
        return {"error": "VAS job must reference a VAS Order"}
    
    # Clear existing charges if requested
    if clear_existing:
        job_doc.set("charges", [])
    
    # Get VAS order
    vas_order = job_doc.reference_order
    vas_doc = frappe.get_doc("VAS Order", vas_order)
    
    # Get contract
    contract = vas_doc.contract
    if not contract:
        return {"error": "No contract found for VAS order"}
    
    # Get contract items with piece billing
    contract_items = frappe.get_all("Warehouse Contract Item",
                                   filters={
                                       "parent": contract,
                                       "billing_method": "Per Piece",
                                       "vas_charge": 1
                                   },
                                   fields=["*"])
    
    if not contract_items:
        return {"message": "No piece-based VAS charges found in contract"}
    
    created_charges = 0
    total_amount = 0.0
    
    # Calculate piece quantity from job items
    total_pieces = 0
    for item in job_doc.items:
        if item.quantity:
            total_pieces += flt(item.quantity)
    
    if total_pieces <= 0:
        return {"message": "No pieces found in job items"}
    
    # Create charges for each contract item
    for contract_item in contract_items:
        rate = flt(contract_item.get("rate", 0))
        currency = contract_item.get("currency", "USD")
        total = total_pieces * rate
        
        charge_line = {
            "item_code": contract_item.get("item_charge"),
            "item_name": contract_item.get("description", ""),
            "uom": contract_item.get("uom", "Nos"),
            "quantity": total_pieces,
            "currency": currency,
            "rate": rate,
            "total": total,
            "billing_method": "Per Piece",
            "piece_quantity": total_pieces,
            "piece_uom": contract_item.get("uom", "Nos")
        }
        
        job_doc.append("charges", charge_line)
        created_charges += 1
        total_amount += total
    
    # Save the job
    if created_charges > 0:
        job_doc.save()
        frappe.db.commit()
    
    return {
        "ok": True,
        "message": f"Created {created_charges} piece-based charge(s). Total: {total_amount}",
        "created_charges": created_charges,
        "total_amount": total_amount,
        "total_pieces": total_pieces
    }


def get_vas_piece_usage_summary(vas_order: str) -> Dict[str, Any]:
    """
    Get piece usage summary for VAS order.
    
    Args:
        vas_order: VAS Order name
    
    Returns:
        Dict with usage summary
    """
    vas_doc = frappe.get_doc("VAS Order", vas_order)
    if not vas_doc:
        return {"error": "VAS Order not found"}
    
    total_pieces = 0
    total_items = 0
    
    for item in vas_doc.items:
        if item.quantity:
            total_pieces += flt(item.quantity)
            total_items += 1
    
    return {
        "vas_order": vas_order,
        "total_pieces": total_pieces,
        "total_items": total_items,
        "average_pieces_per_item": total_pieces / total_items if total_items > 0 else 0,
        "order_date": vas_doc.order_date,
        "due_date": vas_doc.due_date,
        "customer": vas_doc.customer
    }

