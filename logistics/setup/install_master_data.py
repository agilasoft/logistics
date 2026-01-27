# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute():
    """Install master data for logistics app"""
    
    print("Installing logistics master data...")
    
    try:
        # Install UOM records first (required for Transport Capacity Settings)
        install_required_uoms()
        
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
        
        # Install Logistics Milestones
        install_logistics_milestones()
        
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


def install_required_uoms():
    """Install required UOM records for Transport Capacity Settings
    
    Reads default UOM values from Transport Capacity Settings doctype definition
    and creates those UOM records if they don't exist.
    """
    print("📏 Installing required UOM records...")
    
    try:
        # Read the Transport Capacity Settings doctype to get default UOM values
        doctype_path = frappe.get_app_path("logistics", "transport", "doctype", 
                                          "transport_capacity_settings", "transport_capacity_settings.json")
        
        import json
        with open(doctype_path, 'r') as f:
            doctype_def = json.load(f)
        
        # Extract default UOM values from field definitions
        uom_names = set()
        for field in doctype_def.get("fields", []):
            if field.get("fieldname") in ["default_dimension_uom", "default_volume_uom", "default_weight_uom"]:
                default_value = field.get("default")
                if default_value:
                    uom_names.add(default_value)
        
        created_count = 0
        for uom_name in uom_names:
            try:
                # Check if UOM already exists
                if frappe.db.exists("UOM", uom_name):
                    print(f"  ✓ UOM {uom_name} already exists")
                    continue
                
                # Create UOM record
                uom_doc = frappe.new_doc("UOM")
                uom_doc.uom_name = uom_name
                uom_doc.must_be_whole_number = 0
                uom_doc.insert(ignore_permissions=True)
                created_count += 1
                print(f"  ✅ Created UOM: {uom_name}")
                
            except Exception as e:
                print(f"  ❌ Error creating UOM {uom_name}: {e}")
                frappe.log_error(f"Error creating UOM {uom_name}: {str(e)}")
        
        print(f"📏 UOM records: {created_count} created")
        
    except Exception as e:
        print(f"  ⚠️  Error reading Transport Capacity Settings defaults: {e}")
        frappe.log_error(f"Error reading Transport Capacity Settings defaults: {str(e)}")


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
        },
        # Philippine Ports and Airports
        {
            "unlocode": "PHMNL",
            "location_name": "Manila",
            "country": "Philippines",
            "country_code": "PH",
            "subdivision": "Metro Manila",
            "city": "Manila",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "MNL",
            "icao_code": "RPLL",
            "timezone": "Asia/Manila",
            "currency": "PHP",
            "language": "en",
            "latitude": 14.5995,
            "longitude": 120.9842,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "PHCEB",
            "location_name": "Cebu",
            "country": "Philippines",
            "country_code": "PH",
            "subdivision": "Cebu",
            "city": "Cebu",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "CEB",
            "icao_code": "RPVM",
            "timezone": "Asia/Manila",
            "currency": "PHP",
            "language": "en",
            "latitude": 10.3157,
            "longitude": 123.8854,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "PHDVO",
            "location_name": "Davao",
            "country": "Philippines",
            "country_code": "PH",
            "subdivision": "Davao del Sur",
            "city": "Davao",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "DVO",
            "icao_code": "RPMD",
            "timezone": "Asia/Manila",
            "currency": "PHP",
            "language": "en",
            "latitude": 7.1256,
            "longitude": 125.6560,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "PHILO",
            "location_name": "Iloilo",
            "country": "Philippines",
            "country_code": "PH",
            "subdivision": "Iloilo",
            "city": "Iloilo",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "ILO",
            "icao_code": "RPVI",
            "timezone": "Asia/Manila",
            "currency": "PHP",
            "language": "en",
            "latitude": 10.7202,
            "longitude": 122.5621,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "PHZAM",
            "location_name": "Zamboanga",
            "country": "Philippines",
            "country_code": "PH",
            "subdivision": "Zamboanga del Sur",
            "city": "Zamboanga",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "ZAM",
            "icao_code": "RPMZ",
            "timezone": "Asia/Manila",
            "currency": "PHP",
            "language": "en",
            "latitude": 6.9214,
            "longitude": 122.0590,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "PHBAG",
            "location_name": "Baguio",
            "country": "Philippines",
            "country_code": "PH",
            "subdivision": "Benguet",
            "city": "Baguio",
            "function": "4 - Airport",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "BAG",
            "icao_code": "RPUB",
            "timezone": "Asia/Manila",
            "currency": "PHP",
            "language": "en",
            "latitude": 16.3751,
            "longitude": 120.6196,
            "is_airport": 1,
            "is_port": 0,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "PHBOH",
            "location_name": "Bohol",
            "country": "Philippines",
            "country_code": "PH",
            "subdivision": "Bohol",
            "city": "Tagbilaran",
            "function": "4 - Airport",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "TAG",
            "icao_code": "RPVT",
            "timezone": "Asia/Manila",
            "currency": "PHP",
            "language": "en",
            "latitude": 9.6641,
            "longitude": 123.8532,
            "is_airport": 1,
            "is_port": 0,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "PHBAT",
            "location_name": "Batangas",
            "country": "Philippines",
            "country_code": "PH",
            "subdivision": "Batangas",
            "city": "Batangas",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "",
            "icao_code": "",
            "timezone": "Asia/Manila",
            "currency": "PHP",
            "language": "en",
            "latitude": 13.7563,
            "longitude": 121.0583,
            "is_airport": 0,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "PHSUB",
            "location_name": "Subic",
            "country": "Philippines",
            "country_code": "PH",
            "subdivision": "Zambales",
            "city": "Subic",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "",
            "icao_code": "",
            "timezone": "Asia/Manila",
            "currency": "PHP",
            "language": "en",
            "latitude": 14.7944,
            "longitude": 120.2794,
            "is_airport": 0,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        # Major Global Ports with PH Connections
        {
            "unlocode": "HKHKG",
            "location_name": "Hong Kong",
            "country": "Hong Kong",
            "country_code": "HK",
            "subdivision": "Hong Kong",
            "city": "Hong Kong",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "HKG",
            "icao_code": "VHHH",
            "timezone": "Asia/Hong_Kong",
            "currency": "HKD",
            "language": "en",
            "latitude": 22.3080,
            "longitude": 113.9185,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "TWKHH",
            "location_name": "Kaohsiung",
            "country": "Taiwan",
            "country_code": "TW",
            "subdivision": "Kaohsiung",
            "city": "Kaohsiung",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "KHH",
            "icao_code": "RCKH",
            "timezone": "Asia/Taipei",
            "currency": "TWD",
            "language": "zh",
            "latitude": 22.5771,
            "longitude": 120.3508,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "JPYOK",
            "location_name": "Yokohama",
            "country": "Japan",
            "country_code": "JP",
            "subdivision": "Kanagawa",
            "city": "Yokohama",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "YOK",
            "icao_code": "RJTY",
            "timezone": "Asia/Tokyo",
            "currency": "JPY",
            "language": "ja",
            "latitude": 35.4437,
            "longitude": 139.6380,
            "is_airport": 0,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "JPOSA",
            "location_name": "Osaka",
            "country": "Japan",
            "country_code": "JP",
            "subdivision": "Osaka",
            "city": "Osaka",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "KIX",
            "icao_code": "RJBB",
            "timezone": "Asia/Tokyo",
            "currency": "JPY",
            "language": "ja",
            "latitude": 34.6937,
            "longitude": 135.5023,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "KRINC",
            "location_name": "Incheon",
            "country": "South Korea",
            "country_code": "KR",
            "subdivision": "Incheon",
            "city": "Incheon",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "ICN",
            "icao_code": "RKSI",
            "timezone": "Asia/Seoul",
            "currency": "KRW",
            "language": "ko",
            "latitude": 37.4563,
            "longitude": 126.7052,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "THLCH",
            "location_name": "Laem Chabang",
            "country": "Thailand",
            "country_code": "TH",
            "subdivision": "Chonburi",
            "city": "Laem Chabang",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "UTP",
            "icao_code": "VTBU",
            "timezone": "Asia/Bangkok",
            "currency": "THB",
            "language": "th",
            "latitude": 13.0642,
            "longitude": 100.8831,
            "is_airport": 0,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "MYLGK",
            "location_name": "Langkawi",
            "country": "Malaysia",
            "country_code": "MY",
            "subdivision": "Kedah",
            "city": "Langkawi",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "LGK",
            "icao_code": "WMKL",
            "timezone": "Asia/Kuala_Lumpur",
            "currency": "MYR",
            "language": "ms",
            "latitude": 6.3297,
            "longitude": 99.7289,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "IDJKT",
            "location_name": "Jakarta",
            "country": "Indonesia",
            "country_code": "ID",
            "subdivision": "Jakarta",
            "city": "Jakarta",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "CGK",
            "icao_code": "WIII",
            "timezone": "Asia/Jakarta",
            "currency": "IDR",
            "language": "id",
            "latitude": -6.1751,
            "longitude": 106.8650,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "VNSGN",
            "location_name": "Ho Chi Minh City",
            "country": "Vietnam",
            "country_code": "VN",
            "subdivision": "Ho Chi Minh City",
            "city": "Ho Chi Minh City",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "SGN",
            "icao_code": "VVTS",
            "timezone": "Asia/Ho_Chi_Minh",
            "currency": "VND",
            "language": "vi",
            "latitude": 10.8231,
            "longitude": 106.6297,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "AUMLB",
            "location_name": "Melbourne",
            "country": "Australia",
            "country_code": "AU",
            "subdivision": "Victoria",
            "city": "Melbourne",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "MEL",
            "icao_code": "YMML",
            "timezone": "Australia/Melbourne",
            "currency": "AUD",
            "language": "en",
            "latitude": -37.6736,
            "longitude": 144.8433,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "AUSYD",
            "location_name": "Sydney",
            "country": "Australia",
            "country_code": "AU",
            "subdivision": "New South Wales",
            "city": "Sydney",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "SYD",
            "icao_code": "YSSY",
            "timezone": "Australia/Sydney",
            "currency": "AUD",
            "language": "en",
            "latitude": -33.9399,
            "longitude": 151.1753,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "NZAKL",
            "location_name": "Auckland",
            "country": "New Zealand",
            "country_code": "NZ",
            "subdivision": "Auckland",
            "city": "Auckland",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "AKL",
            "icao_code": "NZAA",
            "timezone": "Pacific/Auckland",
            "currency": "NZD",
            "language": "en",
            "latitude": -36.8485,
            "longitude": 174.7633,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "CAYVR",
            "location_name": "Vancouver",
            "country": "Canada",
            "country_code": "CA",
            "subdivision": "British Columbia",
            "city": "Vancouver",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "YVR",
            "icao_code": "CYVR",
            "timezone": "America/Vancouver",
            "currency": "CAD",
            "language": "en",
            "latitude": 49.1967,
            "longitude": -123.1815,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "USSEA",
            "location_name": "Seattle",
            "country": "United States",
            "country_code": "US",
            "subdivision": "Washington",
            "city": "Seattle",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "SEA",
            "icao_code": "KSEA",
            "timezone": "America/Los_Angeles",
            "currency": "USD",
            "language": "en",
            "latitude": 47.4502,
            "longitude": -122.3088,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "USOAK",
            "location_name": "Oakland",
            "country": "United States",
            "country_code": "US",
            "subdivision": "California",
            "city": "Oakland",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "OAK",
            "icao_code": "KOAK",
            "timezone": "America/Los_Angeles",
            "currency": "USD",
            "language": "en",
            "latitude": 37.8044,
            "longitude": -122.2712,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "USLGB",
            "location_name": "Long Beach",
            "country": "United States",
            "country_code": "US",
            "subdivision": "California",
            "city": "Long Beach",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "LGB",
            "icao_code": "KLGB",
            "timezone": "America/Los_Angeles",
            "currency": "USD",
            "language": "en",
            "latitude": 33.8177,
            "longitude": -118.1516,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        # Additional Major Global Ports with PH Connections
        # Europe
        {
            "unlocode": "GBFXT",
            "location_name": "Felixstowe",
            "country": "United Kingdom",
            "country_code": "GB",
            "subdivision": "Suffolk",
            "city": "Felixstowe",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "",
            "icao_code": "",
            "timezone": "Europe/London",
            "currency": "GBP",
            "language": "en",
            "latitude": 51.9500,
            "longitude": 1.3500,
            "is_airport": 0,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "GBSOU",
            "location_name": "Southampton",
            "country": "United Kingdom",
            "country_code": "GB",
            "subdivision": "Hampshire",
            "city": "Southampton",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "SOU",
            "icao_code": "EGHI",
            "timezone": "Europe/London",
            "currency": "GBP",
            "language": "en",
            "latitude": 50.9000,
            "longitude": -1.4000,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "DEBRE",
            "location_name": "Bremerhaven",
            "country": "Germany",
            "country_code": "DE",
            "subdivision": "Bremen",
            "city": "Bremerhaven",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "BRE",
            "icao_code": "EDDW",
            "timezone": "Europe/Berlin",
            "currency": "EUR",
            "language": "de",
            "latitude": 53.5500,
            "longitude": 8.5833,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "BEANR",
            "location_name": "Antwerp",
            "country": "Belgium",
            "country_code": "BE",
            "subdivision": "Antwerp",
            "city": "Antwerp",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "ANR",
            "icao_code": "EBAW",
            "timezone": "Europe/Brussels",
            "currency": "EUR",
            "language": "nl",
            "latitude": 51.2194,
            "longitude": 4.4025,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "FRLEH",
            "location_name": "Le Havre",
            "country": "France",
            "country_code": "FR",
            "subdivision": "Normandy",
            "city": "Le Havre",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "LEH",
            "icao_code": "LFOH",
            "timezone": "Europe/Paris",
            "currency": "EUR",
            "language": "fr",
            "latitude": 49.4944,
            "longitude": 0.1075,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "ITGOA",
            "location_name": "Genoa",
            "country": "Italy",
            "country_code": "IT",
            "subdivision": "Liguria",
            "city": "Genoa",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "GOA",
            "icao_code": "LIMJ",
            "timezone": "Europe/Rome",
            "currency": "EUR",
            "language": "it",
            "latitude": 44.4056,
            "longitude": 8.9464,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "ESALG",
            "location_name": "Algeciras",
            "country": "Spain",
            "country_code": "ES",
            "subdivision": "Andalusia",
            "city": "Algeciras",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "AEI",
            "icao_code": "LEAG",
            "timezone": "Europe/Madrid",
            "currency": "EUR",
            "language": "es",
            "latitude": 36.1408,
            "longitude": -5.4561,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        # Middle East
        {
            "unlocode": "AEJEA",
            "location_name": "Jebel Ali",
            "country": "United Arab Emirates",
            "country_code": "AE",
            "subdivision": "Dubai",
            "city": "Dubai",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "DXB",
            "icao_code": "OMDB",
            "timezone": "Asia/Dubai",
            "currency": "AED",
            "language": "ar",
            "latitude": 25.0657,
            "longitude": 55.1713,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "SADAM",
            "location_name": "Dammam",
            "country": "Saudi Arabia",
            "country_code": "SA",
            "subdivision": "Eastern Province",
            "city": "Dammam",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "DMM",
            "icao_code": "OEDF",
            "timezone": "Asia/Riyadh",
            "currency": "SAR",
            "language": "ar",
            "latitude": 26.4207,
            "longitude": 50.0888,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        # Africa
        {
            "unlocode": "ZADUR",
            "location_name": "Durban",
            "country": "South Africa",
            "country_code": "ZA",
            "subdivision": "KwaZulu-Natal",
            "city": "Durban",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "DUR",
            "icao_code": "FADN",
            "timezone": "Africa/Johannesburg",
            "currency": "ZAR",
            "language": "en",
            "latitude": -29.8587,
            "longitude": 31.0218,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "ZACPT",
            "location_name": "Cape Town",
            "country": "South Africa",
            "country_code": "ZA",
            "subdivision": "Western Cape",
            "city": "Cape Town",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "CPT",
            "icao_code": "FACT",
            "timezone": "Africa/Johannesburg",
            "currency": "ZAR",
            "language": "en",
            "latitude": -33.9249,
            "longitude": 18.4241,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        # South America
        {
            "unlocode": "BRSSZ",
            "location_name": "Santos",
            "country": "Brazil",
            "country_code": "BR",
            "subdivision": "São Paulo",
            "city": "Santos",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "SSZ",
            "icao_code": "SBST",
            "timezone": "America/Sao_Paulo",
            "currency": "BRL",
            "language": "pt",
            "latitude": -23.9608,
            "longitude": -46.3331,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "CLVAP",
            "location_name": "Valparaiso",
            "country": "Chile",
            "country_code": "CL",
            "subdivision": "Valparaíso",
            "city": "Valparaíso",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "VAP",
            "icao_code": "SCVA",
            "timezone": "America/Santiago",
            "currency": "CLP",
            "language": "es",
            "latitude": -33.0458,
            "longitude": -71.6197,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "ARBUE",
            "location_name": "Buenos Aires",
            "country": "Argentina",
            "country_code": "AR",
            "subdivision": "Buenos Aires",
            "city": "Buenos Aires",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "BUE",
            "icao_code": "SABE",
            "timezone": "America/Argentina/Buenos_Aires",
            "currency": "ARS",
            "language": "es",
            "latitude": -34.6037,
            "longitude": -58.3816,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        # Additional US Ports
        {
            "unlocode": "USNYC",
            "location_name": "New York",
            "country": "United States",
            "country_code": "US",
            "subdivision": "New York",
            "city": "New York",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "JFK",
            "icao_code": "KJFK",
            "timezone": "America/New_York",
            "currency": "USD",
            "language": "en",
            "latitude": 40.6413,
            "longitude": -73.7781,
            "is_airport": 1,
            "is_port": 1,
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
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "MIA",
            "icao_code": "KMIA",
            "timezone": "America/New_York",
            "currency": "USD",
            "language": "en",
            "latitude": 25.7959,
            "longitude": -80.2870,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "USCHI",
            "location_name": "Chicago",
            "country": "United States",
            "country_code": "US",
            "subdivision": "Illinois",
            "city": "Chicago",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "CHI",
            "icao_code": "KORD",
            "timezone": "America/Chicago",
            "currency": "USD",
            "language": "en",
            "latitude": 41.8781,
            "longitude": -87.6298,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "USATL",
            "location_name": "Atlanta",
            "country": "United States",
            "country_code": "US",
            "subdivision": "Georgia",
            "city": "Atlanta",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "ATL",
            "icao_code": "KATL",
            "timezone": "America/New_York",
            "currency": "USD",
            "language": "en",
            "latitude": 33.7490,
            "longitude": -84.3880,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        # Additional Asian Ports
        {
            "unlocode": "CNQIN",
            "location_name": "Qingdao",
            "country": "China",
            "country_code": "CN",
            "subdivision": "Shandong",
            "city": "Qingdao",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "TAO",
            "icao_code": "ZSQD",
            "timezone": "Asia/Shanghai",
            "currency": "CNY",
            "language": "zh",
            "latitude": 36.0986,
            "longitude": 120.3719,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "CNTSN",
            "location_name": "Tianjin",
            "country": "China",
            "country_code": "CN",
            "subdivision": "Tianjin",
            "city": "Tianjin",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "TSN",
            "icao_code": "ZBTJ",
            "timezone": "Asia/Shanghai",
            "currency": "CNY",
            "language": "zh",
            "latitude": 39.3434,
            "longitude": 117.3616,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "CNGUA",
            "location_name": "Guangzhou",
            "country": "China",
            "country_code": "CN",
            "subdivision": "Guangdong",
            "city": "Guangzhou",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "CAN",
            "icao_code": "ZGGG",
            "timezone": "Asia/Shanghai",
            "currency": "CNY",
            "language": "zh",
            "latitude": 23.1291,
            "longitude": 113.2644,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "CNXIA",
            "location_name": "Xiamen",
            "country": "China",
            "country_code": "CN",
            "subdivision": "Fujian",
            "city": "Xiamen",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "XMN",
            "icao_code": "ZSAM",
            "timezone": "Asia/Shanghai",
            "currency": "CNY",
            "language": "zh",
            "latitude": 24.4798,
            "longitude": 118.0819,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "CNNIN",
            "location_name": "Ningbo",
            "country": "China",
            "country_code": "CN",
            "subdivision": "Zhejiang",
            "city": "Ningbo",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "NGB",
            "icao_code": "ZSNB",
            "timezone": "Asia/Shanghai",
            "currency": "CNY",
            "language": "zh",
            "latitude": 29.8683,
            "longitude": 121.5440,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "JPYOK",
            "location_name": "Yokohama",
            "country": "Japan",
            "country_code": "JP",
            "subdivision": "Kanagawa",
            "city": "Yokohama",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "YOK",
            "icao_code": "RJTY",
            "timezone": "Asia/Tokyo",
            "currency": "JPY",
            "language": "ja",
            "latitude": 35.4437,
            "longitude": 139.6380,
            "is_airport": 0,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "JPKOB",
            "location_name": "Kobe",
            "country": "Japan",
            "country_code": "JP",
            "subdivision": "Hyogo",
            "city": "Kobe",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "UKB",
            "icao_code": "RJBE",
            "timezone": "Asia/Tokyo",
            "currency": "JPY",
            "language": "ja",
            "latitude": 34.6901,
            "longitude": 135.1956,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "JPNAG",
            "location_name": "Nagoya",
            "country": "Japan",
            "country_code": "JP",
            "subdivision": "Aichi",
            "city": "Nagoya",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "NGO",
            "icao_code": "RJGG",
            "timezone": "Asia/Tokyo",
            "currency": "JPY",
            "language": "ja",
            "latitude": 35.1815,
            "longitude": 136.9066,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "KRBUS",
            "location_name": "Busan",
            "country": "South Korea",
            "country_code": "KR",
            "subdivision": "Busan",
            "city": "Busan",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "PUS",
            "icao_code": "RKPK",
            "timezone": "Asia/Seoul",
            "currency": "KRW",
            "language": "ko",
            "latitude": 35.1796,
            "longitude": 129.0756,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "THBKK",
            "location_name": "Bangkok",
            "country": "Thailand",
            "country_code": "TH",
            "subdivision": "Bangkok",
            "city": "Bangkok",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "BKK",
            "icao_code": "VTBS",
            "timezone": "Asia/Bangkok",
            "currency": "THB",
            "language": "th",
            "latitude": 13.7563,
            "longitude": 100.5018,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "MYKUL",
            "location_name": "Kuala Lumpur",
            "country": "Malaysia",
            "country_code": "MY",
            "subdivision": "Selangor",
            "city": "Kuala Lumpur",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "KUL",
            "icao_code": "WMKK",
            "timezone": "Asia/Kuala_Lumpur",
            "currency": "MYR",
            "language": "ms",
            "latitude": 3.1390,
            "longitude": 101.6869,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "MYPEN",
            "location_name": "Penang",
            "country": "Malaysia",
            "country_code": "MY",
            "subdivision": "Penang",
            "city": "Penang",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "PEN",
            "icao_code": "WMKP",
            "timezone": "Asia/Kuala_Lumpur",
            "currency": "MYR",
            "language": "ms",
            "latitude": 5.4164,
            "longitude": 100.3327,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "IDSUR",
            "location_name": "Surabaya",
            "country": "Indonesia",
            "country_code": "ID",
            "subdivision": "East Java",
            "city": "Surabaya",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "SUB",
            "icao_code": "WARR",
            "timezone": "Asia/Jakarta",
            "currency": "IDR",
            "language": "id",
            "latitude": -7.2575,
            "longitude": 112.7521,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "IDMDN",
            "location_name": "Medan",
            "country": "Indonesia",
            "country_code": "ID",
            "subdivision": "North Sumatra",
            "city": "Medan",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "MES",
            "icao_code": "WIMM",
            "timezone": "Asia/Jakarta",
            "currency": "IDR",
            "language": "id",
            "latitude": 3.5852,
            "longitude": 98.6756,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "VNHAN",
            "location_name": "Hanoi",
            "country": "Vietnam",
            "country_code": "VN",
            "subdivision": "Hanoi",
            "city": "Hanoi",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "HAN",
            "icao_code": "VVNB",
            "timezone": "Asia/Ho_Chi_Minh",
            "currency": "VND",
            "language": "vi",
            "latitude": 21.0285,
            "longitude": 105.8542,
            "is_airport": 1,
            "is_port": 1,
            "is_railway": 0,
            "is_road": 0
        },
        {
            "unlocode": "VNDAD",
            "location_name": "Da Nang",
            "country": "Vietnam",
            "country_code": "VN",
            "subdivision": "Da Nang",
            "city": "Da Nang",
            "function": "1 - Port",
            "status": "AA - Approved by competent national government agency",
            "iata_code": "DAD",
            "icao_code": "VVDN",
            "timezone": "Asia/Ho_Chi_Minh",
            "currency": "VND",
            "language": "vi",
            "latitude": 16.0544,
            "longitude": 108.2022,
            "is_airport": 1,
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


def install_logistics_milestones():
    """Install Logistics Milestone master data for Sea Freight"""
    print("📊 Installing Logistics Milestone data...")
    
    # Sea Freight milestones based on shipping_status options
    sea_freight_milestones = [
        {"code": "SF-BOOK-REC", "description": "Booking Received", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-BOOK-CONF", "description": "Booking Confirmed", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-CARGO-NR", "description": "Cargo Not Ready", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-PICKUP-SCH", "description": "Pick-Up Scheduled", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-GATE-IN", "description": "Gate-In at Port / CY", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-CUST-EXP", "description": "Customs Clearance (Export)", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-LOADED", "description": "Loaded on Vessel", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-DEPARTED", "description": "Departed", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-IN-TRANSIT", "description": "In-Transit", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-ARRIVED", "description": "Arrived", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-DISCHARGED", "description": "Discharged from Vessel", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-CUST-IMP", "description": "Customs Clearance (Import)", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-AVAILABLE", "description": "Available for Pick-Up", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-OUT-DELIV", "description": "Out for Delivery", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-DELIVERED", "description": "Delivered", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-EMPTY-RET", "description": "Empty Container Returned", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-DELAYED", "description": "Delayed", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-CUST-HOLD", "description": "Customs Hold", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-DOC-ISSUE", "description": "Document Issue", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-DET-DEM", "description": "Detention / Demurrage Ongoing", "sea_freight": 1, "air_freight": 0, "transport": 0},
        {"code": "SF-CLOSED", "description": "Closed", "sea_freight": 1, "air_freight": 0, "transport": 0},
    ]
    
    created_count = 0
    for milestone_data in sea_freight_milestones:
        try:
            if not frappe.db.exists("Logistics Milestone", milestone_data["code"]):
                doc = frappe.new_doc("Logistics Milestone")
                doc.update(milestone_data)
                doc.insert()
                created_count += 1
                print(f"  ✅ Created Milestone: {milestone_data['code']} - {milestone_data['description']}")
            else:
                # Update existing milestone to ensure sea_freight flag is set
                doc = frappe.get_doc("Logistics Milestone", milestone_data["code"])
                if not doc.sea_freight:
                    doc.sea_freight = 1
                    doc.save()
                    print(f"  ✓ Updated Milestone: {milestone_data['code']}")
        except Exception as e:
            print(f"  ❌ Error creating Milestone {milestone_data['code']}: {e}")
    
    print(f"📊 Logistics Milestones: {created_count} created/updated")


if __name__ == "__main__":
    execute()
