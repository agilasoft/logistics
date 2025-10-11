# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

"""
Master Data Synchronization
Syncs between:
- Airline Master ↔ Airline
- Airport Master ↔ Location
"""

from __future__ import unicode_literals
import frappe
from typing import Optional, Dict, Any


# ============================================================================
# AIRLINE SYNCHRONIZATION
# ============================================================================

def sync_airline_master_to_airline(airline_master_name: str) -> Optional[str]:
	"""
	Sync Airline Master to Airline DocType
	Creates or updates Airline based on Airline Master data
	
	Args:
		airline_master_name: Name of Airline Master (IATA code)
	
	Returns:
		Name of synced Airline record
	"""
	try:
		airline_master = frappe.get_doc("Airline Master", airline_master_name)
		
		# Check if Airline exists with this IATA code
		existing = frappe.db.exists("Airline", airline_master.iata_code)
		
		if existing:
			# Update existing
			airline = frappe.get_doc("Airline", existing)
			airline.airline_name = airline_master.airline_name
			if airline_master.icao_code and not airline.three_letter_numeric_code:
				airline.three_letter_numeric_code = airline_master.icao_code
			airline.save(ignore_permissions=True)
			
			frappe.msgprint(f"Updated Airline: {airline.name}")
		else:
			# Create new Airline
			airline = frappe.get_doc({
				"doctype": "Airline",
				"code": airline_master.iata_code,
				"airline_name": airline_master.airline_name,
				"two_character_code": airline_master.iata_code,
				"three_letter_numeric_code": airline_master.icao_code
			})
			airline.insert(ignore_permissions=True)
			
			frappe.msgprint(f"Created Airline: {airline.name}")
		
		frappe.db.commit()
		return airline.name
		
	except Exception as e:
		frappe.log_error(f"Error syncing Airline Master to Airline: {str(e)}")
		return None


def sync_airline_to_airline_master(airline_name: str) -> Optional[str]:
	"""
	Sync Airline to Airline Master DocType
	Creates or updates Airline Master based on Airline data
	
	Args:
		airline_name: Name of Airline (IATA code)
	
	Returns:
		Name of synced Airline Master record
	"""
	try:
		airline = frappe.get_doc("Airline", airline_name)
		
		# Get IATA code from code field
		iata_code = airline.code or airline.two_character_code
		if not iata_code:
			return None
		
		# Check if Airline Master exists
		existing = frappe.db.exists("Airline Master", iata_code)
		
		if existing:
			# Update existing
			airline_master = frappe.get_doc("Airline Master", existing)
			airline_master.airline_name = airline.airline_name
			if airline.three_letter_numeric_code:
				airline_master.icao_code = airline.three_letter_numeric_code
			airline_master.save(ignore_permissions=True)
			
			frappe.msgprint(f"Updated Airline Master: {airline_master.name}")
		else:
			# Create new Airline Master
			airline_master = frappe.get_doc({
				"doctype": "Airline Master",
				"iata_code": iata_code,
				"airline_name": airline.airline_name,
				"icao_code": airline.three_letter_numeric_code,
				"data_source": "Manual"
			})
			airline_master.insert(ignore_permissions=True)
			
			frappe.msgprint(f"Created Airline Master: {airline_master.name}")
		
		frappe.db.commit()
		return airline_master.name
		
	except Exception as e:
		frappe.log_error(f"Error syncing Airline to Airline Master: {str(e)}")
		return None


# ============================================================================
# AIRPORT/LOCATION SYNCHRONIZATION
# ============================================================================

