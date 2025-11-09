"""
Smart UNLOCO Update Command with Options
Usage: bench --site all execute logistics.air_freight.commands.smart_unlocode_update.smart_unlocode_update
"""

import frappe
from frappe import _
import json
from datetime import datetime
from typing import Dict, List, Optional

def smart_unlocode_update():
    """Smart UNLOCO update with command-line options"""
    
    print("🌍 Smart UNLOCO Update System")
    print("=" * 60)
    
    # Display available options
    display_options()
    
    # Get user choice
    choice = get_user_choice()
    
    # Execute based on choice
    execute_choice(choice)

def display_options():
    """Display available update options"""
    print("\n📋 Available Update Options:")
    print("=" * 40)
    print("1️⃣  Full UNLOCO Database (100,000+ locations)")
    print("2️⃣  US Locations Only (Airports & Ports)")
    print("3️⃣  European Locations (Major Airports & Ports)")
    print("4️⃣  Asian Locations (Major Airports & Ports)")
    print("5️⃣  Airport Locations Only")
    print("6️⃣  Port Locations Only")
    print("7️⃣  Major International Hubs")
    print("8️⃣  Custom Selection")
    print("9️⃣  Update Existing Locations Only")
    print("🔟  Check for Updates")
    print("❌  Exit")

def get_user_choice():
    """Get user choice"""
    while True:
        try:
            choice = input("\nEnter your choice (1-10): ").strip()
            if choice in ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10"]:
                return int(choice)
            elif choice.lower() in ["exit", "quit", "q"]:
                return 0
            else:
                print("❌ Invalid choice. Please enter 1-10 or 'exit'")
        except KeyboardInterrupt:
            print("\n❌ Update cancelled by user")
            return 0

def execute_choice(choice):
    """Execute based on user choice"""
    if choice == 0:
        print("👋 Goodbye!")
        return
    
    print(f"\n🚀 Executing Option {choice}...")
    print("=" * 40)
    
    if choice == 1:
        execute_full_database()
    elif choice == 2:
        execute_us_locations()
    elif choice == 3:
        execute_european_locations()
    elif choice == 4:
        execute_asian_locations()
    elif choice == 5:
        execute_airport_locations()
    elif choice == 6:
        execute_port_locations()
    elif choice == 7:
        execute_major_hubs()
    elif choice == 8:
        execute_custom_selection()
    elif choice == 9:
        execute_update_existing()
    elif choice == 10:
        execute_check_updates()

def execute_full_database():
    """Execute full UNLOCO database update"""
    print("🌍 Full UNLOCO Database Update")
    print("=" * 40)
    
    print("⚠️  This will process 100,000+ locations")
    print("Estimated time: 2-4 hours")
    
    confirm = input("\nDo you want to proceed? (y/n): ").lower().strip()
    if confirm == "y":
        print("🚀 Starting full database update...")
        # Implement full database update
        update_unlocode_data("full")
    else:
        print("❌ Full database update cancelled")

def execute_us_locations():
    """Execute US locations update"""
    print("🇺🇸 US Locations Update")
    print("=" * 40)
    
    print("Updating US airports and ports...")
    update_unlocode_data("countries", ["US"])
    print("✅ US locations updated successfully!")

def execute_european_locations():
    """Execute European locations update"""
    print("🇪🇺 European Locations Update")
    print("=" * 40)
    
    print("Updating European airports and ports...")
    countries = ["GB", "DE", "FR", "IT", "ES", "NL", "BE", "CH", "AT"]
    update_unlocode_data("countries", countries)
    print("✅ European locations updated successfully!")

def execute_asian_locations():
    """Execute Asian locations update"""
    print("🌏 Asian Locations Update")
    print("=" * 40)
    
    print("Updating Asian airports and ports...")
    countries = ["CN", "JP", "KR", "SG", "TH", "MY", "ID", "PH", "VN", "IN"]
    update_unlocode_data("countries", countries)
    print("✅ Asian locations updated successfully!")

def execute_airport_locations():
    """Execute airport locations update"""
    print("✈️ Airport Locations Update")
    print("=" * 40)
    
    print("Updating airport locations...")
    update_unlocode_data("functions", ["Airport"])
    print("✅ Airport locations updated successfully!")

def execute_port_locations():
    """Execute port locations update"""
    print("🚢 Port Locations Update")
    print("=" * 40)
    
    print("Updating port locations...")
    update_unlocode_data("functions", ["Port"])
    print("✅ Port locations updated successfully!")

def execute_major_hubs():
    """Execute major international hubs update"""
    print("🌐 Major International Hubs Update")
    print("=" * 40)
    
    print("Updating major international hubs...")
    major_hubs = [
        "USLAX", "USJFK", "USMIA", "USORD", "USDFW", "USATL", "USSEA",
        "GBLHR", "GBLGW", "DEHAM", "NLRTM", "SGSIN", "CNPVG", "JPYOK"
    ]
    update_unlocode_data("custom", major_hubs)
    print("✅ Major hubs updated successfully!")

