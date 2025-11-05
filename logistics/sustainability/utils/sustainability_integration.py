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
        
        # Calculate carbon footprint based on vehicle type and distance
        if hasattr(doc, 'legs') and doc.legs:
            for leg in doc.legs:
                if leg.distance and leg.vehicle_type:
                    # Get vehicle emission factor
                    vehicle_factor = self._get_vehicle_emission_factor(leg.vehicle_type)
                    if vehicle_factor:
                        carbon_result = trigger_carbon_calculation(
                            module=self.module,
                            activity_type="Transport",
                            activity_data=flt(leg.distance),
                            activity_unit="km",
                            company=doc.company,
                            reference_doctype=self.doctype,
                            reference_docname=self.docname,
                            description=f"Transport leg from {leg.from_location} to {leg.to_location}"
                        )
                        results.append(carbon_result)
        
        # Record fuel consumption if available
        if hasattr(doc, 'fuel_consumption') and doc.fuel_consumption:
            energy_result = trigger_energy_consumption_recording(
                module=self.module,
                energy_type="Diesel",  # Default to diesel for transport
                consumption_value=flt(doc.fuel_consumption),
                unit_of_measure="Liters",
                company=doc.company,
                reference_doctype=self.doctype,
                reference_docname=self.docname,
                description=f"Fuel consumption for {self.doctype} {self.docname}"
            )
            results.append(energy_result)
        
        return {
            "status": "success",
            "message": f"Sustainability metrics recorded for {self.doctype}",
            "results": results
        }
    
    def record_warehouse_sustainability(self, doc: Any) -> Dict[str, Any]:
        """Record sustainability metrics for warehouse operations"""
        if not self.enabled:
            return {"status": "skipped", "message": f"Sustainability tracking not enabled for {self.module}"}
        
        results = []
        
        # Record energy consumption for warehouse operations
        if hasattr(doc, 'operations') and doc.operations:
            for operation in doc.operations:
                if operation.equipment_type and operation.energy_consumption:
                    energy_result = trigger_energy_consumption_recording(
                        module=self.module,
                        energy_type="Electricity",
                        consumption_value=flt(operation.energy_consumption),
                        unit_of_measure="kWh",
                        company=doc.company,
                        reference_doctype=self.doctype,
                        reference_docname=self.docname,
                        site=doc.warehouse if hasattr(doc, 'warehouse') else None,
                        description=f"Energy consumption for {operation.operation_type} operation"
                    )
                    results.append(energy_result)
        
        # Record waste generation if available
        if hasattr(doc, 'waste_generated') and doc.waste_generated:
            waste_result = self._record_waste_metrics(doc)
            if waste_result:
                results.append(waste_result)
        
        return {
            "status": "success",
            "message": f"Sustainability metrics recorded for {self.doctype}",
            "results": results
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
                        activity_type="Freight",
                        activity_data=flt(doc.weight) * flt(distance),
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
        """Record general sustainability metrics for any job type"""
        if not self.enabled:
            return {"status": "skipped", "message": f"Sustainability tracking not enabled for {self.module}"}
        
        results = []
        
        # Record basic energy consumption if available
        if hasattr(doc, 'energy_consumption') and doc.energy_consumption:
            energy_result = trigger_energy_consumption_recording(
                module=self.module,
                energy_type="Electricity",
                consumption_value=flt(doc.energy_consumption),
                unit_of_measure="kWh",
                company=doc.company,
                reference_doctype=self.doctype,
                reference_docname=self.docname,
                description=f"General energy consumption for {self.doctype}"
            )
            results.append(energy_result)
        
        return {
            "status": "success",
            "message": f"Sustainability metrics recorded for {self.doctype}",
            "results": results
        }
    
    def _get_vehicle_emission_factor(self, vehicle_type: str) -> Optional[float]:
        """Get emission factor for vehicle type"""
        # This would typically query the Emission Factors DocType
        # For now, return default values
        vehicle_factors = {
            "Truck": 0.2,  # kg CO2e per km
            "Van": 0.15,
            "Car": 0.12,
            "Motorcycle": 0.08
        }
        return vehicle_factors.get(vehicle_type, 0.2)
    
    def _get_shipment_emission_factor(self, module: str) -> Optional[float]:
        """Get emission factor for shipment type"""
        if module == "Air Freight":
            return 0.5  # kg CO2e per ton-km
        elif module == "Sea Freight":
            return 0.01  # kg CO2e per ton-km
        return None
    
    def _calculate_port_distance(self, origin: str, destination: str) -> Optional[float]:
        """Calculate distance between ports (simplified)"""
        # This would typically use a geocoding service or database
        # For now, return a default distance
        return 1000.0  # Default 1000 km
    
    def _record_waste_metrics(self, doc: Any) -> Optional[Dict[str, Any]]:
        """Record waste generation metrics"""
        try:
            from logistics.sustainability.api.sustainability_api import record_sustainability_metric
            
            return record_sustainability_metric(
                metric_name=f"Waste Generated - {self.doctype}",
                module=self.module,
                metric_type="Waste Reduction",
                current_value=flt(doc.waste_generated),
                unit_of_measure="kg",
                company=doc.company,
                description=f"Waste generated from {self.doctype} {self.docname}",
                related_doctype=self.doctype,
                related_docname=self.docname
            )
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
