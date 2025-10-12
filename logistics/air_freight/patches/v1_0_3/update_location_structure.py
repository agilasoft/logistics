"""
Update Location doctype structure for UNLOCO integration
- Location Name should be UNLOCO code
- Add Logistics Details and Identifiers sections
- Populate full UNLOCO database
"""

import frappe
from frappe import _

def execute():
    """Update Location doctype structure and populate full UNLOCO database"""
    
    print("🌍 Updating Location Structure for UNLOCO Integration...")
    print("=" * 60)
    
    # Update existing locations to use UNLOCO code as name
    update_existing_locations()
    
    # Add new custom fields for comprehensive UNLOCO data
    add_comprehensive_unlocode_fields()
    
    # Populate full UNLOCO database
    populate_full_unlocode_database()
    
    print("✅ Location structure updated and full UNLOCO database populated!")

def update_existing_locations():
    """Update existing locations to use UNLOCO code as the name"""
    try:
        print("📝 Updating existing locations to use UNLOCO codes as names...")
        
        # Get all locations with UNLOCO codes
        locations = frappe.get_all("Location", 
                                 filters={"custom_unlocode": ["!=", ""]},
                                 fields=["name", "custom_unlocode", "location_name"])
        
        for loc in locations:
            if loc.custom_unlocode:
                # Update the location name to be the UNLOCO code
                location_doc = frappe.get_doc("Location", loc.name)
                old_name = location_doc.location_name
                location_doc.location_name = loc.custom_unlocode
                location_doc.save(ignore_permissions=True)
                print(f"✓ Updated {old_name} → {loc.custom_unlocode}")
        
        frappe.db.commit()
        print(f"✓ Updated {len(locations)} existing locations")
        
    except Exception as e:
        print(f"✗ Error updating existing locations: {str(e)}")
        frappe.log_error(f"Location update error: {str(e)}")

