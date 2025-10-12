"""
Bench command to populate Location records with UNLOCO codes
Usage: bench --site all execute logistics.air_freight.commands.populate_unlocode.populate_locations
"""

import frappe
from frappe import _
from typing import Dict, List, Optional

def populate_locations():
    """Populate Location records with UNLOCO data"""
    
    print("🌍 Starting UNLOCO Location Population...")
    print("=" * 50)
    
    # Sample UNLOCO data for major airports and ports
    unlocode_data = {
        "USLAX": {
            "name": "Los Angeles",
            "country": "United States",
            "country_code": "US",
            "location_type": "Airport",
            "iata_code": "LAX",
            "latitude": 33.9425,
            "longitude": -118.4081,
            "description": "Los Angeles International Airport"
        },
        "USJFK": {
            "name": "New York",
            "country": "United States", 
            "country_code": "US",
            "location_type": "Airport",
            "iata_code": "JFK",
            "latitude": 40.6413,
            "longitude": -73.7781,
            "description": "John F. Kennedy International Airport"
        },
        "USMIA": {
            "name": "Miami",
            "country": "United States",
            "country_code": "US", 
            "location_type": "Airport",
            "iata_code": "MIA",
            "latitude": 25.7959,
            "longitude": -80.2870,
            "description": "Miami International Airport"
        },
        "USORD": {
            "name": "Chicago",
            "country": "United States",
            "country_code": "US",
            "location_type": "Airport", 
            "iata_code": "ORD",
            "latitude": 41.9786,
            "longitude": -87.9048,
            "description": "Chicago O'Hare International Airport"
        },
        "USDFW": {
            "name": "Dallas",
            "country": "United States",
            "country_code": "US",
            "location_type": "Airport",
            "iata_code": "DFW", 
            "latitude": 32.8968,
            "longitude": -97.0380,
            "description": "Dallas/Fort Worth International Airport"
        },
        "USATL": {
            "name": "Atlanta",
            "country": "United States",
            "country_code": "US",
            "location_type": "Airport",
            "iata_code": "ATL",
            "latitude": 33.6407,
            "longitude": -84.4277,
            "description": "Hartsfield-Jackson Atlanta International Airport"
        },
        "USSEA": {
            "name": "Seattle",
            "country": "United States",
            "country_code": "US",
            "location_type": "Airport",
            "iata_code": "SEA",
            "latitude": 47.4502,
            "longitude": -122.3088,
            "description": "Seattle-Tacoma International Airport"
        },
        "USLGB": {
            "name": "Long Beach",
            "country": "United States",
            "country_code": "US",
            "location_type": "Port",
            "iata_code": "LGB",
            "latitude": 33.8172,
            "longitude": -118.1515,
            "description": "Port of Long Beach"
        },
        "USNYC": {
            "name": "New York",
            "country": "United States",
            "country_code": "US",
            "location_type": "Port",
            "iata_code": "NYC",
            "latitude": 40.7128,
            "longitude": -74.0060,
            "description": "Port of New York and New Jersey"
        },
        "GBLHR": {
            "name": "London",
            "country": "United Kingdom",
            "country_code": "GB",
            "location_type": "Airport",
            "iata_code": "LHR",
            "latitude": 51.4700,
            "longitude": -0.4543,
            "description": "London Heathrow Airport"
        },
        "GBLGW": {
            "name": "London",
            "country": "United Kingdom", 
            "country_code": "GB",
            "location_type": "Airport",
            "iata_code": "LGW",
            "latitude": 51.1481,
            "longitude": -0.1903,
            "description": "London Gatwick Airport"
        },
        "DEHAM": {
            "name": "Hamburg",
            "country": "Germany",
            "country_code": "DE",
            "location_type": "Port",
            "iata_code": "HAM",
            "latitude": 53.5511,
            "longitude": 9.9937,
            "description": "Port of Hamburg"
        },
        "NLRTM": {
            "name": "Rotterdam",
            "country": "Netherlands",
            "country_code": "NL",
            "location_type": "Port",
            "iata_code": "RTM",
            "latitude": 51.9244,
            "longitude": 4.4777,
            "description": "Port of Rotterdam"
        },
        "SGSIN": {
            "name": "Singapore",
            "country": "Singapore",
            "country_code": "SG",
            "location_type": "Port",
            "iata_code": "SIN",
            "latitude": 1.2966,
            "longitude": 103.7764,
            "description": "Port of Singapore"
        },
        "CNPVG": {
            "name": "Shanghai",
            "country": "China",
            "country_code": "CN",
            "location_type": "Port",
            "iata_code": "PVG",
            "latitude": 31.1434,
            "longitude": 121.8052,
            "description": "Port of Shanghai"
        },
        "JPYOK": {
            "name": "Yokohama",
            "country": "Japan",
            "country_code": "JP",
            "location_type": "Port",
            "iata_code": "YOK",
            "latitude": 35.4437,
            "longitude": 139.6380,
            "description": "Port of Yokohama"
        }
    }
    
    # Add UNLOCO fields to Location doctype if needed
    add_unlocode_fields()
    
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
    print("\n" + "=" * 50)
    print("📊 UNLOCO Location Population Summary")
    print("=" * 50)
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

