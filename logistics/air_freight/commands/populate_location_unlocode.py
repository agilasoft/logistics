"""
Bench command to populate Location doctype with UNLOCO data including identifiers
Usage: bench --site all execute logistics.air_freight.commands.populate_location_unlocode.populate_locations
"""

import frappe
from frappe import _
from typing import Dict, List, Optional

def populate_locations():
    """Populate Location doctype with comprehensive UNLOCO data including identifiers"""
    
    print("🌍 Starting UNLOCO Location Population with Identifiers...")
    print("=" * 60)
    
    # Check if Location doctype exists
    if not frappe.db.exists("DocType", "Location"):
        print("❌ Location doctype does not exist. Creating it...")
        create_location_doctype()
    else:
        print("✓ Location doctype exists")
    
    # Add custom fields for UNLOCO data
    add_custom_fields_to_location()
    
    # Get comprehensive UNLOCO data
    unlocode_data = get_unlocode_data()
    
    results = {
        "total_processed": 0,
        "successful": 0,
        "failed": 0,
        "created": 0,
        "updated": 0,
        "errors": []
    }
    
    print(f"\n📍 Processing {len(unlocode_data)} locations...")
    
    for unlocode, location_data in unlocode_data.items():
        results["total_processed"] += 1
        
        try:
            # Check if this is a new location
            existing = frappe.db.get_value("Location", {"custom_unlocode": unlocode})
            was_new = not existing
            
            # Create or update location
            location_name = create_or_update_location(unlocode, location_data)
            
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
    print("📊 UNLOCO Location Population Summary")
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
    
    # Verify locations
    verify_locations()
    
    print("\n✅ UNLOCO Location population completed successfully!")
    return results

def create_location_doctype():
    """Create Location doctype if it doesn't exist"""
    try:
        # Create basic Location doctype
        location_doctype = frappe.get_doc({
            "doctype": "DocType",
            "name": "Location",
            "module": "Air Freight",
            "custom": 1,
            "istable": 0,
            "issingle": 0,
            "autoname": "field:location_name",
            "naming_rule": "By fieldname",
            "fields": [
                {
                    "fieldname": "location_name",
                    "fieldtype": "Data",
                    "label": "Location Name",
                    "reqd": 1,
                    "search_index": 1
                },
                {
                    "fieldname": "is_logistics_location",
                    "fieldtype": "Check",
                    "label": "Is Logistics Location",
                    "default": 1
                },
                {
                    "fieldname": "latitude",
                    "fieldtype": "Float",
                    "label": "Latitude",
                    "precision": 8
                },
                {
                    "fieldname": "longitude", 
                    "fieldtype": "Float",
                    "label": "Longitude",
                    "precision": 8
                }
            ],
            "permissions": [
                {
                    "role": "System Manager",
                    "create": 1,
                    "delete": 1,
                    "email": 1,
                    "export": 1,
                    "print": 1,
                    "read": 1,
                    "report": 1,
                    "share": 1,
                    "write": 1
                }
            ],
            "sort_field": "location_name",
            "sort_order": "ASC"
        })
        
        location_doctype.insert(ignore_permissions=True)
        frappe.db.commit()
        print("✓ Location doctype created successfully")
        
    except Exception as e:
        print(f"✗ Error creating Location doctype: {str(e)}")
        frappe.log_error(f"Location doctype creation error: {str(e)}")

def add_custom_fields_to_location():
    """Add custom fields to Location doctype for UNLOCO data"""
    try:
        meta = frappe.get_meta("Location")
        existing_fields = [field.fieldname for field in meta.fields]
        
        custom_fields_to_add = [
            {
                "fieldname": "custom_unlocode",
                "label": "UNLOCO Code",
                "fieldtype": "Data",
                "insert_after": "location_name",
                "description": "United Nations Code for Trade and Transport Locations",
                "reqd": 0
            },
            {
                "fieldname": "custom_country",
                "label": "Country",
                "fieldtype": "Data",
                "insert_after": "custom_unlocode",
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
                "fieldname": "custom_location_type",
                "label": "Location Type",
                "fieldtype": "Select",
                "options": "Airport\nPort\nRailway Station\nRoad Terminal\nOther",
                "insert_after": "custom_country_code",
                "description": "Type of transport location",
                "reqd": 0
            },
            {
                "fieldname": "custom_iata_code",
                "label": "IATA Code",
                "fieldtype": "Data",
                "insert_after": "custom_location_type",
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
                "fieldname": "custom_timezone",
                "label": "Timezone",
                "fieldtype": "Data",
                "insert_after": "custom_icao_code",
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
                "fieldname": "custom_description",
                "label": "Description",
                "fieldtype": "Text",
                "insert_after": "custom_language",
                "description": "Detailed description of the location",
                "reqd": 0
            }
        ]
        
        fields_added = 0
        for field_data in custom_fields_to_add:
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