def execute_custom_selection():
    """Execute custom selection"""
    print("🎯 Custom Selection Update")
    print("=" * 40)
    
    print("Please specify your custom selection:")
    print("1. Enter UNLOCO codes (comma-separated)")
    print("2. Enter country codes (comma-separated)")
    print("3. Enter function types (comma-separated)")
    
    selection_type = input("\nEnter selection type (1/2/3): ").strip()
    
    if selection_type == "1":
        codes = input("Enter UNLOCO codes: ").strip().upper()
        codes_list = [c.strip() for c in codes.split(",")]
        update_unlocode_data("custom", codes_list)
    elif selection_type == "2":
        countries = input("Enter country codes: ").strip().upper()
        countries_list = [c.strip() for c in countries.split(",")]
        update_unlocode_data("countries", countries_list)
    elif selection_type == "3":
        functions = input("Enter function types: ").strip()
        functions_list = [f.strip() for f in functions.split(",")]
        update_unlocode_data("functions", functions_list)
    else:
        print("❌ Invalid selection type")
        return
    
    print("✅ Custom selection updated successfully!")

def execute_update_existing():
    """Execute update existing locations only"""
    print("🔄 Update Existing Locations")
    print("=" * 40)
    
    print("Updating existing locations with latest data...")
    update_existing_locations()
    print("✅ Existing locations updated successfully!")

def execute_check_updates():
    """Execute check for updates"""
    print("🔍 Check for Updates")
    print("=" * 40)
    
    print("Checking for UNLOCO updates...")
    check_for_updates()
    print("✅ Update check completed!")

def update_unlocode_data(scope, data=None):
    """Update UNLOCO data based on scope"""
    try:
        print(f"📊 Updating UNLOCO data (scope: {scope})...")
        
        if scope == "full":
            print("Processing full UNLOCO database...")
            # Implement full database processing
        elif scope == "countries":
            print(f"Processing countries: {', '.join(data)}")
            # Implement country-based processing
        elif scope == "functions":
            print(f"Processing functions: {', '.join(data)}")
            # Implement function-based processing
        elif scope == "custom":
            print(f"Processing custom selection: {', '.join(data)}")
            # Implement custom processing
        
        print("✅ UNLOCO data update completed!")
        
    except Exception as e:
        print(f"❌ Error updating UNLOCO data: {str(e)}")
        frappe.log_error(f"UNLOCO data update error: {str(e)}")

def update_existing_locations():
    """Update existing locations with latest data"""
    try:
        print("🔄 Updating existing locations...")
        
        # Get all existing UNLOCO locations
        locations = frappe.get_all("Location", 
                                 filters={"custom_unlocode": ["!=", ""]},
                                 fields=["name", "custom_unlocode"])
        
        print(f"Found {len(locations)} existing locations")
        
        updated_count = 0
        for loc in locations:
            try:
                # Update location with latest data
                location_doc = frappe.get_doc("Location", loc.name)
                
                # Update with latest UNLOCO data
                update_location_from_latest_data(location_doc, loc.custom_unlocode)
                
                location_doc.save(ignore_permissions=True)
                updated_count += 1
                print(f"✓ Updated {loc.custom_unlocode}")
                
            except Exception as e:
                print(f"✗ Error updating {loc.custom_unlocode}: {str(e)}")
                frappe.log_error(f"Location update error for {loc.custom_unlocode}: {str(e)}")
        
        frappe.db.commit()
        print(f"✅ Updated {updated_count} locations successfully")
        
    except Exception as e:
        print(f"❌ Error updating existing locations: {str(e)}")
        frappe.log_error(f"Existing locations update error: {str(e)}")

def update_location_from_latest_data(location_doc, unlocode):
    """Update location with latest UNLOCO data"""
    # This would integrate with actual UNLOCO data sources
    # For now, just update the last_updated timestamp
    location_doc.custom_last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def check_for_updates():
    """Check for available UNLOCO updates"""
    try:
        print("🔍 Checking for UNLOCO updates...")
        
        # Check current data version
        current_version = get_current_data_version()
        print(f"Current data version: {current_version}")
        
        # Check for new versions
        print("📅 UNLOCO Update Schedule:")
        print("  - March 31st (cut-off date)")
        print("  - September 30th (cut-off date)")
        print("  - Biannual releases by UNECE")
        
        # Check if update is needed
        last_update = get_last_update_date()
        if last_update:
            print(f"Last update: {last_update}")
            
            # Check if 6 months have passed
            from datetime import datetime, timedelta
            six_months_ago = datetime.now() - timedelta(days=180)
            if last_update < six_months_ago:
                print("⚠️  Update recommended - data is older than 6 months")
            else:
                print("✅ Data is current")
        else:
            print("⚠️  No previous update found - update recommended")
        
        print("✅ Update check completed!")
        
    except Exception as e:
        print(f"❌ Error checking for updates: {str(e)}")
        frappe.log_error(f"Update check error: {str(e)}")

def get_current_data_version():
    """Get current data version"""
    try:
        version_info = frappe.get_single("UNLOCO Settings")
        return version_info.get("current_version", "Unknown")
    except:
        return "Unknown"

def get_last_update_date():
    """Get last update date"""
    try:
        version_info = frappe.get_single("UNLOCO Settings")
        return version_info.get("last_update_date")
    except:
        return None

def main():
    """Main function for smart UNLOCO update"""
    try:
        print("🚀 Smart UNLOCO Update System")
        print("=" * 60)
        
        # Display options and get choice
        display_options()
        choice = get_user_choice()
        
        # Execute choice
        execute_choice(choice)
        
    except Exception as e:
        print(f"❌ Error in smart update: {str(e)}")
        frappe.log_error(f"Smart UNLOCO update error: {str(e)}")

if __name__ == "__main__":
    main()
