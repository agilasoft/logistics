# -*- coding: utf-8 -*-
# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class MasterAirWaybill(Document):
	def validate(self):
		"""Validate Master Air Waybill"""
		# Auto-sync flight schedule if flight number and date are provided
		if self.flight_no and self.flight_date and not self.flight_schedule:
			self.auto_link_flight_schedule()
	
	def on_update(self):
		"""Called after saving"""
		# Update flight data if auto-update is enabled
		if self.auto_update_flight_status and self.flight_schedule:
			self.sync_from_flight_schedule()
	
	def auto_link_flight_schedule(self):
		"""Automatically link to flight schedule based on flight number and date"""
		try:
			# Search for matching flight schedule
			filters = {
				"flight_number": self.flight_no,
				"departure_time_scheduled": ["between", [
					f"{self.flight_date} 00:00:00",
					f"{self.flight_date} 23:59:59"
				]]
			}
			
			flight_schedule = frappe.get_all(
				"Flight Schedule",
				filters=filters,
				fields=["name"],
				limit=1
			)
			
			if flight_schedule:
				self.flight_schedule = flight_schedule[0].name
				frappe.msgprint(f"Linked to Flight Schedule: {self.flight_schedule}")
			else:
				# Try to fetch from API
				self.fetch_flight_from_api()
				
		except Exception as e:
			frappe.log_error(f"Auto-link flight schedule error: {str(e)}")
	
	def fetch_flight_from_api(self):
		"""Fetch flight schedule from API and link"""
		try:
			result = frappe.call(
				'logistics.air_freight.api.flight_schedule_api.sync_flight_data',
				flight_number=self.flight_no,
				date=str(self.flight_date)
			)
			
			if result.get('success'):
				self.flight_schedule = result.get('flight_schedule')
				frappe.msgprint(f"Flight data fetched and linked: {self.flight_schedule}")
			
		except Exception as e:
			frappe.log_error(f"Fetch flight from API error: {str(e)}")
	
	def sync_from_flight_schedule(self):
		"""Sync flight times and status from linked flight schedule"""
		try:
			if not self.flight_schedule:
				return
			
			flight = frappe.get_doc("Flight Schedule", self.flight_schedule)
			
			# Update basic info
			if flight.flight_status:
				self.flight_status = flight.flight_status
			if flight.delay_minutes:
				self.delay_minutes = flight.delay_minutes
			
			# Update airports
			if flight.departure_airport:
				self.origin_airport = flight.departure_airport
			if flight.departure_iata:
				self.origin_airport_iata = flight.departure_iata
			if flight.departure_terminal:
				self.departure_terminal = flight.departure_terminal
			if flight.departure_gate:
				self.departure_gate = flight.departure_gate
				
			if flight.arrival_airport:
				self.destination_airport = flight.arrival_airport
			if flight.arrival_iata:
				self.destination_airport_iata = flight.arrival_iata
			if flight.arrival_terminal:
				self.arrival_terminal = flight.arrival_terminal
			if flight.arrival_gate:
				self.arrival_gate = flight.arrival_gate
			
			# Update times
			if flight.departure_time_scheduled:
				self.scheduled_departure = flight.departure_time_scheduled
			if flight.departure_time_actual:
				self.actual_departure = flight.departure_time_actual
			if flight.arrival_time_scheduled:
				self.scheduled_arrival = flight.arrival_time_scheduled
			if flight.arrival_time_actual:
				self.actual_arrival = flight.arrival_time_actual
			
			# Update flight details
			if flight.flight_duration_minutes:
				self.flight_duration_minutes = flight.flight_duration_minutes
			if flight.distance_km:
				self.distance_km = flight.distance_km
			
			# Update cargo capacity
			if flight.cargo_capacity_kg:
				self.cargo_capacity_kg = flight.cargo_capacity_kg
			if flight.available_cargo_capacity_kg:
				self.available_capacity_kg = flight.available_cargo_capacity_kg
			
			# Update real-time tracking data (only for active flights)
			if flight.flight_status in ['Active', 'EnRoute']:
				if flight.latitude:
					self.current_latitude = flight.latitude
				if flight.longitude:
					self.current_longitude = flight.longitude
				if flight.altitude_meters:
					self.current_altitude_meters = flight.altitude_meters
				if flight.speed_kmh:
					self.current_speed_kmh = flight.speed_kmh
				if flight.is_on_ground is not None:
					self.is_on_ground = flight.is_on_ground
				if flight.last_position_update:
					self.last_position_update = flight.last_position_update
				
				# Build position string
				if flight.latitude and flight.longitude:
					self.last_known_position = f"{flight.latitude:.4f}, {flight.longitude:.4f}"
			
			# Update aircraft info
			if flight.aircraft_type and not self.aircraft_type:
				self.aircraft_type = flight.aircraft_type
			if flight.registration and not self.aircraft_registration_no:
				self.aircraft_registration_no = flight.registration
			
			# Format local times (if timezone info available)
			self.format_local_times(flight)
				
		except Exception as e:
			frappe.log_error(f"Sync from flight schedule error: {str(e)}")
	
	def format_local_times(self, flight):
		"""Format departure/arrival times in local timezone"""
		try:
			# ETD Local
			if flight.departure_time_scheduled and flight.departure_timezone:
				self.etd_local = f"{flight.departure_time_scheduled} {flight.departure_timezone}"
			elif flight.departure_time_scheduled:
				self.etd_local = str(flight.departure_time_scheduled)
			
			# ETA Local
			if flight.arrival_time_scheduled and flight.arrival_timezone:
				self.eta_local = f"{flight.arrival_time_scheduled} {flight.arrival_timezone}"
			elif flight.arrival_time_scheduled:
				self.eta_local = str(flight.arrival_time_scheduled)
		except Exception:
			pass


