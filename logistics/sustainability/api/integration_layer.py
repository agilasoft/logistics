# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt, getdate
from typing import Dict, List, Any, Optional
from .sustainability_api import SustainabilityAPI
from .calculation_engine import SustainabilityCalculationEngine


class SustainabilityIntegrationLayer:
	"""Integration layer for connecting sustainability tracking with all logistics modules"""
	
	def __init__(self, company=None):
		self.company = company or frappe.defaults.get_user_default("Company")
		self.api = SustainabilityAPI(company)
		self.calculator = SustainabilityCalculationEngine(company)
		self.settings = self._get_settings()
	
	def _get_settings(self):
		"""Get sustainability settings"""
		try:
			return frappe.get_doc("Sustainability Settings", self.company)
		except frappe.DoesNotExistError:
			return None
	
	def integrate_with_transport(self, transport_leg_name):
		"""Integrate sustainability tracking with transport leg"""
		if not self.settings or not self.settings.is_module_integrated("Transport"):
			return
		
		try:
			# Get transport leg data
			leg = frappe.get_doc("Transport Leg", transport_leg_name)
			
			# Calculate carbon footprint
			carbon_data = self._calculate_transport_carbon(leg)
			
			# Create carbon footprint record
			carbon_record = self.api.create_carbon_footprint(
				module="Transport",
				reference_doctype="Transport Leg",
				reference_name=transport_leg_name,
				site=leg.site,
				facility=leg.facility_from,
				**carbon_data
			)
			
			# Calculate energy consumption (if available)
			energy_data = self._calculate_transport_energy(leg)
			if energy_data:
				energy_record = self.api.create_energy_consumption(
					module="Transport",
					reference_doctype="Transport Leg",
					reference_name=transport_leg_name,
					site=leg.site,
					facility=leg.facility_from,
					**energy_data
				)
			
			# Create sustainability metrics
			metrics_data = self._calculate_transport_metrics(leg, carbon_data, energy_data)
			metrics_record = self.api.create_sustainability_metric(
				module="Transport",
				reference_doctype="Transport Leg",
				reference_name=transport_leg_name,
				site=leg.site,
				facility=leg.facility_from,
				**metrics_data
			)
			
			return {
				"carbon_record": carbon_record,
				"energy_record": energy_record,
				"metrics_record": metrics_record
			}
			
		except Exception as e:
			frappe.log_error(f"Error integrating transport leg {transport_leg_name}: {str(e)}")
			return None
	
	def integrate_with_warehousing(self, warehouse_job_name):
		"""Integrate sustainability tracking with warehouse job"""
		if not self.settings or not self.settings.is_module_integrated("Warehousing"):
			return
		
		try:
			# Get warehouse job data
			job = frappe.get_doc("Warehouse Job", warehouse_job_name)
			
			# Calculate energy consumption
			energy_data = self._calculate_warehousing_energy(job)
			if energy_data:
				energy_record = self.api.create_energy_consumption(
					module="Warehousing",
					reference_doctype="Warehouse Job",
					reference_name=warehouse_job_name,
					site=job.site,
					facility=job.facility,
					**energy_data
				)
			
			# Calculate carbon footprint
			carbon_data = self._calculate_warehousing_carbon(job)
			if carbon_data:
				carbon_record = self.api.create_carbon_footprint(
					module="Warehousing",
					reference_doctype="Warehouse Job",
					reference_name=warehouse_job_name,
					site=job.site,
					facility=job.facility,
					**carbon_data
				)
			
			# Calculate waste generation
			waste_data = self._calculate_warehousing_waste(job)
			
			# Create sustainability metrics
			metrics_data = self._calculate_warehousing_metrics(job, energy_data, carbon_data, waste_data)
			metrics_record = self.api.create_sustainability_metric(
				module="Warehousing",
				reference_doctype="Warehouse Job",
				reference_name=warehouse_job_name,
				site=job.site,
				facility=job.facility,
				**metrics_data
			)
			
			return {
				"energy_record": energy_record,
				"carbon_record": carbon_record,
				"metrics_record": metrics_record
			}
			
		except Exception as e:
			frappe.log_error(f"Error integrating warehouse job {warehouse_job_name}: {str(e)}")
			return None
	
	def integrate_with_air_freight(self, air_shipment_name):
		"""Integrate sustainability tracking with air shipment"""
		if not self.settings or not self.settings.is_module_integrated("Air Freight"):
			return
		
		try:
			# Get air shipment data
			shipment = frappe.get_doc("Air Shipment", air_shipment_name)
			
			# Calculate carbon footprint for air freight
			carbon_data = self._calculate_air_freight_carbon(shipment)
			if carbon_data:
				carbon_record = self.api.create_carbon_footprint(
					module="Air Freight",
					reference_doctype="Air Shipment",
					reference_name=air_shipment_name,
					site=shipment.site,
					facility=shipment.origin_port,
					**carbon_data
				)
			
			# Create sustainability metrics
			metrics_data = self._calculate_air_freight_metrics(shipment, carbon_data)
			metrics_record = self.api.create_sustainability_metric(
				module="Air Freight",
				reference_doctype="Air Shipment",
				reference_name=air_shipment_name,
				site=shipment.site,
				facility=shipment.origin_port,
				**metrics_data
			)
			
			return {
				"carbon_record": carbon_record,
				"metrics_record": metrics_record
			}
			
		except Exception as e:
			frappe.log_error(f"Error integrating air shipment {air_shipment_name}: {str(e)}")
			return None
	
	def integrate_with_sea_freight(self, sea_shipment_name):
		"""Integrate sustainability tracking with sea shipment"""
		if not self.settings or not self.settings.is_module_integrated("Sea Freight"):
			return
		
		try:
			# Get sea shipment data
			shipment = frappe.get_doc("Sea Shipment", sea_shipment_name)
			
			# Calculate carbon footprint for sea freight
			carbon_data = self._calculate_sea_freight_carbon(shipment)
			if carbon_data:
				carbon_record = self.api.create_carbon_footprint(
					module="Sea Freight",
					reference_doctype="Sea Shipment",
					reference_name=sea_shipment_name,
					site=shipment.site,
					facility=shipment.origin_port,
					**carbon_data
				)
			
			# Create sustainability metrics
			metrics_data = self._calculate_sea_freight_metrics(shipment, carbon_data)
			metrics_record = self.api.create_sustainability_metric(
				module="Sea Freight",
				reference_doctype="Sea Shipment",
				reference_name=sea_shipment_name,
				site=shipment.site,
				facility=shipment.origin_port,
				**metrics_data
			)
			
			return {
				"carbon_record": carbon_record,
				"metrics_record": metrics_record
			}
			
		except Exception as e:
			frappe.log_error(f"Error integrating sea shipment {sea_shipment_name}: {str(e)}")
			return None
	
	def _calculate_transport_carbon(self, leg):
		"""Calculate carbon footprint for transport leg"""
		# Use existing transport carbon calculation
		from logistics.transport.carbon import compute_leg_carbon
		
		result = compute_leg_carbon(leg.name)
		if result.get("ok"):
			return {
				"total_emissions": result.get("co2e_kg", 0),
				"scope": "Scope 1",
				"calculation_method": result.get("method", "Emission Factor"),
				"notes": f"Calculated using {result.get('provider', 'Unknown')} method"
			}
		return {}
	
	def _calculate_transport_energy(self, leg):
		"""Calculate energy consumption for transport leg"""
		# Estimate energy consumption based on distance and vehicle type
		distance = getattr(leg, 'route_distance_km', 0) or getattr(leg, 'distance_km', 0)
		vehicle_type = getattr(leg, 'vehicle_type', 'Unknown')
		
		if not distance:
			return {}
		
		# Energy consumption factors by vehicle type (kWh per km)
		energy_factors = {
			"Truck": 2.5,
			"Van": 1.8,
			"Car": 1.2,
			"Motorcycle": 0.5
		}
		
		factor = energy_factors.get(vehicle_type, 2.0)
		consumption = distance * factor
		
		return {
			"energy_type": "Diesel",
			"consumption_value": consumption,
			"unit_of_measure": "kWh",
			"notes": f"Estimated based on {distance}km distance and {vehicle_type} vehicle"
		}
	
	def _calculate_transport_metrics(self, leg, carbon_data, energy_data):
		"""Calculate sustainability metrics for transport leg"""
		metrics = {
			"carbon_footprint": carbon_data.get("total_emissions", 0),
			"energy_consumption": energy_data.get("consumption_value", 0),
			"renewable_energy_percentage": 0  # Default for transport
		}
		
		# Calculate efficiency scores
		distance = getattr(leg, 'route_distance_km', 0) or getattr(leg, 'distance_km', 0)
		weight = getattr(leg, 'cargo_weight_kg', 0) or getattr(leg, 'weight_kg', 0)
		
		if distance and weight:
			activity_data = {"activity_value": distance * weight}
			efficiency = self.calculator.calculate_energy_efficiency(energy_data, activity_data)
			metrics.update(efficiency)
		
		return metrics
	
	def _calculate_warehousing_energy(self, job):
		"""Calculate energy consumption for warehouse job"""
		# Estimate energy consumption based on job type and duration
		job_type = getattr(job, 'job_type', 'Storage')
		duration_hours = getattr(job, 'duration_hours', 1)
		
		# Energy consumption factors by job type (kWh per hour)
		energy_factors = {
			"Storage": 0.5,
			"Picking": 1.0,
			"Packing": 0.8,
			"Loading": 1.2,
			"Unloading": 1.2
		}
		
		factor = energy_factors.get(job_type, 0.5)
		consumption = duration_hours * factor
		
		return {
			"energy_type": "Electricity",
			"consumption_value": consumption,
			"unit_of_measure": "kWh",
			"notes": f"Estimated for {job_type} job lasting {duration_hours} hours"
		}
	
	def _calculate_warehousing_carbon(self, job):
		"""Calculate carbon footprint for warehouse job"""
		# Use energy consumption to calculate carbon footprint
		energy_data = self._calculate_warehousing_energy(job)
		if not energy_data:
			return {}
		
		# Calculate carbon footprint from energy consumption
		consumption = energy_data["consumption_value"]
		carbon_factor = 0.4  # kg CO2 per kWh for electricity
		total_emissions = consumption * carbon_factor
		
		return {
			"total_emissions": total_emissions,
			"scope": "Scope 2",
			"calculation_method": "Emission Factor",
			"notes": "Calculated from electricity consumption"
		}
	
	def _calculate_warehousing_waste(self, job):
		"""Calculate waste generation for warehouse job"""
		# Estimate waste based on job type
		job_type = getattr(job, 'job_type', 'Storage')
		
		# Waste generation factors by job type (kg per job)
		waste_factors = {
			"Storage": 0.1,
			"Picking": 0.2,
			"Packing": 0.5,
			"Loading": 0.3,
			"Unloading": 0.3
		}
		
		factor = waste_factors.get(job_type, 0.1)
		
		return {
			"waste_generated": factor,
			"waste_type": "Packaging Materials",
			"notes": f"Estimated for {job_type} job"
		}
	
	def _calculate_warehousing_metrics(self, job, energy_data, carbon_data, waste_data):
		"""Calculate sustainability metrics for warehouse job"""
		metrics = {
			"energy_consumption": energy_data.get("consumption_value", 0),
			"carbon_footprint": carbon_data.get("total_emissions", 0),
			"waste_generated": waste_data.get("waste_generated", 0),
			"renewable_energy_percentage": 0  # Default for warehousing
		}
		
		# Calculate efficiency scores
		duration_hours = getattr(job, 'duration_hours', 1)
		activity_data = {"activity_value": duration_hours}
		efficiency = self.calculator.calculate_energy_efficiency(energy_data, activity_data)
		metrics.update(efficiency)
		
		return metrics
	
	def _calculate_air_freight_carbon(self, shipment):
		"""Calculate carbon footprint for air freight"""
		# Use weight and distance to calculate carbon footprint
		weight = flt(shipment.weight or 0)
		distance = self._estimate_air_distance(shipment)
		
		if not weight or not distance:
			return {}
		
		# Air freight carbon factor (kg CO2 per ton-km)
		carbon_factor = 0.5
		total_emissions = (weight / 1000) * distance * carbon_factor
		
		return {
			"total_emissions": total_emissions,
			"scope": "Scope 3",
			"calculation_method": "Emission Factor",
			"notes": f"Calculated for {weight}kg over {distance}km"
		}
	
	def _calculate_air_freight_metrics(self, shipment, carbon_data):
		"""Calculate sustainability metrics for air freight"""
		metrics = {
			"carbon_footprint": carbon_data.get("total_emissions", 0),
			"renewable_energy_percentage": 0  # Default for air freight
		}
		
		return metrics
	
	def _calculate_sea_freight_carbon(self, shipment):
		"""Calculate carbon footprint for sea freight"""
		# Use weight and distance to calculate carbon footprint
		weight = flt(shipment.weight or 0)
		distance = self._estimate_sea_distance(shipment)
		
		if not weight or not distance:
			return {}
		
		# Sea freight carbon factor (kg CO2 per ton-km)
		carbon_factor = 0.01
		total_emissions = (weight / 1000) * distance * carbon_factor
		
		return {
			"total_emissions": total_emissions,
			"scope": "Scope 3",
			"calculation_method": "Emission Factor",
			"notes": f"Calculated for {weight}kg over {distance}km"
		}
	
	def _calculate_sea_freight_metrics(self, shipment, carbon_data):
		"""Calculate sustainability metrics for sea freight"""
		metrics = {
			"carbon_footprint": carbon_data.get("total_emissions", 0),
			"renewable_energy_percentage": 0  # Default for sea freight
		}
		
		return metrics
	
	def _estimate_air_distance(self, shipment):
		"""Estimate air distance between origin and destination"""
		# This is a simplified calculation - in practice, you'd use a proper distance API
		origin = getattr(shipment, 'origin_port', '')
		destination = getattr(shipment, 'destination_port', '')
		
		# Default distance if ports are not available
		return 5000  # km
	
	def _estimate_sea_distance(self, shipment):
		"""Estimate sea distance between origin and destination"""
		# This is a simplified calculation - in practice, you'd use a proper distance API
		origin = getattr(shipment, 'origin_port', '')
		destination = getattr(shipment, 'destination_port', '')
		
		# Default distance if ports are not available
		return 10000  # km