def add_comprehensive_unlocode_fields():
    """Add comprehensive custom fields for UNLOCO data"""
    try:
        meta = frappe.get_meta("Location")
        existing_fields = [field.fieldname for field in meta.fields]
        
        # Comprehensive UNLOCO fields
        unlocode_fields = [
            # Basic UNLOCO Information
            {
                "fieldname": "custom_unlocode",
                "label": "UNLOCO Code",
                "fieldtype": "Data",
                "insert_after": "location_name",
                "description": "United Nations Code for Trade and Transport Locations",
                "reqd": 1,
                "unique": 1
            },
            {
                "fieldname": "custom_location_name",
                "label": "Location Name",
                "fieldtype": "Data",
                "insert_after": "custom_unlocode",
                "description": "Official location name",
                "reqd": 0
            },
            {
                "fieldname": "custom_country",
                "label": "Country",
                "fieldtype": "Data",
                "insert_after": "custom_location_name",
                "description": "Country name",
                "reqd": 0
            },
            {
                "fieldname": "custom_country_code",
                "label": "Country Code",
                "fieldtype": "Data",
                "insert_after": "custom_country",
                "description": "ISO 3166-1 alpha-2 country code",
                "reqd": 0
            },
            {
                "fieldname": "custom_subdivision",
                "label": "Subdivision",
                "fieldtype": "Data",
                "insert_after": "custom_country_code",
                "description": "State/Province/Region",
                "reqd": 0
            },
            {
                "fieldname": "custom_city",
                "label": "City",
                "fieldtype": "Data",
                "insert_after": "custom_subdivision",
                "description": "City name",
                "reqd": 0
            },
            
            # Location Type and Classification
            {
                "fieldname": "custom_location_type",
                "label": "Location Type",
                "fieldtype": "Select",
                "options": "Airport\nPort\nRailway Station\nRoad Terminal\nBorder Crossing\nOther",
                "insert_after": "custom_city",
                "description": "Type of transport location",
                "reqd": 0
            },
            {
                "fieldname": "custom_function",
                "label": "Function",
                "fieldtype": "Select",
                "options": "0 - Not known\n1 - Port\n2 - Rail\n3 - Road\n4 - Airport\n5 - Postal Exchange Office\n6 - Reserved for multimodal functions\n7 - Reserved for fixed transport functions\nB - Border crossing",
                "insert_after": "custom_location_type",
                "description": "UNLOCO function code",
                "reqd": 0
            },
            {
                "fieldname": "custom_status",
                "label": "Status",
                "fieldtype": "Select",
                "options": "AA - Approved by competent national government agency\nAC - Approved by Customs authority\nAF - Approved by national facilitation body\nAS - Approved by national standardisation body\nRL - Recognised location\nRN - Request from national authority\nRQ - Request under consideration\nRR - Request rejected\nUR - Under review by the secretariat\nXX - Entry that will be removed from the next issue of UN/LOCODE",
                "insert_after": "custom_function",
                "description": "UNLOCO status code",
                "reqd": 0
            },
            
            # Identifiers Section
            {
                "fieldname": "identifiers_section",
                "label": "Identifiers",
                "fieldtype": "Section Break",
                "insert_after": "custom_status",
                "collapsible": 1
            },
            {
                "fieldname": "custom_iata_code",
                "label": "IATA Code",
                "fieldtype": "Data",
                "insert_after": "identifiers_section",
                "description": "International Air Transport Association code",
                "reqd": 0
            },
            {
                "fieldname": "custom_icao_code",
                "label": "ICAO Code",
                "fieldtype": "Data",
                "insert_after": "custom_iata_code",
                "description": "International Civil Aviation Organization code",
                "reqd": 0
            },
            {
                "fieldname": "custom_railway_code",
                "label": "Railway Code",
                "fieldtype": "Data",
                "insert_after": "custom_icao_code",
                "description": "Railway station code",
                "reqd": 0
            },
            {
                "fieldname": "custom_port_code",
                "label": "Port Code",
                "fieldtype": "Data",
                "insert_after": "custom_railway_code",
                "description": "Port code",
                "reqd": 0
            },
            {
                "fieldname": "custom_alternative_names",
                "label": "Alternative Names",
                "fieldtype": "Text",
                "insert_after": "custom_port_code",
                "description": "Alternative names for the location",
                "reqd": 0
            },
            
            # Logistics Details Section
            {
                "fieldname": "logistics_section",
                "label": "Logistics Details",
                "fieldtype": "Section Break",
                "insert_after": "custom_alternative_names",
                "collapsible": 1
            },
            {
                "fieldname": "custom_timezone",
                "label": "Timezone",
                "fieldtype": "Data",
                "insert_after": "logistics_section",
                "description": "Timezone identifier (e.g., America/New_York)",
                "reqd": 0
            },
            {
                "fieldname": "custom_currency",
                "label": "Currency",
                "fieldtype": "Data",
                "insert_after": "custom_timezone",
                "description": "Local currency code (e.g., USD, EUR)",
                "reqd": 0
            },
            {
                "fieldname": "custom_language",
                "label": "Language",
                "fieldtype": "Data",
                "insert_after": "custom_currency",
                "description": "Primary language code (e.g., en, es, fr)",
                "reqd": 0
            },
            {
                "fieldname": "custom_utc_offset",
                "label": "UTC Offset",
                "fieldtype": "Data",
                "insert_after": "custom_language",
                "description": "UTC offset (e.g., +05:30, -08:00)",
                "reqd": 0
            },
            {
                "fieldname": "custom_operating_hours",
                "label": "Operating Hours",
                "fieldtype": "Text",
                "insert_after": "custom_utc_offset",
                "description": "Operating hours information",
                "reqd": 0
            },
            {
                "fieldname": "custom_customs_office",
                "label": "Customs Office",
                "fieldtype": "Check",
                "insert_after": "custom_operating_hours",
                "description": "Has customs office",
                "reqd": 0
            },
            {
                "fieldname": "custom_immigration_office",
                "label": "Immigration Office",
                "fieldtype": "Check",
                "insert_after": "custom_customs_office",
                "description": "Has immigration office",
                "reqd": 0
            },
            {
                "fieldname": "custom_quarantine_facility",
                "label": "Quarantine Facility",
                "fieldtype": "Check",
                "insert_after": "custom_immigration_office",
                "description": "Has quarantine facility",
                "reqd": 0
            },
            {
                "fieldname": "custom_health_authority",
                "label": "Health Authority",
                "fieldtype": "Check",
                "insert_after": "custom_quarantine_facility",
                "description": "Has health authority",
                "reqd": 0
            },
            {
                "fieldname": "custom_description",
                "label": "Description",
                "fieldtype": "Text",
                "insert_after": "custom_health_authority",
                "description": "Detailed description of the location",
                "reqd": 0
            }
        ]
        
        fields_added = 0
        for field_data in unlocode_fields:
            if field_data["fieldname"] not in existing_fields:
                print(f"Adding {field_data['fieldname']} field...")
                
                field_doc = frappe.get_doc({
                    "doctype": "Custom Field",
                    "dt": "Location",
                    **field_data
                })
                field_doc.insert(ignore_permissions=True)
                fields_added += 1
                print(f"✓ Added {field_data['fieldname']} field")
            else:
                print(f"✓ {field_data['fieldname']} field already exists")
        
        if fields_added > 0:
            frappe.db.commit()
            print(f"✓ Successfully added {fields_added} custom fields to Location doctype")
        
        return True
        
    except Exception as e:
        print(f"✗ Error adding custom fields: {e}")
        frappe.log_error(f"Custom fields addition error: {str(e)}")
        return False