def sync_airport_master_to_location(airport_master_name: str) -> Optional[str]:
	"""
	Sync Airport Master to Location DocType
	Creates or updates Location based on Airport Master data
	
	Args:
		airport_master_name: Name of Airport Master (IATA code)
	
	Returns:
		Name of synced Location record
	"""
	try:
		airport_master = frappe.get_doc("Airport Master", airport_master_name)
		
		# Check if Location exists with this IATA code
		existing = frappe.db.get_value(
			"Location",
			{"custom_iata_code": airport_master.iata_code},
			"name"
		)
		
		if existing:
			# Update existing
			location = frappe.get_doc("Location", existing)
			location.location_name = airport_master.airport_name
			location.custom_iata_code = airport_master.iata_code
			if airport_master.latitude:
				location.latitude = airport_master.latitude
			if airport_master.longitude:
				location.longitude = airport_master.longitude
			if airport_master.country:
				location.custom_country = airport_master.country
			location.is_logistics_location = 1
			location.save(ignore_permissions=True)
			
			frappe.msgprint(f"Updated Location: {location.name}")
		else:
			# Create new Location
			location = frappe.get_doc({
				"doctype": "Location",
				"location_name": f"{airport_master.airport_name} ({airport_master.iata_code})",
				"custom_iata_code": airport_master.iata_code,
				"custom_port_name": airport_master.airport_name,
				"custom_proper_name": airport_master.city if airport_master.city else airport_master.airport_name,
				"custom_country": airport_master.country,
				"latitude": airport_master.latitude,
				"longitude": airport_master.longitude,
				"is_logistics_location": 1,
				"is_group": 0
			})
			location.insert(ignore_permissions=True)
			
			frappe.msgprint(f"Created Location: {location.name}")
		
		frappe.db.commit()
		return location.name
		
	except Exception as e:
		frappe.log_error(f"Error syncing Airport Master to Location: {str(e)}")
		return None


def sync_location_to_airport_master(location_name: str) -> Optional[str]:
	"""
	Sync Location to Airport Master DocType
	Creates or updates Airport Master based on Location data
	
	Args:
		location_name: Name of Location
	
	Returns:
		Name of synced Airport Master record
	"""
	try:
		location = frappe.get_doc("Location", location_name)
		
		# Only sync if Location has IATA code
		if not location.custom_iata_code:
			return None
		
		iata_code = location.custom_iata_code.upper()
		
		# Check if Airport Master exists
		existing = frappe.db.exists("Airport Master", iata_code)
		
		if existing:
			# Update existing
			airport_master = frappe.get_doc("Airport Master", existing)
			if location.custom_port_name:
				airport_master.airport_name = location.custom_port_name
			elif location.location_name:
				airport_master.airport_name = location.location_name
			if location.latitude:
				airport_master.latitude = location.latitude
			if location.longitude:
				airport_master.longitude = location.longitude
			if location.custom_country:
				airport_master.country = location.custom_country
			airport_master.save(ignore_permissions=True)
			
			frappe.msgprint(f"Updated Airport Master: {airport_master.name}")
		else:
			# Create new Airport Master
			airport_name = location.custom_port_name or location.location_name
			airport_master = frappe.get_doc({
				"doctype": "Airport Master",
				"iata_code": iata_code,
				"airport_name": airport_name,
				"city": location.custom_proper_name,
				"country": location.custom_country,
				"latitude": location.latitude,
				"longitude": location.longitude,
				"data_source": "Manual"
			})
			airport_master.insert(ignore_permissions=True)
			
			frappe.msgprint(f"Created Airport Master: {airport_master.name}")
		
		frappe.db.commit()
		return airport_master.name
		
	except Exception as e:
		frappe.log_error(f"Error syncing Location to Airport Master: {str(e)}")
		return None


# ============================================================================
# BATCH SYNCHRONIZATION
# ============================================================================

