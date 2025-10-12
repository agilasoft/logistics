"""
Populate UNLOCO doctype with comprehensive data
- Create UNLOCO records from existing data
- Add comprehensive UNLOCO database
- Set up auto-populate functionality
"""

import frappe
from frappe import _

def execute():
    """Populate UNLOCO doctype with comprehensive data"""
    
    print("🌍 Populating UNLOCO doctype with comprehensive data...")
    print("=" * 60)
    
    # Populate UNLOCO data
    populate_unlocode_data()
    
    print("✅ UNLOCO doctype populated successfully!")

def populate_unlocode_data():
    """Populate UNLOCO doctype with comprehensive data"""
    try:
        print("📊 Populating UNLOCO data...")
        
        # Get comprehensive UNLOCO data
        unlocode_data = get_comprehensive_unlocode_data()
        
        results = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "created": 0,
            "updated": 0,
            "errors": []
        }
        
        for unlocode, location_data in unlocode_data.items():
            results["total_processed"] += 1
            
            try:
                # Check if this is a new location
                existing = frappe.db.get_value("UNLOCO", {"unlocode": unlocode})
                was_new = not existing
                
                # Create or update location
                location_name = create_or_update_unlocode(unlocode, location_data)
                
                if location_name:
                    results["successful"] += 1
                    if was_new:
                        results["created"] += 1
                    else:
                        results["updated"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append(f"Failed to process {unlocode}")
                    
            except Exception as e:
                results["failed"] += 1
                error_msg = f"Error processing {unlocode}: {str(e)}"
                results["errors"].append(error_msg)
                print(f"✗ {error_msg}")
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 UNLOCO Data Population Summary")
        print("=" * 60)
        print(f"Total Processed: {results['total_processed']}")
        print(f"Successful: {results['successful']}")
        print(f"Failed: {results['failed']}")
        print(f"Created: {results['created']}")
        print(f"Updated: {results['updated']}")
        
        if results["errors"]:
            print(f"\n❌ Errors ({len(results['errors'])}):")
            for error in results["errors"]:
                print(f"  - {error}")
        
        return results
        
    except Exception as e:
        print(f"✗ Error populating UNLOCO data: {str(e)}")
        frappe.log_error(f"UNLOCO data population error: {str(e)}")
        return None

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
            "description": "Los Angeles International Airport - Major international gateway to the US West Coast",
            "has_airport": 1,
            "has_customs": 1,
            "has_terminal": 1,
            "has_store": 1
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
            "description": "John F. Kennedy International Airport - Major international gateway to New York",
            "has_airport": 1,
            "has_customs": 1,
            "has_terminal": 1,
            "has_store": 1
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
            "description": "Miami International Airport - Gateway to Latin America and the Caribbean",
            "has_airport": 1,
            "has_customs": 1,
            "has_terminal": 1,
            "has_store": 1
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
            "description": "Chicago O'Hare International Airport - Major US hub and international gateway",
            "has_airport": 1,
            "has_customs": 1,
            "has_terminal": 1,
            "has_store": 1
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
            "description": "Dallas/Fort Worth International Airport - Major US hub",
            "has_airport": 1,
            "has_customs": 1,
            "has_terminal": 1,
            "has_store": 1
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
            "description": "Hartsfield-Jackson Atlanta International Airport - World's busiest airport",
            "has_airport": 1,
            "has_customs": 1,
            "has_terminal": 1,
            "has_store": 1
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
            "description": "Seattle-Tacoma International Airport - Gateway to the Pacific Northwest",
            "has_airport": 1,
            "has_customs": 1,
            "has_terminal": 1,
            "has_store": 1
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
            "description": "Port of Long Beach - Major container port on the US West Coast",
            "has_seaport": 1,
            "has_customs": 1,
            "has_unload": 1,
            "has_discharge": 1,
            "has_terminal": 1,
            "has_store": 1
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
            "description": "Port of New York and New Jersey - Major East Coast port",
            "has_seaport": 1,
            "has_customs": 1,
            "has_unload": 1,
            "has_discharge": 1,
            "has_terminal": 1,
            "has_store": 1
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
            "description": "London Heathrow Airport - Major international hub for Europe",
            "has_airport": 1,
            "has_customs": 1,
            "has_terminal": 1,
            "has_store": 1
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
            "description": "London Gatwick Airport - Secondary London airport",
            "has_airport": 1,
            "has_customs": 1,
            "has_terminal": 1,
            "has_store": 1
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
            "description": "Port of Hamburg - Major European port and gateway to Central Europe",
            "has_seaport": 1,
            "has_customs": 1,
            "has_unload": 1,
            "has_discharge": 1,
            "has_terminal": 1,
            "has_store": 1
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
            "description": "Port of Rotterdam - Europe's largest port",
            "has_seaport": 1,
            "has_customs": 1,
            "has_unload": 1,
            "has_discharge": 1,
            "has_terminal": 1,
            "has_store": 1
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
            "description": "Port of Singapore - World's busiest transshipment port",
            "has_seaport": 1,
            "has_customs": 1,
            "has_unload": 1,
            "has_discharge": 1,
            "has_terminal": 1,
            "has_store": 1
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
            "description": "Port of Shanghai - World's largest container port",
            "has_seaport": 1,
            "has_customs": 1,
            "has_unload": 1,
            "has_discharge": 1,
            "has_terminal": 1,
            "has_store": 1
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
            "description": "Port of Yokohama - Major Japanese port near Tokyo",
            "has_seaport": 1,
            "has_customs": 1,
            "has_unload": 1,
            "has_discharge": 1,
            "has_terminal": 1,
            "has_store": 1
        }
    }

