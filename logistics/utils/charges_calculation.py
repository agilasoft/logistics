# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Centralized charge calculation for Air, Sea, Transport, and Declaration charges.

Follows the Sales Quote charge calculation pattern using TransportRateCalculationEngine.
Supports Weight Break and Qty Break methods via Sales Quote Weight Break / Qty Break tables.
"""

import json

import frappe
from frappe.utils import flt
from typing import Dict, List, Optional, Any

from logistics.pricing_center.api_parts.transport_rate_calculation_engine import (
    TransportRateCalculationEngine,
)

# Field mapping: charge doctypes may use charge_basis/rate; Sales Quote uses calculation_method/unit_rate
METHOD_FIELDS = ("calculation_method", "charge_basis")
RATE_FIELDS = ("unit_rate", "rate")

# Map charge_basis (e.g. "Per kg", "Per m³") to engine calculation_method + unit_type
CHARGE_BASIS_TO_ENGINE = {
    "Per kg": ("Per Unit", "Weight"),
    "Per m³": ("Per Unit", "Volume"),
    "Per m3": ("Per Unit", "Volume"),
    "Per package": ("Per Unit", "Package"),
    "Per piece": ("Per Unit", "Piece"),
    "Per shipment": ("Flat Rate", None),
    "Fixed amount": ("Flat Rate", None),
    "Flat rate": ("Flat Rate", None),
}
UNIT_TYPE_FIELDS = ("unit_type",)
COST_METHOD_FIELDS = ("cost_calculation_method",)
COST_RATE_FIELDS = ("unit_cost",)
COST_UNIT_TYPE_FIELDS = ("cost_unit_type",)

# Parent doctype -> quantity field mapping for actual data extraction
PARENT_QUANTITY_FIELDS = {
    "Air Booking": ("total_weight", "chargeable_weight", "weight", "total_volume", "volume", "total_pieces"),
    "Air Shipment": ("total_weight", "chargeable_weight", "weight", "total_volume", "volume", "total_pieces"),
    "Sea Booking": ("total_weight", "total_volume", "total_pieces", "total_teu", "total_containers"),
    "Sea Shipment": ("total_weight", "weight", "total_volume", "volume", "total_pieces", "total_teu", "total_containers"),
    "Sea Consolidation": ("total_weight", "chargeable_weight", "total_volume", "total_packages", "total_teu", "total_containers"),
    "Declaration": ("total_weight", "weight", "total_volume", "volume", "total_pieces"),
    "Declaration Order": ("total_weight", "weight", "total_volume", "volume", "total_pieces"),
    "Transport Order": ("total_weight", "weight", "total_volume", "volume", "total_distance", "total_pieces"),
    "Transport Job": ("total_weight", "weight", "total_volume", "volume", "total_distance", "total_pieces"),
    "Warehouse Job": ("total_weight", "weight", "total_volume", "volume", "total_pieces"),
}


def _get_field(doc: Any, *field_names: str, default=None):
    """Get first non-empty value from doc for given field names."""
    for name in field_names:
        val = getattr(doc, name, None)
        if val is not None and val != "":
            return val
    return default


def get_charge_bill_to_customers(charge: Any) -> List[str]:
    """
    Return list of Customer names/IDs this charge is billable to.
    One charge item, one Bill To only (single Link).
    """
    bill_to = getattr(charge, "bill_to", None)
    if bill_to:
        return [bill_to]
    return []


def _get_parent_actual_data(charge_doc: Any, parent_doc: Any) -> Dict:
    """Extract actual quantity data from parent document for charge calculation."""
    if not parent_doc:
        return {
            "actual_quantity": 0,
            "actual_weight": 0,
            "actual_volume": 0,
            "actual_distance": 0,
            "actual_pieces": 0,
            "actual_teu": 0,
            "actual_operation_time": 0,
        }

    parent_doctype = getattr(parent_doc, "doctype", None) or parent_doc.get("doctype")
    fields = PARENT_QUANTITY_FIELDS.get(parent_doctype, ())

    weight = flt(
        _get_field(parent_doc, "total_weight", "chargeable_weight", "weight") or 0
    )
    volume = flt(
        _get_field(parent_doc, "total_volume", "volume") or 0
    )
    pieces = flt(
        _get_field(parent_doc, "total_pieces", "total_packages") or 0
    )
    if pieces <= 0 and hasattr(parent_doc, "packages") and parent_doc.packages:
        pieces = len(parent_doc.packages)
    distance = flt(
        _get_field(parent_doc, "total_distance") or 0
    )
    teu = flt(
        _get_field(parent_doc, "total_teu", "total_containers") or 0
    )
    operation_time = flt(
        _get_field(parent_doc, "total_operation_time") or 0
    )

    return {
        "actual_quantity": weight or volume or pieces or distance or teu or 1,
        "actual_weight": weight,
        "actual_volume": volume,
        "actual_distance": distance,
        "actual_pieces": pieces,
        "actual_teu": teu,
        "actual_operation_time": operation_time,
    }


def _normalize_calculation_method(method: str, unit_type: str) -> tuple:
    """Map charge_basis (e.g. Per kg) to engine calculation_method and unit_type."""
    if not method:
        return None, unit_type or "Weight"
    mapped = CHARGE_BASIS_TO_ENGINE.get(method.strip())
    if mapped:
        calc_method, mapped_unit = mapped
        return calc_method, mapped_unit or unit_type or "Weight"
    return method, unit_type or "Weight"


def _prepare_rate_data(
    charge_doc: Any,
    is_revenue: bool = True,
) -> Optional[Dict]:
    """Prepare rate data dict for TransportRateCalculationEngine from charge doc."""
    if is_revenue:
        method = _get_field(charge_doc, *METHOD_FIELDS)
        rate = flt(_get_field(charge_doc, *RATE_FIELDS) or 0)
        unit_type = _get_field(charge_doc, *UNIT_TYPE_FIELDS) or "Weight"
        prefix = ""
    else:
        method = _get_field(charge_doc, *COST_METHOD_FIELDS)
        rate = flt(_get_field(charge_doc, *COST_RATE_FIELDS) or 0)
        unit_type = _get_field(charge_doc, *COST_UNIT_TYPE_FIELDS) or "Weight"
        prefix = "cost_"

    if not method:
        return None

    # Map charge_basis to engine format
    method, unit_type = _normalize_calculation_method(method, unit_type)

    # Weight Break and Qty Break are handled separately
    if method in ("Weight Break", "Qty Break"):
        return None

    rate_data = {
        "calculation_method": method,
        "rate": rate,
        "unit_type": unit_type or "Weight",
        "minimum_quantity": flt(getattr(charge_doc, f"{prefix}minimum_quantity", None) or 0),
        "minimum_unit_rate": flt(getattr(charge_doc, f"{prefix}minimum_unit_rate", None) or 0),
        "minimum_charge": flt(getattr(charge_doc, f"{prefix}minimum_charge", None) or 0),
        "maximum_charge": flt(getattr(charge_doc, f"{prefix}maximum_charge", None) or 0),
        "base_amount": flt(getattr(charge_doc, f"{prefix}base_amount", None) or 0),
        "base_quantity": flt(getattr(charge_doc, f"{prefix}base_quantity", None) or 1),
        "currency": getattr(charge_doc, "currency", None) or getattr(charge_doc, f"{prefix}currency", None) or "USD",
        "item_code": getattr(charge_doc, "item_code", None),
        "item_name": getattr(charge_doc, "item_name", None),
    }
    return rate_data


def _resolve_weight_break_rate(
    charge_doc: Any,
    actual_weight: float,
    record_type: str = "Selling",
) -> Optional[Dict]:
    """Resolve applicable unit rate from Sales Quote Weight Break (reference-based, same as Sales Quote)."""
    ref_name = getattr(charge_doc, "name", None)
    if not ref_name or ref_name == "new":
        return None

    weight_breaks = frappe.get_all(
        "Sales Quote Weight Break",
        filters={
            "reference_doctype": charge_doc.doctype,
            "reference_no": ref_name,
            "type": record_type,
        },
        fields=["weight_break", "unit_rate", "rate_type", "currency"],
        order_by="weight_break asc",
    )
    if not weight_breaks:
        return None

    sorted_breaks = sorted(
        weight_breaks,
        key=lambda x: flt(x.get("weight_break", 0)),
        reverse=True,
    )
    for wb in sorted_breaks:
        if flt(actual_weight) >= flt(wb.get("weight_break", 0)):
            return wb
    return sorted(weight_breaks, key=lambda x: flt(x.get("weight_break", 0)))[0]


def _resolve_qty_break_rate(
    charge_doc: Any,
    actual_qty: float,
    record_type: str = "Selling",
) -> Optional[Dict]:
    """Resolve applicable unit rate from Sales Quote Qty Break (reference-based, same as Sales Quote)."""
    ref_name = getattr(charge_doc, "name", None)
    if not ref_name or ref_name == "new":
        return None

    qty_breaks = frappe.get_all(
        "Sales Quote Qty Break",
        filters={
            "reference_doctype": charge_doc.doctype,
            "reference_no": ref_name,
            "type": record_type,
        },
        fields=["qty_break", "unit_rate", "currency"],
        order_by="qty_break asc",
    )
    if not qty_breaks:
        return None

    sorted_breaks = sorted(
        qty_breaks,
        key=lambda x: flt(x.get("qty_break", 0)),
        reverse=True,
    )
    for qb in sorted_breaks:
        if flt(actual_qty) >= flt(qb.get("qty_break", 0)):
            return qb
    return sorted(qty_breaks, key=lambda x: flt(x.get("qty_break", 0)))[0]


def calculate_charge_revenue(charge_doc: Any, parent_doc: Optional[Any] = None) -> Dict:
    """
    Calculate estimated revenue for a charge row.

    Args:
        charge_doc: The charge child document (e.g. Air Booking Charges row)
        parent_doc: Parent document (Air Booking, etc.). If None, derived from charge_doc.parent.

    Returns:
        Dict with keys: amount, calc_notes, success, error
    """
    return _calculate_charge_amount(charge_doc, parent_doc, is_revenue=True)


def calculate_charge_cost(charge_doc: Any, parent_doc: Optional[Any] = None) -> Dict:
    """
    Calculate estimated cost for a charge row.

    Args:
        charge_doc: The charge child document
        parent_doc: Parent document. If None, derived from charge_doc.parent.

    Returns:
        Dict with keys: amount, calc_notes, success, error
    """
    return _calculate_charge_amount(charge_doc, parent_doc, is_revenue=False)


def _calculate_charge_amount(
    charge_doc: Any,
    parent_doc: Optional[Any],
    is_revenue: bool = True,
) -> Dict:
    """Internal: calculate revenue or cost for a charge row."""
    result = {"amount": 0, "calc_notes": "", "success": False, "error": None}

    if is_revenue:
        method = _get_field(charge_doc, *METHOD_FIELDS)
        record_type = "Selling"
    else:
        method = _get_field(charge_doc, *COST_METHOD_FIELDS)
        record_type = "Cost"

    if not method:
        result["calc_notes"] = "No calculation method specified"
        return result

    if parent_doc is None and getattr(charge_doc, "parent", None):
        try:
            parent_doc = frappe.get_doc(charge_doc.parenttype, charge_doc.parent)
        except Exception:
            parent_doc = None

    actual_data = _get_parent_actual_data(charge_doc, parent_doc)

    # Weight Break
    if method == "Weight Break":
        applicable = _resolve_weight_break_rate(
            charge_doc,
            actual_data["actual_weight"],
            record_type,
        )
        if not applicable:
            result["calc_notes"] = "No weight break rates defined"
            return result
        rate = flt(applicable.get("unit_rate", 0))
        amount = rate * actual_data["actual_weight"]
        result["amount"] = amount
        result["calc_notes"] = (
            f"Weight Break: {actual_data['actual_weight']} × {rate} = {amount} "
            f"(Break: {applicable.get('weight_break', 0)})"
        )
        result["success"] = True
        return result

    # Qty Break
    if method == "Qty Break":
        qty = actual_data["actual_pieces"] or actual_data["actual_weight"] or 1
        applicable = _resolve_qty_break_rate(charge_doc, qty, record_type)
        if not applicable:
            result["calc_notes"] = "No qty break rates defined"
            return result
        rate = flt(applicable.get("unit_rate", 0))
        amount = rate * qty
        result["amount"] = amount
        result["calc_notes"] = (
            f"Qty Break: {qty} × {rate} = {amount} (Break: {applicable.get('qty_break', 0)})"
        )
        result["success"] = True
        return result

    # Standard methods via engine
    rate_data = _prepare_rate_data(charge_doc, is_revenue=is_revenue)
    if not rate_data:
        result["calc_notes"] = "Could not prepare rate data"
        return result

    rate = flt(rate_data.get("rate", 0))
    if not rate and rate_data.get("calculation_method") not in ("Fixed Amount", "Flat Rate"):
        result["calc_notes"] = "No unit rate specified"
        return result

    if rate_data.get("calculation_method") == "Percentage":
        base = flt(rate_data.get("base_amount", 0))
        if not base:
            result["calc_notes"] = "Base Amount is required for Percentage calculation"
            return result

    try:
        engine = TransportRateCalculationEngine()
        res = engine.calculate_transport_rate(rate_data=rate_data, **actual_data)
        if res.get("success"):
            result["amount"] = flt(res.get("amount", 0))
            result["calc_notes"] = res.get("calculation_details", "")
            result["success"] = True
        else:
            result["calc_notes"] = f"Calculation failed: {res.get('error', 'Unknown error')}"
            result["error"] = res.get("error")
    except Exception as e:
        frappe.log_error(f"Charge calculation error: {str(e)}")
        result["calc_notes"] = f"Error: {str(e)}"
        result["error"] = str(e)

    return result


# Charge doctypes that use centralized calculation (for client-side recalculation API)
CHARGE_DOCTYPES = (
    "Transport Order Charges",
    "Transport Job Charges",
    "Air Booking Charges",
    "Air Shipment Charges",
    "Sea Booking Charges",
    "Sea Freight Charges",
    "Declaration Charges",
    "Declaration Order Charges",
)


@frappe.whitelist()
def calculate_charge_row(doctype: str, parenttype: str, parent: str, row_data: str):
    """
    Recalculate estimated_revenue and estimated_cost for a charge row.
    Used by client-side form events when user changes unit_rate, calculation_method, etc.

    Args:
        doctype: Charge child doctype (e.g. 'Air Booking Charges')
        parenttype: Parent doctype (e.g. 'Air Booking')
        parent: Parent document name
        row_data: JSON string of the charge row data (or dict)

    Returns:
        dict with estimated_revenue, estimated_cost, revenue_calc_notes, cost_calc_notes
    """
    import json

    if doctype not in CHARGE_DOCTYPES:
        return {"success": False, "error": f"Unsupported doctype: {doctype}"}

    try:
        if isinstance(row_data, str):
            row_dict = json.loads(row_data)
        else:
            row_dict = row_data

        doc = frappe.new_doc(doctype)
        doc.update(row_dict)
        doc.parenttype = parenttype
        doc.parent = parent

        parent_doc = None
        if parent and parent not in ("new", ""):
            try:
                parent_doc = frappe.get_doc(parenttype, parent)
            except Exception:
                pass

        rev = calculate_charge_revenue(doc, parent_doc)
        cost = calculate_charge_cost(doc, parent_doc)

        return {
            "success": True,
            "estimated_revenue": flt(rev.get("amount", 0)),
            "estimated_cost": flt(cost.get("amount", 0)),
            "revenue_calc_notes": rev.get("calc_notes", ""),
            "cost_calc_notes": cost.get("calc_notes", ""),
        }
    except Exception as e:
        frappe.log_error(f"Charge row calculation error: {str(e)}")
        return {"success": False, "error": str(e)}