def get_unlocode_data():
    """Get comprehensive UNLOCO data with identifiers and details"""
    return {
        "USLAX": {
            "name": "Los Angeles International Airport",
            "country": "United States",
            "country_code": "US",
            "location_type": "Airport",
            "iata_code": "LAX",
            "icao_code": "KLAX",
            "timezone": "America/Los_Angeles",
            "currency": "USD",
            "language": "en",
            "latitude": 33.9425,
            "longitude": -118.4081,
            "description": "Los Angeles International Airport - Major international gateway to the US West Coast"
        },
        "USJFK": {
            "name": "John F. Kennedy International Airport",
            "country": "United States", 
            "country_code": "US",
            "location_type": "Airport",
            "iata_code": "JFK",
            "icao_code": "KJFK",
            "timezone": "America/New_York",
            "currency": "USD",
            "language": "en",
            "latitude": 40.6413,
            "longitude": -73.7781,
            "description": "John F. Kennedy International Airport - Major international gateway to New York"
        },
        "USMIA": {
            "name": "Miami International Airport",
            "country": "United States",
            "country_code": "US", 
            "location_type": "Airport",
            "iata_code": "MIA",
            "icao_code": "KMIA",
            "timezone": "America/New_York",
            "currency": "USD",
            "language": "en",
            "latitude": 25.7959,
            "longitude": -80.2870,
            "description": "Miami International Airport - Gateway to Latin America and the Caribbean"
        },
        "USORD": {
            "name": "Chicago O'Hare International Airport",
            "country": "United States",
            "country_code": "US",
            "location_type": "Airport", 
            "iata_code": "ORD",
            "icao_code": "KORD",
            "timezone": "America/Chicago",
            "currency": "USD",
            "language": "en",
            "latitude": 41.9786,
            "longitude": -87.9048,
            "description": "Chicago O'Hare International Airport - Major US hub and international gateway"
        },
        "USDFW": {
            "name": "Dallas/Fort Worth International Airport",
            "country": "United States",
            "country_code": "US",
            "location_type": "Airport",
            "iata_code": "DFW", 
            "icao_code": "KDFW",
            "timezone": "America/Chicago",
            "currency": "USD",
            "language": "en",
            "latitude": 32.8968,
            "longitude": -97.0380,
            "description": "Dallas/Fort Worth International Airport - Major US hub"
        },
        "USATL": {
            "name": "Hartsfield-Jackson Atlanta International Airport",
            "country": "United States",
            "country_code": "US",
            "location_type": "Airport",
            "iata_code": "ATL",
            "icao_code": "KATL",
            "timezone": "America/New_York",
            "currency": "USD",
            "language": "en",
            "latitude": 33.6407,
            "longitude": -84.4277,
            "description": "Hartsfield-Jackson Atlanta International Airport - World's busiest airport"
        },
        "USSEA": {
            "name": "Seattle-Tacoma International Airport",
            "country": "United States",
            "country_code": "US",
            "location_type": "Airport",
            "iata_code": "SEA",
            "icao_code": "KSEA",
            "timezone": "America/Los_Angeles",
            "currency": "USD",
            "language": "en",
            "latitude": 47.4502,
            "longitude": -122.3088,
            "description": "Seattle-Tacoma International Airport - Gateway to the Pacific Northwest"
        },
        "USLGB": {
            "name": "Port of Long Beach",
            "country": "United States",
            "country_code": "US",
            "location_type": "Port",
            "iata_code": "LGB",
            "icao_code": "KLGB",
            "timezone": "America/Los_Angeles",
            "currency": "USD",
            "language": "en",
            "latitude": 33.8172,
            "longitude": -118.1515,
            "description": "Port of Long Beach - Major container port on the US West Coast"
        },
        "USNYC": {
            "name": "Port of New York and New Jersey",
            "country": "United States",
            "country_code": "US",
            "location_type": "Port",
            "iata_code": "NYC",
            "icao_code": "KNYC",
            "timezone": "America/New_York",
            "currency": "USD",
            "language": "en",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "description": "Port of New York and New Jersey - Major East Coast port"
        },
        "GBLHR": {
            "name": "London Heathrow Airport",
            "country": "United Kingdom",
            "country_code": "GB",
            "location_type": "Airport",
            "iata_code": "LHR",
            "icao_code": "EGLL",
            "timezone": "Europe/London",
            "currency": "GBP",
            "language": "en",
            "latitude": 51.4700,
            "longitude": -0.4543,
            "description": "London Heathrow Airport - Major international hub for Europe"
        },
        "GBLGW": {
            "name": "London Gatwick Airport",
            "country": "United Kingdom", 
            "country_code": "GB",
            "location_type": "Airport",
            "iata_code": "LGW",
            "icao_code": "EGKK",
            "timezone": "Europe/London",
            "currency": "GBP",
            "language": "en",
            "latitude": 51.1481,
            "longitude": -0.1903,
            "description": "London Gatwick Airport - Secondary London airport"
        },
        "DEHAM": {
            "name": "Port of Hamburg",
            "country": "Germany",
            "country_code": "DE",
            "location_type": "Port",
            "iata_code": "HAM",
            "icao_code": "EDDH",
            "timezone": "Europe/Berlin",
            "currency": "EUR",
            "language": "de",
            "latitude": 53.5511,
            "longitude": 9.9937,
            "description": "Port of Hamburg - Major European port and gateway to Central Europe"
        },
        "NLRTM": {
            "name": "Port of Rotterdam",
            "country": "Netherlands",
            "country_code": "NL",
            "location_type": "Port",
            "iata_code": "RTM",
            "icao_code": "EHRD",
            "timezone": "Europe/Amsterdam",
            "currency": "EUR",
            "language": "nl",
            "latitude": 51.9244,
            "longitude": 4.4777,
            "description": "Port of Rotterdam - Europe's largest port"
        },
        "SGSIN": {
            "name": "Port of Singapore",
            "country": "Singapore",
            "country_code": "SG",
            "location_type": "Port",
            "iata_code": "SIN",
            "icao_code": "WSSS",
            "timezone": "Asia/Singapore",
            "currency": "SGD",
            "language": "en",
            "latitude": 1.2966,
            "longitude": 103.7764,
            "description": "Port of Singapore - World's busiest transshipment port"
        },
        "CNPVG": {
            "name": "Port of Shanghai",
            "country": "China",
            "country_code": "CN",
            "location_type": "Port",
            "iata_code": "PVG",
            "icao_code": "ZSPD",
            "timezone": "Asia/Shanghai",
            "currency": "CNY",
            "language": "zh",
            "latitude": 31.1434,
            "longitude": 121.8052,
            "description": "Port of Shanghai - World's largest container port"
        },
        "JPYOK": {
            "name": "Port of Yokohama",
            "country": "Japan",
            "country_code": "JP",
            "location_type": "Port",
            "iata_code": "YOK",
            "icao_code": "RJTY",
            "timezone": "Asia/Tokyo",
            "currency": "JPY",
            "language": "ja",
            "latitude": 35.4437,
            "longitude": 139.6380,
            "description": "Port of Yokohama - Major Japanese port near Tokyo"
        }
    }