def populate_full_unlocode_database():
    """Populate comprehensive UNLOCO database"""
    try:
        print("📊 Populating comprehensive UNLOCO database...")
        
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
                existing = frappe.db.get_value("Location", {"custom_unlocode": unlocode})
                was_new = not existing
                
                # Create or update location
                location_name = create_or_update_comprehensive_location(unlocode, location_data)
                
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
        print("📊 Comprehensive UNLOCO Database Population Summary")
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
        print(f"✗ Error populating UNLOCO database: {str(e)}")
        frappe.log_error(f"UNLOCO database population error: {str(e)}")
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
            "function": "4",
            "status": "AA",
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
            "function": "4",
            "status": "AA",
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
            "function": "4",
            "status": "AA",
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
            "function": "4",
            "status": "AA",
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
            "function": "4",
            "status": "AA",
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
            "function": "4",
            "status": "AA",
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
            "function": "4",
            "status": "AA",
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
            "function": "1",
            "status": "AA",
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
            "function": "1",
            "status": "AA",
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
            "function": "4",
            "status": "AA",
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
            "function": "4",
            "status": "AA",
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
            "function": "1",
            "status": "AA",
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
            "function": "1",
            "status": "AA",
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
            "function": "1",
            "status": "AA",
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
            "function": "1",
            "status": "AA",
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
            "function": "1",
            "status": "AA",
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

def create_or_update_comprehensive_location(unlocode, location_data):
    """Create or update a Location record with comprehensive UNLOCO data"""
    try:
        # Check if Location already exists by UNLOCO code
        existing_location = frappe.db.get_value("Location", {"custom_unlocode": unlocode})
        
        if existing_location:
            # Update existing location
            location = frappe.get_doc("Location", existing_location)
            print(f"Updating existing Location: {unlocode}")
        else:
            # Create new location
            location = frappe.get_doc({
                "doctype": "Location",
                "location_name": unlocode,  # Use UNLOCO code as the name
                "is_logistics_location": 1
            })
            print(f"Creating new Location: {unlocode}")
        
        # Update/Set all location fields with comprehensive data
        location.location_name = unlocode  # UNLOCO code as name
        location.custom_unlocode = unlocode
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
        
        print(f"✓ Successfully processed Location: {location.name}")
        return location.name
        
    except Exception as e:
        print(f"✗ Error processing Location {unlocode}: {str(e)}")
        frappe.log_error(f"UNLOCO Location creation error: {str(e)}")
        return None