# Convenience functions
@frappe.whitelist()
def get_integration_layer(company=None):
	"""Get Sustainability Integration Layer instance"""
	return SustainabilityIntegrationLayer(company)


@frappe.whitelist()
def integrate_transport_leg(transport_leg_name):
	"""Integrate sustainability tracking with transport leg"""
	integration = SustainabilityIntegrationLayer()
	return integration.integrate_with_transport(transport_leg_name)


@frappe.whitelist()
def integrate_warehouse_job(warehouse_job_name):
	"""Integrate sustainability tracking with warehouse job"""
	integration = SustainabilityIntegrationLayer()
	return integration.integrate_with_warehousing(warehouse_job_name)


@frappe.whitelist()
def integrate_air_shipment(air_shipment_name):
	"""Integrate sustainability tracking with air shipment"""
	integration = SustainabilityIntegrationLayer()
	return integration.integrate_with_air_freight(air_shipment_name)


@frappe.whitelist()
def integrate_sea_shipment(sea_shipment_name):
	"""Integrate sustainability tracking with sea shipment"""
	integration = SustainabilityIntegrationLayer()
	return integration.integrate_with_sea_freight(sea_shipment_name)


# ----------------------------------------------------------------------
# Convenience helpers used by other modules
# ----------------------------------------------------------------------
def _get_sustainability_settings(company: Optional[str] = None):
	try:
		return frappe.get_doc("Sustainability Settings", company or frappe.defaults.get_user_default("Company"))
	except frappe.DoesNotExistError:
		return None