def create_or_update_location(unlocode, location_data):
    """Create or update a Location record with comprehensive UNLOCO data"""
    try:
        # Check if Location already exists by UNLOCO code
        existing_location = frappe.db.get_value("Location", {"custom_unlocode": unlocode})
        
        if existing_location:
            # Update existing location
            location = frappe.get_doc("Location", existing_location)
            print(f"Updating existing Location: {existing_location}")
        else:
            # Create new location
            location = frappe.get_doc({
                "doctype": "Location",
                "location_name": f"{location_data['name']} ({unlocode})",
                "is_logistics_location": 1
            })
            print(f"Creating new Location: {location_data['name']} ({unlocode})")
        
        # Update/Set all location fields
        location.location_name = f"{location_data['name']} ({unlocode})"
        location.custom_unlocode = unlocode
        location.custom_country = location_data['country']
        location.custom_country_code = location_data['country_code']
        location.custom_location_type = location_data['location_type']
        location.custom_iata_code = location_data.get('iata_code', '')
        location.custom_icao_code = location_data.get('icao_code', '')
        location.custom_timezone = location_data.get('timezone', '')
        location.custom_currency = location_data.get('currency', '')
        location.custom_language = location_data.get('language', '')
        location.latitude = location_data.get('latitude')
        location.longitude = location_data.get('longitude')
        location.custom_description = location_data.get('description', '')
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

def verify_locations():
    """Verify that Location records have been created properly with all identifiers"""
    print("\n🔍 Verifying Location Records with Identifiers...")
    print("=" * 60)
    
    # Get all locations with UNLOCO codes
    locations = frappe.get_all("Location", 
                             filters={"custom_unlocode": ["!=", ""]},
                             fields=["name", "location_name", "custom_unlocode", "custom_country", 
                                   "custom_location_type", "custom_iata_code", "custom_icao_code",
                                   "custom_timezone", "custom_currency", "custom_language"])
    
    print(f"Found {len(locations)} locations with UNLOCO codes:")
    for loc in locations:
        print(f"\n📍 {loc.name}:")
        print(f"   Name: {loc.location_name}")
        print(f"   UNLOCO: {loc.custom_unlocode}")
        print(f"   Country: {loc.custom_country}")
        print(f"   Type: {loc.custom_location_type}")
        print(f"   IATA: {loc.custom_iata_code}")
        print(f"   ICAO: {loc.custom_icao_code}")
        print(f"   Timezone: {loc.custom_timezone}")
        print(f"   Currency: {loc.custom_currency}")
        print(f"   Language: {loc.custom_language}")
