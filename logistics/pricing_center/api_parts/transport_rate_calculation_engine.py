# Copyright (c) 2024, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

"""
Transport Rate Calculation Engine - delegates to unified RateCalculationEngine.

Transport-specific logic (get_matching_rates, route lookup) remains here.
Core calculation delegates to logistics.utils.rate_calculation_engine.
"""

import frappe
import json
from typing import Dict, List

from logistics.utils.rate_calculation_engine import (
    RateCalculationEngine,
    get_available_calculation_methods,
    get_available_unit_types,
    validate_rate_data,
)


class TransportRateCalculationEngine(RateCalculationEngine):
    """
    Transport-specific extension of RateCalculationEngine.

    Adds get_matching_rates and route lookup for Transport Rate / Tariff.
    """

    def get_matching_rates(
        self,
        origin_location: str = None,
        destination_location: str = None,
        vehicle_type: str = None,
        load_type: str = None,
        container_type: str = None,
        tariff_name: str = None,
        **kwargs,
    ) -> List[Dict]:
        """Get matching transport rates based on criteria."""
        try:
            filters = {"enabled": 1}

            if tariff_name:
                tariff_doc = frappe.get_doc("Tariff", tariff_name)
                rates = []
                for rate in tariff_doc.transport_rates:
                    rate_dict = rate.as_dict()
                    if self._matches_criteria(
                        rate_dict,
                        origin_location,
                        destination_location,
                        vehicle_type,
                        load_type,
                        container_type,
                    ):
                        rates.append(rate_dict)
                return rates
            else:
                filters.update({
                    "location_from": origin_location,
                    "location_to": destination_location,
                    "vehicle_type": vehicle_type,
                    "load_type": load_type,
                    "container_type": container_type,
                })
                filters = {k: v for k, v in filters.items() if v is not None}
                return frappe.get_all("Transport Rate", filters=filters, fields=["*"])
        except Exception as e:
            frappe.log_error(f"Error getting matching rates: {str(e)}")
            return []

    def _matches_criteria(
        self,
        rate_data: Dict,
        origin: str,
        destination: str,
        vehicle_type: str,
        load_type: str,
        container_type: str,
    ) -> bool:
        """Check if rate matches the given criteria."""
        if origin and rate_data.get("location_from") != origin:
            return False
        if destination and rate_data.get("location_to") != destination:
            return False
        if vehicle_type and rate_data.get("vehicle_type") != vehicle_type:
            return False
        if load_type and rate_data.get("load_type") != load_type:
            return False
        if container_type and rate_data.get("container_type") != container_type:
            return False
        return True


@frappe.whitelist()
def calculate_transport_rate_for_quote(rate_data: str, **kwargs) -> Dict:
    """API endpoint for Sales Quote to calculate transport rates."""
    try:
        rate_config = json.loads(rate_data) if isinstance(rate_data, str) else rate_data
        calculator = TransportRateCalculationEngine()
        return calculator.calculate_transport_rate(rate_data=rate_config, **kwargs)
    except Exception as e:
        frappe.log_error(f"Transport rate calculation API error: {str(e)}")
        return {"success": False, "error": str(e), "amount": 0}


@frappe.whitelist()
def get_transport_rates_for_route(
    origin: str = None,
    destination: str = None,
    vehicle_type: str = None,
    load_type: str = None,
    container_type: str = None,
    tariff_name: str = None,
) -> List[Dict]:
    """API endpoint to get transport rates for a specific route."""
    try:
        calculator = TransportRateCalculationEngine()
        return calculator.get_matching_rates(
            origin_location=origin,
            destination_location=destination,
            vehicle_type=vehicle_type,
            load_type=load_type,
            container_type=container_type,
            tariff_name=tariff_name,
        )
    except Exception as e:
        frappe.log_error(f"Get transport rates API error: {str(e)}")
        return []


@frappe.whitelist()
def calculate_bulk_transport_rates(
    rate_configurations: str, actual_data: str
) -> List[Dict]:
    """API endpoint to calculate multiple transport rates at once."""
    try:
        rate_configs = (
            json.loads(rate_configurations)
            if isinstance(rate_configurations, str)
            else rate_configurations
        )
        actual_data_dict = (
            json.loads(actual_data) if isinstance(actual_data, str) else actual_data
        )
        calculator = TransportRateCalculationEngine()
        return calculator.calculate_bulk_rates(
            rate_configurations=rate_configs,
            actual_data=actual_data_dict,
        )
    except Exception as e:
        frappe.log_error(f"Bulk transport rate calculation API error: {str(e)}")
        return []
