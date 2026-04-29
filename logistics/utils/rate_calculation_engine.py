# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Unified Rate Calculation Engine for all logistics charge/rate calculations.

Used by Sales Quote, operational charges (Air, Sea, Transport, Declaration),
and warehouse charge amount calculation.
"""

import frappe
from frappe import _
from frappe.utils import flt
from typing import Dict, List, Optional, Any
from decimal import Decimal, ROUND_HALF_UP
import json


class RateCalculationEngine:
    """
    Unified Rate Calculation Engine for all rate and charge calculations.

    Key Features:
    - All calculation methods: Per Unit, Fixed Amount, Flat Rate, Base Plus Additional,
      First Plus Additional, Percentage, Location-based
    - Quantity-inclusive calculation_details for revenue_calc_notes / cost_calc_notes
    - quantity_used in result for traceability
    - Min/max charge handling
    """

    def __init__(self):
        self.calculation_methods = {
            "Per Unit": self._calculate_per_unit,
            "Fixed Amount": self._calculate_fixed_amount,
            "Flat Rate": self._calculate_flat_rate,
            "Base Plus Additional": self._calculate_base_plus_additional,
            "First Plus Additional": self._calculate_first_plus_additional,
            "Percentage": self._calculate_percentage,
            "Location-based": self._calculate_location_based,
        }

        self.unit_types = {
            "Distance": "km",
            "Weight": "kg",
            "Volume": "m3",
            "Package": "pcs",
            "Piece": "pcs",
            "Job": "job",
            "Trip": "trip",
            "TEU": "teu",
            "Container": "cnt",
            "Shipment": "shipment",
            "Item Count": "items",
            "Handling Unit": "hu",
            "Operation Time": "hrs",
            "Day": "day",
        }

    def calculate_rate(
        self,
        rate_data: Dict,
        actual_quantity: float = 0,
        actual_weight: float = 0,
        actual_chargeable_weight: float = 0,
        actual_volume: float = 0,
        actual_distance: float = 0,
        actual_pieces: float = 0,
        actual_teu: float = 0,
        actual_containers: float = 0,
        actual_operation_time: float = 0,
        **kwargs,
    ) -> Dict:
        """
        Main calculation method for rate/charge amount.

        Args:
            rate_data: Rate configuration (calculation_method, rate/unit_rate, unit_type, etc.)
            actual_quantity: Actual quantity for calculation
            actual_weight: Actual weight in KG
            actual_volume: Actual volume in M3
            actual_distance: Actual distance in KM
            actual_pieces: Actual number of pieces
            actual_teu: Actual TEU count
            actual_operation_time: Actual operation time in hours
            **kwargs: Additional parameters

        Returns:
            Dict with success, amount, calculation_details, quantity_used, etc.
        """
        try:
            if not rate_data:
                return self._create_error_result("Rate data is required")

            # Normalize rate: support both rate and unit_rate
            rate_data = dict(rate_data)
            if "rate" not in rate_data and "unit_rate" in rate_data:
                rate_data["rate"] = rate_data["unit_rate"]
            elif "unit_rate" not in rate_data and "rate" in rate_data:
                rate_data["unit_rate"] = rate_data["rate"]

            calculation_method = rate_data.get("calculation_method", "Per Unit")

            if calculation_method not in self.calculation_methods:
                return self._create_error_result(
                    f"Invalid calculation method: {calculation_method}"
                )

            # Calculate base amount and get quantity used
            base_amount, quantity_used = self.calculation_methods[calculation_method](
                rate_data=rate_data,
                actual_quantity=actual_quantity,
                actual_weight=actual_weight,
                actual_chargeable_weight=actual_chargeable_weight,
                actual_volume=actual_volume,
                actual_distance=actual_distance,
                actual_pieces=actual_pieces,
                actual_teu=actual_teu,
                actual_containers=actual_containers,
                actual_operation_time=actual_operation_time,
                **kwargs,
            )

            # Apply minimum and maximum charges
            final_amount = self._apply_min_max_charges(base_amount, rate_data)

            # Round to 2 decimal places
            final_amount = float(
                Decimal(str(final_amount)).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
            )

            return {
                "success": True,
                "amount": final_amount,
                "base_amount": base_amount,
                "calculation_method": calculation_method,
                "rate_data": rate_data,
                "calculation_details": self._get_calculation_details(
                    calculation_method,
                    rate_data,
                    final_amount,
                    quantity_used=quantity_used,
                    base_amount=base_amount,
                ),
                "quantity_used": quantity_used,
                "currency": rate_data.get("currency", "USD"),
                "item_code": rate_data.get("item_code"),
                "item_name": rate_data.get("item_name"),
            }

        except Exception as e:
            frappe.log_error(f"Rate calculation error: {str(e)}")
            return self._create_error_result(f"Calculation failed: {str(e)}")

    def calculate_transport_rate(self, rate_data: Dict, **kwargs) -> Dict:
        """Backward compatibility alias for calculate_rate."""
        return self.calculate_rate(rate_data=rate_data, **kwargs)

    def calculate_bulk_rates(
        self,
        rate_configurations: List[Dict],
        actual_data: Dict,
    ) -> List[Dict]:
        """Calculate rates for multiple configurations."""
        results = []
        for rate_config in rate_configurations:
            result = self.calculate_rate(rate_data=rate_config, **actual_data)
            results.append(result)
        return results

    def _get_quantity_for_unit_type(
        self,
        unit_type: str,
        actual_quantity: float,
        actual_weight: float,
        actual_chargeable_weight: float,
        actual_volume: float,
        actual_distance: float,
        actual_pieces: float,
        actual_teu: float,
        actual_operation_time: float = 0,
        actual_containers: float = 0,
        **kwargs,
    ) -> float:
        """Get quantity based on unit type."""
        ac_items = kwargs.get("actual_item_count")
        ah_units = kwargs.get("actual_handling_units")
        trips = kwargs.get("actual_trips")
        days = kwargs.get("actual_days")

        if unit_type == "Weight":
            return actual_weight
        elif unit_type == "Chargeable Weight":
            cw = flt(actual_chargeable_weight or kwargs.get("actual_chargeable_weight", 0))
            if cw > 0:
                return cw
            return flt(actual_weight or 0)
        elif unit_type == "Volume":
            return actual_volume
        elif unit_type == "Distance":
            return actual_distance
        elif unit_type in ("Package", "Piece"):
            return actual_pieces
        elif unit_type == "TEU":
            return actual_teu
        elif unit_type == "Container":
            return flt(actual_containers or kwargs.get("actual_containers", 0))
        elif unit_type == "Operation Time":
            return actual_operation_time
        elif unit_type == "Day":
            d = flt(days or 0)
            if d > 0:
                return d
            return flt(actual_operation_time or 0) or 1.0
        elif unit_type == "Item Count":
            return flt(ac_items or 0)
        elif unit_type == "Handling Unit":
            hu = flt(ah_units or 0)
            return hu if hu > 0 else 1.0
        elif unit_type == "Job":
            return 1.0
        elif unit_type == "Trip":
            t = flt(trips or 0)
            return t if t > 0 else 1.0
        elif unit_type == "Shipment":
            return 1.0
        else:
            return actual_quantity

    def _calculate_per_unit(
        self,
        rate_data: Dict,
        actual_quantity: float = 0,
        actual_weight: float = 0,
        actual_chargeable_weight: float = 0,
        actual_volume: float = 0,
        actual_distance: float = 0,
        actual_pieces: float = 0,
        actual_teu: float = 0,
        actual_operation_time: float = 0,
        actual_containers: float = 0,
        **kwargs,
    ) -> tuple:
        """Calculate rate using Per Unit method. Returns (amount, quantity_used)."""
        rate = flt(rate_data.get("rate", 0) or rate_data.get("unit_rate", 0))
        unit_type = rate_data.get("unit_type", "Weight")
        quantity = self._get_quantity_for_unit_type(
            unit_type,
            actual_quantity,
            actual_weight,
            actual_chargeable_weight,
            actual_volume,
            actual_distance,
            actual_pieces,
            actual_teu,
            actual_operation_time,
            actual_containers or kwargs.get("actual_containers", 0),
            **kwargs,
        )
        return rate * quantity, quantity

    def _calculate_fixed_amount(
        self,
        rate_data: Dict,
        actual_quantity: float = 0,
        **kwargs,
    ) -> tuple:
        """Calculate rate using Fixed Amount method. Returns (amount, quantity_used)."""
        rate = flt(rate_data.get("rate", 0) or rate_data.get("unit_rate", 0))
        quantity = flt(actual_quantity or 0) or 1
        return rate * quantity, quantity

    def _calculate_flat_rate(self, rate_data: Dict, **kwargs) -> tuple:
        """Calculate rate using Flat Rate method. Returns (amount, quantity_used)."""
        rate = flt(rate_data.get("rate", 0) or rate_data.get("unit_rate", 0))
        return rate, 0

    def _calculate_base_plus_additional(
        self,
        rate_data: Dict,
        actual_quantity: float = 0,
        actual_weight: float = 0,
        actual_chargeable_weight: float = 0,
        actual_volume: float = 0,
        actual_distance: float = 0,
        actual_pieces: float = 0,
        actual_teu: float = 0,
        actual_operation_time: float = 0,
        actual_containers: float = 0,
        **kwargs,
    ) -> tuple:
        """Calculate rate using Base Plus Additional. Returns (amount, quantity_used)."""
        base_amount = flt(rate_data.get("base_amount", 0))
        rate = flt(rate_data.get("rate", 0) or rate_data.get("unit_rate", 0))
        base_quantity = flt(rate_data.get("base_quantity", 1))
        unit_type = rate_data.get("unit_type", "Weight")
        total_quantity = self._get_quantity_for_unit_type(
            unit_type,
            actual_quantity,
            actual_weight,
            actual_chargeable_weight,
            actual_volume,
            actual_distance,
            actual_pieces,
            actual_teu,
            actual_operation_time,
            actual_containers or kwargs.get("actual_containers", 0),
            **kwargs,
        )
        additional_quantity = max(0, total_quantity - base_quantity)
        additional_amount = rate * additional_quantity
        return base_amount + additional_amount, total_quantity

    def _calculate_first_plus_additional(
        self,
        rate_data: Dict,
        actual_quantity: float = 0,
        actual_weight: float = 0,
        actual_chargeable_weight: float = 0,
        actual_volume: float = 0,
        actual_distance: float = 0,
        actual_pieces: float = 0,
        actual_teu: float = 0,
        actual_operation_time: float = 0,
        actual_containers: float = 0,
        **kwargs,
    ) -> tuple:
        """Calculate rate using First Plus Additional. Returns (amount, quantity_used)."""
        minimum_unit_rate = flt(rate_data.get("minimum_unit_rate", 0))
        rate = flt(rate_data.get("rate", 0) or rate_data.get("unit_rate", 0))
        minimum_quantity = flt(rate_data.get("minimum_quantity", 0))
        unit_type = rate_data.get("unit_type", "Weight")
        actual_qty = self._get_quantity_for_unit_type(
            unit_type,
            actual_quantity,
            actual_weight,
            actual_chargeable_weight,
            actual_volume,
            actual_distance,
            actual_pieces,
            actual_teu,
            actual_operation_time,
            actual_containers or kwargs.get("actual_containers", 0),
            **kwargs,
        )

        if actual_qty <= minimum_quantity:
            if minimum_unit_rate:
                return minimum_unit_rate * actual_qty, actual_qty
            return rate, actual_qty
        else:
            first_block = (
                (minimum_unit_rate * minimum_quantity) if minimum_unit_rate else rate
            )
            additional_quantity = actual_qty - minimum_quantity
            return first_block + (rate * additional_quantity), actual_qty

    def _calculate_percentage(self, rate_data: Dict, **kwargs) -> tuple:
        """Calculate rate using Percentage method. Returns (amount, quantity_used)."""
        base_amount = flt(rate_data.get("base_amount", 0))
        percentage = flt(rate_data.get("rate", 0) or rate_data.get("unit_rate", 0))
        return base_amount * (percentage / 100), 0

    def _calculate_location_based(self, rate_data: Dict, **kwargs) -> tuple:
        """Calculate rate using Location-based method. Falls back to Per Unit."""
        return self._calculate_per_unit(rate_data, **kwargs)

    def _apply_min_max_charges(self, amount: float, rate_data: Dict) -> float:
        """Apply minimum and maximum charges."""
        min_charge = flt(rate_data.get("minimum_charge", 0))
        max_charge = flt(rate_data.get("maximum_charge", 0))
        if min_charge > 0 and amount < min_charge:
            amount = min_charge
        if max_charge > 0 and amount > max_charge:
            amount = max_charge
        return amount

    def _get_calculation_details(
        self,
        method: str,
        rate_data: Dict,
        amount: float,
        quantity_used: float = 0,
        base_amount: float = None,
    ) -> str:
        """Get human-readable calculation details with quantity, unit type, currency, min/max."""
        rate = flt(rate_data.get("rate", 0) or rate_data.get("unit_rate", 0))
        qty = flt(quantity_used or 0)
        calc_base = base_amount if base_amount is not None else amount
        min_charge = flt(rate_data.get("minimum_charge", 0))
        max_charge = flt(rate_data.get("maximum_charge", 0))
        unit_type = rate_data.get("unit_type", "Weight")
        currency = rate_data.get("currency", "USD")
        # Prefer UOM from charge/rate definition; fall back to unit_types mapping
        uom = (rate_data.get("uom") or "").strip()
        unit_suffix = uom if uom else self.unit_types.get(unit_type, "")

        if method == "Per Unit":
            qty_str = f"{qty} {unit_suffix}".strip() if unit_suffix else f"{qty} units"
            rate_str = f"{rate} {currency}/{unit_suffix}" if unit_suffix else f"{rate} {currency}/unit"
            detail = f"Per Unit ({unit_type}): {qty_str} × {rate_str} = {calc_base} {currency}"
        elif method == "Fixed Amount":
            detail = f"Fixed Amount: {rate} {currency}"
            if qty and qty != 1:
                detail = f"Fixed Amount: {qty} × {rate} {currency} = {calc_base} {currency}"
        elif method == "Flat Rate":
            detail = f"Flat Rate: {calc_base} {currency}"
        elif method == "Base Plus Additional":
            base_amt = flt(rate_data.get("base_amount", 0))
            base_qty = flt(rate_data.get("base_quantity", 1))
            additional_qty = max(0, qty - base_qty)
            detail = f"Base Plus Additional: Base {base_amt} {currency} + ({additional_qty} {unit_suffix} × {rate} {currency}) = {calc_base} {currency}"
        elif method == "First Plus Additional":
            minimum_quantity = flt(rate_data.get("minimum_quantity", 0))
            if qty <= minimum_quantity:
                detail = f"First Plus Additional: First {minimum_quantity} @ {rate} {currency}; Qty {qty} = {calc_base} {currency}"
            else:
                additional_qty = qty - minimum_quantity
                detail = f"First Plus Additional: First {minimum_quantity} @ {rate}; Additional {additional_qty} × {rate} {currency} = {calc_base} {currency}"
        elif method == "Percentage":
            base_amt = flt(rate_data.get("base_amount", 0))
            detail = f"Percentage: Base {base_amt} {currency} × {rate}% = {calc_base} {currency}"
        else:
            detail = f"Calculated: {amount} {currency}"

        # Append min/max when applied
        suffixes = []
        if min_charge > 0 and calc_base < min_charge and amount == min_charge:
            suffixes.append(f"Minimum charge {min_charge} {currency} applied")
        if max_charge > 0 and calc_base > max_charge and amount == max_charge:
            suffixes.append(f"Maximum charge {max_charge} {currency} applied")
        if suffixes:
            detail = f"{detail}; {'; '.join(suffixes)}"
        elif amount != calc_base:
            detail = f"{detail} (final: {amount} {currency})"

        return detail

    def _create_error_result(self, message: str) -> Dict:
        """Create error result."""
        return {"success": False, "error": message, "amount": 0, "quantity_used": 0}


# Backward compatibility alias
TransportRateCalculationEngine = RateCalculationEngine


def get_available_calculation_methods() -> List[str]:
    """Get list of available calculation methods."""
    return [
        "Per Unit",
        "Fixed Amount",
        "Flat Rate",
        "Base Plus Additional",
        "First Plus Additional",
        "Percentage",
        "Location-based",
    ]


def get_available_unit_types() -> List[str]:
    """Get list of available unit types."""
    return [
        "Distance",
        "Weight",
        "Volume",
        "Package",
        "Piece",
        "Job",
        "Trip",
        "TEU",
        "Container",
        "Operation Time",
    ]


def validate_rate_data(rate_data: Dict) -> Dict:
    """Validate rate data before calculation."""
    errors = []
    if not rate_data.get("calculation_method"):
        errors.append("Calculation method is required")
    rate = rate_data.get("rate") or rate_data.get("unit_rate")
    if not rate and rate_data.get("calculation_method") not in (
        "Fixed Amount",
        "Flat Rate",
    ):
        errors.append("Rate is required")
    if not rate_data.get("currency") and rate_data.get("calculation_method"):
        pass  # currency optional
    method = rate_data.get("calculation_method")
    if method == "Base Plus Additional" and not rate_data.get("base_amount"):
        errors.append("Base amount is required for Base Plus Additional method")
    if method == "First Plus Additional" and not rate_data.get("minimum_quantity"):
        errors.append("Minimum quantity is required for First Plus Additional method")
    if method == "Percentage" and not rate_data.get("base_amount"):
        errors.append("Base amount is required for Percentage method")
    return {"valid": len(errors) == 0, "errors": errors}


@frappe.whitelist()
def calculate_rate_for_quote(rate_data: str, **kwargs) -> Dict:
    """Whitelisted API for Sales Quote rate calculation."""
    try:
        rate_config = json.loads(rate_data) if isinstance(rate_data, str) else rate_data
        engine = RateCalculationEngine()
        return engine.calculate_rate(rate_data=rate_config, **kwargs)
    except Exception as e:
        frappe.log_error(f"Rate calculation API error: {str(e)}")
        return {"success": False, "error": str(e), "amount": 0}
