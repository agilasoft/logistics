"""
Populate detailed UNLOCO information for all locations
"""

import frappe
from frappe import _

def execute():
    """Populate detailed UNLOCO information"""
    
    print("🌍 Populating Detailed UNLOCO Information...")
    print("=" * 60)
    
    # Get comprehensive UNLOCO data
    unlocode_data = get_comprehensive_unlocode_data()
    
    results = {
        "total_processed": 0,
        "successful": 0,
        "failed": 0,
        "errors": []
    }
    
    for unlocode, location_data in unlocode_data.items():
        results["total_processed"] += 1
        
        try:
            # Update location with detailed information
            location_name = update_location_with_details(unlocode, location_data)
            
            if location_name:
                results["successful"] += 1
                print(f"✓ Updated {unlocode} with detailed information")
            else:
                results["failed"] += 1
                results["errors"].append(f"Failed to update {unlocode}")
                
        except Exception as e:
            results["failed"] += 1
            error_msg = f"Error updating {unlocode}: {str(e)}"
            results["errors"].append(error_msg)
            print(f"✗ {error_msg}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 Detailed UNLOCO Information Population Summary")
    print("=" * 60)
    print(f"Total Processed: {results['total_processed']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    
    if results["errors"]:
        print(f"\n❌ Errors ({len(results['errors'])}):")
        for error in results["errors"]:
            print(f"  - {error}")
    
    print("\n✅ Detailed UNLOCO information populated successfully!")
    return results

def get_comprehensive_unlocode_data():
    """Get comprehensive UNLOCO data with full details"""
    return {
        # US Airports
        "USLAX": {
            "location_name": "Los Angeles International Airport",
            "country": "United States",
            "country_code": "US",
            "subdivision": "California",
            "city": "Los Angeles",
            "location_type": "Airport",
            "function": "4 - Airport",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "LAX",
            "icao_code": "KLAX",
            "timezone": "America/Los_Angeles",
            "currency": "USD",
            "language": "en",
            "utc_offset": "-08:00",
            "operating_hours": "24/7",
            "customs_office": 1,
            "immigration_office": 1,
            "quarantine_facility": 1,
            "health_authority": 1,
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
            "function": "4 - Airport",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "JFK",
            "icao_code": "KJFK",
            "timezone": "America/New_York",
            "currency": "USD",
            "language": "en",
            "utc_offset": "-05:00",
            "operating_hours": "24/7",
            "customs_office": 1,
            "immigration_office": 1,
            "quarantine_facility": 1,
            "health_authority": 1,
            "latitude": 40.6413,
            "longitude": -73.7781,
            "description": "John F. Kennedy International Airport - Major international gateway to New York"
        },
        "USMIA": {
            "location_name": "Miami International Airport",
            "country": "United States",
            "country_code": "US",
            "subdivision": "Florida",
            "city": "Miami",
            "location_type": "Airport",
            "function": "4 - Airport",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "MIA",
            "icao_code": "KMIA",
            "timezone": "America/New_York",
            "currency": "USD",
            "language": "en",
            "utc_offset": "-05:00",
            "operating_hours": "24/7",
            "customs_office": 1,
            "immigration_office": 1,
            "quarantine_facility": 1,
            "health_authority": 1,
            "latitude": 25.7959,
            "longitude": -80.2870,
            "description": "Miami International Airport - Gateway to Latin America and the Caribbean"
        },
        "USORD": {
            "location_name": "Chicago O'Hare International Airport",
            "country": "United States",
            "country_code": "US",
            "subdivision": "Illinois",
            "city": "Chicago",
            "location_type": "Airport",
            "function": "4 - Airport",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "ORD",
            "icao_code": "KORD",
            "timezone": "America/Chicago",
            "currency": "USD",
            "language": "en",
            "utc_offset": "-06:00",
            "operating_hours": "24/7",
            "customs_office": 1,
            "immigration_office": 1,
            "quarantine_facility": 1,
            "health_authority": 1,
            "latitude": 41.9786,
            "longitude": -87.9048,
            "description": "Chicago O'Hare International Airport - Major US hub and international gateway"
        },
        "USDFW": {
            "location_name": "Dallas/Fort Worth International Airport",
            "country": "United States",
            "country_code": "US",
            "subdivision": "Texas",
            "city": "Dallas",
            "location_type": "Airport",
            "function": "4 - Airport",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "DFW",
            "icao_code": "KDFW",
            "timezone": "America/Chicago",
            "currency": "USD",
            "language": "en",
            "utc_offset": "-06:00",
            "operating_hours": "24/7",
            "customs_office": 1,
            "immigration_office": 1,
            "quarantine_facility": 1,
            "health_authority": 1,
            "latitude": 32.8968,
            "longitude": -97.0380,
            "description": "Dallas/Fort Worth International Airport - Major US hub"
        },
        "USATL": {
            "location_name": "Hartsfield-Jackson Atlanta International Airport",
            "country": "United States",
            "country_code": "US",
            "subdivision": "Georgia",
            "city": "Atlanta",
            "location_type": "Airport",
            "function": "4 - Airport",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "ATL",
            "icao_code": "KATL",
            "timezone": "America/New_York",
            "currency": "USD",
            "language": "en",
            "utc_offset": "-05:00",
            "operating_hours": "24/7",
            "customs_office": 1,
            "immigration_office": 1,
            "quarantine_facility": 1,
            "health_authority": 1,
            "latitude": 33.6407,
            "longitude": -84.4277,
            "description": "Hartsfield-Jackson Atlanta International Airport - World's busiest airport"
        },
        "USSEA": {
            "location_name": "Seattle-Tacoma International Airport",
            "country": "United States",
            "country_code": "US",
            "subdivision": "Washington",
            "city": "Seattle",
            "location_type": "Airport",
            "function": "4 - Airport",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "SEA",
            "icao_code": "KSEA",
            "timezone": "America/Los_Angeles",
            "currency": "USD",
            "language": "en",
            "utc_offset": "-08:00",
            "operating_hours": "24/7",
            "customs_office": 1,
            "immigration_office": 1,
            "quarantine_facility": 1,
            "health_authority": 1,
            "latitude": 47.4502,
            "longitude": -122.3088,
            "description": "Seattle-Tacoma International Airport - Gateway to the Pacific Northwest"
        },
        
        # US Ports
        "USLGB": {
            "location_name": "Port of Long Beach",
            "country": "United States",
            "country_code": "US",
            "subdivision": "California",
            "city": "Long Beach",
            "location_type": "Port",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "LGB",
            "icao_code": "KLGB",
            "timezone": "America/Los_Angeles",
            "currency": "USD",
            "language": "en",
            "utc_offset": "-08:00",
            "operating_hours": "24/7",
            "customs_office": 1,
            "immigration_office": 0,
            "quarantine_facility": 1,
            "health_authority": 1,
            "latitude": 33.8172,
            "longitude": -118.1515,
            "description": "Port of Long Beach - Major container port on the US West Coast"
        },
        "USNYC": {
            "location_name": "Port of New York and New Jersey",
            "country": "United States",
            "country_code": "US",
            "subdivision": "New York",
            "city": "New York",
            "location_type": "Port",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "NYC",
            "icao_code": "KNYC",
            "timezone": "America/New_York",
            "currency": "USD",
            "language": "en",
            "utc_offset": "-05:00",
            "operating_hours": "24/7",
            "customs_office": 1,
            "immigration_office": 0,
            "quarantine_facility": 1,
            "health_authority": 1,
            "latitude": 40.7128,
            "longitude": -74.0060,
            "description": "Port of New York and New Jersey - Major East Coast port"
        },
        
        # International Airports
        "GBLHR": {
            "location_name": "London Heathrow Airport",
            "country": "United Kingdom",
            "country_code": "GB",
            "subdivision": "England",
            "city": "London",
            "location_type": "Airport",
            "function": "4 - Airport",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "LHR",
            "icao_code": "EGLL",
            "timezone": "Europe/London",
            "currency": "GBP",
            "language": "en",
            "utc_offset": "+00:00",
            "operating_hours": "24/7",
            "customs_office": 1,
            "immigration_office": 1,
            "quarantine_facility": 1,
            "health_authority": 1,
            "latitude": 51.4700,
            "longitude": -0.4543,
            "description": "London Heathrow Airport - Major international hub for Europe"
        },
        "GBLGW": {
            "location_name": "London Gatwick Airport",
            "country": "United Kingdom",
            "country_code": "GB",
            "subdivision": "England",
            "city": "London",
            "location_type": "Airport",
            "function": "4 - Airport",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "LGW",
            "icao_code": "EGKK",
            "timezone": "Europe/London",
            "currency": "GBP",
            "language": "en",
            "utc_offset": "+00:00",
            "operating_hours": "24/7",
            "customs_office": 1,
            "immigration_office": 1,
            "quarantine_facility": 1,
            "health_authority": 1,
            "latitude": 51.1481,
            "longitude": -0.1903,
            "description": "London Gatwick Airport - Secondary London airport"
        },
        
        # International Ports
        "DEHAM": {
            "location_name": "Port of Hamburg",
            "country": "Germany",
            "country_code": "DE",
            "subdivision": "Hamburg",
            "city": "Hamburg",
            "location_type": "Port",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "HAM",
            "icao_code": "EDDH",
            "timezone": "Europe/Berlin",
            "currency": "EUR",
            "language": "de",
            "utc_offset": "+01:00",
            "operating_hours": "24/7",
            "customs_office": 1,
            "immigration_office": 0,
            "quarantine_facility": 1,
            "health_authority": 1,
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
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "RTM",
            "icao_code": "EHRD",
            "timezone": "Europe/Amsterdam",
            "currency": "EUR",
            "language": "nl",
            "utc_offset": "+01:00",
            "operating_hours": "24/7",
            "customs_office": 1,
            "immigration_office": 0,
            "quarantine_facility": 1,
            "health_authority": 1,
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
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "SIN",
            "icao_code": "WSSS",
            "timezone": "Asia/Singapore",
            "currency": "SGD",
            "language": "en",
            "utc_offset": "+08:00",
            "operating_hours": "24/7",
            "customs_office": 1,
            "immigration_office": 0,
            "quarantine_facility": 1,
            "health_authority": 1,
            "latitude": 1.2966,
            "longitude": 103.7764,
            "description": "Port of Singapore - World's busiest transshipment port"
        },
        "CNPVG": {
            "location_name": "Port of Shanghai",
            "country": "China",
            "country_code": "CN",
            "subdivision": "Shanghai",
            "city": "Shanghai",
            "location_type": "Port",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "PVG",
            "icao_code": "ZSPD",
            "timezone": "Asia/Shanghai",
            "currency": "CNY",
            "language": "zh",
            "utc_offset": "+08:00",
            "operating_hours": "24/7",
            "customs_office": 1,
            "immigration_office": 0,
            "quarantine_facility": 1,
            "health_authority": 1,
            "latitude": 31.1434,
            "longitude": 121.8052,
            "description": "Port of Shanghai - World's largest container port"
        },
        "JPYOK": {
            "location_name": "Port of Yokohama",
            "country": "Japan",
            "country_code": "JP",
            "subdivision": "Kanagawa",
            "city": "Yokohama",
            "location_type": "Port",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "YOK",
            "icao_code": "RJTY",
            "timezone": "Asia/Tokyo",
            "currency": "JPY",
            "language": "ja",
            "utc_offset": "+09:00",
            "operating_hours": "24/7",
            "customs_office": 1,
            "immigration_office": 0,
            "quarantine_facility": 1,
            "health_authority": 1,
            "latitude": 35.4437,
            "longitude": 139.6380,
            "description": "Port of Yokohama - Major Japanese port near Tokyo"
        }
    }

def update_location_with_details(unlocode, location_data):
    """Update location with detailed UNLOCO information"""
    try:
        # Get existing location
        location = frappe.get_doc("Location", unlocode)
        
        # Update all fields with detailed information
        location.custom_location_name = location_data.get('location_name', '')
        location.custom_country = location_data.get('country', '')
        location.custom_country_code = location_data.get('country_code', '')
        location.custom_subdivision = location_data.get('subdivision', '')
        location.custom_city = location_data.get('city', '')
        location.custom_location_type = location_data.get('location_type', '')
        location.custom_function = location_data.get('function', '')
        location.custom_status = location_data.get('status', '')
        
        # Identifiers
        location.custom_iata_code = location_data.get('iata_code', '')
        location.custom_icao_code = location_data.get('icao_code', '')
        location.custom_railway_code = location_data.get('railway_code', '')
        location.custom_port_code = location_data.get('port_code', '')
        location.custom_alternative_names = location_data.get('alternative_names', '')
        
        # Logistics Details
        location.custom_timezone = location_data.get('timezone', '')
        location.custom_currency = location_data.get('currency', '')
        location.custom_language = location_data.get('language', '')
        location.custom_utc_offset = location_data.get('utc_offset', '')
        location.custom_operating_hours = location_data.get('operating_hours', '')
        location.custom_customs_office = location_data.get('customs_office', 0)
        location.custom_immigration_office = location_data.get('immigration_office', 0)
        location.custom_quarantine_facility = location_data.get('quarantine_facility', 0)
        location.custom_health_authority = location_data.get('health_authority', 0)
        location.custom_description = location_data.get('description', '')
        
        # Coordinates
        location.latitude = location_data.get('latitude')
        location.longitude = location_data.get('longitude')
        location.is_logistics_location = 1
        
        # Save the location
        location.save(ignore_permissions=True)
        frappe.db.commit()
        
        return location.name
        
    except Exception as e:
        print(f"✗ Error updating Location {unlocode}: {str(e)}")
        frappe.log_error(f"Location update error: {str(e)}")
        return None
