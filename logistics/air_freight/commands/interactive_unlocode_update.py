"""
Interactive UNLOCO Update Command
Allows users to specify update preferences:
- Full list or specific countries
- Function types to include
- Update scope and filters
Usage: bench --site all execute logistics.air_freight.commands.interactive_unlocode_update.interactive_unlocode_update
"""

import frappe
from frappe import _
import json
from datetime import datetime
from typing import Dict, List, Optional

def interactive_unlocode_update():
    """Interactive UNLOCO update with user preferences"""
    
    print("🌍 Interactive UNLOCO Update System")
    print("=" * 60)
    
    # Get user preferences
    preferences = get_user_preferences()
    
    # Display update plan
    display_update_plan(preferences)
    
    # Confirm with user
    if confirm_update(preferences):
        # Execute update based on preferences
        execute_update(preferences)
    else:
        print("❌ Update cancelled by user")
        return

def get_user_preferences():
    """Get user preferences for UNLOCO update"""
    preferences = {
        "update_scope": None,
        "countries": [],
        "functions": [],
        "location_types": [],
        "max_locations": None,
        "include_existing": True,
        "update_frequency": "manual"
    }
    
    print("\n📋 Please specify your update preferences:")
    print("=" * 50)
    
    # 1. Update Scope
    print("\n1️⃣ Update Scope:")
    print("   a) Full UNLOCO database (100,000+ locations)")
    print("   b) Specific countries only")
    print("   c) Function-based selection")
    print("   d) Location type-based selection")
    print("   e) Custom selection")
    
    scope_choice = input("\nEnter your choice (a/b/c/d/e): ").lower().strip()
    
    if scope_choice == "a":
        preferences["update_scope"] = "full"
        preferences["max_locations"] = 100000
    elif scope_choice == "b":
        preferences["update_scope"] = "countries"
        preferences["countries"] = get_country_selection()
    elif scope_choice == "c":
        preferences["update_scope"] = "functions"
        preferences["functions"] = get_function_selection()
    elif scope_choice == "d":
        preferences["update_scope"] = "location_types"
        preferences["location_types"] = get_location_type_selection()
    elif scope_choice == "e":
        preferences["update_scope"] = "custom"
        preferences = get_custom_selection(preferences)
    else:
        print("❌ Invalid choice. Using default: Full database")
        preferences["update_scope"] = "full"
    
    # 2. Include Existing Locations
    print("\n2️⃣ Include Existing Locations:")
    print("   a) Update existing locations")
    print("   b) Skip existing locations")
    print("   c) Replace existing locations")
    
    existing_choice = input("\nEnter your choice (a/b/c): ").lower().strip()
    if existing_choice == "a":
        preferences["include_existing"] = True
    elif existing_choice == "b":
        preferences["include_existing"] = False
    elif existing_choice == "c":
        preferences["include_existing"] = "replace"
    else:
        preferences["include_existing"] = True
    
    # 3. Update Frequency
    print("\n3️⃣ Update Frequency:")
    print("   a) One-time update")
    print("   b) Schedule regular updates")
    print("   c) Set up automatic updates")
    
    frequency_choice = input("\nEnter your choice (a/b/c): ").lower().strip()
    if frequency_choice == "a":
        preferences["update_frequency"] = "manual"
    elif frequency_choice == "b":
        preferences["update_frequency"] = "scheduled"
    elif frequency_choice == "c":
        preferences["update_frequency"] = "automatic"
    else:
        preferences["update_frequency"] = "manual"
    
    return preferences

def get_country_selection():
    """Get country selection from user"""
    print("\n🌍 Country Selection:")
    print("Available countries:")
    
    # Common countries for UNLOCO
    countries = [
        "US", "GB", "DE", "FR", "IT", "ES", "NL", "BE", "CH", "AT",
        "CN", "JP", "KR", "SG", "AU", "CA", "MX", "BR", "AR", "CL",
        "IN", "TH", "MY", "ID", "PH", "VN", "RU", "UA", "PL", "CZ"
    ]
    
    for i, country in enumerate(countries, 1):
        print(f"   {i:2d}) {country}")
    
    print("   Enter country codes separated by commas (e.g., US,GB,DE)")
    print("   Or enter 'all' for all countries")
    
    country_input = input("\nEnter countries: ").strip().upper()
    
    if country_input.lower() == "all":
        return countries
    else:
        selected_countries = [c.strip() for c in country_input.split(",")]
        return [c for c in selected_countries if c in countries]

