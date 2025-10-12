# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute():
    """Install master data for logistics app"""
    
    print("Installing logistics master data...")
    
    try:
        # Install Load Type data
        install_load_types()
        
        # Install Storage Environment data
        install_storage_environments()
        
        # Install Incoterm data
        install_incoterms()
        
        # Install Pick and Drop Mode data
        install_pick_and_drop_modes()
        
        # Install UNLOCO data
        install_unloco_data()
        
        frappe.db.commit()
        print("✅ Logistics master data installed successfully!")
        
        return {
            "success": True,
            "message": "Logistics master data installed successfully"
        }
        
    except Exception as e:
        print(f"❌ Error installing master data: {e}")
        frappe.log_error(f"Master data installation error: {str(e)}")
        return {
            "success": False,
            "message": f"Error installing master data: {str(e)}"
        }


def install_load_types():
    """Install Load Type master data"""
    print("📦 Installing Load Type data...")
    
    load_types = [
        {
            "load_type_name": "FCL",
            "description": "Full Container Load",
            "sea": 1,
            "air": 0,
            "transport": 0
        },
        {
            "load_type_name": "LCL",
            "description": "Less than Container Load",
            "sea": 1,
            "air": 0,
            "transport": 0
        },
        {
            "load_type_name": "BULK",
            "description": "Bulk Cargo",
            "sea": 1,
            "air": 0,
            "transport": 1
        },
        {
            "load_type_name": "AIR",
            "description": "Air Cargo",
            "sea": 0,
            "air": 1,
            "transport": 0
        },
        {
            "load_type_name": "ROAD",
            "description": "Road Transport",
            "sea": 0,
            "air": 0,
            "transport": 1
        },
        {
            "load_type_name": "RAIL",
            "description": "Rail Transport",
            "sea": 0,
            "air": 0,
            "transport": 1
        },
        {
            "load_type_name": "MULTI",
            "description": "Multimodal Transport",
            "sea": 1,
            "air": 1,
            "transport": 1
        }
    ]
    
    created_count = 0
    for load_type_data in load_types:
        try:
            if not frappe.db.exists("Load Type", load_type_data["load_type_name"]):
                doc = frappe.new_doc("Load Type")
                doc.update(load_type_data)
                doc.insert()
                created_count += 1
                print(f"  ✅ Created Load Type: {load_type_data['load_type_name']}")
            else:
                print(f"  ✓ Load Type already exists: {load_type_data['load_type_name']}")
        except Exception as e:
            print(f"  ❌ Error creating Load Type {load_type_data['load_type_name']}: {e}")
    
    print(f"📦 Load Types: {created_count} created")


def install_storage_environments():
    """Install Storage Environment master data"""
    print("🏭 Installing Storage Environment data...")
    
    environments = [
        {
            "code": "DRY",
            "description": "Dry Storage",
            "purpose": "General purpose dry storage for non-perishable goods"
        },
        {
            "code": "COLD",
            "description": "Cold Storage",
            "purpose": "Temperature controlled storage for perishable goods"
        },
        {
            "code": "FROZEN",
            "description": "Frozen Storage",
            "purpose": "Freezer storage for frozen goods"
        },
        {
            "code": "HAZMAT",
            "description": "Hazardous Materials Storage",
            "purpose": "Specialized storage for dangerous goods"
        },
        {
            "code": "BONDED",
            "description": "Bonded Storage",
            "purpose": "Customs bonded warehouse storage"
        },
        {
            "code": "OPEN",
            "description": "Open Storage",
            "purpose": "Outdoor storage for weather-resistant goods"
        },
        {
            "code": "SECURE",
            "description": "Secure Storage",
            "purpose": "High-security storage for valuable goods"
        }
    ]
    
    created_count = 0
    for env_data in environments:
        try:
            if not frappe.db.exists("Storage Environment", env_data["code"]):
                doc = frappe.new_doc("Storage Environment")
                doc.update(env_data)
                doc.insert()
                created_count += 1
                print(f"  ✅ Created Storage Environment: {env_data['code']}")
            else:
                print(f"  ✓ Storage Environment already exists: {env_data['code']}")
        except Exception as e:
            print(f"  ❌ Error creating Storage Environment {env_data['code']}: {e}")
    
    print(f"🏭 Storage Environments: {created_count} created")


