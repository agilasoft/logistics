# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

"""
AviationStack API Connector
Free tier: 100 API calls/month
Documentation: https://aviationstack.com/documentation
"""

from __future__ import unicode_literals
import frappe
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from ..base_flight_connector import BaseFlightConnector
from ..exceptions import *


class AviationStackConnector(BaseFlightConnector):
	"""AviationStack API Connector"""
	
	def __init__(self):
		super().__init__()
		self.provider_name = "AviationStack"
		self.base_url = self.settings.aviationstack_endpoint or "http://api.aviationstack.com/v1"
		self.api_key = self.settings.get_password("aviationstack_api_key")
		
		if not self.api_key:
			raise APIAuthenticationError("AviationStack API key is required")
	
	def authenticate(self) -> bool:
		"""Test API key validity"""
		try:
			url = f"{self.base_url}/flights"
			response = self.make_request("GET", url, params={
				"access_key": self.api_key,
				"limit": 1
			})
			return response.status_code == 200
		except Exception as e:
			frappe.log_error(f"AviationStack authentication failed: {str(e)}")
			return False
	
	def get_flight_by_number(self, flight_number: str, date: Optional[str] = None) -> Dict[str, Any]:
		"""Get flight by flight number"""
		try:
			url = f"{self.base_url}/flights"
			params = {
				"access_key": self.api_key,
				"flight_iata": flight_number
			}
			
			if date:
				params["flight_date"] = date
			
			response = self.make_request("GET", url, params=params)
			data = response.json()
			
			if not data.get("data"):
				raise FlightNotFoundError(f"Flight {flight_number} not found")
			
			# Return first result
			flight = data["data"][0]
			return self.normalize_aviationstack_flight(flight)
			
		except Exception as e:
			raise FlightNotFoundError(f"Flight {flight_number} not found: {str(e)}")
	
	def get_airport_schedule(self, iata_code: str, date: Optional[str] = None, 
	                         schedule_type: str = "departure") -> List[Dict[str, Any]]:
		"""Get airport arrivals or departures"""
		try:
			url = f"{self.base_url}/flights"
			params = {
				"access_key": self.api_key,
				"limit": 100
			}
			
			# Set airport parameter based on schedule type
			if schedule_type == "departure":
				params["dep_iata"] = iata_code.upper()
			else:
				params["arr_iata"] = iata_code.upper()
			
			if date:
				params["flight_date"] = date
			
			response = self.make_request("GET", url, params=params)
			data = response.json()
			
			flights = []
			for flight in data.get("data", []):
				normalized = self.normalize_aviationstack_flight(flight)
				flights.append(normalized)
			
			return flights
			
		except Exception as e:
			frappe.log_error(f"Error getting airport schedule: {str(e)}")
			return []
	
	def search_flights(self, origin: str, destination: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
		"""Search flights by route"""
		try:
			url = f"{self.base_url}/flights"
			params = {
				"access_key": self.api_key,
				"dep_iata": origin.upper(),
				"arr_iata": destination.upper(),
				"limit": 100
			}
			
			if date:
				params["flight_date"] = date
			
			response = self.make_request("GET", url, params=params)
			data = response.json()
			
			flights = []
			for flight in data.get("data", []):
				normalized = self.normalize_aviationstack_flight(flight)
				flights.append(normalized)
			
			return flights
			
		except Exception as e:
			frappe.log_error(f"Error searching flights: {str(e)}")
			return []
	
	def get_real_time_flight(self, flight_number: str) -> Dict[str, Any]:
		"""Get real-time flight status"""
		return self.get_flight_by_number(flight_number)
	
	def normalize_aviationstack_flight(self, flight: Dict) -> Dict[str, Any]:
		"""Normalize AviationStack flight data to standard format"""
		flight_info = flight.get("flight", {})
		departure = flight.get("departure", {})
		arrival = flight.get("arrival", {})
		airline = flight.get("airline", {})
		aircraft = flight.get("aircraft", {})
		
		return {
			"flight_number": flight_info.get("iata") or flight_info.get("icao"),
			"airline": self.get_or_create_airline(
				airline.get("iata"),
				{"name": airline.get("name"), "icao": airline.get("icao")}
			),
			"airline_iata": airline.get("iata"),
			"airline_icao": airline.get("icao"),
			"departure_airport": self.get_or_create_airport(
				departure.get("iata"),
				{
					"name": departure.get("airport"),
					"icao": departure.get("icao"),
					"timezone": departure.get("timezone")
				}
			),
			"departure_iata": departure.get("iata"),
			"departure_icao": departure.get("icao"),
			"departure_terminal": departure.get("terminal"),
			"departure_gate": departure.get("gate"),
			"departure_time_scheduled": self.parse_datetime(departure.get("scheduled")),
			"departure_time_estimated": self.parse_datetime(departure.get("estimated")),
			"departure_time_actual": self.parse_datetime(departure.get("actual")),
			"departure_timezone": departure.get("timezone"),
			"arrival_airport": self.get_or_create_airport(
				arrival.get("iata"),
				{
					"name": arrival.get("airport"),
					"icao": arrival.get("icao"),
					"timezone": arrival.get("timezone")
				}
			),
			"arrival_iata": arrival.get("iata"),
			"arrival_icao": arrival.get("icao"),
			"arrival_terminal": arrival.get("terminal"),
			"arrival_gate": arrival.get("gate"),
			"arrival_time_scheduled": self.parse_datetime(arrival.get("scheduled")),
			"arrival_time_estimated": self.parse_datetime(arrival.get("estimated")),
			"arrival_time_actual": self.parse_datetime(arrival.get("actual")),
			"arrival_timezone": arrival.get("timezone"),
			"aircraft_type": aircraft.get("iata") or aircraft.get("icao"),
			"registration": aircraft.get("registration"),
			"flight_status": self.map_flight_status(flight.get("flight_status")),
			"data_source": self.provider_name,
			"raw_data_json": json.dumps(flight)
		}
	
	def parse_datetime(self, dt_string: Optional[str]) -> Optional[datetime]:
		"""Parse datetime string"""
		if not dt_string:
			return None
		try:
			return datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
		except Exception:
			return None
	
	def map_flight_status(self, status: Optional[str]) -> str:
		"""Map AviationStack status to standard status"""
		status_map = {
			"scheduled": "Scheduled",
			"active": "Active",
			"landed": "Landed",
			"cancelled": "Cancelled",
			"incident": "Diverted",
			"diverted": "Diverted"
		}
		return status_map.get(status.lower() if status else "", "Unknown")
	
	def sync_airlines(self) -> int:
		"""Sync airline master data"""
		try:
			url = f"{self.base_url}/airlines"
			response = self.make_request("GET", url, params={
				"access_key": self.api_key,
				"limit": 100
			})
			
			data = response.json()
			saved_count = 0
			
			for airline in data.get("data", []):
				try:
					self.get_or_create_airline(
						airline.get("iata_code"),
						{
							"name": airline.get("airline_name"),
							"icao": airline.get("icao_code"),
							"callsign": airline.get("callsign"),
							"country": airline.get("country_name")
						}
					)
					saved_count += 1
				except Exception:
					continue
			
			self.create_sync_log(
				sync_type="Airline Master",
				status="Success",
				records_fetched=len(data.get("data", [])),
				records_created=saved_count
			)
			
			return saved_count
			
		except Exception as e:
			frappe.log_error(f"Error syncing airlines: {str(e)}")
			return 0
	
	def sync_airports(self) -> int:
		"""Sync airport master data"""
		try:
			url = f"{self.base_url}/airports"
			response = self.make_request("GET", url, params={
				"access_key": self.api_key,
				"limit": 100
			})
			
			data = response.json()
			saved_count = 0
			
			for airport in data.get("data", []):
				try:
					self.get_or_create_airport(
						airport.get("iata_code"),
						{
							"name": airport.get("airport_name"),
							"icao": airport.get("icao_code"),
							"city": airport.get("city_name"),
							"country": airport.get("country_name"),
							"latitude": airport.get("latitude"),
							"longitude": airport.get("longitude"),
							"timezone": airport.get("timezone")
						}
					)
					saved_count += 1
				except Exception:
					continue
			
			self.create_sync_log(
				sync_type="Airport Master",
				status="Success",
				records_fetched=len(data.get("data", [])),
				records_created=saved_count
			)
			
			return saved_count
			
		except Exception as e:
			frappe.log_error(f"Error syncing airports: {str(e)}")
			return 0


