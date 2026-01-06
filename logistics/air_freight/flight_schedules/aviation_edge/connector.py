# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

"""
Aviation Edge API Connector
Free tier: 100 API calls/month
Documentation: https://aviation-edge.com/developers/
"""

from __future__ import unicode_literals
import frappe
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from ..base_flight_connector import BaseFlightConnector
from ..exceptions import *


class AviationEdgeConnector(BaseFlightConnector):
	"""Aviation Edge API Connector"""
	
	def __init__(self):
		super().__init__()
		self.provider_name = "Aviation Edge"
		self.base_url = self.settings.aviation_edge_endpoint or "https://aviation-edge.com/v2/public"
		self.api_key = self.settings.get_password("aviation_edge_api_key")
		
		if not self.api_key:
			raise APIAuthenticationError("Aviation Edge API key is required")
	
	def authenticate(self) -> bool:
		"""Test API key validity"""
		try:
			url = f"{self.base_url}/flights"
			response = self.make_request("GET", url, params={
				"key": self.api_key,
				"limit": 1
			})
			return response.status_code == 200
		except Exception as e:
			frappe.log_error(f"Aviation Edge authentication failed: {str(e)}")
			return False
	
	def get_flight_by_number(self, flight_number: str, date: Optional[str] = None) -> Dict[str, Any]:
		"""Get flight by flight number"""
		try:
			url = f"{self.base_url}/flights"
			params = {
				"key": self.api_key,
				"flightIata": flight_number
			}
			
			response = self.make_request("GET", url, params=params)
			data = response.json()
			
			if not data or len(data) == 0:
				raise FlightNotFoundError(f"Flight {flight_number} not found")
			
			# Return first result
			flight = data[0]
			return self.normalize_aviation_edge_flight(flight)
			
		except Exception as e:
			raise FlightNotFoundError(f"Flight {flight_number} not found: {str(e)}")
	
	def get_airport_schedule(self, iata_code: str, date: Optional[str] = None, 
	                         schedule_type: str = "departure") -> List[Dict[str, Any]]:
		"""Get airport arrivals or departures"""
		try:
			url = f"{self.base_url}/timetable"
			params = {
				"key": self.api_key,
				"iataCode": iata_code.upper(),
				"type": schedule_type
			}
			
			response = self.make_request("GET", url, params=params)
			data = response.json()
			
			flights = []
			for flight in data:
				normalized = self.normalize_aviation_edge_flight(flight)
				flights.append(normalized)
			
			return flights
			
		except Exception as e:
			frappe.log_error(f"Error getting airport schedule: {str(e)}")
			return []
	
	def search_flights(self, origin: str, destination: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
		"""Search flights by route"""
		try:
			url = f"{self.base_url}/routes"
			params = {
				"key": self.api_key,
				"departureIata": origin.upper(),
				"arrivalIata": destination.upper()
			}
			
			response = self.make_request("GET", url, params=params)
			data = response.json()
			
			flights = []
			for flight in data:
				normalized = self.normalize_aviation_edge_flight(flight)
				flights.append(normalized)
			
			return flights
			
		except Exception as e:
			frappe.log_error(f"Error searching flights: {str(e)}")
			return []
	
	def get_real_time_flight(self, flight_number: str) -> Dict[str, Any]:
		"""Get real-time flight status"""
		return self.get_flight_by_number(flight_number)
	
	def normalize_aviation_edge_flight(self, flight: Dict) -> Dict[str, Any]:
		"""Normalize Aviation Edge flight data to standard format"""
		flight_info = flight.get("flight", {})
		departure = flight.get("departure", {})
		arrival = flight.get("arrival", {})
		airline = flight.get("airline", {})
		aircraft = flight.get("aircraft", {})
		
		return {
			"flight_number": flight_info.get("iataNumber") or flight_info.get("icaoNumber"),
			"airline": self.get_or_create_airline(
				airline.get("iataCode"),
				{"name": airline.get("name"), "icao": airline.get("icaoCode")}
			),
			"airline_iata": airline.get("iataCode"),
			"airline_icao": airline.get("icaoCode"),
			"departure_airport": self.get_or_create_airport(
				departure.get("iataCode"),
				{
					"name": departure.get("airport"),
					"icao": departure.get("icaoCode")
				}
			),
			"departure_iata": departure.get("iataCode"),
			"departure_icao": departure.get("icaoCode"),
			"departure_terminal": departure.get("terminal"),
			"departure_gate": departure.get("gate"),
			"departure_time_scheduled": self.parse_datetime(departure.get("scheduledTime")),
			"departure_time_estimated": self.parse_datetime(departure.get("estimatedTime")),
			"departure_time_actual": self.parse_datetime(departure.get("actualTime")),
			"arrival_airport": self.get_or_create_airport(
				arrival.get("iataCode"),
				{
					"name": arrival.get("airport"),
					"icao": arrival.get("icaoCode")
				}
			),
			"arrival_iata": arrival.get("iataCode"),
			"arrival_icao": arrival.get("icaoCode"),
			"arrival_terminal": arrival.get("terminal"),
			"arrival_gate": arrival.get("gate"),
			"arrival_time_scheduled": self.parse_datetime(arrival.get("scheduledTime")),
			"arrival_time_estimated": self.parse_datetime(arrival.get("estimatedTime")),
			"arrival_time_actual": self.parse_datetime(arrival.get("actualTime")),
			"aircraft_type": aircraft.get("iataCode") or aircraft.get("icaoCode"),
			"registration": aircraft.get("regNumber"),
			"flight_status": self.map_flight_status(flight.get("status")),
			"data_source": self.provider_name,
			"raw_data_json": json.dumps(flight)
		}
	
	def parse_datetime(self, dt_string: Optional[str]) -> Optional[datetime]:
		"""Parse datetime string"""
		if not dt_string:
			return None
		try:
			# Aviation Edge uses ISO format
			return datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
		except:
			return None
	
	def map_flight_status(self, status: Optional[str]) -> str:
		"""Map Aviation Edge status to standard status"""
		if not status:
			return "Unknown"
		
		status_lower = status.lower()
		if "scheduled" in status_lower:
			return "Scheduled"
		elif "active" in status_lower or "en-route" in status_lower:
			return "Active"
		elif "landed" in status_lower:
			return "Landed"
		elif "cancelled" in status_lower:
			return "Cancelled"
		elif "delayed" in status_lower:
			return "Delayed"
		elif "diverted" in status_lower:
			return "Diverted"
		else:
			return "Unknown"