@frappe.whitelist()
def fetch_and_link_flight(master_awb_name):
	"""Manually trigger flight schedule fetch and link"""
	try:
		doc = frappe.get_doc("Master Air Waybill", master_awb_name)
		
		if not doc.flight_no or not doc.flight_date:
			return {
				"success": False,
				"error": "Flight number and date are required"
			}
		
		# Try to link existing flight schedule
		doc.auto_link_flight_schedule()
		
		# If still not linked, fetch from API
		if not doc.flight_schedule:
			doc.fetch_flight_from_api()
		
		# Sync data
		if doc.flight_schedule:
			doc.sync_from_flight_schedule()
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			
			return {
				"success": True,
				"flight_schedule": doc.flight_schedule,
				"flight_status": doc.flight_status
			}
		else:
			return {
				"success": False,
				"error": "Could not find or fetch flight schedule"
			}
			
	except Exception as e:
		frappe.log_error(f"Fetch and link flight error: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def refresh_flight_status(master_awb_name):
	"""Manually refresh flight status from flight schedule"""
	try:
		doc = frappe.get_doc("Master Air Waybill", master_awb_name)
		
		if not doc.flight_schedule:
			return {
				"success": False,
				"error": "No flight schedule linked"
			}
		
		# Get latest flight data
		result = frappe.call(
			'logistics.air_freight.api.flight_schedule_api.sync_flight_data',
			flight_number=doc.flight_no,
			date=str(doc.flight_date)
		)
		
		if result.get('success'):
			# Reload and sync
			doc.reload()
			doc.sync_from_flight_schedule()
			doc.save(ignore_permissions=True)
			frappe.db.commit()
			
			return {
				"success": True,
				"flight_status": doc.flight_status,
				"actual_departure": doc.actual_departure,
				"actual_arrival": doc.actual_arrival
			}
		else:
			return result
			
	except Exception as e:
		frappe.log_error(f"Refresh flight status error: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}
