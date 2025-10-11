# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

"""
OpenSky Network API Connector
Free and open-source flight tracking data
Documentation: https://openskynetwork.github.io/opensky-api/
"""

from __future__ import unicode_literals
import frappe
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from ..base_flight_connector import BaseFlightConnector
from ..exceptions import *


class OpenSkyConnector(BaseFlightConnector):
	"""OpenSky Network API Connector (Free)"""
	
	def __init__(self):
		super().__init__()
		self.provider_name = "OpenSky Network"
		self.base_url = self.settings.opensky_endpoint or "https://opensky-network.org/api"
		
		# Optional authentication for higher rate limits
		if self.settings.opensky_username and self.settings.opensky_password:
			self.session.auth = (
				self.settings.opensky_username,
				self.settings.get_password("opensky_password")
			)
	
	def authenticate(self) -> bool:
		"""
		OpenSky Network doesn't require authentication for basic access
		Optional authentication increases rate limits
		"""
		try:
			# Test connection
			url = f"{self.base_url}/states/all"
			response = self.make_request("GET", url, params={"time": 0})
			return response.status_code == 200
		except Exception as e:
			frappe.log_error(f"OpenSky authentication test failed: {str(e)}")
			return False
	
	def get_flight_by_number(self, flight_number: str, date: Optional[str] = None) -> Dict[str, Any]:
		"""
		Get flight by flight number
		Note: OpenSky doesn't have direct flight number search, we need to use aircraft search
		"""
		try:
			# OpenSky requires ICAO24 address, not flight number
			# This is a limitation - we'll return a message
			raise FlightNotFoundError(
				"OpenSky Network requires aircraft ICAO24 address. "
				"Use get_real_time_flight with callsign instead."
			)
		except Exception as e:
			raise FlightNotFoundError(f"Flight {flight_number} not found: {str(e)}")
	
	def get_airport_schedule(self, iata_code: str, date: Optional[str] = None, 
	                         schedule_type: str = "departure") -> List[Dict[str, Any]]:
		"""
		Get airport arrivals or departures
		OpenSky provides this through the flights endpoint
		"""
		try:
			# Convert IATA to ICAO (OpenSky uses ICAO codes)
			icao_code = self.iata_to_icao(iata_code)
			if not icao_code:
				raise AirportNotFoundError(f"Could not find ICAO code for {iata_code}")
			
			# Calculate time range
			if date:
				begin = int(datetime.strptime(date, "%Y-%m-%d").timestamp())
				end = begin + 86400  # 24 hours
			else:
				end = int(datetime.now().timestamp())
				begin = end - 86400
			
			# Build URL based on schedule type
			if schedule_type == "departure":
				url = f"{self.base_url}/flights/departure"
			else:
				url = f"{self.base_url}/flights/arrival"
			
			# Make request
			response = self.make_request("GET", url, params={
				"airport": icao_code,
				"begin": begin,
				"end": end
			})
			
			flights = response.json()
			
			# Normalize flight data
			normalized_flights = []
			for flight in flights:
				normalized = self.normalize_opensky_flight(flight)
				normalized_flights.append(normalized)
			
			return normalized_flights
			
		except Exception as e:
			frappe.log_error(f"Error getting airport schedule: {str(e)}")
			return []
	
	def search_flights(self, origin: str, destination: str, date: Optional[str] = None) -> List[Dict[str, Any]]:
		"""
		Search flights by route
		This combines departure airport data with destination filtering
		"""
		try:
			# Get all departures from origin
			departures = self.get_airport_schedule(origin, date, "departure")
			
			# Filter by destination
			destination_icao = self.iata_to_icao(destination)
			route_flights = [
				f for f in departures 
				if f.get("arrival_icao") == destination_icao
			]
			
			return route_flights
			
		except Exception as e:
			frappe.log_error(f"Error searching flights: {str(e)}")
			return []
	
	def get_real_time_flight(self, callsign: str) -> Dict[str, Any]:
		"""
		Get real-time flight position by callsign
		This is OpenSky's strength - real-time ADS-B data
		"""
		try:
			# Get all current states
			url = f"{self.base_url}/states/all"
			response = self.make_request("GET", url)
			
			data = response.json()
			states = data.get("states", [])
			
			# Find matching callsign
			for state in states:
				flight_callsign = state[1].strip() if state[1] else ""
				if flight_callsign.upper() == callsign.upper():
					return self.normalize_state_vector(state)
			
			raise FlightNotFoundError(f"Flight with callsign {callsign} not found")
			
		except Exception as e:
			frappe.log_error(f"Error getting real-time flight: {str(e)}")
			raise
	
	def get_flights_in_area(self, lat_min: float, lon_min: float, 
	                        lat_max: float, lon_max: float) -> List[Dict[str, Any]]:
		"""
		Get all flights in a geographic area
		Unique to OpenSky's real-time capabilities
		"""
		try:
			url = f"{self.base_url}/states/all"
			response = self.make_request("GET", url, params={
				"lamin": lat_min,
				"lomin": lon_min,
				"lamax": lat_max,
				"lomax": lon_max
			})
			
			data = response.json()
			states = data.get("states", [])
			
			flights = []
			for state in states:
				flights.append(self.normalize_state_vector(state))
			
			return flights
			
		except Exception as e:
			frappe.log_error(f"Error getting flights in area: {str(e)}")
			return []
	
	def normalize_state_vector(self, state: List) -> Dict[str, Any]:
		"""
		Normalize OpenSky state vector to standard format
		State vector format: [icao24, callsign, origin_country, time_position, 
		                      last_contact, longitude, latitude, baro_altitude, 
		                      on_ground, velocity, true_track, vertical_rate, ...]
		"""
		return {
			"aircraft_registration": state[0],
			"flight_number": state[1].strip() if state[1] else None,
			"country": state[2],
			"last_position_update": datetime.fromtimestamp(state[3]) if state[3] else None,
			"last_contact": datetime.fromtimestamp(state[4]) if state[4] else None,
			"longitude": state[5],
			"latitude": state[6],
			"altitude_meters": state[7],
			"is_on_ground": state[8],
			"speed_kmh": state[9] * 3.6 if state[9] else None,  # Convert m/s to km/h
			"heading": state[10],
			"vertical_speed_ms": state[11],
			"flight_status": "On Ground" if state[8] else "Active",
			"data_source": self.provider_name,
			"raw_data_json": json.dumps(state)
		}
	
	def normalize_opensky_flight(self, flight: Dict) -> Dict[str, Any]:
		"""
		Normalize OpenSky flight data to standard format
		"""
		return {
			"flight_number": flight.get("callsign", "").strip(),
			"aircraft_registration": flight.get("icao24"),
			"departure_icao": flight.get("estDepartureAirport"),
			"arrival_icao": flight.get("estArrivalAirport"),
			"departure_time_scheduled": datetime.fromtimestamp(flight.get("firstSeen")) if flight.get("firstSeen") else None,
			"arrival_time_scheduled": datetime.fromtimestamp(flight.get("lastSeen")) if flight.get("lastSeen") else None,
			"flight_status": "Landed" if flight.get("lastSeen") else "Active",
			"data_source": self.provider_name,
			"raw_data_json": json.dumps(flight)
		}
	
	def iata_to_icao(self, iata_code: str) -> Optional[str]:
		"""Convert IATA airport code to ICAO code"""
		try:
			airport = frappe.get_doc("Airport Master", iata_code.upper())
			return airport.icao_code
		except:
			# If not in our database, return None
			return None
	
	def sync_flights_by_area(self, lat_min: float, lon_min: float, 
	                         lat_max: float, lon_max: float) -> int:
		"""
		Sync all flights in a geographic area to database
		Useful for tracking flights in a region
		"""
		try:
			flights = self.get_flights_in_area(lat_min, lon_min, lat_max, lon_max)
			
			saved_count = 0
			for flight in flights:
				try:
					if flight.get("flight_number"):
						self.save_flight_schedule(flight)
						saved_count += 1
				except Exception as e:
					frappe.log_error(f"Error saving flight: {str(e)}")
					continue
			
			# Create sync log
			self.create_sync_log(
				sync_type="Real-time Tracking",
				status="Success",
				records_fetched=len(flights),
				records_created=saved_count
			)
			
			return saved_count
			
		except Exception as e:
			frappe.log_error(f"Error syncing flights by area: {str(e)}")
			return 0


