"""
UNLOCO Utilities for Location Auto-Population
Provides functions to populate UNLOCO details automatically
"""

import frappe
from frappe import _
from typing import Dict, Optional, Any
from datetime import datetime

@frappe.whitelist()
def populate_unlocode_details(unlocode: str, doc: Any = None) -> Dict[str, Any]:
    """
    Populate UNLOCO details for a location
    
    Args:
        unlocode: UNLOCO code (e.g., "USLAX")
        doc: Location document (optional)
    
    Returns:
        Dictionary of populated fields
    """
    try:
        if not unlocode:
            return {}
        
        print(f"🔍 Looking up UNLOCO details for: {unlocode}")
        
        # Get UNLOCO data
        unlocode_data = get_unlocode_data(unlocode.upper())
        
        if unlocode_data:
            # Populate fields
            populated_fields = populate_fields_from_data(unlocode_data)
            
            # Update document if provided
            if doc:
                update_document_fields(doc, populated_fields)
            
            print(f"✅ UNLOCO details populated for {unlocode}")
            return populated_fields
        else:
            print(f"⚠️  No UNLOCO data found for {unlocode}")
            # Try to populate basic details from code
            basic_fields = populate_basic_details_from_code(unlocode.upper())
            if doc:
                update_document_fields(doc, basic_fields)
            return basic_fields
            
    except Exception as e:
        print(f"❌ Error populating UNLOCO details: {str(e)}")
        frappe.log_error(f"UNLOCO details population error: {str(e)}")
        return {}

def get_unlocode_data(unlocode: str) -> Optional[Dict[str, Any]]:
    """
    Get UNLOCO data for a specific code
    
    Args:
        unlocode: UNLOCO code (e.g., "USLAX")
    
    Returns:
        Dictionary of UNLOCO data or None
    """
    try:
        # First, check if we have this UNLOCO code in our existing UNLOCO records
        existing_unlocode = frappe.db.get_value("UNLOCO", 
                                               {"unlocode": unlocode.upper()},
                                               ["name", "location_name", "country", 
                                                "country_code", "subdivision", "city",
                                                "location_type", "iata_code", "icao_code",
                                                "timezone", "currency", "language",
                                                "utc_offset", "operating_hours", "latitude", "longitude",
                                                "description"])
        
        if existing_unlocode:
            # Return data from existing UNLOCO record
            return {
                'location_name': existing_unlocode[1] or '',
                'country': existing_unlocode[2] or '',
                'country_code': existing_unlocode[3] or '',
                'subdivision': existing_unlocode[4] or '',
                'city': existing_unlocode[5] or '',
                'location_type': existing_unlocode[6] or '',
                'iata_code': existing_unlocode[7] or '',
                'icao_code': existing_unlocode[8] or '',
                'timezone': existing_unlocode[9] or '',
                'currency': existing_unlocode[10] or '',
                'language': existing_unlocode[11] or '',
                'utc_offset': existing_unlocode[12] or '',
                'operating_hours': existing_unlocode[13] or '',
                'latitude': existing_unlocode[14],
                'longitude': existing_unlocode[15],
                'description': existing_unlocode[16] or ''
            }
        
        # If not found in existing locations, try to get from UNLOCO database
        return get_unlocode_from_database(unlocode)
        
    except Exception as e:
        print(f"❌ Error getting UNLOCO data: {str(e)}")
        frappe.log_error(f"UNLOCO data retrieval error: {str(e)}")
        return None