def install_incoterms():
    """Install Incoterm master data"""
    print("📋 Installing Incoterm data...")
    
    incoterms = [
        {
            "code": "EXW",
            "title": "Ex Works",
            "description": "The seller makes the goods available at their premises. The buyer is responsible for all costs and risks from that point."
        },
        {
            "code": "FCA",
            "title": "Free Carrier",
            "description": "The seller delivers the goods to the carrier or another person nominated by the buyer at the seller's premises or another named place."
        },
        {
            "code": "FAS",
            "title": "Free Alongside Ship",
            "description": "The seller delivers when the goods are placed alongside the vessel at the named port of shipment."
        },
        {
            "code": "FOB",
            "title": "Free On Board",
            "description": "The seller delivers when the goods pass the ship's rail at the named port of shipment."
        },
        {
            "code": "CFR",
            "title": "Cost and Freight",
            "description": "The seller delivers when the goods pass the ship's rail in the port of shipment and pays the costs and freight necessary to bring the goods to the port of destination."
        },
        {
            "code": "CIF",
            "title": "Cost, Insurance and Freight",
            "description": "The seller delivers when the goods pass the ship's rail in the port of shipment and pays the costs and freight and insurance necessary to bring the goods to the port of destination."
        },
        {
            "code": "CPT",
            "title": "Carriage Paid To",
            "description": "The seller delivers the goods to the carrier or another person nominated by the seller and pays the freight for the carriage of the goods to the named destination."
        },
        {
            "code": "CIP",
            "title": "Carriage and Insurance Paid To",
            "description": "The seller delivers the goods to the carrier or another person nominated by the seller and pays the freight and insurance for the carriage of the goods to the named destination."
        },
        {
            "code": "DAP",
            "title": "Delivered At Place",
            "description": "The seller delivers when the goods are placed at the disposal of the buyer on the arriving means of transport ready for unloading at the named place of destination."
        },
        {
            "code": "DPU",
            "title": "Delivered at Place Unloaded",
            "description": "The seller delivers when the goods are placed at the disposal of the buyer on the arriving means of transport ready for unloading at the named place of destination, and the seller has unloaded the goods."
        },
        {
            "code": "DDP",
            "title": "Delivered Duty Paid",
            "description": "The seller delivers when the goods are placed at the disposal of the buyer, cleared for import on the arriving means of transport ready for unloading at the named place of destination."
        }
    ]
    
    created_count = 0
    for incoterm_data in incoterms:
        try:
            if not frappe.db.exists("Incoterm", incoterm_data["code"]):
                doc = frappe.new_doc("Incoterm")
                doc.update(incoterm_data)
                doc.insert()
                created_count += 1
                print(f"  ✅ Created Incoterm: {incoterm_data['code']}")
            else:
                print(f"  ✓ Incoterm already exists: {incoterm_data['code']}")
        except Exception as e:
            print(f"  ❌ Error creating Incoterm {incoterm_data['code']}: {e}")
    
    print(f"📋 Incoterms: {created_count} created")


def install_pick_and_drop_modes():
    """Install Pick and Drop Mode master data"""
    print("🚚 Installing Pick and Drop Mode data...")
    
    modes = [
        {
            "code": "PICKUP",
            "description": "Pickup Only",
            "usage": "Customer pickup at origin location",
            "allow_in_pick": 1,
            "allow_in_drop": 0
        },
        {
            "code": "DELIVERY",
            "description": "Delivery Only",
            "usage": "Delivery to destination location",
            "allow_in_pick": 0,
            "allow_in_drop": 1
        },
        {
            "code": "DOOR_TO_DOOR",
            "description": "Door to Door",
            "usage": "Complete pickup and delivery service",
            "allow_in_pick": 1,
            "allow_in_drop": 1
        },
        {
            "code": "TERMINAL_TO_TERMINAL",
            "description": "Terminal to Terminal",
            "usage": "Transport between terminals only",
            "allow_in_pick": 1,
            "allow_in_drop": 1
        },
        {
            "code": "DOOR_TO_TERMINAL",
            "description": "Door to Terminal",
            "usage": "Pickup at origin, delivery to terminal",
            "allow_in_pick": 1,
            "allow_in_drop": 1
        },
        {
            "code": "TERMINAL_TO_DOOR",
            "description": "Terminal to Door",
            "usage": "Pickup at terminal, delivery to destination",
            "allow_in_pick": 1,
            "allow_in_drop": 1
        }
    ]
    
    created_count = 0
    for mode_data in modes:
        try:
            if not frappe.db.exists("Pick and Drop Mode", mode_data["code"]):
                doc = frappe.new_doc("Pick and Drop Mode")
                doc.update(mode_data)
                doc.insert()
                created_count += 1
                print(f"  ✅ Created Pick and Drop Mode: {mode_data['code']}")
            else:
                print(f"  ✓ Pick and Drop Mode already exists: {mode_data['code']}")
        except Exception as e:
            print(f"  ❌ Error creating Pick and Drop Mode {mode_data['code']}: {e}")
    
    print(f"🚚 Pick and Drop Modes: {created_count} created")


