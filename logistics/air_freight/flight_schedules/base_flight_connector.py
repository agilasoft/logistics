# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

"""
Base Flight Schedule Connector
Base class for all flight schedule API integrations
"""

from __future__ import unicode_literals
import frappe
import requests
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from .exceptions import *


class BaseFlightConnector(ABC):
	"""Base class for flight schedule API integrations"""
	
	def __init__(self):
		self.settings = frappe.get_single('Flight Schedule Settings')
		self.session = requests.Session()
		self.session.headers.update({
			'Accept': 'application/json',
			'User-Agent': 'Frappe-Logistics/1.0'
		})
		self.provider_name = "Unknown"
		self.api_calls_count = 0
	
	@abstractmethod
	def authenticate(self) -> bool:
		"""Handle API authentication - must be implemented by subclasses"""
		pass
	
	@abstractmethod
	def get_flight_by_number(self, flight_number: str, date: Optional[str] = None) -> Dict[str, Any]:
		"""Get flight schedule by flight number"""
		pass
	
	@abstractmethod
	def get_airport_schedule(self, iata_code: str, date: Optional[str] = None, 
	                         schedule_type: str = "departure") -> List[Dict[str, Any]]:
		"""Get airport schedule (arrivals or departures)"""
		pass
	
	@abstractmethod
	def search_flights(self, origin: str, destination: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
		"""Search flights by route"""
		pass
	
	@abstractmethod
	def get_real_time_flight(self, flight_number: str) -> Dict[str, Any]:
		"""Get real-time flight position and status"""
		pass
	
	def make_request(self, method: str, url: str, **kwargs) -> requests.Response:
		"""Make HTTP request with error handling"""
		try:
			self.api_calls_count += 1
			
			# Check rate limiting
			self.check_rate_limit()
			
			# Make request with timeout
			response = self.session.request(
				method=method,
				url=url,
				timeout=30,
				**kwargs
			)
			
			# Log API call
			self.log_api_call(method, url, response.status_code)
			
			# Handle errors
			if response.status_code == 401:
				raise APIAuthenticationError(f"Authentication failed for {self.provider_name}")
			elif response.status_code == 429:
				raise APIRateLimitError(f"Rate limit exceeded for {self.provider_name}")
			elif response.status_code >= 400:
				raise APIConnectionError(
					f"API request failed with status {response.status_code}: {response.text}"
				)
			
			return response
			
		except requests.exceptions.Timeout:
			raise APIConnectionError(f"Request timeout for {self.provider_name}")
		except requests.exceptions.ConnectionError:
			raise APIConnectionError(f"Connection error for {self.provider_name}")
		except requests.exceptions.RequestException as e:
			raise APIConnectionError(f"Request failed: {str(e)}")
	
	def check_rate_limit(self):
		"""Check if rate limit is exceeded"""
		max_calls = self.settings.max_api_calls_per_hour or 1000
		
		# Get API calls in the last hour
		one_hour_ago = datetime.now() - timedelta(hours=1)
		
		calls_count = frappe.db.count(
			"Flight Schedule Sync Log",
			filters={
				"data_source": self.provider_name,
				"sync_date": [">=", one_hour_ago]
			}
		)
		
		if calls_count >= max_calls:
			raise APIRateLimitError(
				f"Rate limit exceeded: {calls_count}/{max_calls} calls per hour"
			)
	
	def log_api_call(self, method: str, url: str, status_code: int):
		"""Log API call for debugging"""
		if self.settings.debug_logging:
			frappe.log_error(
				title=f"Flight Schedule API Call - {self.provider_name}",
				message=f"Method: {method}\nURL: {url}\nStatus: {status_code}"
			)
	
	def normalize_flight_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
		"""Normalize flight data to standard format"""
		# This should be overridden by subclasses but provides a default structure
		return {
			"flight_number": None,
			"airline_iata": None,
			"airline_icao": None,
			"departure_iata": None,
			"departure_icao": None,
			"departure_time_scheduled": None,
			"departure_time_actual": None,
			"arrival_iata": None,
			"arrival_icao": None,
			"arrival_time_scheduled": None,
			"arrival_time_actual": None,
			"flight_status": "Unknown",
			"aircraft_type": None,
			"registration": None,
			"data_source": self.provider_name,
			"raw_data_json": json.dumps(raw_data)
		}
	
	def save_flight_schedule(self, flight_data: Dict[str, Any]) -> str:
		"""Save or update flight schedule"""
		try:
			# Check if flight schedule already exists
			existing = frappe.db.exists(
				"Flight Schedule",
				{
					"flight_number": flight_data.get("flight_number"),
					"departure_time_scheduled": flight_data.get("departure_time_scheduled")
				}
			)
			
			if existing:
				# Update existing record
				doc = frappe.get_doc("Flight Schedule", existing)
				for key, value in flight_data.items():
					if value is not None:
						setattr(doc, key, value)
				doc.save(ignore_permissions=True)
			else:
				# Create new record
				doc = frappe.get_doc({
					"doctype": "Flight Schedule",
					**flight_data
				})
				doc.insert(ignore_permissions=True)
			
			frappe.db.commit()
			return doc.name
			
		except Exception as e:
			frappe.log_error(f"Error saving flight schedule: {str(e)}")
			raise
	
	def get_or_create_airport(self, iata_code: str, airport_data: Optional[Dict] = None) -> str:
		"""
		Get or create airport master record
		Also syncs to Location DocType for compatibility
		"""
		if not iata_code:
			return None
		
		iata_code = iata_code.upper()
		
		# Check if airport exists
		existing = frappe.db.exists("Airport Master", iata_code)
		if existing:
			return existing
		
		# Create new airport if data is provided
		if airport_data:
			try:
				# Create Airport Master
				doc = frappe.get_doc({
					"doctype": "Airport Master",
					"iata_code": iata_code,
					"airport_name": airport_data.get("name", iata_code),
					"city": airport_data.get("city"),
					"country": airport_data.get("country"),
					"latitude": airport_data.get("latitude"),
					"longitude": airport_data.get("longitude"),
					"data_source": self.provider_name
				})
				doc.insert(ignore_permissions=True)
				frappe.db.commit()
				
				# Auto-sync to Location DocType
				try:
					from logistics.air_freight.flight_schedules.master_data_sync import sync_airport_master_to_location
					sync_airport_master_to_location(doc.name)
				except Exception as e:
					frappe.log_error(f"Error syncing airport to Location DocType: {str(e)}")
				
				return doc.name
			except Exception as e:
				frappe.log_error(f"Error creating airport {iata_code}: {str(e)}")
		
		return None
	
	def get_or_create_airline(self, iata_code: str, airline_data: Optional[Dict] = None) -> str:
		"""
		Get or create airline master record
		Also syncs to Airline DocType for compatibility
		"""
		if not iata_code:
			return None
		
		iata_code = iata_code.upper()
		
		# Check if airline master exists
		existing = frappe.db.exists("Airline Master", iata_code)
		if existing:
			return existing
		
		# Create new airline if data is provided
		if airline_data:
			try:
				# Create Airline Master
				doc = frappe.get_doc({
					"doctype": "Airline Master",
					"iata_code": iata_code,
					"airline_name": airline_data.get("name", iata_code),
					"icao_code": airline_data.get("icao"),
					"country": airline_data.get("country"),
					"data_source": self.provider_name
				})
				doc.insert(ignore_permissions=True)
				frappe.db.commit()
				
				# Auto-sync to Airline DocType
				try:
					from logistics.air_freight.flight_schedules.master_data_sync import sync_airline_master_to_airline
					sync_airline_master_to_airline(doc.name)
				except Exception as e:
					frappe.log_error(f"Error syncing airline to Airline DocType: {str(e)}")
				
				return doc.name
			except Exception as e:
				frappe.log_error(f"Error creating airline {iata_code}: {str(e)}")
		
		return None
	
	def create_sync_log(self, sync_type: str, status: str, **kwargs) -> str:
		"""Create sync log entry"""
		try:
			log = frappe.get_doc({
				"doctype": "Flight Schedule Sync Log",
				"data_source": self.provider_name,
				"sync_type": sync_type,
				"status": status,
				"api_calls_made": self.api_calls_count,
				**kwargs
			})
			log.insert(ignore_permissions=True)
			frappe.db.commit()
			return log.name
		except Exception as e:
			frappe.log_error(f"Error creating sync log: {str(e)}")
			return None