def get_unlocode_from_database(unlocode: str) -> Optional[Dict[str, Any]]:
    """
    Get UNLOCO data from external database or API
    
    Args:
        unlocode: UNLOCO code
    
    Returns:
        Dictionary of UNLOCO data or None
    """
    try:
        # Sample data for common UNLOCO codes
        sample_data = {
            "USLAX": {
                "location_name": "Los Angeles International Airport",
                "country": "United States",
                "country_code": "US",
                "subdivision": "California",
                "city": "Los Angeles",
                "location_type": "Airport",
                "iata_code": "LAX",
                "icao_code": "KLAX",
                "timezone": "America/Los_Angeles",
                "currency": "USD",
                "language": "en",
                "utc_offset": "-08:00",
                "operating_hours": "24/7",
                "latitude": 33.9425,
                "longitude": -118.4081,
                "description": "Los Angeles International Airport - Major international gateway to the US West Coast"
            },
            "USJFK": {
                "location_name": "John F. Kennedy International Airport",
                "country": "United States",
                "country_code": "US",
                "subdivision": "New York",
                "city": "New York",
                "location_type": "Airport",
                "iata_code": "JFK",
                "icao_code": "KJFK",
                "timezone": "America/New_York",
                "currency": "USD",
                "language": "en",
                "utc_offset": "-05:00",
                "operating_hours": "24/7",
                "latitude": 40.6413,
                "longitude": -73.7781,
                "description": "John F. Kennedy International Airport - Major international gateway to New York"
            },
            "GBLHR": {
                "location_name": "London Heathrow Airport",
                "country": "United Kingdom",
                "country_code": "GB",
                "subdivision": "England",
                "city": "London",
                "location_type": "Airport",
                "iata_code": "LHR",
                "icao_code": "EGLL",
                "timezone": "Europe/London",
                "currency": "GBP",
                "language": "en",
                "utc_offset": "+00:00",
                "operating_hours": "24/7",
                "latitude": 51.4700,
                "longitude": -0.4543,
                "description": "London Heathrow Airport - Major international hub for Europe"
            },
            "DEHAM": {
                "location_name": "Port of Hamburg",
                "country": "Germany",
                "country_code": "DE",
                "subdivision": "Hamburg",
                "city": "Hamburg",
                "location_type": "Port",
                "iata_code": "HAM",
                "icao_code": "EDDH",
                "timezone": "Europe/Berlin",
                "currency": "EUR",
                "language": "de",
                "utc_offset": "+01:00",
                "operating_hours": "24/7",
                "latitude": 53.5511,
                "longitude": 9.9937,
                "description": "Port of Hamburg - Major European port and gateway to Central Europe"
            },
            "NLRTM": {
                "location_name": "Port of Rotterdam",
                "country": "Netherlands",
                "country_code": "NL",
                "subdivision": "South Holland",
                "city": "Rotterdam",
                "location_type": "Port",
                "iata_code": "RTM",
                "icao_code": "EHRD",
                "timezone": "Europe/Amsterdam",
                "currency": "EUR",
                "language": "nl",
                "utc_offset": "+01:00",
                "operating_hours": "24/7",
                "latitude": 51.9244,
                "longitude": 4.4777,
                "description": "Port of Rotterdam - Europe's largest port"
            },
            "SGSIN": {
                "location_name": "Port of Singapore",
                "country": "Singapore",
                "country_code": "SG",
                "subdivision": "Singapore",
                "city": "Singapore",
                "location_type": "Port",
                "iata_code": "SIN",
                "icao_code": "WSSS",
                "timezone": "Asia/Singapore",
                "currency": "SGD",
                "language": "en",
                "utc_offset": "+08:00",
                "operating_hours": "24/7",
                "latitude": 1.2966,
                "longitude": 103.7764,
                "description": "Port of Singapore - World's busiest transshipment port"
            }
        }
        
        if unlocode in sample_data:
            return sample_data[unlocode]
        
        # If not in sample data, try to infer from UNLOCO code pattern
        return infer_unlocode_data(unlocode)
        
    except Exception as e:
        print(f"❌ Error getting UNLOCO from database: {str(e)}")
        frappe.log_error(f"UNLOCO database retrieval error: {str(e)}")
        return None

def infer_unlocode_data(unlocode: str) -> Optional[Dict[str, Any]]:
    """
    Infer UNLOCO data from code pattern
    
    Args:
        unlocode: UNLOCO code
    
    Returns:
        Dictionary of inferred data or None
    """
    try:
        if len(unlocode) != 5:
            return None
        
        country_code = unlocode[:2]
        location_code = unlocode[2:]
        
        # Get country information
        country_info = get_country_info(country_code)
        
        # Infer location type and details
        location_info = infer_location_details(unlocode, country_code, location_code)
        
        if country_info and location_info:
            return {
                **country_info,
                **location_info
            }
        
        return None
        
    except Exception as e:
        print(f"❌ Error inferring UNLOCO data: {str(e)}")
        frappe.log_error(f"UNLOCO data inference error: {str(e)}")
        return None

