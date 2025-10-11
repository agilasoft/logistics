# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

"""
Flight Schedule Cache Manager
Manages caching of flight schedule data to reduce API calls
"""

from __future__ import unicode_literals
import frappe
import json
from typing import Any, Optional
from datetime import datetime, timedelta


class FlightCacheManager:
	"""Manages flight schedule data caching"""
	
	def __init__(self):
		self.settings = frappe.get_single('Flight Schedule Settings')
		self.cache_duration = self.settings.cache_duration_hours or 6
	
	def cache_data(self, cache_type: str, key: str, data: Any, date: Optional[str] = None):
		"""
		Cache flight schedule data
		
		Args:
			cache_type: Type of data (flight, airport_schedule, route_search, etc.)
			key: Cache key
			data: Data to cache
			date: Optional date parameter for time-based caching
		"""
		try:
			cache_key = self._build_cache_key(cache_type, key, date)
			expiry = datetime.now() + timedelta(hours=self.cache_duration)
			
			# Use Frappe's cache system
			frappe.cache().set_value(
				cache_key,
				json.dumps(data),
				expires_in_sec=self.cache_duration * 3600
			)
			
			# Also store in database for persistence (optional)
			if self.settings.debug_logging:
				frappe.log_error(
					title=f"Cache Saved - {cache_type}",
					message=f"Key: {cache_key}, Expiry: {expiry}"
				)
			
		except Exception as e:
			frappe.log_error(f"Cache save error: {str(e)}")
	
	def get_cached_data(self, cache_type: str, key: str, date: Optional[str] = None) -> Optional[Any]:
		"""
		Retrieve cached data
		
		Returns:
			Cached data if found and not expired, None otherwise
		"""
		try:
			cache_key = self._build_cache_key(cache_type, key, date)
			
			# Get from Frappe cache
			cached_value = frappe.cache().get_value(cache_key)
			
			if cached_value:
				if self.settings.debug_logging:
					frappe.log_error(
						title=f"Cache Hit - {cache_type}",
						message=f"Key: {cache_key}"
					)
				return json.loads(cached_value)
			
			return None
			
		except Exception as e:
			frappe.log_error(f"Cache retrieval error: {str(e)}")
			return None
	
	def invalidate_cache(self, cache_type: Optional[str] = None, key: Optional[str] = None):
		"""
		Invalidate cached data
		
		Args:
			cache_type: Type to invalidate (None for all)
			key: Specific key to invalidate (None for all of type)
		"""
		try:
			if cache_type and key:
				# Invalidate specific key
				cache_key = self._build_cache_key(cache_type, key)
				frappe.cache().delete_value(cache_key)
			elif cache_type:
				# Invalidate all keys of type (pattern matching)
				# This requires clearing by pattern which Frappe doesn't natively support
				# So we'll just clear all
				frappe.cache().delete_keys(f"flight_schedule:{cache_type}:*")
			else:
				# Clear all flight schedule cache
				frappe.cache().delete_keys("flight_schedule:*")
			
			if self.settings.debug_logging:
				frappe.log_error(
					title="Cache Invalidated",
					message=f"Type: {cache_type}, Key: {key}"
				)
			
		except Exception as e:
			frappe.log_error(f"Cache invalidation error: {str(e)}")
	
	def cache_flight_schedule(self, flight_number: str, flight_data: dict, date: Optional[str] = None):
		"""Cache a flight schedule"""
		self.cache_data('flight', flight_number, flight_data, date)
	
	def get_cached_flight(self, flight_number: str, date: Optional[str] = None) -> Optional[dict]:
		"""Get cached flight schedule"""
		return self.get_cached_data('flight', flight_number, date)
	
	def cache_airport_data(self, iata_code: str, airport_data: dict):
		"""Cache airport master data"""
		self.cache_data('airport', iata_code, airport_data)
	
	def get_cached_airport(self, iata_code: str) -> Optional[dict]:
		"""Get cached airport data"""
		return self.get_cached_data('airport', iata_code)
	
	def cache_airline_data(self, iata_code: str, airline_data: dict):
		"""Cache airline master data"""
		self.cache_data('airline', iata_code, airline_data)
	
	def get_cached_airline(self, iata_code: str) -> Optional[dict]:
		"""Get cached airline data"""
		return self.get_cached_data('airline', iata_code)
	
	def cleanup_old_cache(self, days: int = 7):
		"""
		Cleanup old cache entries
		Note: Frappe's cache system handles this automatically with expiry
		This is for additional database cleanup if needed
		"""
		try:
			cutoff_date = datetime.now() - timedelta(days=days)
			
			# Clean up old flight schedules
			frappe.db.sql("""
				DELETE FROM `tabFlight Schedule`
				WHERE sync_status = 'Stale'
				AND last_updated < %s
			""", (cutoff_date,))
			
			frappe.db.commit()
			
			frappe.log_error(
				title="Cache Cleanup",
				message=f"Cleaned up cache entries older than {days} days"
			)
			
		except Exception as e:
			frappe.log_error(f"Cache cleanup error: {str(e)}")
	
	def get_cache_stats(self) -> dict:
		"""Get cache statistics"""
		try:
			stats = {
				"cache_duration_hours": self.cache_duration,
				"cache_enabled": True,
				"total_cached_flights": frappe.db.count("Flight Schedule", {"sync_status": "Synced"}),
				"stale_flights": frappe.db.count("Flight Schedule", {"sync_status": "Stale"}),
				"cache_hit_rate": "N/A"  # Would need tracking
			}
			return stats
		except Exception as e:
			frappe.log_error(f"Error getting cache stats: {str(e)}")
			return {}
	
	def _build_cache_key(self, cache_type: str, key: str, date: Optional[str] = None) -> str:
		"""Build a cache key"""
		if date:
			return f"flight_schedule:{cache_type}:{key}:{date}"
		return f"flight_schedule:{cache_type}:{key}"


@frappe.whitelist()
def clear_all_cache():
	"""Clear all flight schedule cache - whitelisted for API access"""
	cache_manager = FlightCacheManager()
	cache_manager.invalidate_cache()
	return {"success": True, "message": "All flight schedule cache cleared"}


@frappe.whitelist()
def get_cache_statistics():
	"""Get cache statistics - whitelisted for API access"""
	cache_manager = FlightCacheManager()
	return cache_manager.get_cache_stats()