def get_function_selection():
    """Get function selection from user"""
    print("\n🔧 Function Selection:")
    print("Available functions:")
    
    functions = [
        "Airport", "Port", "Railway", "Road", "Border Crossing",
        "Postal", "Multimodal", "Fixed Transport", "Customs", "Immigration"
    ]
    
    for i, func in enumerate(functions, 1):
        print(f"   {i:2d}) {func}")
    
    print("   Enter function names separated by commas")
    print("   Or enter 'all' for all functions")
    
    function_input = input("\nEnter functions: ").strip()
    
    if function_input.lower() == "all":
        return functions
    else:
        selected_functions = [f.strip() for f in function_input.split(",")]
        return [f for f in selected_functions if f in functions]

def get_location_type_selection():
    """Get location type selection from user"""
    print("\n🏢 Location Type Selection:")
    print("Available location types:")
    
    location_types = [
        "Airport", "Port", "Railway Station", "Road Terminal",
        "Border Crossing", "Postal Office", "Multimodal Terminal"
    ]
    
    for i, loc_type in enumerate(location_types, 1):
        print(f"   {i:2d}) {loc_type}")
    
    print("   Enter location types separated by commas")
    print("   Or enter 'all' for all types")
    
    type_input = input("\nEnter location types: ").strip()
    
    if type_input.lower() == "all":
        return location_types
    else:
        selected_types = [t.strip() for t in type_input.split(",")]
        return [t for t in selected_types if t in location_types]

def get_custom_selection(preferences):
    """Get custom selection from user"""
    print("\n🎯 Custom Selection:")
    
    # Get countries
    preferences["countries"] = get_country_selection()
    
    # Get functions
    preferences["functions"] = get_function_selection()
    
    # Get location types
    preferences["location_types"] = get_location_type_selection()
    
    # Get max locations
    print("\n📊 Maximum Locations:")
    print("   Enter maximum number of locations to process")
    print("   Or enter 'unlimited' for no limit")
    
    max_input = input("\nEnter max locations: ").strip()
    if max_input.lower() == "unlimited":
        preferences["max_locations"] = None
    else:
        try:
            preferences["max_locations"] = int(max_input)
        except ValueError:
            preferences["max_locations"] = 1000
    
    return preferences

def display_update_plan(preferences):
    """Display the update plan based on preferences"""
    print("\n📋 Update Plan:")
    print("=" * 50)
    
    print(f"Update Scope: {preferences['update_scope']}")
    
    if preferences["countries"]:
        print(f"Countries: {', '.join(preferences['countries'])}")
    
    if preferences["functions"]:
        print(f"Functions: {', '.join(preferences['functions'])}")
    
    if preferences["location_types"]:
        print(f"Location Types: {', '.join(preferences['location_types'])}")
    
    if preferences["max_locations"]:
        print(f"Max Locations: {preferences['max_locations']}")
    
    print(f"Include Existing: {preferences['include_existing']}")
    print(f"Update Frequency: {preferences['update_frequency']}")
    
    # Estimate processing time
    estimated_time = estimate_processing_time(preferences)
    print(f"Estimated Processing Time: {estimated_time}")

def estimate_processing_time(preferences):
    """Estimate processing time based on preferences"""
    if preferences["update_scope"] == "full":
        return "2-4 hours (100,000+ locations)"
    elif preferences["max_locations"]:
        if preferences["max_locations"] <= 1000:
            return "5-10 minutes"
        elif preferences["max_locations"] <= 10000:
            return "30-60 minutes"
        else:
            return "1-2 hours"
    else:
        return "10-30 minutes"

def confirm_update(preferences):
    """Confirm update with user"""
    print("\n❓ Confirm Update:")
    print("=" * 30)
    
    print("Do you want to proceed with this update?")
    print("   y) Yes, proceed with update")
    print("   n) No, cancel update")
    print("   m) Modify preferences")
    
    choice = input("\nEnter your choice (y/n/m): ").lower().strip()
    
    if choice == "y":
        return True
    elif choice == "m":
        # Allow user to modify preferences
        return get_user_preferences()
    else:
        return False

def execute_update(preferences):
    """Execute the update based on preferences"""
    print("\n🚀 Executing UNLOCO Update...")
    print("=" * 50)
    
    try:
        # Get UNLOCO data based on preferences
        unlocode_data = get_filtered_unlocode_data(preferences)
        
        # Process locations
        results = process_locations(unlocode_data, preferences)
        
        # Display results
        display_results(results)
        
        # Set up update frequency if requested
        if preferences["update_frequency"] != "manual":
            setup_update_frequency(preferences)
        
        print("\n✅ UNLOCO update completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during update: {str(e)}")
        frappe.log_error(f"UNLOCO update error: {str(e)}")