def is_sustainability_enabled_for_module(module: str, company: Optional[str] = None) -> bool:
	"""Return True if sustainability tracking is enabled for the given module."""
	settings = _get_sustainability_settings(company)
	if not settings:
		return False
	try:
		return settings.is_module_integrated(module)
	except Exception:
		return False


def trigger_carbon_calculation(
	module: str,
	activity_type: str,
	activity_data: Any,
	activity_unit: str,
	company: Optional[str] = None,
	reference_doctype: Optional[str] = None,
	reference_docname: Optional[str] = None,
	description: Optional[str] = None,
	site: Optional[str] = None,
	facility: Optional[str] = None,
) -> Dict[str, Any]:
	"""Calculate and record a carbon footprint entry."""
	api = SustainabilityAPI(company)

	if isinstance(activity_data, dict):
		payload = activity_data
	else:
		payload = {"activity_value": flt(activity_data) if activity_data is not None else 0}

	try:
		calculation = api.calculate_carbon_footprint(payload, activity_type, module)
		total_emissions = calculation.get("total_emissions", 0)
	except Exception as exc:
		frappe.log_error(f"Carbon calculation failed for {module}: {exc}", "Sustainability Integration")
		total_emissions = flt(payload.get("activity_value", 0))
		calculation = {"total_emissions": total_emissions, "emission_breakdown": []}

	record = api.create_carbon_footprint(
		module=module,
		reference_doctype=reference_doctype,
		reference_name=reference_docname,
		site=site,
		facility=facility,
		total_emissions=total_emissions,
		calculation_method=f"Automated ({activity_type})",
		notes=description or f"{activity_type} activity recorded in {activity_unit}",
	)

	return {
		"status": "success",
		"record": record,
		"total_emissions": total_emissions,
		"breakdown": calculation.get("emission_breakdown", []),
	}


def trigger_energy_consumption_recording(
	module: str,
	energy_type: str,
	consumption_value: float,
	unit_of_measure: str,
	company: Optional[str] = None,
	reference_doctype: Optional[str] = None,
	reference_docname: Optional[str] = None,
	description: Optional[str] = None,
	site: Optional[str] = None,
	facility: Optional[str] = None,
	renewable_percentage: Optional[float] = None,
) -> Dict[str, Any]:
	"""Record an energy consumption entry."""
	api = SustainabilityAPI(company)
	record = api.create_energy_consumption(
		module=module,
		reference_doctype=reference_doctype,
		reference_name=reference_docname,
		site=site,
		facility=facility,
		energy_type=energy_type,
		consumption_value=flt(consumption_value),
		unit_of_measure=unit_of_measure,
		renewable_percentage=flt(renewable_percentage) if renewable_percentage is not None else 0,
		notes=description,
	)

	return {
		"status": "success",
		"record": record,
		"consumption_value": flt(consumption_value),
		"energy_type": energy_type,
		"unit_of_measure": unit_of_measure,
	}