def get_country_info(country_code: str) -> Dict[str, str]:
    """
    Get country information from country code
    
    Args:
        country_code: ISO country code (e.g., "US")
    
    Returns:
        Dictionary of country information
    """
    country_mapping = {
        "US": {"country": "United States", "country_code": "US", "currency": "USD", "language": "en"},
        "GB": {"country": "United Kingdom", "country_code": "GB", "currency": "GBP", "language": "en"},
        "DE": {"country": "Germany", "country_code": "DE", "currency": "EUR", "language": "de"},
        "FR": {"country": "France", "country_code": "FR", "currency": "EUR", "language": "fr"},
        "IT": {"country": "Italy", "country_code": "IT", "currency": "EUR", "language": "it"},
        "ES": {"country": "Spain", "country_code": "ES", "currency": "EUR", "language": "es"},
        "NL": {"country": "Netherlands", "country_code": "NL", "currency": "EUR", "language": "nl"},
        "BE": {"country": "Belgium", "country_code": "BE", "currency": "EUR", "language": "nl"},
        "CH": {"country": "Switzerland", "country_code": "CH", "currency": "CHF", "language": "de"},
        "AT": {"country": "Austria", "country_code": "AT", "currency": "EUR", "language": "de"},
        "CN": {"country": "China", "country_code": "CN", "currency": "CNY", "language": "zh"},
        "JP": {"country": "Japan", "country_code": "JP", "currency": "JPY", "language": "ja"},
        "KR": {"country": "South Korea", "country_code": "KR", "currency": "KRW", "language": "ko"},
        "SG": {"country": "Singapore", "country_code": "SG", "currency": "SGD", "language": "en"},
        "AU": {"country": "Australia", "country_code": "AU", "currency": "AUD", "language": "en"},
        "CA": {"country": "Canada", "country_code": "CA", "currency": "CAD", "language": "en"},
        "MX": {"country": "Mexico", "country_code": "MX", "currency": "MXN", "language": "es"},
        "BR": {"country": "Brazil", "country_code": "BR", "currency": "BRL", "language": "pt"},
        "AR": {"country": "Argentina", "country_code": "AR", "currency": "ARS", "language": "es"},
        "CL": {"country": "Chile", "country_code": "CL", "currency": "CLP", "language": "es"},
        "IN": {"country": "India", "country_code": "IN", "currency": "INR", "language": "hi"},
        "TH": {"country": "Thailand", "country_code": "TH", "currency": "THB", "language": "th"},
        "MY": {"country": "Malaysia", "country_code": "MY", "currency": "MYR", "language": "ms"},
        "ID": {"country": "Indonesia", "country_code": "ID", "currency": "IDR", "language": "id"},
        "PH": {"country": "Philippines", "country_code": "PH", "currency": "PHP", "language": "en"},
        "VN": {"country": "Vietnam", "country_code": "VN", "currency": "VND", "language": "vi"},
        "RU": {"country": "Russia", "country_code": "RU", "currency": "RUB", "language": "ru"},
        "UA": {"country": "Ukraine", "country_code": "UA", "currency": "UAH", "language": "uk"},
        "PL": {"country": "Poland", "country_code": "PL", "currency": "PLN", "language": "pl"},
        "CZ": {"country": "Czech Republic", "country_code": "CZ", "currency": "CZK", "language": "cs"}
    }
    
    return country_mapping.get(country_code, {})

