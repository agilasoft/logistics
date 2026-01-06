# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

"""
Master Data Synchronization
Syncs between:
- Airline Master → Airline (for migration)
- Airport Master → UNLOCO (for migration)
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
			if airline_master.icao_code:
				airline.three_letter_numeric_code = airline_master.icao_code
				airline.icao_code = airline_master.icao_code
			# Update IATA Integration tab fields
			airline.iata_code = airline_master.iata_code
			airline.callsign = airline_master.callsign
			airline.country = airline_master.country
			airline.airline_type = airline_master.airline_type
			airline.is_active = airline_master.is_active
			airline.is_cargo_carrier = airline_master.is_cargo_carrier
			airline.is_passenger_carrier = airline_master.is_passenger_carrier
			airline.supports_dangerous_goods = airline_master.supports_dangerous_goods
			airline.supports_live_animals = airline_master.supports_live_animals
			airline.supports_refrigerated = airline_master.supports_refrigerated
			airline.supports_oversized = airline_master.supports_oversized
			# Contact info
			airline.website = airline_master.website
			airline.phone = airline_master.phone
			airline.email = airline_master.email
			airline.address_line_1 = airline_master.address_line_1
			airline.address_line_2 = airline_master.address_line_2
			airline.city = airline_master.city
			airline.postal_code = airline_master.postal_code
			# API integration
			airline.has_api_integration = airline_master.has_api_integration
			airline.api_endpoint = airline_master.api_endpoint
			airline.api_key = airline_master.api_key
			airline.api_username = airline_master.api_username
			airline.api_password = airline_master.api_password
			# Metadata
			airline.data_source = airline_master.data_source
			airline.last_synced = airline_master.last_synced
			airline.disabled = airline_master.disabled
			airline.save(ignore_permissions=True)
			
			frappe.msgprint(f"Updated Airline: {airline.name}")
		else:
			# Create new Airline
			airline = frappe.get_doc({
				"doctype": "Airline",
				"code": airline_master.iata_code,
				"airline_name": airline_master.airline_name,
				"two_character_code": airline_master.iata_code,
				"three_letter_numeric_code": airline_master.icao_code,
				# IATA Integration tab fields
				"iata_code": airline_master.iata_code,
				"icao_code": airline_master.icao_code,
				"callsign": airline_master.callsign,
				"country": airline_master.country,
				"airline_type": airline_master.airline_type,
				"is_active": airline_master.is_active,
				"is_cargo_carrier": airline_master.is_cargo_carrier,
				"is_passenger_carrier": airline_master.is_passenger_carrier,
				"supports_dangerous_goods": airline_master.supports_dangerous_goods,
				"supports_live_animals": airline_master.supports_live_animals,
				"supports_refrigerated": airline_master.supports_refrigerated,
				"supports_oversized": airline_master.supports_oversized,
				"website": airline_master.website,
				"phone": airline_master.phone,
				"email": airline_master.email,
				"address_line_1": airline_master.address_line_1,
				"address_line_2": airline_master.address_line_2,
				"city": airline_master.city,
				"postal_code": airline_master.postal_code,
				"has_api_integration": airline_master.has_api_integration,
				"api_endpoint": airline_master.api_endpoint,
				"api_key": airline_master.api_key,
				"api_username": airline_master.api_username,
				"api_password": airline_master.api_password,
				"data_source": airline_master.data_source or "Airline Master Migration",
				"last_synced": airline_master.last_synced,
				"disabled": airline_master.disabled
			})
			airline.insert(ignore_permissions=True)
			
			frappe.msgprint(f"Created Airline: {airline.name}")
		
		frappe.db.commit()
		return airline.name
		
	except Exception as e:
		frappe.log_error(f"Error syncing Airline Master to Airline: {str(e)}")
		return None


# ============================================================================
# AIRPORT/UNLOCO SYNCHRONIZATION
# ============================================================================

def sync_airport_master_to_unloco(airport_master_name: str) -> Optional[str]:
	"""
	Sync Airport Master to UNLOCO DocType
	Creates or updates UNLOCO based on Airport Master data
	
	Args:
		airport_master_name: Name of Airport Master (IATA code)
	
	Returns:
		Name of synced UNLOCO record
	"""
	try:
		airport_master = frappe.get_doc("Airport Master", airport_master_name)
		
		# Check if UNLOCO exists with this IATA code
		existing = frappe.db.get_value(
			"UNLOCO",
			{"iata_code": airport_master.iata_code},
			"name"
		)
		
		if existing:
			# Update existing UNLOCO with Airport Master data
			unloco = frappe.get_doc("UNLOCO", existing)
			# Update Airport tab fields
			if airport_master.airport_name:
				unloco.airport_name = airport_master.airport_name
			if airport_master.airport_type:
				unloco.airport_type = airport_master.airport_type
			if airport_master.altitude_meters:
				unloco.altitude_meters = airport_master.altitude_meters
			if airport_master.gmt_offset:
				unloco.gmt_offset = airport_master.gmt_offset
			if airport_master.dst:
				unloco.dst = airport_master.dst
			if airport_master.is_cargo_hub is not None:
				unloco.is_cargo_hub = airport_master.is_cargo_hub
			if airport_master.is_international is not None:
				unloco.is_international = airport_master.is_international
			if airport_master.supports_dangerous_goods is not None:
				unloco.supports_dangerous_goods = airport_master.supports_dangerous_goods
			if airport_master.supports_live_animals is not None:
				unloco.supports_live_animals = airport_master.supports_live_animals
			if airport_master.supports_refrigerated is not None:
				unloco.supports_refrigerated = airport_master.supports_refrigerated
			# Contact info
			if airport_master.website:
				unloco.website = airport_master.website
			if airport_master.phone:
				unloco.phone = airport_master.phone
			if airport_master.email:
				unloco.email = airport_master.email
			if airport_master.address_line_1:
				unloco.address_line_1 = airport_master.address_line_1
			if airport_master.address_line_2:
				unloco.address_line_2 = airport_master.address_line_2
			if airport_master.postal_code:
				unloco.postal_code = airport_master.postal_code
			# Metadata
			if airport_master.is_active is not None:
				unloco.is_active = airport_master.is_active
			if airport_master.disabled is not None:
				unloco.disabled = airport_master.disabled
			if airport_master.last_synced:
				unloco.last_synced = airport_master.last_synced
			
			unloco.save(ignore_permissions=True)
			frappe.msgprint(f"Updated UNLOCO: {unloco.name}")
		else:
			# Create new UNLOCO with Airport Master data
			# Generate UNLOCO code from country and IATA if possible
			country_code = ""
			if airport_master.country:
				country_doc = frappe.get_doc("Country", airport_master.country)
				country_code = country_doc.code if hasattr(country_doc, 'code') else ""
			
			unlocode = f"{country_code}{airport_master.iata_code}" if country_code else None
			
			unloco = frappe.get_doc({
				"doctype": "UNLOCO",
				"unlocode": unlocode or airport_master.iata_code,
				"location_name": airport_master.airport_name,
				"iata_code": airport_master.iata_code,
				"icao_code": airport_master.icao_code,
				"location_type": "Airport",
				"country": airport_master.country if isinstance(airport_master.country, str) else None,
				"city": airport_master.city,
				"latitude": airport_master.latitude,
				"longitude": airport_master.longitude,
				"timezone": airport_master.timezone,
				"has_airport": 1,
				# Airport tab fields
				"airport_name": airport_master.airport_name,
				"airport_type": airport_master.airport_type,
				"altitude_meters": airport_master.altitude_meters,
				"gmt_offset": airport_master.gmt_offset,
				"dst": airport_master.dst,
				"is_cargo_hub": airport_master.is_cargo_hub,
				"is_international": airport_master.is_international,
				"supports_dangerous_goods": airport_master.supports_dangerous_goods,
				"supports_live_animals": airport_master.supports_live_animals,
				"supports_refrigerated": airport_master.supports_refrigerated,
				"website": airport_master.website,
				"phone": airport_master.phone,
				"email": airport_master.email,
				"address_line_1": airport_master.address_line_1,
				"address_line_2": airport_master.address_line_2,
				"postal_code": airport_master.postal_code,
				"is_active": airport_master.is_active,
				"disabled": airport_master.disabled,
				"last_synced": airport_master.last_synced,
				"data_source": airport_master.data_source or "Airport Master Migration"
			})
			unloco.insert(ignore_permissions=True)
			frappe.msgprint(f"Created UNLOCO: {unloco.name}")
		
		frappe.db.commit()
		return unloco.name
		
	except Exception as e:
		frappe.log_error(f"Error syncing Airport Master to UNLOCO: {str(e)}")
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
def sync_all_airport_masters_to_unloco():
	"""Sync all Airport Masters to UNLOCO"""
	try:
		airport_masters = frappe.get_all(
			"Airport Master",
			fields=["name", "iata_code", "airport_name"]
		)
		
		synced_count = 0
		for am in airport_masters:
			result = sync_airport_master_to_unloco(am.name)
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


def get_unloco_from_airport_master(airport_master_name: str) -> Optional[str]:
	"""Get UNLOCO name from Airport Master name"""
	try:
		airport_master = frappe.get_doc("Airport Master", airport_master_name)
		unloco = frappe.db.get_value("UNLOCO", {"iata_code": airport_master.iata_code}, "name")
		
		if not unloco:
			# Auto-create if not exists
			unloco = sync_airport_master_to_unloco(airport_master_name)
		
		return unloco
	except:
		return None