def create_or_update_unlocode(unlocode, location_data):
    """Create or update a UNLOCO record with comprehensive data"""
    try:
        # Check if UNLOCO already exists
        existing_unlocode = frappe.db.get_value("UNLOCO", {"unlocode": unlocode})
        
        if existing_unlocode:
            # Update existing UNLOCO
            unlocode_doc = frappe.get_doc("UNLOCO", existing_unlocode)
            print(f"Updating existing UNLOCO: {unlocode}")
        else:
            # Create new UNLOCO
            unlocode_doc = frappe.get_doc({
                "doctype": "UNLOCO",
                "unlocode": unlocode
            })
            print(f"Creating new UNLOCO: {unlocode}")
        
        # Update/Set all UNLOCO fields with comprehensive data
        unlocode_doc.location_name = location_data.get('location_name', '')
        unlocode_doc.country = location_data.get('country', '')
        unlocode_doc.country_code = location_data.get('country_code', '')
        unlocode_doc.subdivision = location_data.get('subdivision', '')
        unlocode_doc.city = location_data.get('city', '')
        unlocode_doc.location_type = location_data.get('location_type', '')
        unlocode_doc.function = location_data.get('function', '')
        unlocode_doc.status = location_data.get('status', '')
        
        # Identifiers
        unlocode_doc.iata_code = location_data.get('iata_code', '')
        unlocode_doc.icao_code = location_data.get('icao_code', '')
        unlocode_doc.railway_code = location_data.get('railway_code', '')
        unlocode_doc.port_code = location_data.get('port_code', '')
        unlocode_doc.alternative_names = location_data.get('alternative_names', '')
        
        # Logistics Details
        unlocode_doc.timezone = location_data.get('timezone', '')
        unlocode_doc.currency = location_data.get('currency', '')
        unlocode_doc.language = location_data.get('language', '')
        unlocode_doc.utc_offset = location_data.get('utc_offset', '')
        unlocode_doc.operating_hours = location_data.get('operating_hours', '')
        
        # Function Capabilities
        unlocode_doc.has_post = location_data.get('has_post', 0)
        unlocode_doc.has_customs = location_data.get('has_customs', 0)
        unlocode_doc.has_unload = location_data.get('has_unload', 0)
        unlocode_doc.has_airport = location_data.get('has_airport', 0)
        unlocode_doc.has_rail = location_data.get('has_rail', 0)
        unlocode_doc.has_road = location_data.get('has_road', 0)
        unlocode_doc.has_store = location_data.get('has_store', 0)
        unlocode_doc.has_terminal = location_data.get('has_terminal', 0)
        unlocode_doc.has_discharge = location_data.get('has_discharge', 0)
        unlocode_doc.has_seaport = location_data.get('has_seaport', 0)
        unlocode_doc.has_outport = location_data.get('has_outport', 0)
        
        # Regulatory Facilities
        unlocode_doc.customs_office = location_data.get('customs_office', 0)
        unlocode_doc.immigration_office = location_data.get('immigration_office', 0)
        unlocode_doc.quarantine_facility = location_data.get('quarantine_facility', 0)
        unlocode_doc.health_authority = location_data.get('health_authority', 0)
        
        # Coordinates
        unlocode_doc.latitude = location_data.get('latitude')
        unlocode_doc.longitude = location_data.get('longitude')
        unlocode_doc.description = location_data.get('description', '')
        
        # Auto-populate settings
        unlocode_doc.auto_populate = 1
        unlocode_doc.last_updated = frappe.utils.now()
        unlocode_doc.data_source = "Internal Database"
        
        # Save the UNLOCO record
        unlocode_doc.save(ignore_permissions=True)
        frappe.db.commit()
        
        print(f"✓ Successfully processed UNLOCO: {unlocode_doc.name}")
        return unlocode_doc.name
        
    except Exception as e:
        print(f"✗ Error processing UNLOCO {unlocode}: {str(e)}")
        frappe.log_error(f"UNLOCO creation error: {str(e)}")
        return None

def main():
    """Main function for populating UNLOCO data"""
    try:
        print("🚀 Populating UNLOCO DocType with Comprehensive Data")
        print("=" * 60)
        
        # Populate UNLOCO data
        populate_unlocode_data()
        
        print("\n✅ UNLOCO doctype populated successfully!")
        print("\n📋 Data Populated:")
        print("  - 16 international locations with complete details")
        print("  - US Airports: LAX, JFK, MIA, ORD, DFW, ATL, SEA")
        print("  - US Ports: Long Beach, New York")
        print("  - International Airports: Heathrow, Gatwick")
        print("  - International Ports: Hamburg, Rotterdam, Singapore, Shanghai, Yokohama")
        print("  - All function capabilities and regulatory facilities")
        print("  - Auto-populate settings configured")
        
    except Exception as e:
        print(f"❌ Error populating UNLOCO data: {str(e)}")
        frappe.log_error(f"UNLOCO data population error: {str(e)}")

if __name__ == "__main__":
    main()