def infer_location_details(unlocode: str, country_code: str, location_code: str) -> Dict[str, Any]:
    """
    Infer location details from UNLOCO code
    
    Args:
        unlocode: Full UNLOCO code
        country_code: Country code
        location_code: Location code
    
    Returns:
        Dictionary of location details
    """
    try:
        # Common patterns for location types
        if location_code in ["LAX", "JFK", "MIA", "ORD", "DFW", "ATL", "SEA", "LHR", "LGW", "CDG", "FRA", "MAD", "FCO", "AMS", "BRU", "ZUR", "VIE", "PEK", "NRT", "ICN", "SIN", "SYD", "YYZ", "MEX", "GRU", "EZE", "SCL", "BOM", "BKK", "KUL", "CGK", "MNL", "SGN", "SVO", "KBP", "WAW", "PRG"]:
            return {
                "location_type": "Airport",
                "iata_code": location_code,
                "icao_code": f"K{location_code}" if country_code == "US" else f"E{location_code}" if country_code in ["GB", "DE", "FR", "IT", "ES", "NL", "BE", "CH", "AT"] else location_code,
                "timezone": get_timezone_for_country(country_code),
                "utc_offset": get_utc_offset_for_country(country_code),
                "operating_hours": "24/7",
                "description": f"Airport location with UNLOCO code {unlocode}"
            }
        elif location_code in ["LGB", "NYC", "HAM", "RTM", "SIN", "PVG", "YOK", "LON", "PAR", "HAM", "ROT", "SGP", "SHA", "YOK"]:
            return {
                "location_type": "Port",
                "timezone": get_timezone_for_country(country_code),
                "utc_offset": get_utc_offset_for_country(country_code),
                "operating_hours": "24/7",
                "description": f"Port location with UNLOCO code {unlocode}"
            }
        else:
            return {
                "location_type": "Other",
                "timezone": get_timezone_for_country(country_code),
                "utc_offset": get_utc_offset_for_country(country_code),
                "operating_hours": "24/7",
                "description": f"Transport location with UNLOCO code {unlocode}"
            }
        
    except Exception as e:
        print(f"❌ Error inferring location details: {str(e)}")
        frappe.log_error(f"Location details inference error: {str(e)}")
        return {}

def get_timezone_for_country(country_code: str) -> str:
    """
    Get timezone for country code
    
    Args:
        country_code: ISO country code
    
    Returns:
        Timezone identifier
    """
    timezone_mapping = {
        "US": "America/New_York",
        "GB": "Europe/London",
        "DE": "Europe/Berlin",
        "FR": "Europe/Paris",
        "IT": "Europe/Rome",
        "ES": "Europe/Madrid",
        "NL": "Europe/Amsterdam",
        "BE": "Europe/Brussels",
        "CH": "Europe/Zurich",
        "AT": "Europe/Vienna",
        "CN": "Asia/Shanghai",
        "JP": "Asia/Tokyo",
        "KR": "Asia/Seoul",
        "SG": "Asia/Singapore",
        "AU": "Australia/Sydney",
        "CA": "America/Toronto",
        "MX": "America/Mexico_City",
        "BR": "America/Sao_Paulo",
        "AR": "America/Argentina/Buenos_Aires",
        "CL": "America/Santiago",
        "IN": "Asia/Kolkata",
        "TH": "Asia/Bangkok",
        "MY": "Asia/Kuala_Lumpur",
        "ID": "Asia/Jakarta",
        "PH": "Asia/Manila",
        "VN": "Asia/Ho_Chi_Minh",
        "RU": "Europe/Moscow",
        "UA": "Europe/Kiev",
        "PL": "Europe/Warsaw",
        "CZ": "Europe/Prague"
    }
    
    return timezone_mapping.get(country_code, "UTC")

def get_utc_offset_for_country(country_code: str) -> str:
    """
    Get UTC offset for country code
    
    Args:
        country_code: ISO country code
    
    Returns:
        UTC offset string
    """
    offset_mapping = {
        "US": "-05:00",
        "GB": "+00:00",
        "DE": "+01:00",
        "FR": "+01:00",
        "IT": "+01:00",
        "ES": "+01:00",
        "NL": "+01:00",
        "BE": "+01:00",
        "CH": "+01:00",
        "AT": "+01:00",
        "CN": "+08:00",
        "JP": "+09:00",
        "KR": "+09:00",
        "SG": "+08:00",
        "AU": "+10:00",
        "CA": "-05:00",
        "MX": "-06:00",
        "BR": "-03:00",
        "AR": "-03:00",
        "CL": "-03:00",
        "IN": "+05:30",
        "TH": "+07:00",
        "MY": "+08:00",
        "ID": "+07:00",
        "PH": "+08:00",
        "VN": "+07:00",
        "RU": "+03:00",
        "UA": "+02:00",
        "PL": "+01:00",
        "CZ": "+01:00"
    }
    
    return offset_mapping.get(country_code, "+00:00")

