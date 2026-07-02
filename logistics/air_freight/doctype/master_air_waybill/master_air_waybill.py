# -*- coding: utf-8 -*-
# Copyright (c) 2025, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime

from logistics.air_freight.utils.iata_airport import resolve_unloco_iata_code


class MasterAirWaybill(Document):
	def validate(self):
		"""Validate Master Air Waybill"""
		if self.flight_no and self.flight_date and not self.flight_schedule:
			self.auto_link_flight_schedule()

	@frappe.whitelist()
	def submit_eawb(self):
		"""Build and submit master e-AWB (XFWB) to IATA / sandbox."""
		self.ensure_eawb_routing()
		self.validate_eawb_submission()
		self.check_permission("write")

		from logistics.air_freight.utils.iata_settings_utils import resolve_company
		from logistics.air_freight.iata_cargo_xml.message_builder import MessageBuilder

		company = resolve_company(master_awb=self.name)
		builder = MessageBuilder(company=company)
		result = builder.send_mawb_eawb_message(self.name)

		sandbox_mode = result.get("sandbox_mode") or builder.get_sandbox_mode()
		self.eawb_sandbox_mode = sandbox_mode
		self.eawb_submitted_date = now_datetime()

		if result.get("success"):
			self.eawb_status = "Submitted"
			if result.get("accepted"):
				self.eawb_status = "Accepted"
			message_id = result.get("message_id")
			if not message_id and result.get("response"):
				message_id = _extract_message_id_from_response(result.get("response"))
			if message_id:
				self.eawb_message_id = message_id
		else:
			self.eawb_status = "Rejected"
			self.save(ignore_permissions=True)
			frappe.db.commit()
			error = result.get("error") or _("Unknown error submitting e-AWB")
			frappe.throw(
				_("e-AWB submission failed: {0}").format(error),
				title=_("e-AWB Error"),
			)

		self.save(ignore_permissions=True)
		frappe.db.commit()

		return {
			"success": True,
			"eawb_status": self.eawb_status,
			"sandbox_mode": sandbox_mode,
			"message_id": self.eawb_message_id,
			"message_queue": result.get("message_queue"),
		}

	def validate_eawb_submission(self):
		if self.eawb_status == "Accepted":
			frappe.throw(
				_("e-AWB has already been accepted for this Master AWB."),
				title=_("e-AWB Error"),
			)

		if not self.master_awb_no:
			frappe.throw(_("Master AWB number is required."), title=_("e-AWB Error"))

		awb_clean = self.master_awb_no.replace("-", "").replace(" ", "")
		if not re.match(r"^\d{11}$", awb_clean):
			frappe.throw(
				_("Master AWB number must be 11 digits (IATA format). Current format: {0}").format(
					self.master_awb_no
				),
				title=_("AWB Format Error"),
			)

		if not self.airline:
			frappe.throw(_("Airline is required for e-AWB submission."), title=_("e-AWB Error"))

		origin = resolve_unloco_iata_code(self.origin_airport, self.origin_airport_iata)
		destination = resolve_unloco_iata_code(
			self.destination_airport, self.destination_airport_iata
		)
		missing = []
		if not origin:
			missing.append(_("Origin Airport"))
		if not destination:
			missing.append(_("Destination Airport"))
		if missing:
			frappe.throw(
				_(
					"{0} required for e-AWB submission. Set Origin/Destination Airport on the MAWB, "
					"link a Flight Schedule, or assign Air Shipments with origin/destination ports."
				).format(", ".join(missing)),
				title=_("e-AWB Error"),
			)

	def ensure_eawb_routing(self):
		"""Populate routing fields from flight schedule, linked shipments, or UNLOCO."""
		changed = False

		if self.flight_schedule and (not self.origin_airport or not self.destination_airport):
			self.sync_from_flight_schedule()
			changed = True

		if not self.origin_airport or not self.destination_airport:
			shipment = frappe.db.get_value(
				"Air Shipment",
				{"master_awb": self.name},
				["origin_port", "destination_port", "flight_no", "etd", "airline"],
				as_dict=True,
			)
			if shipment:
				if not self.origin_airport and shipment.origin_port:
					self.origin_airport = shipment.origin_port
					changed = True
				if not self.destination_airport and shipment.destination_port:
					self.destination_airport = shipment.destination_port
					changed = True
				if not self.flight_no and shipment.flight_no:
					self.flight_no = shipment.flight_no
					changed = True
				if not self.flight_date and shipment.etd:
					self.flight_date = shipment.etd
					changed = True
				if not self.airline and shipment.airline:
					self.airline = shipment.airline
					changed = True

		for iata_field, unloco_field in (
			("origin_airport_iata", "origin_airport"),
			("destination_airport_iata", "destination_airport"),
		):
			if not self.get(iata_field) and self.get(unloco_field):
				resolved = resolve_unloco_iata_code(self.get(unloco_field))
				if resolved:
					self.set(iata_field, resolved)
					changed = True

		if changed:
			self.save(ignore_permissions=True)
			frappe.db.commit()
	
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


def _extract_message_id_from_response(response_text):
	try:
		import xml.etree.ElementTree as ET

		root = ET.fromstring(response_text)
		if root.get("MessageId"):
			return root.get("MessageId")
		header = root.find("MessageHeader")
		if header is not None and header.get("MessageId"):
			return header.get("MessageId")
	except Exception:
		pass
	return None


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
