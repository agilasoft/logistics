# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class AirportMaster(Document):
	def validate(self):
		"""Validate Airport Master"""
		if not self.iata_code:
			frappe.throw("IATA Code is required")
		
		# Convert IATA code to uppercase
		self.iata_code = self.iata_code.upper()
		
		# Validate IATA code format (3 letters)
		if len(self.iata_code) != 3:
			frappe.throw("IATA Code must be exactly 3 characters")
		
		# Convert ICAO code to uppercase if provided
		if self.icao_code:
			self.icao_code = self.icao_code.upper()
			
			# Validate ICAO code format (4 letters)
			if len(self.icao_code) != 4:
				frappe.throw("ICAO Code must be exactly 4 characters")
		
		# Validate coordinates if provided
		if self.latitude is not None:
			if not (-90 <= self.latitude <= 90):
				frappe.throw("Latitude must be between -90 and 90")
		
		if self.longitude is not None:
			if not (-180 <= self.longitude <= 180):
				frappe.throw("Longitude must be between -180 and 180")
	
	def on_update(self):
		"""Called after saving"""
		# Update related flight schedules
		self.update_related_flights()
	
	def update_related_flights(self):
		"""Update flight schedules that reference this airport"""
		try:
			# Update departures
			frappe.db.sql("""
				UPDATE `tabFlight Schedule`
				SET departure_airport = %s
				WHERE departure_iata = %s
			""", (self.name, self.iata_code))
			
			# Update arrivals
			frappe.db.sql("""
				UPDATE `tabFlight Schedule`
				SET arrival_airport = %s
				WHERE arrival_iata = %s
			""", (self.name, self.iata_code))
			
			frappe.db.commit()
			
		except Exception as e:
			frappe.log_error(f"Error updating related flights: {str(e)}")

@frappe.whitelist()
def get_airport_by_iata(iata_code):
	"""Get airport by IATA code"""
	if not iata_code:
		return None
	
	iata_code = iata_code.upper()
	
	airport = frappe.get_all(
		"Airport Master",
		filters={"iata_code": iata_code},
		fields=["*"],
		limit=1
	)
	
	return airport[0] if airport else None

@frappe.whitelist()
def get_airport_by_icao(icao_code):
	"""Get airport by ICAO code"""
	if not icao_code:
		return None
	
	icao_code = icao_code.upper()
	
	airport = frappe.get_all(
		"Airport Master",
		filters={"icao_code": icao_code},
		fields=["*"],
		limit=1
	)
	
	return airport[0] if airport else None