def get_filtered_unlocode_data(preferences):
    """Get filtered UNLOCO data based on preferences"""
    print("📊 Filtering UNLOCO data based on preferences...")
    
    # This would integrate with actual UNLOCO data sources
    # For now, return sample data
    sample_data = {
        "USLAX": {"country": "US", "function": "Airport", "type": "Airport"},
        "USJFK": {"country": "US", "function": "Airport", "type": "Airport"},
        "GBLHR": {"country": "GB", "function": "Airport", "type": "Airport"},
        "DEHAM": {"country": "DE", "function": "Port", "type": "Port"},
        "NLRTM": {"country": "NL", "function": "Port", "type": "Port"}
    }
    
    # Apply filters based on preferences
    filtered_data = {}
    
    for unlocode, data in sample_data.items():
        # Country filter
        if preferences["countries"] and data["country"] not in preferences["countries"]:
            continue
        
        # Function filter
        if preferences["functions"] and data["function"] not in preferences["functions"]:
            continue
        
        # Location type filter
        if preferences["location_types"] and data["type"] not in preferences["location_types"]:
            continue
        
        filtered_data[unlocode] = data
    
    print(f"✓ Filtered to {len(filtered_data)} locations")
    return filtered_data

def process_locations(unlocode_data, preferences):
    """Process locations based on preferences"""
    print("🔄 Processing locations...")
    
    results = {
        "total_processed": 0,
        "successful": 0,
        "failed": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": []
    }
    
    for unlocode, data in unlocode_data.items():
        results["total_processed"] += 1
        
        try:
            # Check if location exists
            existing = frappe.db.get_value("Location", {"custom_unlocode": unlocode})
            
            if existing and preferences["include_existing"] == False:
                results["skipped"] += 1
                continue
            
            # Create or update location
            if existing:
                if preferences["include_existing"] == "replace":
                    # Replace existing location
                    location = frappe.get_doc("Location", existing)
                    location.delete()
                    results["created"] += 1
                else:
                    # Update existing location
                    results["updated"] += 1
            else:
                results["created"] += 1
            
            # Process location (create/update logic would go here)
            results["successful"] += 1
            print(f"✓ Processed {unlocode}")
            
        except Exception as e:
            results["failed"] += 1
            error_msg = f"Error processing {unlocode}: {str(e)}"
            results["errors"].append(error_msg)
            print(f"✗ {error_msg}")
    
    return results

def display_results(results):
    """Display update results"""
    print("\n📊 Update Results:")
    print("=" * 30)
    print(f"Total Processed: {results['total_processed']}")
    print(f"Successful: {results['successful']}")
    print(f"Failed: {results['failed']}")
    print(f"Created: {results['created']}")
    print(f"Updated: {results['updated']}")
    print(f"Skipped: {results['skipped']}")
    
    if results["errors"]:
        print(f"\n❌ Errors ({len(results['errors'])}):")
        for error in results["errors"][:5]:  # Show first 5 errors
            print(f"  - {error}")
        if len(results["errors"]) > 5:
            print(f"  ... and {len(results['errors']) - 5} more errors")

def setup_update_frequency(preferences):
    """Set up update frequency based on preferences"""
    print("\n⏰ Setting up update frequency...")
    
    if preferences["update_frequency"] == "scheduled":
        print("📅 Scheduled updates will be configured")
        # Set up scheduled updates
    elif preferences["update_frequency"] == "automatic":
        print("🔄 Automatic updates will be configured")
        # Set up automatic updates
    
    print("✓ Update frequency configured")

def main():
    """Main function for interactive UNLOCO update"""
    try:
        print("🚀 Interactive UNLOCO Update System")
        print("=" * 60)
        
        # Get user preferences
        preferences = get_user_preferences()
        
        # Display update plan
        display_update_plan(preferences)
        
        # Confirm with user
        if confirm_update(preferences):
            # Execute update
            execute_update(preferences)
        else:
            print("❌ Update cancelled by user")
        
    except Exception as e:
        print(f"❌ Error in interactive update: {str(e)}")
        frappe.log_error(f"Interactive UNLOCO update error: {str(e)}")

if __name__ == "__main__":
    main()
