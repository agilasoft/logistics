# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

"""
Smart Flight Schedule Aggregator
Manages multiple data providers with intelligent fallback
"""

from __future__ import unicode_literals
import frappe
from typing import Dict, Any, Optional, List
from .opensky.connector import OpenSkyConnector
from .aviationstack.connector import AviationStackConnector
from .aviation_edge.connector import AviationEdgeConnector
from .exceptions import *


class FlightScheduleAggregator:
	"""Smart aggregator that tries multiple providers with fallback"""
	
	def __init__(self):
		self.settings = frappe.get_single('Flight Schedule Settings')
		self.providers = self._initialize_providers()
		self.cache_manager = None  # Will be initialized when needed
	
	def _initialize_providers(self) -> Dict[str, Any]:
		"""Initialize all enabled providers"""
		providers = {}
		
		try:
			if self.settings.opensky_enabled:
				providers['OpenSky Network'] = OpenSkyConnector()
		except Exception as e:
			frappe.log_error(f"Failed to initialize OpenSky: {str(e)}")
		
		try:
			if self.settings.aviationstack_enabled:
				providers['AviationStack'] = AviationStackConnector()
		except Exception as e:
			frappe.log_error(f"Failed to initialize AviationStack: {str(e)}")
		
		try:
			if self.settings.aviation_edge_enabled:
				providers['Aviation Edge'] = AviationEdgeConnector()
		except Exception as e:
			frappe.log_error(f"Failed to initialize Aviation Edge: {str(e)}")
		
		return providers
	
	def _get_provider_priority(self) -> List[str]:
		"""Get list of providers in priority order"""
		default_provider = self.settings.default_provider
		
		# Put default provider first
		priority = [default_provider] if default_provider in self.providers else []
		
		# Add remaining providers
		for provider in self.providers.keys():
			if provider not in priority:
				priority.append(provider)
		
		return priority
	
	def get_flight_by_number(self, flight_number: str, date: Optional[str] = None, 
	                         use_cache: bool = True) -> Dict[str, Any]:
		"""
		Get flight by number with intelligent fallback
		Tries providers in priority order until one succeeds
		"""
		# Check cache first
		if use_cache:
			cached = self._get_from_cache('flight', flight_number, date)
			if cached:
				return cached
		
		errors = []
		providers_tried = []
		
		for provider_name in self._get_provider_priority():
			try:
				provider = self.providers.get(provider_name)
				if not provider:
					continue
				
				providers_tried.append(provider_name)
				flight_data = provider.get_flight_by_number(flight_number, date)
				
				# Cache the result
				if use_cache:
					self._save_to_cache('flight', flight_number, flight_data, date)
				
				# Log successful provider
				frappe.log_error(
					title=f"Flight Data Retrieved - {provider_name}",
					message=f"Successfully retrieved {flight_number} from {provider_name}"
				)
				
				return flight_data
				
			except FlightNotFoundError as e:
				errors.append(f"{provider_name}: Flight not found")
				continue
			except APIRateLimitError as e:
				errors.append(f"{provider_name}: Rate limit exceeded")
				continue
			except Exception as e:
				errors.append(f"{provider_name}: {str(e)}")
				continue
		
		# All providers failed
		error_msg = f"All providers failed for flight {flight_number}. Tried: {', '.join(providers_tried)}. Errors: {'; '.join(errors)}"
		frappe.log_error(title="Flight Schedule Aggregator Failed", message=error_msg)
		raise FlightNotFoundError(error_msg)
	
	def get_airport_schedule(self, iata_code: str, date: Optional[str] = None, 
	                         schedule_type: str = "departure", 
	                         use_cache: bool = True) -> List[Dict[str, Any]]:
		"""Get airport schedule with fallback"""
		# Check cache first
		if use_cache:
			cache_key = f"{iata_code}_{schedule_type}_{date}"
			cached = self._get_from_cache('airport_schedule', cache_key)
			if cached:
				return cached
		
		errors = []
		
		for provider_name in self._get_provider_priority():
			try:
				provider = self.providers.get(provider_name)
				if not provider:
					continue
				
				schedule = provider.get_airport_schedule(iata_code, date, schedule_type)
				
				if schedule:
					# Cache the result
					if use_cache:
						cache_key = f"{iata_code}_{schedule_type}_{date}"
						self._save_to_cache('airport_schedule', cache_key, schedule)
					
					return schedule
				
			except Exception as e:
				errors.append(f"{provider_name}: {str(e)}")
				continue
		
		# Return empty list if all fail
		frappe.log_error(
			title="Airport Schedule Retrieval Failed",
			message=f"Failed to get schedule for {iata_code}: {'; '.join(errors)}"
		)
		return []
	
	def search_flights(self, origin: str, destination: str, date: Optional[str] = None,
	                   use_cache: bool = True) -> List[Dict[str, Any]]:
		"""Search flights by route with fallback"""
		# Check cache first
		if use_cache:
			cache_key = f"{origin}_{destination}_{date}"
			cached = self._get_from_cache('route_search', cache_key)
			if cached:
				return cached
		
		errors = []
		
		for provider_name in self._get_provider_priority():
			try:
				provider = self.providers.get(provider_name)
				if not provider:
					continue
				
				flights = provider.search_flights(origin, destination, date)
				
				if flights:
					# Cache the result
					if use_cache:
						cache_key = f"{origin}_{destination}_{date}"
						self._save_to_cache('route_search', cache_key, flights)
					
					return flights
				
			except Exception as e:
				errors.append(f"{provider_name}: {str(e)}")
				continue
		
		# Return empty list if all fail
		return []
	
	def get_real_time_flight(self, flight_number: str, use_cache: bool = False) -> Dict[str, Any]:
		"""Get real-time flight data (usually not cached due to real-time nature)"""
		errors = []
		
		# Prefer OpenSky for real-time tracking (it's their specialty)
		priority = ['OpenSky Network'] + [p for p in self._get_provider_priority() if p != 'OpenSky Network']
		
		for provider_name in priority:
			try:
				provider = self.providers.get(provider_name)
				if not provider:
					continue
				
				flight_data = provider.get_real_time_flight(flight_number)
				return flight_data
				
			except Exception as e:
				errors.append(f"{provider_name}: {str(e)}")
				continue
		
		raise FlightNotFoundError(f"Could not get real-time data for {flight_number}")
	
	def compare_sources(self, flight_number: str, date: Optional[str] = None) -> Dict[str, Any]:
		"""
		Compare data from multiple sources for validation
		Useful for data quality checking
		"""
		results = {}
		
		for provider_name, provider in self.providers.items():
			try:
				flight_data = provider.get_flight_by_number(flight_number, date)
				results[provider_name] = {
					"success": True,
					"data": flight_data
				}
			except Exception as e:
				results[provider_name] = {
					"success": False,
					"error": str(e)
				}
		
		return results
	
	def get_best_source_for_route(self, origin: str, destination: str) -> Optional[str]:
		"""
		Determine the best data source for a specific route
		Based on historical success rates
		"""
		# Query sync logs to find best provider
		logs = frappe.get_all(
			"Flight Schedule Sync Log",
			filters={
				"sync_type": "Flight Schedule",
				"status": "Success"
			},
			fields=["data_source", "count(name) as success_count"],
			group_by="data_source",
			order_by="success_count desc",
			limit=1
		)
		
		if logs:
			return logs[0].data_source
		
		return self.settings.default_provider
	
	def sync_all_providers(self, sync_type: str = "Flight Schedule") -> Dict[str, Any]:
		"""
		Sync data from all enabled providers
		Returns summary of sync operations
		"""
		results = {}
		
		for provider_name, provider in self.providers.items():
			try:
				if sync_type == "Airport Master" and hasattr(provider, 'sync_airports'):
					count = provider.sync_airports()
					results[provider_name] = {"success": True, "count": count}
				elif sync_type == "Airline Master" and hasattr(provider, 'sync_airlines'):
					count = provider.sync_airlines()
					results[provider_name] = {"success": True, "count": count}
				else:
					results[provider_name] = {"success": False, "error": "Method not supported"}
			except Exception as e:
				results[provider_name] = {"success": False, "error": str(e)}
		
		return results
	
	def _get_from_cache(self, cache_type: str, key: str, date: Optional[str] = None) -> Optional[Any]:
		"""Get data from cache"""
		try:
			from .cache_manager import FlightCacheManager
			if not self.cache_manager:
				self.cache_manager = FlightCacheManager()
			
			return self.cache_manager.get_cached_data(cache_type, key, date)
		except Exception:
			return None
	
	def _save_to_cache(self, cache_type: str, key: str, data: Any, date: Optional[str] = None):
		"""Save data to cache"""
		try:
			from .cache_manager import FlightCacheManager
			if not self.cache_manager:
				self.cache_manager = FlightCacheManager()
			
			self.cache_manager.cache_data(cache_type, key, data, date)
		except Exception as e:
			frappe.log_error(f"Cache save failed: {str(e)}")


@frappe.whitelist()
def get_aggregator() -> FlightScheduleAggregator:
	"""Get aggregator instance (singleton pattern)"""
	if not hasattr(frappe.local, 'flight_schedule_aggregator'):
		frappe.local.flight_schedule_aggregator = FlightScheduleAggregator()
	return frappe.local.flight_schedule_aggregator


