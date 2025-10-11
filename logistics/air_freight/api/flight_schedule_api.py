# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

"""
Flight Schedule API
Public API endpoints for flight schedule operations
"""

from __future__ import unicode_literals
import frappe
from frappe import _
from typing import Dict, Any, List, Optional
import json


@frappe.whitelist()
def search_flights(origin: str, destination: str, date: Optional[str] = None) -> Dict[str, Any]:
	"""
	Search for flights by route
	
	Args:
		origin: Origin airport IATA code
		destination: Destination airport IATA code
		date: Flight date (YYYY-MM-DD format)
	
	Returns:
		List of matching flights
	"""
	try:
		from logistics.air_freight.flight_schedules.aggregator import get_aggregator
		
		aggregator = get_aggregator()
		flights = aggregator.search_flights(origin, destination, date)
		
		return {
			"success": True,
			"count": len(flights),
			"flights": flights
		}
		
	except Exception as e:
		frappe.log_error(f"Search flights error: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_flight_status(flight_number: str, date: Optional[str] = None) -> Dict[str, Any]:
	"""
	Get flight status by flight number
	
	Args:
		flight_number: Flight number (e.g., AA100)
		date: Flight date (YYYY-MM-DD format)
	
	Returns:
		Flight details and status
	"""
	try:
		from logistics.air_freight.flight_schedules.aggregator import get_aggregator
		
		aggregator = get_aggregator()
		flight = aggregator.get_flight_by_number(flight_number, date)
		
		return {
			"success": True,
			"flight": flight
		}
		
	except Exception as e:
		frappe.log_error(f"Get flight status error: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_airport_schedule(iata_code: str, date: Optional[str] = None, 
                         schedule_type: str = "departure") -> Dict[str, Any]:
	"""
	Get airport schedule (arrivals or departures)
	
	Args:
		iata_code: Airport IATA code
		date: Schedule date (YYYY-MM-DD format)
		schedule_type: "departure" or "arrival"
	
	Returns:
		List of flights for the airport
	"""
	try:
		from logistics.air_freight.flight_schedules.aggregator import get_aggregator
		
		aggregator = get_aggregator()
		schedule = aggregator.get_airport_schedule(iata_code, date, schedule_type)
		
		return {
			"success": True,
			"airport": iata_code,
			"schedule_type": schedule_type,
			"count": len(schedule),
			"flights": schedule
		}
		
	except Exception as e:
		frappe.log_error(f"Get airport schedule error: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_real_time_flight(flight_number: str) -> Dict[str, Any]:
	"""
	Get real-time flight tracking data
	
	Args:
		flight_number: Flight number or callsign
	
	Returns:
		Real-time flight position and status
	"""
	try:
		from logistics.air_freight.flight_schedules.aggregator import get_aggregator
		
		aggregator = get_aggregator()
		flight = aggregator.get_real_time_flight(flight_number)
		
		return {
			"success": True,
			"flight": flight
		}
		
	except Exception as e:
		frappe.log_error(f"Get real-time flight error: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def sync_flight_data(flight_number: str, date: Optional[str] = None) -> Dict[str, Any]:
	"""
	Manually sync a specific flight's data
	
	Args:
		flight_number: Flight number
		date: Flight date
	
	Returns:
		Sync result
	"""
	try:
		from logistics.air_freight.flight_schedules.aggregator import get_aggregator
		
		aggregator = get_aggregator()
		flight = aggregator.get_flight_by_number(flight_number, date, use_cache=False)
		
		# Save to database
		connector = list(aggregator.providers.values())[0] if aggregator.providers else None
		if connector:
			flight_name = connector.save_flight_schedule(flight)
			return {
				"success": True,
				"message": "Flight data synced successfully",
				"flight_schedule": flight_name
			}
		
		return {
			"success": False,
			"error": "No providers available"
		}
		
	except Exception as e:
		frappe.log_error(f"Sync flight data error: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_available_providers() -> Dict[str, Any]:
	"""
	Get list of available and enabled flight data providers
	
	Returns:
		List of providers with their status
	"""
	try:
		settings = frappe.get_single('Flight Schedule Settings')
		
		providers = {
			"OpenSky Network": {
				"enabled": settings.opensky_enabled,
				"free": True,
				"capabilities": ["Real-time tracking", "ADS-B data", "Geographic queries"]
			},
			"AviationStack": {
				"enabled": settings.aviationstack_enabled,
				"free": False,
				"free_tier": "100 calls/month",
				"capabilities": ["Flight schedules", "Airport schedules", "Route search", "Airlines", "Airports"]
			},
			"Aviation Edge": {
				"enabled": settings.aviation_edge_enabled,
				"free": False,
				"free_tier": "100 calls/month",
				"capabilities": ["Flight schedules", "Airport timetables", "Routes"]
			},
			"FlightAware": {
				"enabled": settings.flightaware_enabled,
				"free": False,
				"premium": True,
				"capabilities": ["Predictive ETAs", "Historical data", "Alerts"]
			}
		}
		
		return {
			"success": True,
			"default_provider": settings.default_provider,
			"providers": providers
		}
		
	except Exception as e:
		frappe.log_error(f"Get providers error: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def test_provider_connection(provider_name: str) -> Dict[str, Any]:
	"""
	Test connection to a specific provider
	
	Args:
		provider_name: Name of the provider to test
	
	Returns:
		Connection test result
	"""
	try:
		from logistics.air_freight.flight_schedules.aggregator import get_aggregator
		
		aggregator = get_aggregator()
		provider = aggregator.providers.get(provider_name)
		
		if not provider:
			return {
				"success": False,
				"error": f"Provider {provider_name} not found or not enabled"
			}
		
		# Test authentication
		auth_result = provider.authenticate()
		
		return {
			"success": auth_result,
			"provider": provider_name,
			"message": "Connection successful" if auth_result else "Connection failed"
		}
		
	except Exception as e:
		frappe.log_error(f"Test provider connection error: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def manual_sync_airports() -> Dict[str, Any]:
	"""
	Manually sync airport master data from all providers
	
	Returns:
		Sync results from all providers
	"""
	try:
		from logistics.air_freight.flight_schedules.aggregator import get_aggregator
		
		aggregator = get_aggregator()
		results = aggregator.sync_all_providers("Airport Master")
		
		total_synced = sum(r.get("count", 0) for r in results.values() if r.get("success"))
		
		return {
			"success": True,
			"total_synced": total_synced,
			"results": results
		}
		
	except Exception as e:
		frappe.log_error(f"Manual sync airports error: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def manual_sync_airlines() -> Dict[str, Any]:
	"""
	Manually sync airline master data from all providers
	
	Returns:
		Sync results from all providers
	"""
	try:
		from logistics.air_freight.flight_schedules.aggregator import get_aggregator
		
		aggregator = get_aggregator()
		results = aggregator.sync_all_providers("Airline Master")
		
		total_synced = sum(r.get("count", 0) for r in results.values() if r.get("success"))
		
		return {
			"success": True,
			"total_synced": total_synced,
			"results": results
		}
		
	except Exception as e:
		frappe.log_error(f"Manual sync airlines error: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def compare_flight_sources(flight_number: str, date: Optional[str] = None) -> Dict[str, Any]:
	"""
	Compare flight data from multiple sources
	Useful for data quality validation
	
	Args:
		flight_number: Flight number
		date: Flight date
	
	Returns:
		Data from all available sources
	"""
	try:
		from logistics.air_freight.flight_schedules.aggregator import get_aggregator
		
		aggregator = get_aggregator()
		comparison = aggregator.compare_sources(flight_number, date)
		
		return {
			"success": True,
			"flight_number": flight_number,
			"sources": comparison
		}
		
	except Exception as e:
		frappe.log_error(f"Compare sources error: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_flight_schedule_settings() -> Dict[str, Any]:
	"""
	Get current flight schedule settings
	
	Returns:
		Current settings (without sensitive information)
	"""
	try:
		settings = frappe.get_single('Flight Schedule Settings')
		
		return {
			"success": True,
			"settings": {
				"default_provider": settings.default_provider,
				"enable_auto_fallback": settings.enable_auto_fallback,
				"cache_duration_hours": settings.cache_duration_hours,
				"sync_frequency": settings.sync_frequency,
				"enable_realtime_tracking": settings.enable_realtime_tracking,
				"max_api_calls_per_hour": settings.max_api_calls_per_hour,
				"data_retention_days": settings.data_retention_days,
				"test_mode": settings.test_mode,
				"debug_logging": settings.debug_logging,
				"providers": {
					"opensky_enabled": settings.opensky_enabled,
					"aviationstack_enabled": settings.aviationstack_enabled,
					"aviation_edge_enabled": settings.aviation_edge_enabled,
					"flightaware_enabled": settings.flightaware_enabled
				}
			}
		}
		
	except Exception as e:
		frappe.log_error(f"Get settings error: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_sync_logs(limit: int = 20) -> Dict[str, Any]:
	"""
	Get recent sync logs
	
	Args:
		limit: Number of logs to return
	
	Returns:
		Recent sync logs
	"""
	try:
		logs = frappe.get_all(
			"Flight Schedule Sync Log",
			fields=["*"],
			order_by="sync_date desc",
			limit=limit
		)
		
		return {
			"success": True,
			"count": len(logs),
			"logs": logs
		}
		
	except Exception as e:
		frappe.log_error(f"Get sync logs error: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


