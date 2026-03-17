# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Centralized charge calculation for Air, Sea, Transport, and Declaration charges.

Follows the Sales Quote charge calculation pattern using RateCalculationEngine.
Supports Weight Break and Qty Break methods via Sales Quote Weight Break / Qty Break tables.
Uses calculation_method and unit_type for engine; legacy values (e.g. Per kg) are normalized via mapping.
"""

import json

import frappe
from frappe.utils import flt
from typing import Dict, List, Optional, Any

from logistics.utils.rate_calculation_engine import RateCalculationEngine

# Field mapping: charge doctypes use revenue_calculation_method (revenue) and cost_calculation_method (cost)
REVENUE_METHOD_FIELDS = ("revenue_calculation_method", "calculation_method")  # calculation_method for backward compat
RATE_FIELDS = ("unit_rate", "rate")

# Map legacy/display values (e.g. "Per kg", "Per m³") to engine calculation_method + unit_type
METHOD_TO_ENGINE = {
    "Per kg": ("Per Unit", "Weight"),
    "Per m³": ("Per Unit", "Volume"),
    "Per m3": ("Per Unit", "Volume"),
    "Per package": ("Per Unit", "Package"),
    "Per piece": ("Per Unit", "Piece"),
    "Per shipment": ("Flat Rate", None),
    "Fixed amount": ("Flat Rate", None),
    "Flat rate": ("Flat Rate", None),
    "Weight Break": ("Weight Break", "Weight"),
    "Qty Break": ("Qty Break", "Piece"),
    "Per Day": ("Per Unit", "Day"),
    "Per TEU": ("Per Unit", "TEU"),
    "Per container": ("Per Unit", "Container"),
    "Per Container": ("Per Unit", "Container"),
    "Other": ("Flat Rate", None),
}
UNIT_TYPE_FIELDS = ("unit_type",)
COST_METHOD_FIELDS = ("cost_calculation_method",)
COST_RATE_FIELDS = ("unit_cost",)
COST_UNIT_TYPE_FIELDS = ("cost_unit_type",)

# Parent doctype -> quantity field mapping for actual data extraction
PARENT_QUANTITY_FIELDS = {
    "Sales Quote": ("weight", "volume", "chargeable", "total_pieces"),
    "Air Booking": ("total_weight", "chargeable_weight", "total_volume", "total_pieces"),
    "Air Shipment": ("total_weight", "chargeable_weight", "total_volume", "total_pieces"),
    "Sea Booking": ("total_weight", "total_volume", "total_pieces", "total_teu", "total_containers"),
    "Sea Shipment": ("total_weight", "total_volume", "total_pieces", "total_teu", "total_containers"),
    "Sea Consolidation": ("total_weight", "chargeable_weight", "total_volume", "total_packages", "total_teu", "total_containers"),
    "Declaration": ("total_weight", "total_volume", "total_pieces"),
    "Declaration Order": ("total_weight", "total_volume", "total_pieces"),
    "Transport Order": ("total_weight", "total_volume", "total_distance", "total_pieces"),
    "Transport Job": ("total_weight", "total_volume", "total_distance", "total_pieces"),
    "Warehouse Job": ("total_weight", "total_volume", "total_pieces"),
}


def _get_field(doc: Any, *field_names: str, default=None):
    """Get first non-empty value from doc for given field names."""
    for name in field_names:
        val = getattr(doc, name, None)
        if val is not None and val != "":
            return val
    return default


def _sum_distance_from_legs(parent_doc: Any) -> float:
    """Sum distance from legs/routing_legs when parent has no total_distance field."""
    total = 0.0
    legs = (
        getattr(parent_doc, "legs", None)
        or getattr(parent_doc, "routing_legs", None)
        or []
    )
    for leg in legs:
        val = _get_field(
            leg,
            "distance_km", "actual_distance_km", "route_distance_km",
            "distance", "total_distance"
        )
        if val is not None and val != "":
            total += flt(val)
        else:
            # Transport Job Legs links to Transport Leg - fetch distance from linked doc
            transport_leg = getattr(leg, "transport_leg", None)
            if transport_leg:
                try:
                    tl = frappe.db.get_value(
                        "Transport Leg",
                        transport_leg,
                        ["actual_distance_km", "distance_km", "route_distance_km"],
                        as_dict=True,
                    )
                    if tl:
                        val = tl.get("actual_distance_km") or tl.get("distance_km") or tl.get("route_distance_km")
                        if val is not None:
                            total += flt(val)
                except Exception:
                    pass
    return total


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
    """Extract quantity data from parent document for charge calculation.

    On Sales Quote: quantity is estimated (weight, volume, etc. from quote header).
    On Booking/Shipment: quantity is actual (total_weight, chargeable_weight, etc. from packages/actuals).
    """
    if not parent_doc:
        return {
            "actual_quantity": 0,
            "actual_weight": 0,
            "actual_volume": 0,
            "actual_distance": 0,
            "actual_pieces": 0,
            "actual_teu": 0,
            "actual_containers": 0,
            "actual_operation_time": 0,
        }

    parent_doctype = getattr(parent_doc, "doctype", None) or parent_doc.get("doctype")
    fields = PARENT_QUANTITY_FIELDS.get(parent_doctype, ())

    weight = flt(
        _get_field(
            parent_doc,
            "total_weight", "chargeable_weight", "weight", "chargeable",
            "air_weight", "sea_weight", "transport_weight"
        ) or 0
    )
    volume = flt(
        _get_field(
            parent_doc,
            "total_volume", "volume",
            "air_volume", "sea_volume", "transport_volume"
        ) or 0
    )
    pieces = flt(
        _get_field(parent_doc, "total_pieces", "total_packages", "pieces") or 0
    )
    if pieces <= 0 and hasattr(parent_doc, "packages") and parent_doc.packages:
        pieces = len(parent_doc.packages)
    distance = flt(
        _get_field(
            parent_doc,
            "total_distance", "distance", "transport_distance",
            "distance_km", "total_distance_km"
        ) or 0
    )
    # Sum distance from legs when parent has no total_distance (Transport Order, Transport Job, etc.)
    if distance <= 0:
        distance = _sum_distance_from_legs(parent_doc)
    teu = flt(
        _get_field(parent_doc, "total_teu", "teu") or 0
    )
    containers = flt(_get_field(parent_doc, "total_containers") or 0)
    if containers <= 0 and hasattr(parent_doc, "containers") and parent_doc.containers:
        containers = len(parent_doc.containers)
    if containers <= 0 and hasattr(parent_doc, "consolidation_containers") and parent_doc.consolidation_containers:
        containers = len(parent_doc.consolidation_containers)
    if containers <= 0 and _get_field(parent_doc, "container_no"):
        containers = 1
    operation_time = flt(
        _get_field(parent_doc, "total_operation_time", "operation_time", "actual_hours") or 0
    )

    return {
        "actual_quantity": weight or volume or pieces or distance or teu or containers or 1,
        "actual_weight": weight,
        "actual_volume": volume,
        "actual_distance": distance,
        "actual_pieces": pieces,
        "actual_teu": teu,
        "actual_containers": containers,
        "actual_operation_time": operation_time,
    }


def _get_quantity_for_calculation_method(
    actual_data: Dict, method: str, unit_type: str, is_revenue: bool = True
) -> float:
    """Get quantity from parent based on calculation method and unit_type.

    Quantity is the estimated value (Sales Quote) or actual value (Booking/Shipment)
    for the given unit type (weight, volume, pieces, distance, teu, container, etc.).
    """
    if not method:
        return 0.0
    method = (method or "").strip()
    if method in ("Flat Rate", "Fixed Amount"):
        return 1.0
    if method == "Percentage":
        return 1.0
    if method == "Weight Break":
        return flt(actual_data.get("actual_weight") or 0)
    if method == "Qty Break":
        return flt(
            actual_data.get("actual_pieces") or actual_data.get("actual_weight") or 1
        )
    # Per Unit, Base Plus Additional, First Plus Additional, Location-based
    ut = (unit_type or "Weight").strip().lower()
    if ut == "weight":
        return flt(actual_data.get("actual_weight") or 0)
    if ut == "volume":
        return flt(actual_data.get("actual_volume") or 0)
    if ut in ("piece", "package"):
        return flt(actual_data.get("actual_pieces") or 0)
    if ut == "distance":
        return flt(actual_data.get("actual_distance") or 0)
    if ut == "teu":
        return flt(actual_data.get("actual_teu") or 0)
    if ut == "container":
        return flt(actual_data.get("actual_containers") or 0)
    if ut in ("day", "operation time"):
        return flt(actual_data.get("actual_operation_time") or 1)
    return flt(actual_data.get("actual_quantity") or 0)


def _normalize_calculation_method(method: str, unit_type: str) -> tuple:
    """Map legacy values (e.g. Per kg) to engine calculation_method and unit_type."""
    if not method:
        return None, unit_type or "Weight"
    mapped = METHOD_TO_ENGINE.get(method.strip())
    if mapped:
        calc_method, mapped_unit = mapped
        return calc_method, mapped_unit or unit_type or "Weight"
    return method, unit_type or "Weight"


def _get_item_code_from_charge(charge_doc: Any) -> Optional[str]:
    """Get item code from charge doc (supports item_code or charge_item)."""
    return _get_field(charge_doc, "item_code", "charge_item")


def _find_matching_rate_in_tariff(tariff_name: str, item_code: str) -> Optional[Dict]:
    """Find matching rate in tariff by item_code. Tariff has transport_rates child table."""
    if not tariff_name or not item_code:
        return None
    try:
        tariff_doc = frappe.get_doc("Tariff", tariff_name)
        rates = getattr(tariff_doc, "transport_rates", None) or []
        for rate in rates:
            if getattr(rate, "item_code", None) == item_code:
                return rate.as_dict() if hasattr(rate, "as_dict") else dict(rate)
        return None
    except Exception:
        return None


def _fetch_rates_from_tariff_if_needed(charge_doc: Any) -> None:
    """
    When use_tariff_in_revenue or use_tariff_in_cost is set, fetch from revenue_tariff
    or cost_tariff respectively and populate rate fields. Falls back to tariff if specific
    one not set.
    """
    item_code = _get_item_code_from_charge(charge_doc)
    if not item_code:
        return

    # Revenue: use revenue_tariff, fallback to tariff
    rev_tariff = getattr(charge_doc, "revenue_tariff", None) or getattr(charge_doc, "tariff", None)
    if getattr(charge_doc, "use_tariff_in_revenue", False) and rev_tariff:
        rate_data = _find_matching_rate_in_tariff(rev_tariff, item_code)
        if rate_data:
            method = rate_data.get("calculation_method") or "Per Unit"
            if hasattr(charge_doc, "revenue_calculation_method"):
                charge_doc.revenue_calculation_method = method
            if hasattr(charge_doc, "calculation_method"):
                charge_doc.calculation_method = method
            rate_val = rate_data.get("rate", 0)
            if hasattr(charge_doc, "rate"):
                charge_doc.rate = rate_val
            if hasattr(charge_doc, "unit_rate"):
                charge_doc.unit_rate = rate_val
            if hasattr(charge_doc, "unit_type"):
                charge_doc.unit_type = rate_data.get("unit_type")
            if hasattr(charge_doc, "currency"):
                charge_doc.currency = rate_data.get("currency") or "USD"
            if hasattr(charge_doc, "minimum_quantity"):
                charge_doc.minimum_quantity = rate_data.get("minimum_quantity", 0)
            if hasattr(charge_doc, "minimum_charge"):
                charge_doc.minimum_charge = rate_data.get("minimum_charge", 0)
            if hasattr(charge_doc, "maximum_charge"):
                charge_doc.maximum_charge = rate_data.get("maximum_charge", 0)
            if hasattr(charge_doc, "base_amount"):
                charge_doc.base_amount = rate_data.get("base_amount", 0)
            if hasattr(charge_doc, "uom"):
                charge_doc.uom = rate_data.get("uom")

    # Cost: use cost_tariff, fallback to tariff
    cost_tariff = getattr(charge_doc, "cost_tariff", None) or getattr(charge_doc, "tariff", None)
    if getattr(charge_doc, "use_tariff_in_cost", False) and cost_tariff:
        rate_data = _find_matching_rate_in_tariff(cost_tariff, item_code)
        if rate_data:
            method = rate_data.get("calculation_method") or "Per Unit"
            if hasattr(charge_doc, "cost_calculation_method"):
                charge_doc.cost_calculation_method = method
            if hasattr(charge_doc, "unit_cost"):
                charge_doc.unit_cost = rate_data.get("rate", 0)
            if hasattr(charge_doc, "cost_unit_type"):
                charge_doc.cost_unit_type = rate_data.get("unit_type")
            if hasattr(charge_doc, "cost_currency"):
                charge_doc.cost_currency = rate_data.get("currency") or "USD"
            if hasattr(charge_doc, "cost_minimum_quantity"):
                charge_doc.cost_minimum_quantity = rate_data.get("minimum_quantity", 0)
            if hasattr(charge_doc, "cost_minimum_charge"):
                charge_doc.cost_minimum_charge = rate_data.get("minimum_charge", 0)
            if hasattr(charge_doc, "cost_maximum_charge"):
                charge_doc.cost_maximum_charge = rate_data.get("maximum_charge", 0)
            if hasattr(charge_doc, "cost_base_amount"):
                charge_doc.cost_base_amount = rate_data.get("base_amount", 0)
            if hasattr(charge_doc, "cost_uom"):
                charge_doc.cost_uom = rate_data.get("uom")


def _prepare_rate_data(
    charge_doc: Any,
    is_revenue: bool = True,
) -> Optional[Dict]:
    """Prepare rate data dict for RateCalculationEngine from charge doc."""
    if is_revenue:
        method = _get_field(charge_doc, *REVENUE_METHOD_FIELDS)
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

    # Map legacy method values to engine format
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
    """Internal: calculate revenue or cost for a charge row. Fills quantity/cost_quantity from parent based on method."""
    _fetch_rates_from_tariff_if_needed(charge_doc)
    result = {
        "amount": 0,
        "calc_notes": "",
        "success": False,
        "error": None,
        "quantity": None,
        "cost_quantity": None,
    }

    if is_revenue:
        method = _get_field(charge_doc, *REVENUE_METHOD_FIELDS)
        record_type = "Selling"
        unit_type = _get_field(charge_doc, *UNIT_TYPE_FIELDS) or "Weight"
    else:
        method = _get_field(charge_doc, *COST_METHOD_FIELDS)
        record_type = "Cost"
        unit_type = _get_field(charge_doc, *COST_UNIT_TYPE_FIELDS) or "Weight"

    if not method:
        result["calc_notes"] = "Charge calculation: No calculation method specified. Set revenue/cost calculation method."
        return result

    if parent_doc is None and getattr(charge_doc, "parent", None):
        parent_name = charge_doc.parent
        # Skip loading parent when it's a temporary name (unsaved document)
        if parent_name and not str(parent_name).startswith("new-") and parent_name not in ("new", ""):
            try:
                parent_doc = frappe.get_doc(charge_doc.parenttype, parent_name)
            except Exception:
                parent_doc = None

    actual_data = _get_parent_actual_data(charge_doc, parent_doc)

    # Derive and set quantity from parent based on calculation method
    derived_qty = _get_quantity_for_calculation_method(
        actual_data, method, unit_type, is_revenue=is_revenue
    )

    # Sales Quote only: use charge row quantity for any unit type when user has entered it
    parent_is_sales_quote = (
        (parent_doc and getattr(parent_doc, "doctype", None) == "Sales Quote")
        or getattr(charge_doc, "parenttype", None) == "Sales Quote"
    )
    if parent_is_sales_quote:
        row_qty = flt(
            _get_field(charge_doc, "quantity") if is_revenue else _get_field(charge_doc, "cost_quantity")
        )
        if row_qty > 0:
            derived_qty = row_qty
            ut = (unit_type or "Weight").strip().lower()
            actual_data["actual_quantity"] = row_qty
            if ut == "weight":
                actual_data["actual_weight"] = row_qty
            elif ut == "volume":
                actual_data["actual_volume"] = row_qty
            elif ut in ("piece", "package"):
                actual_data["actual_pieces"] = row_qty
            elif ut == "distance":
                actual_data["actual_distance"] = row_qty
            elif ut == "teu":
                actual_data["actual_teu"] = row_qty
            elif ut == "container":
                actual_data["actual_containers"] = row_qty
            elif ut in ("day", "operation time"):
                actual_data["actual_operation_time"] = row_qty

    if is_revenue:
        if getattr(charge_doc, "quantity", None) is None or (
            isinstance(getattr(charge_doc, "quantity", None), (int, float))
            and flt(charge_doc.quantity) == 0
        ):
            charge_doc.quantity = derived_qty
        result["quantity"] = flt(getattr(charge_doc, "quantity", None) or derived_qty)
    else:
        if getattr(charge_doc, "cost_quantity", None) is None or (
            isinstance(getattr(charge_doc, "cost_quantity", None), (int, float))
            and flt(charge_doc.cost_quantity) == 0
        ):
            charge_doc.cost_quantity = derived_qty
        result["cost_quantity"] = flt(
            getattr(charge_doc, "cost_quantity", None) or derived_qty
        )

    # Weight Break
    if method == "Weight Break":
        applicable = _resolve_weight_break_rate(
            charge_doc,
            actual_data["actual_weight"],
            record_type,
        )
        if not applicable:
            result["calc_notes"] = "Weight Break: No weight break rates defined for this charge"
            return result
        rate = flt(applicable.get("unit_rate", 0))
        weight = actual_data["actual_weight"]
        calc_base = rate * weight
        min_charge = flt(_get_field(charge_doc, "minimum_charge") or 0) if is_revenue else flt(_get_field(charge_doc, "cost_minimum_charge") or 0)
        max_charge = flt(_get_field(charge_doc, "maximum_charge") or 0) if is_revenue else flt(_get_field(charge_doc, "cost_maximum_charge") or 0)
        amount = calc_base
        if min_charge > 0 and amount < min_charge:
            amount = min_charge
        if max_charge > 0 and amount > max_charge:
            amount = max_charge
        currency = applicable.get("currency") or getattr(charge_doc, "currency", None) or getattr(charge_doc, "cost_currency", None) or "USD"
        weight_break = flt(applicable.get("weight_break", 0))
        detail = (
            f"Weight Break (Weight): Actual weight {weight} kg ≥ break {weight_break} kg → "
            f"Rate {rate} {currency}/kg × {weight} kg = {calc_base} {currency}"
        )
        if min_charge > 0 and calc_base < min_charge and amount == min_charge:
            detail += f"; Minimum charge {min_charge} {currency} applied"
        elif max_charge > 0 and calc_base > max_charge and amount == max_charge:
            detail += f"; Maximum charge {max_charge} {currency} applied"
        if amount != calc_base:
            detail += f" (Final: {amount} {currency})"
        result["amount"] = amount
        result["calc_notes"] = detail
        result["success"] = True
        return result

    # Qty Break
    if method == "Qty Break":
        qty = actual_data["actual_pieces"] or actual_data["actual_weight"] or 1
        applicable = _resolve_qty_break_rate(charge_doc, qty, record_type)
        if not applicable:
            result["calc_notes"] = "Qty Break: No qty break rates defined for this charge"
            return result
        rate = flt(applicable.get("unit_rate", 0))
        calc_base = rate * qty
        min_charge = flt(_get_field(charge_doc, "minimum_charge") or 0) if is_revenue else flt(_get_field(charge_doc, "cost_minimum_charge") or 0)
        max_charge = flt(_get_field(charge_doc, "maximum_charge") or 0) if is_revenue else flt(_get_field(charge_doc, "cost_maximum_charge") or 0)
        amount = calc_base
        if min_charge > 0 and amount < min_charge:
            amount = min_charge
        if max_charge > 0 and amount > max_charge:
            amount = max_charge
        currency = applicable.get("currency") or getattr(charge_doc, "currency", None) or getattr(charge_doc, "cost_currency", None) or "USD"
        qty_break = flt(applicable.get("qty_break", 0))
        detail = (
            f"Qty Break (Piece): Actual qty {qty} pcs ≥ break {qty_break} pcs → "
            f"Rate {rate} {currency}/pc × {qty} pcs = {calc_base} {currency}"
        )
        if min_charge > 0 and calc_base < min_charge and amount == min_charge:
            detail += f"; Minimum charge {min_charge} {currency} applied"
        elif max_charge > 0 and calc_base > max_charge and amount == max_charge:
            detail += f"; Maximum charge {max_charge} {currency} applied"
        if amount != calc_base:
            detail += f" (Final: {amount} {currency})"
        result["amount"] = amount
        result["calc_notes"] = detail
        result["success"] = True
        return result

    # Standard methods via engine
    rate_data = _prepare_rate_data(charge_doc, is_revenue=is_revenue)
    if not rate_data:
        result["calc_notes"] = "Charge calculation: Could not prepare rate data. Check calculation method and unit type."
        return result

    rate = flt(rate_data.get("rate", 0))
    if not rate and rate_data.get("calculation_method") not in ("Fixed Amount", "Flat Rate"):
        result["calc_notes"] = "Charge calculation: No unit rate specified. Enter rate for this charge."
        return result

    if rate_data.get("calculation_method") == "Percentage":
        base = flt(rate_data.get("base_amount", 0))
        if not base:
            result["calc_notes"] = "Charge calculation: Base Amount is required for Percentage method. Enter base amount."
            return result

    # Use quantity from charge row (already set above from method, or user override)
    if is_revenue:
        line_qty = _get_field(charge_doc, "quantity")
    else:
        line_qty = _get_field(charge_doc, "cost_quantity")
    if line_qty is not None and flt(line_qty) > 0:
        qty_val = flt(line_qty)
        actual_data["actual_quantity"] = qty_val
        # When parent has no weight/volume/etc, use charge row quantity for unit-type lookup
        if actual_data.get("actual_weight", 0) <= 0 and actual_data.get("actual_volume", 0) <= 0:
            actual_data["actual_weight"] = qty_val
            actual_data["actual_volume"] = qty_val
            actual_data["actual_pieces"] = max(actual_data.get("actual_pieces", 0), qty_val)

    try:
        engine = RateCalculationEngine()
        res = engine.calculate_rate(rate_data=rate_data, **actual_data)
        if res.get("success"):
            result["amount"] = flt(res.get("amount", 0))
            result["calc_notes"] = res.get("calculation_details", "")
            result["success"] = True
        else:
            result["calc_notes"] = f"Charge calculation failed: {res.get('error', 'Unknown error')}"
            result["error"] = res.get("error")
    except Exception as e:
        frappe.log_error(f"Charge calculation error: {str(e)}")
        result["calc_notes"] = f"Error: {str(e)}"
        result["error"] = str(e)

    return result


# Charge doctypes that use centralized calculation (for client-side recalculation API)
CHARGE_DOCTYPES = (
    "Sales Quote Charge",
    "Transport Order Charges",
    "Transport Job Charges",
    "Air Booking Charges",
    "Air Shipment Charges",
    "Sea Booking Charges",
    "Sea Shipment Charges",
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
        # Skip loading parent when it's a temporary name (unsaved document)
        if parent and parent not in ("new", "") and not str(parent).startswith("new-"):
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
            "quantity": rev.get("quantity"),
            "cost_quantity": cost.get("cost_quantity"),
        }
    except Exception as e:
        frappe.log_error(f"Charge row calculation error: {str(e)}")
        return {"success": False, "error": str(e)}