def add_unlocode_fields():
    """Add UNLOCO fields to Location doctype if they don't exist"""
    try:
        # Check if custom_unlocode field exists
        meta = frappe.get_meta("Location")
        existing_fields = [field.fieldname for field in meta.fields]
        
        fields_to_add = [
            {
                "fieldname": "custom_unlocode",
                "label": "UNLOCO Code",
                "fieldtype": "Data",
                "insert_after": "location_name",
                "description": "United Nations Code for Trade and Transport Locations"
            },
            {
                "fieldname": "custom_country_code",
                "label": "Country Code",
                "fieldtype": "Data",
                "insert_after": "custom_unlocode",
                "description": "ISO 3166-1 alpha-2 country code"
            },
            {
                "fieldname": "custom_location_type",
                "label": "Location Type",
                "fieldtype": "Select",
                "options": "Airport\nPort\nRailway Station\nRoad Terminal\nOther",
                "insert_after": "custom_country_code",
                "description": "Type of transport location"
            }
        ]
        
        for field_data in fields_to_add:
            if field_data["fieldname"] not in existing_fields:
                print(f"Adding {field_data['fieldname']} field to Location doctype...")
                
                field_doc = frappe.get_doc({
                    "doctype": "Custom Field",
                    "dt": "Location",
                    **field_data
                })
                field_doc.insert(ignore_permissions=True)
                print(f"✓ Added {field_data['fieldname']} field")
            else:
                print(f"✓ {field_data['fieldname']} field already exists")
        
        frappe.db.commit()
        print("✓ Successfully added UNLOCO fields to Location doctype")
        
    except Exception as e:
        print(f"✗ Error adding UNLOCO fields: {str(e)}")
        frappe.log_error(f"UNLOCO fields addition error: {str(e)}")

def create_or_update_location(unlocode: str, location_data: Dict) -> str:
    """Create or update a Location record with UNLOCO data"""
    try:
        # Check if Location already exists
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
        
        # Update/Set location fields
        location.location_name = f"{location_data['name']} ({unlocode})"
        location.custom_unlocode = unlocode
        location.custom_country = location_data['country']
        location.custom_country_code = location_data['country_code']
        location.custom_location_type = location_data['location_type']
        location.custom_iata_code = location_data.get('iata_code', '')
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
    """Verify that Location records have been created properly"""
    print("\n🔍 Verifying Location Records...")
    print("=" * 50)
    
    # Get all locations with UNLOCO codes
    locations = frappe.get_all("Location", 
                             filters={"custom_unlocode": ["!=", ""]},
                             fields=["name", "location_name", "custom_unlocode", "custom_country", "custom_location_type"])
    
    print(f"Found {len(locations)} locations with UNLOCO codes:")
    for loc in locations:
        print(f"  - {loc.name}: {loc.location_name} ({loc.custom_unlocode}) - {loc.custom_country} - {loc.custom_location_type}")