def install_unloco_data():
    """Install UNLOCO master data"""
    print("🌍 Installing UNLOCO data...")
    
    # Sample UNLOCO data for major global locations
    unloco_data = [
        {
            "unlocode": "USLAX",
            "location_name": "Los Angeles",
            "country": "United States",
            "country_code": "US",
            "subdivision": "California",
            "city": "Los Angeles",
            "function": "4 - Airport",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "LAX",
            "icao_code": "KLAX",
            "timezone": "America/Los_Angeles",
            "currency": "USD",
            "language": "en",
            "latitude": 33.9425,
            "longitude": -118.4081,
            "is_airport": 1,
            "is_port": 0,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "USNYC",
            "location_name": "New York",
            "country": "United States",
            "country_code": "US",
            "subdivision": "New York",
            "city": "New York",
            "function": "4 - Airport",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "JFK",
            "icao_code": "KJFK",
            "timezone": "America/New_York",
            "currency": "USD",
            "language": "en",
            "latitude": 40.6413,
            "longitude": -73.7781,
            "is_airport": 1,
            "is_port": 0,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "USMIA",
            "location_name": "Miami",
            "country": "United States",
            "country_code": "US",
            "subdivision": "Florida",
            "city": "Miami",
            "function": "4 - Airport",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "MIA",
            "icao_code": "KMIA",
            "timezone": "America/New_York",
            "currency": "USD",
            "language": "en",
            "latitude": 25.7959,
            "longitude": -80.2870,
            "is_airport": 1,
            "is_port": 0,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "GBLHR",
            "location_name": "London Heathrow",
            "country": "United Kingdom",
            "country_code": "GB",
            "subdivision": "England",
            "city": "London",
            "function": "4 - Airport",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "LHR",
            "icao_code": "EGLL",
            "timezone": "Europe/London",
            "currency": "GBP",
            "language": "en",
            "latitude": 51.4700,
            "longitude": -0.4543,
            "is_airport": 1,
            "is_port": 0,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "DEHAM",
            "location_name": "Hamburg",
            "country": "Germany",
            "country_code": "DE",
            "subdivision": "Hamburg",
            "city": "Hamburg",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "HAM",
            "icao_code": "EDDH",
            "timezone": "Europe/Berlin",
            "currency": "EUR",
            "language": "de",
            "latitude": 53.5511,
            "longitude": 9.9937,
            "is_airport": 0,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "NLRTM",
            "location_name": "Rotterdam",
            "country": "Netherlands",
            "country_code": "NL",
            "subdivision": "South Holland",
            "city": "Rotterdam",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "RTM",
            "icao_code": "EHRD",
            "timezone": "Europe/Amsterdam",
            "currency": "EUR",
            "language": "nl",
            "latitude": 51.9244,
            "longitude": 4.4777,
            "is_airport": 0,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "SGSIN",
            "location_name": "Singapore",
            "country": "Singapore",
            "country_code": "SG",
            "subdivision": "Singapore",
            "city": "Singapore",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "SIN",
            "icao_code": "WSSS",
            "timezone": "Asia/Singapore",
            "currency": "SGD",
            "language": "en",
            "latitude": 1.2966,
            "longitude": 103.7764,
            "is_airport": 0,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "CNSHA",
            "location_name": "Shanghai",
            "country": "China",
            "country_code": "CN",
            "subdivision": "Shanghai",
            "city": "Shanghai",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "PVG",
            "icao_code": "ZSPD",
            "timezone": "Asia/Shanghai",
            "currency": "CNY",
            "language": "zh",
            "latitude": 31.1433,
            "longitude": 121.8052,
            "is_airport": 0,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        }
    ]
    
    created_count = 0
    for unloco in unloco_data:
        try:
            if not frappe.db.exists("UNLOCO", unloco["unlocode"]):
                doc = frappe.new_doc("UNLOCO")
                doc.update(unloco)
                doc.insert()
                created_count += 1
                print(f"  ✅ Created UNLOCO: {unloco['unlocode']} - {unloco['location_name']}")
            else:
                print(f"  ✓ UNLOCO already exists: {unloco['unlocode']}")
        except Exception as e:
            print(f"  ❌ Error creating UNLOCO {unloco['unlocode']}: {e}")
    
    print(f"🌍 UNLOCO locations: {created_count} created")


if __name__ == "__main__":
    execute()