@frappe.whitelist()
def sync_all_airlines_to_airline_master():
	"""Sync all Airlines to Airline Master"""
	try:
		airlines = frappe.get_all(
			"Airline",
			fields=["name", "code", "airline_name"],
			filters={"code": ["!=", ""]}
		)
		
		synced_count = 0
		for airline in airlines:
			result = sync_airline_to_airline_master(airline.name)
			if result:
				synced_count += 1
		
		return {
			"success": True,
			"total": len(airlines),
			"synced": synced_count,
			"message": f"Synced {synced_count} of {len(airlines)} airlines"
		}
		
	except Exception as e:
		frappe.log_error(f"Error in batch airline sync: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def sync_all_airline_masters_to_airline():
	"""Sync all Airline Masters to Airline"""
	try:
		airline_masters = frappe.get_all(
			"Airline Master",
			fields=["name", "iata_code", "airline_name"]
		)
		
		synced_count = 0
		for am in airline_masters:
			result = sync_airline_master_to_airline(am.name)
			if result:
				synced_count += 1
		
		return {
			"success": True,
			"total": len(airline_masters),
			"synced": synced_count,
			"message": f"Synced {synced_count} of {len(airline_masters)} airline masters"
		}
		
	except Exception as e:
		frappe.log_error(f"Error in batch airline master sync: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def sync_all_locations_to_airport_master():
	"""Sync all Locations with IATA codes to Airport Master"""
	try:
		locations = frappe.get_all(
			"Location",
			fields=["name", "location_name", "custom_iata_code"],
			filters={
				"custom_iata_code": ["!=", ""],
				"is_logistics_location": 1
			}
		)
		
		synced_count = 0
		for location in locations:
			result = sync_location_to_airport_master(location.name)
			if result:
				synced_count += 1
		
		return {
			"success": True,
			"total": len(locations),
			"synced": synced_count,
			"message": f"Synced {synced_count} of {len(locations)} locations"
		}
		
	except Exception as e:
		frappe.log_error(f"Error in batch location sync: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def sync_all_airport_masters_to_location():
	"""Sync all Airport Masters to Location"""
	try:
		airport_masters = frappe.get_all(
			"Airport Master",
			fields=["name", "iata_code", "airport_name"]
		)
		
		synced_count = 0
		for am in airport_masters:
			result = sync_airport_master_to_location(am.name)
			if result:
				synced_count += 1
		
		return {
			"success": True,
			"total": len(airport_masters),
			"synced": synced_count,
			"message": f"Synced {synced_count} of {len(airport_masters)} airport masters"
		}
		
	except Exception as e:
		frappe.log_error(f"Error in batch airport master sync: {str(e)}")
		return {"success": False, "error": str(e)}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_airline_from_airline_master(airline_master_name: str) -> Optional[str]:
	"""Get Airline name from Airline Master name"""
	try:
		airline_master = frappe.get_doc("Airline Master", airline_master_name)
		airline = frappe.db.get_value("Airline", {"code": airline_master.iata_code}, "name")
		
		if not airline:
			# Auto-create if not exists
			airline = sync_airline_master_to_airline(airline_master_name)
		
		return airline
	except:
		return None


def get_location_from_airport_master(airport_master_name: str) -> Optional[str]:
	"""Get Location name from Airport Master name"""
	try:
		airport_master = frappe.get_doc("Airport Master", airport_master_name)
		location = frappe.db.get_value(
			"Location",
			{"custom_iata_code": airport_master.iata_code},
			"name"
		)
		
		if not location:
			# Auto-create if not exists
			location = sync_airport_master_to_location(airport_master_name)
		
		return location
	except:
		return None


def get_airline_master_from_airline(airline_name: str) -> Optional[str]:
	"""Get Airline Master name from Airline name"""
	try:
		airline = frappe.get_doc("Airline", airline_name)
		iata_code = airline.code or airline.two_character_code
		
		if not iata_code:
			return None
		
		airline_master = frappe.db.exists("Airline Master", iata_code)
		
		if not airline_master:
			# Auto-create if not exists
			airline_master = sync_airline_to_airline_master(airline_name)
		
		return airline_master
	except:
		return None


def get_airport_master_from_location(location_name: str) -> Optional[str]:
	"""Get Airport Master name from Location name"""
	try:
		location = frappe.get_doc("Location", location_name)
		
		if not location.custom_iata_code:
			return None
		
		airport_master = frappe.db.exists("Airport Master", location.custom_iata_code.upper())
		
		if not airport_master:
			# Auto-create if not exists
			airport_master = sync_location_to_airport_master(location_name)
		
		return airport_master
	except:
		return None