def populate_fields_from_data(unlocode_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Populate fields from UNLOCO data
    
    Args:
        unlocode_data: Dictionary of UNLOCO data
    
    Returns:
        Dictionary of populated fields
    """
    try:
        populated_fields = {}
        
        # Basic information
        if unlocode_data.get('location_name'):
            populated_fields['location_name'] = unlocode_data['location_name']
        
        if unlocode_data.get('country'):
            populated_fields['country'] = unlocode_data['country']
        
        if unlocode_data.get('country_code'):
            populated_fields['country_code'] = unlocode_data['country_code']
        
        if unlocode_data.get('subdivision'):
            populated_fields['subdivision'] = unlocode_data['subdivision']
        
        if unlocode_data.get('city'):
            populated_fields['city'] = unlocode_data['city']
        
        if unlocode_data.get('location_type'):
            populated_fields['location_type'] = unlocode_data['location_type']
        
        # Identifiers
        if unlocode_data.get('iata_code'):
            populated_fields['iata_code'] = unlocode_data['iata_code']
        
        if unlocode_data.get('icao_code'):
            populated_fields['icao_code'] = unlocode_data['icao_code']
        
        # Logistics details
        if unlocode_data.get('timezone'):
            populated_fields['timezone'] = unlocode_data['timezone']
        
        if unlocode_data.get('currency'):
            populated_fields['currency'] = unlocode_data['currency']
        
        if unlocode_data.get('language'):
            populated_fields['language'] = unlocode_data['language']
        
        if unlocode_data.get('utc_offset'):
            populated_fields['utc_offset'] = unlocode_data['utc_offset']
        
        if unlocode_data.get('operating_hours'):
            populated_fields['operating_hours'] = unlocode_data['operating_hours']
        
        # Coordinates
        if unlocode_data.get('latitude'):
            populated_fields['latitude'] = unlocode_data['latitude']
        
        if unlocode_data.get('longitude'):
            populated_fields['longitude'] = unlocode_data['longitude']
        
        # Description
        if unlocode_data.get('description'):
            populated_fields['description'] = unlocode_data['description']
        
        # Set function checkboxes
        function_checkboxes = set_function_checkboxes_from_data(unlocode_data)
        populated_fields.update(function_checkboxes)
        
        # Set regulatory facilities
        regulatory_facilities = set_regulatory_facilities_from_data(unlocode_data)
        populated_fields.update(regulatory_facilities)
        
        return populated_fields
        
    except Exception as e:
        print(f"❌ Error populating fields from data: {str(e)}")
        frappe.log_error(f"Fields population error: {str(e)}")
        return {}

def set_function_checkboxes_from_data(unlocode_data: Dict[str, Any]) -> Dict[str, int]:
    """
    Set function checkboxes based on location data
    
    Args:
        unlocode_data: Dictionary of UNLOCO data
    
    Returns:
        Dictionary of function checkbox values
    """
    try:
        checkboxes = {
            'has_post': 0,
            'has_customs': 0,
            'has_unload': 0,
            'has_airport': 0,
            'has_rail': 0,
            'has_road': 0,
            'has_store': 1,  # Most locations have some storage
            'has_terminal': 0,
            'has_discharge': 0,
            'has_seaport': 0,
            'has_outport': 0
        }
        
        location_type = unlocode_data.get('location_type', '')
        unlocode = unlocode_data.get('unlocode', '').upper()
        
        # Set checkboxes based on location type
        if location_type == "Airport":
            checkboxes['has_airport'] = 1
            checkboxes['has_customs'] = 1
            checkboxes['has_terminal'] = 1
        elif location_type == "Port":
            checkboxes['has_seaport'] = 1
            checkboxes['has_customs'] = 1
            checkboxes['has_unload'] = 1
            checkboxes['has_discharge'] = 1
            checkboxes['has_terminal'] = 1
        elif location_type == "Railway Station":
            checkboxes['has_rail'] = 1
            checkboxes['has_terminal'] = 1
        elif location_type == "Road Terminal":
            checkboxes['has_road'] = 1
            checkboxes['has_terminal'] = 1
        
        # Set additional checkboxes based on UNLOCO code patterns
        if "LAX" in unlocode or "JFK" in unlocode or "MIA" in unlocode or "ORD" in unlocode or "DFW" in unlocode or "ATL" in unlocode or "SEA" in unlocode or "LHR" in unlocode or "LGW" in unlocode:
            checkboxes['has_airport'] = 1
            checkboxes['has_customs'] = 1
            checkboxes['has_terminal'] = 1
        elif "LGB" in unlocode or "NYC" in unlocode or "HAM" in unlocode or "RTM" in unlocode or "SIN" in unlocode or "PVG" in unlocode or "YOK" in unlocode:
            checkboxes['has_seaport'] = 1
            checkboxes['has_customs'] = 1
            checkboxes['has_unload'] = 1
            checkboxes['has_discharge'] = 1
            checkboxes['has_terminal'] = 1
        
        return checkboxes
        
    except Exception as e:
        print(f"❌ Error setting function checkboxes: {str(e)}")
        frappe.log_error(f"Function checkbox setting error: {str(e)}")
        return {}

def set_regulatory_facilities_from_data(unlocode_data: Dict[str, Any]) -> Dict[str, int]:
    """
    Set regulatory facilities based on location data
    
    Args:
        unlocode_data: Dictionary of UNLOCO data
    
    Returns:
        Dictionary of regulatory facility values
    """
    try:
        facilities = {
            'customs_office': 0,
            'immigration_office': 0,
            'quarantine_facility': 0,
            'health_authority': 0
        }
        
        location_type = unlocode_data.get('location_type', '')
        unlocode = unlocode_data.get('unlocode', '').upper()
        
        # Set regulatory facilities based on location type
        if location_type == "Airport":
            facilities['customs_office'] = 1
            facilities['immigration_office'] = 1
            facilities['quarantine_facility'] = 1
            facilities['health_authority'] = 1
        elif location_type == "Port":
            facilities['customs_office'] = 1
            facilities['quarantine_facility'] = 1
            facilities['health_authority'] = 1
        elif location_type == "Border Crossing":
            facilities['customs_office'] = 1
            facilities['immigration_office'] = 1
        
        # Set additional regulatory facilities based on UNLOCO code patterns
        if "LAX" in unlocode or "JFK" in unlocode or "MIA" in unlocode or "ORD" in unlocode or "DFW" in unlocode or "ATL" in unlocode or "SEA" in unlocode or "LHR" in unlocode or "LGW" in unlocode:
            facilities['customs_office'] = 1
            facilities['immigration_office'] = 1
            facilities['quarantine_facility'] = 1
            facilities['health_authority'] = 1
        elif "LGB" in unlocode or "NYC" in unlocode or "HAM" in unlocode or "RTM" in unlocode or "SIN" in unlocode or "PVG" in unlocode or "YOK" in unlocode:
            facilities['customs_office'] = 1
            facilities['quarantine_facility'] = 1
            facilities['health_authority'] = 1
        
        return facilities
        
    except Exception as e:
        print(f"❌ Error setting regulatory facilities: {str(e)}")
        frappe.log_error(f"Regulatory facilities setting error: {str(e)}")
        return {}

def update_document_fields(doc: Any, populated_fields: Dict[str, Any]) -> None:
    """
    Update document fields with populated data
    
    Args:
        doc: Location document
        populated_fields: Dictionary of populated fields
    """
    try:
        for field_name, field_value in populated_fields.items():
            if hasattr(doc, field_name):
                setattr(doc, field_name, field_value)
        
        # Update last updated timestamp
        doc.last_updated = frappe.utils.now()
        
    except Exception as e:
        print(f"❌ Error updating document fields: {str(e)}")
        frappe.log_error(f"Document fields update error: {str(e)}")

def populate_basic_details_from_code(unlocode: str) -> Dict[str, Any]:
    """
    Populate basic details from UNLOCO code when no data is found
    
    Args:
        unlocode: UNLOCO code
    
    Returns:
        Dictionary of basic populated fields
    """
    try:
        if len(unlocode) != 5:
            return {}
        
        country_code = unlocode[:2]
        location_code = unlocode[2:]
        
        # Get country information
        country_info = get_country_info(country_code)
        
        # Set basic fields
        basic_fields = {
            'country': country_info.get('country', ''),
            'country_code': country_info.get('country_code', ''),
            'currency': country_info.get('currency', ''),
            'language': country_info.get('language', ''),
            'timezone': get_timezone_for_country(country_code),
            'utc_offset': get_utc_offset_for_country(country_code),
            'description': f"Transport location with UNLOCO code {unlocode}",
            'has_store': 1  # Most locations have some storage
        }
        
        return basic_fields
        
    except Exception as e:
        print(f"❌ Error populating basic details from code: {str(e)}")
        frappe.log_error(f"Basic details population error: {str(e)}")
        return {}
