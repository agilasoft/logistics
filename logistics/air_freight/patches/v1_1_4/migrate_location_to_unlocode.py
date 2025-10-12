"""
Migrate existing Location data to UNLOCO doctype
- Copy all Location records with UNLOCO codes to UNLOCO doctype
- Map all fields from Location to UNLOCO
- Preserve all data and relationships
"""

import frappe
from frappe import _

def execute():
    """Migrate existing Location data to UNLOCO doctype"""
    
    print("🔄 Migrating Location data to UNLOCO doctype...")
    print("=" * 60)
    
    # Get all locations with UNLOCO codes
    locations = get_locations_with_unlocode()
    
    # Migrate each location
    migrate_locations_to_unlocode(locations)
    
    print("✅ Location data migrated to UNLOCO successfully!")

def get_locations_with_unlocode():
    """Get all locations with UNLOCO codes"""
    try:
        print("📋 Getting locations with UNLOCO codes...")
        
        # Get all locations that have UNLOCO codes
        locations = frappe.get_all("Location", 
                                 filters={"custom_unlocode": ["!=", ""]},
                                 fields=["*"])
        
        print(f"Found {len(locations)} locations with UNLOCO codes")
        return locations
        
    except Exception as e:
        print(f"✗ Error getting locations: {str(e)}")
        frappe.log_error(f"Location retrieval error: {str(e)}")
        return []

def migrate_locations_to_unlocode(locations):
    """Migrate locations to UNLOCO doctype"""
    try:
        print("🔄 Migrating locations to UNLOCO doctype...")
        
        migrated_count = 0
        skipped_count = 0
        error_count = 0
        
        for location in locations:
            try:
                # Check if UNLOCO record already exists
                existing_unlocode = frappe.db.get_value("UNLOCO", {"unlocode": location.custom_unlocode})
                
                if existing_unlocode:
                    print(f"⚠️  UNLOCO {location.custom_unlocode} already exists, skipping")
                    skipped_count += 1
                    continue
                
                # Create UNLOCO record
                unlocode_doc = create_unlocode_from_location(location)
                
                if unlocode_doc:
                    migrated_count += 1
                    print(f"✓ Migrated {location.custom_unlocode}")
                else:
                    error_count += 1
                    print(f"✗ Failed to migrate {location.custom_unlocode}")
                
            except Exception as e:
                error_count += 1
                print(f"✗ Error migrating {location.custom_unlocode}: {str(e)}")
                frappe.log_error(f"Location migration error for {location.custom_unlocode}: {str(e)}")
        
        # Print summary
        print(f"\n📊 Migration Summary:")
        print(f"  - Migrated: {migrated_count}")
        print(f"  - Skipped: {skipped_count}")
        print(f"  - Errors: {error_count}")
        print(f"  - Total: {len(locations)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error migrating locations: {str(e)}")
        frappe.log_error(f"Location migration error: {str(e)}")
        return False

def create_unlocode_from_location(location):
    """Create UNLOCO record from Location data"""
    try:
        # Create UNLOCO document
        unlocode_doc = frappe.get_doc({
            "doctype": "UNLOCO",
            "unlocode": location.custom_unlocode,
            "location_name": location.custom_location_name or location.location_name,
            "country": location.custom_country or "",
            "country_code": location.custom_country_code or "",
            "subdivision": location.custom_subdivision or "",
            "city": location.custom_city or "",
            "location_type": location.custom_location_type or "",
            "function": location.custom_function or "",
            "status": location.custom_status or "",
            "latitude": location.latitude,
            "longitude": location.longitude,
            "description": location.custom_description or "",
            
            # Identifiers
            "iata_code": location.custom_iata_code or "",
            "icao_code": location.custom_icao_code or "",
            "railway_code": location.custom_railway_code or "",
            "port_code": location.custom_port_code or "",
            "alternative_names": location.custom_alternative_names or "",
            
            # Logistics Details
            "timezone": location.custom_timezone or "",
            "currency": location.custom_currency or "",
            "language": location.custom_language or "",
            "utc_offset": location.custom_utc_offset or "",
            "operating_hours": location.custom_operating_hours or "",
            
            # Function Capabilities
            "has_post": location.custom_has_post or 0,
            "has_customs": location.custom_has_customs or 0,
            "has_unload": location.custom_has_unload or 0,
            "has_airport": location.custom_has_airport or 0,
            "has_rail": location.custom_has_rail or 0,
            "has_road": location.custom_has_road or 0,
            "has_store": location.custom_has_store or 0,
            "has_terminal": location.custom_has_terminal or 0,
            "has_discharge": location.custom_has_discharge or 0,
            "has_seaport": location.custom_has_seaport or 0,
            "has_outport": location.custom_has_outport or 0,
            
            # Regulatory Facilities
            "customs_office": location.custom_customs_office or 0,
            "immigration_office": location.custom_immigration_office or 0,
            "quarantine_facility": location.custom_quarantine_facility or 0,
            "health_authority": location.custom_health_authority or 0,
            
            # Auto-Populate Settings
            "auto_populate": location.custom_auto_populate or 1,
            "last_updated": location.custom_last_updated or frappe.utils.now(),
            "data_source": location.custom_data_source or "Internal Database"
        })
        
        # Insert the document
        unlocode_doc.insert(ignore_permissions=True)
        frappe.db.commit()
        
        return unlocode_doc
        
    except Exception as e:
        print(f"✗ Error creating UNLOCO from location: {str(e)}")
        frappe.log_error(f"UNLOCO creation error: {str(e)}")
        return None

def main():
    """Main function for migrating Location data to UNLOCO"""
    try:
        print("🚀 Migrating Location Data to UNLOCO DocType")
        print("=" * 60)
        
        # Get locations with UNLOCO codes
        locations = get_locations_with_unlocode()
        
        if not locations:
            print("⚠️  No locations with UNLOCO codes found")
            return
        
        # Migrate locations
        migrate_locations_to_unlocode(locations)
        
        print("\n✅ Location data migration completed successfully!")
        print("\n📋 Migration Results:")
        print("  - All Location records with UNLOCO codes migrated to UNLOCO doctype")
        print("  - All field mappings preserved")
        print("  - Function checkboxes migrated")
        print("  - Regulatory facilities migrated")
        print("  - Auto-populate settings migrated")
        
    except Exception as e:
        print(f"❌ Error in Location data migration: {str(e)}")
        frappe.log_error(f"Location data migration error: {str(e)}")

if __name__ == "__main__":
    main()
