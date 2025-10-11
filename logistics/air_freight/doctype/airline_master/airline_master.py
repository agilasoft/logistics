# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class AirlineMaster(Document):
	def validate(self):
		"""Validate Airline Master"""
		if not self.iata_code:
			frappe.throw("IATA Code is required")
		
		# Convert IATA code to uppercase
		self.iata_code = self.iata_code.upper()
		
		# Validate IATA code format (2 letters/digits)
		if len(self.iata_code) != 2:
			frappe.throw("IATA Code must be exactly 2 characters")
		
		# Convert ICAO code to uppercase if provided
		if self.icao_code:
			self.icao_code = self.icao_code.upper()
			
			# Validate ICAO code format (3 letters)
			if len(self.icao_code) != 3:
				frappe.throw("ICAO Code must be exactly 3 characters")
	
	def on_update(self):
		"""Called after saving"""
		# Update related flight schedules
		self.update_related_flights()
	
	def update_related_flights(self):
		"""Update flight schedules that reference this airline"""
		try:
			frappe.db.sql("""
				UPDATE `tabFlight Schedule`
				SET airline = %s
				WHERE airline_iata = %s
			""", (self.name, self.iata_code))
			
			frappe.db.commit()
			
		except Exception as e:
			frappe.log_error(f"Error updating related flights: {str(e)}")

@frappe.whitelist()
def get_airline_by_iata(iata_code):
	"""Get airline by IATA code"""
	if not iata_code:
		return None
	
	iata_code = iata_code.upper()
	
	airline = frappe.get_all(
		"Airline Master",
		filters={"iata_code": iata_code},
		fields=["*"],
		limit=1
	)
	
	return airline[0] if airline else None

@frappe.whitelist()
def get_airline_by_icao(icao_code):
	"""Get airline by ICAO code"""
	if not icao_code:
		return None
	
	icao_code = icao_code.upper()
	
	airline = frappe.get_all(
		"Airline Master",
		filters={"icao_code": icao_code},
		fields=["*"],
		limit=1
	)
	
	return airline[0] if airline else None

@frappe.whitelist()
def get_cargo_carriers():
	"""Get all active cargo carriers"""
	return frappe.get_all(
		"Airline Master",
		filters={
			"is_cargo_carrier": 1,
			"is_active": 1,
			"disabled": 0
		},
		fields=["*"],
		order_by="airline_name"
	)


