# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate, now_datetime
from typing import Dict, Any, Optional, List
from logistics.sustainability.api.integration_layer import is_sustainability_enabled_for_module, trigger_carbon_calculation, trigger_energy_consumption_recording

class SustainabilityIntegration:
    """Centralized sustainability integration for all logistics modules"""
    
    def __init__(self, doctype: str, docname: str, module: str):
        self.doctype = doctype
        self.docname = docname
        self.module = module
        self.enabled = is_sustainability_enabled_for_module(module)
    
    def record_transport_sustainability(self, doc: Any) -> Dict[str, Any]:
        """Record sustainability metrics for transport operations"""
        if not self.enabled:
            return {"status": "skipped", "message": f"Sustainability tracking not enabled for {self.module}"}

        results = []
        company = getattr(doc, "company", None)
        vehicle_type = getattr(doc, "vehicle_type", None)
        total_distance = flt(getattr(doc, "total_distance", 0))
        fuel_consumption = flt(getattr(doc, "fuel_consumption", 0))

        # Fallback: aggregate distance from legs (Transport Leg) when job-level total_distance is empty
        if not total_distance and hasattr(doc, "legs") and doc.legs:
            for leg_row in doc.legs:
                transport_leg_link = getattr(leg_row, "transport_leg", None)
                if transport_leg_link:
                    try:
                        leg_doc = frappe.get_cached_doc("Transport Leg", transport_leg_link)
                        dist = flt(
                            getattr(leg_doc, "distance_km", 0)
                            or getattr(leg_doc, "actual_distance_km", 0)
                            or getattr(leg_doc, "route_distance_km", 0)
                        )
                        if dist:
                            total_distance += dist
                            if not vehicle_type:
                                vehicle_type = getattr(leg_doc, "vehicle_type", None)
                    except Exception:
                        pass
                # Direct fields on child row (if present)
                dist = flt(getattr(leg_row, "distance", 0) or getattr(leg_row, "distance_km", 0))
                if dist:
                    total_distance += dist
                if not vehicle_type:
                    vehicle_type = getattr(leg_row, "vehicle_type", None)

        # Calculate carbon footprint from distance and vehicle type
        if total_distance > 0 and vehicle_type:
            emission_factor = self._get_vehicle_emission_factor(vehicle_type)
            if emission_factor:
                carbon_result = trigger_carbon_calculation(
                    module=self.module,
                    activity_type="Transport",
                    activity_data={"activity_value": total_distance, "vehicle_type": vehicle_type},
                    activity_unit="km",
                    company=company,
                    reference_doctype=self.doctype,
                    reference_docname=self.docname,
                    description=f"Transport {self.doctype} {self.docname} - {total_distance} km",
                )
                results.append(carbon_result)

        # Record fuel consumption if available
        if fuel_consumption > 0:
            energy_result = trigger_energy_consumption_recording(
                module=self.module,
                energy_type="Diesel",
                consumption_value=fuel_consumption,
                unit_of_measure="Liters",
                company=company,
                reference_doctype=self.doctype,
                reference_docname=self.docname,
                description=f"Fuel consumption for {self.doctype} {self.docname}",
            )
            results.append(energy_result)

        return {
            "status": "success",
            "message": f"Sustainability metrics recorded for {self.doctype}",
            "results": results,
        }
    
    def record_warehouse_sustainability(self, doc: Any) -> Dict[str, Any]:
        """Record sustainability metrics for warehouse operations"""
        if not self.enabled:
            return {"status": "skipped", "message": f"Sustainability tracking not enabled for {self.module}"}

        results = []
        company = getattr(doc, "company", None)
        site = getattr(doc, "warehouse", None) or getattr(doc, "site", None)
        facility = getattr(doc, "facility", None)

        # Use job-level total_energy_consumption (primary) or sum from operations
        total_energy = flt(getattr(doc, "total_energy_consumption", 0))
        if total_energy <= 0 and hasattr(doc, "operations") and doc.operations:
            for op in doc.operations:
                energy = flt(getattr(op, "energy_consumption", 0))
                if energy <= 0:
                    energy = flt(getattr(op, "actual_hours", 0) or getattr(op, "total_std_hours", 0)) * 1.0  # kWh estimate
                total_energy += energy

        if total_energy > 0:
            energy_result = trigger_energy_consumption_recording(
                module=self.module,
                energy_type="Electricity",
                consumption_value=total_energy,
                unit_of_measure="kWh",
                company=company,
                reference_doctype=self.doctype,
                reference_docname=self.docname,
                site=site,
                facility=facility,
                description=f"Energy consumption for {self.doctype} {self.docname}",
            )
            results.append(energy_result)

        # Record waste generation if available
        waste_val = flt(getattr(doc, "waste_generated", 0) or getattr(doc, "total_waste_generated", 0))
        if waste_val > 0:
            waste_result = self._record_waste_metrics(doc)
            if waste_result:
                results.append(waste_result)

        return {
            "status": "success",
            "message": f"Sustainability metrics recorded for {self.doctype}",
            "results": results,
        }
    
    def record_shipment_sustainability(self, doc: Any) -> Dict[str, Any]:
        """Record sustainability metrics for air/sea shipments"""
        if not self.enabled:
            return {"status": "skipped", "message": f"Sustainability tracking not enabled for {self.module}"}
        
        results = []
        
        # Calculate carbon footprint based on weight and distance
        if hasattr(doc, 'weight') and hasattr(doc, 'origin_port') and hasattr(doc, 'destination_port'):
            # Get distance between ports (simplified calculation)
            distance = self._calculate_port_distance(doc.origin_port, doc.destination_port)
            if distance and doc.weight:
                # Use appropriate emission factor based on transport mode
                emission_factor = self._get_shipment_emission_factor(self.module)
                if emission_factor:
                    carbon_result = trigger_carbon_calculation(
                        module=self.module,
                        activity_type="Transport",
                        activity_data={"activity_value": (flt(doc.weight) / 1000) * flt(distance)},
                        activity_unit="ton-km",
                        company=doc.company,
                        reference_doctype=self.doctype,
                        reference_docname=self.docname,
                        description=f"Freight transport from {doc.origin_port} to {doc.destination_port}"
                    )
                    results.append(carbon_result)
        
        return {
            "status": "success",
            "message": f"Sustainability metrics recorded for {self.doctype}",
            "results": results
        }
    
    def record_general_sustainability(self, doc: Any) -> Dict[str, Any]:
        """Record general sustainability metrics for any job type (Customs, Job Management, etc.)."""
        if not self.enabled:
            return {"status": "skipped", "message": f"Sustainability tracking not enabled for {self.module}"}

        results = []
        company = getattr(doc, "company", None)
        energy_val = flt(
            getattr(doc, "energy_consumption", 0) or getattr(doc, "estimated_energy_consumption", 0)
        )
        carbon_val = flt(getattr(doc, "estimated_carbon_footprint", 0))

        if energy_val > 0:
            energy_result = trigger_energy_consumption_recording(
                module=self.module,
                energy_type="Electricity",
                consumption_value=energy_val,
                unit_of_measure="kWh",
                company=company,
                reference_doctype=self.doctype,
                reference_docname=self.docname,
                description=f"General energy consumption for {self.doctype} {self.docname}",
            )
            results.append(energy_result)

        if carbon_val > 0:
            from logistics.sustainability.api.sustainability_api import SustainabilityAPI

            api = SustainabilityAPI(company)
            record = api.create_carbon_footprint(
                module=self.module,
                reference_doctype=self.doctype,
                reference_name=self.docname,
                total_emissions=carbon_val,
                calculation_method="Estimated",
                notes=f"Carbon footprint for {self.doctype} {self.docname}",
            )
            results.append({"status": "success", "record": record})

        return {
            "status": "success",
            "message": f"Sustainability metrics recorded for {self.doctype}",
            "results": results,
        }
    
    def _get_vehicle_emission_factor(self, vehicle_type: str) -> Optional[float]:
        """Get emission factor for vehicle type from Emission Factors DocType, with fallback defaults."""
        try:
            factors = frappe.get_all(
                "Emission Factors",
                filters={
                    "category": "Transport",
                    "is_active": 1,
                    "module": ["in", ["Transport", "All"]],
                },
                fields=["factor_name", "factor_value", "unit_of_measure"],
                order_by="valid_from desc, creation desc",
            )
            vt_lower = (vehicle_type or "").lower()
            for f in factors:
                if vt_lower in (f.get("factor_name") or "").lower():
                    return flt(f.get("factor_value"))
            for f in factors:
                uom = (f.get("unit_of_measure") or "").lower()
                if "per km" in uom or "/km" in uom:
                    return flt(f.get("factor_value"))
            if factors:
                return flt(factors[0].get("factor_value"))
        except Exception:
            pass
        vehicle_factors = {"Truck": 0.8, "Van": 0.3, "Car": 0.2, "Motorcycle": 0.08}
        return vehicle_factors.get(vehicle_type, 0.2)

    def _get_shipment_emission_factor(self, module: str) -> Optional[float]:
        """Get emission factor for shipment type from Emission Factors DocType."""
        try:
            mod_filter = "Air Freight" if module == "Air Freight" else "Sea Freight"
            factors = frappe.get_all(
                "Emission Factors",
                filters={
                    "category": "Transport",
                    "is_active": 1,
                    "module": ["in", [mod_filter, "All"]],
                },
                fields=["factor_name", "factor_value", "unit_of_measure"],
                order_by="valid_from desc, creation desc",
                limit=5,
            )
            for f in factors:
                uom = (f.get("unit_of_measure") or "").lower()
                if "ton-km" in uom or "ton km" in uom:
                    return flt(f.get("factor_value"))
            if factors:
                return flt(factors[0].get("factor_value"))
        except Exception:
            pass
        return 0.5 if module == "Air Freight" else 0.01

    def _calculate_port_distance(self, origin: str, destination: str) -> Optional[float]:
        """Estimate distance between ports. Uses Port Distance matrix if available, else defaults."""
        if not origin or not destination or origin == destination:
            return 1000.0
        try:
            if frappe.db.table_exists("Port Distance"):
                dist = frappe.db.get_value(
                    "Port Distance",
                    {"origin_port": origin, "destination_port": destination},
                    "distance_km",
                )
                if dist:
                    return flt(dist)
            if frappe.db.table_exists("Distance Matrix"):
                dist = frappe.db.get_value(
                    "Distance Matrix",
                    {"origin": origin, "destination": destination},
                    "distance_km",
                )
                if dist:
                    return flt(dist)
        except Exception:
            pass
        return 5000.0 if self.module == "Air Freight" else 10000.0
    
    def _record_waste_metrics(self, doc: Any) -> Optional[Dict[str, Any]]:
        """Record waste generation metrics"""
        try:
            from logistics.sustainability.api.sustainability_api import record_sustainability_metric

            metric_name = record_sustainability_metric(
                module=self.module,
                reference_doctype=self.doctype,
                reference_name=self.docname,
                metric_type="Waste Reduction",
                current_value=flt(getattr(doc, "waste_generated", 0) or getattr(doc, "total_waste_generated", 0)),
                unit_of_measure="kg",
                company=getattr(doc, "company", None),
                description=f"Waste generated from {self.doctype} {self.docname}",
            )
            return {"status": "success", "record": metric_name} if metric_name else None
        except Exception as e:
            frappe.log_error(f"Error recording waste metrics: {e}", "Sustainability Integration Error")
            return None

def integrate_sustainability(doctype: str, docname: str, module: str, doc: Any) -> Dict[str, Any]:
    """Main function to integrate sustainability tracking into any logistics module"""
    integration = SustainabilityIntegration(doctype, docname, module)
    
    if module == "Transport":
        return integration.record_transport_sustainability(doc)
    elif module == "Warehousing":
        return integration.record_warehouse_sustainability(doc)
    elif module in ["Air Freight", "Sea Freight"]:
        return integration.record_shipment_sustainability(doc)
    else:
        return integration.record_general_sustainability(doc)
