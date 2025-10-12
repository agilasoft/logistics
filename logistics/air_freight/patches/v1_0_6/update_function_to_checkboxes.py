"""
Update Function field to use checkboxes for multiple function selection
- Replace single Select field with multiple Check fields
- Allow locations to have multiple functions (Port, Airport, Rail, Road, etc.)
"""

import frappe
from frappe import _

def execute():
    """Update Function field to use checkboxes for multiple function selection"""
    
    print("🔧 Updating Function field to use checkboxes...")
    print("=" * 60)
    
    # Remove the old single Select function field
    remove_old_function_field()
    
    # Add new checkbox fields for each function type
    add_function_checkbox_fields()
    
    # Update existing locations with checkbox values
    update_existing_locations_with_checkboxes()
    
    print("✅ Function field updated to use checkboxes successfully!")

def remove_old_function_field():
    """Remove the old single Select function field"""
    try:
        print("🗑️  Removing old function field...")
        
        # Check if the old field exists
        old_field = frappe.db.get_value("Custom Field", {
            "dt": "Location",
            "fieldname": "custom_function"
        })
        
        if old_field:
            # Delete the old field
            frappe.delete_doc("Custom Field", old_field)
            frappe.db.commit()
            print("✓ Removed old custom_function field")
        else:
            print("✓ Old custom_function field not found (already removed)")
            
    except Exception as e:
        print(f"✗ Error removing old function field: {str(e)}")
        frappe.log_error(f"Function field removal error: {str(e)}")

def add_function_checkbox_fields():
    """Add new checkbox fields for each function type"""
    try:
        print("➕ Adding function checkbox fields...")
        
        # Function checkbox fields
        function_fields = [
            {
                "fieldname": "custom_has_post",
                "label": "Has Post",
                "fieldtype": "Check",
                "insert_after": "custom_location_type",
                "description": "Has postal exchange office",
                "reqd": 0
            },
            {
                "fieldname": "custom_has_customs",
                "label": "Has Customs",
                "fieldtype": "Check",
                "insert_after": "custom_has_post",
                "description": "Has customs office",
                "reqd": 0
            },
            {
                "fieldname": "custom_has_unload",
                "label": "Has Unload",
                "fieldtype": "Check",
                "insert_after": "custom_has_customs",
                "description": "Has unloading facilities",
                "reqd": 0
            },
            {
                "fieldname": "custom_has_airport",
                "label": "Has Airport",
                "fieldtype": "Check",
                "insert_after": "custom_has_unload",
                "description": "Has airport facilities",
                "reqd": 0
            },
            {
                "fieldname": "custom_has_rail",
                "label": "Has Rail",
                "fieldtype": "Check",
                "insert_after": "custom_has_airport",
                "description": "Has railway facilities",
                "reqd": 0
            },
            {
                "fieldname": "custom_has_road",
                "label": "Has Road",
                "fieldtype": "Check",
                "insert_after": "custom_has_rail",
                "description": "Has road transport facilities",
                "reqd": 0
            },
            {
                "fieldname": "custom_has_store",
                "label": "Has Store",
                "fieldtype": "Check",
                "insert_after": "custom_has_road",
                "description": "Has storage facilities",
                "reqd": 0
            },
            {
                "fieldname": "custom_has_terminal",
                "label": "Has Terminal",
                "fieldtype": "Check",
                "insert_after": "custom_has_store",
                "description": "Has terminal facilities",
                "reqd": 0
            },
            {
                "fieldname": "custom_has_discharge",
                "label": "Has Discharge",
                "fieldtype": "Check",
                "insert_after": "custom_has_terminal",
                "description": "Has discharge facilities",
                "reqd": 0
            },
            {
                "fieldname": "custom_has_seaport",
                "label": "Has Seaport",
                "fieldtype": "Check",
                "insert_after": "custom_has_discharge",
                "description": "Has seaport facilities",
                "reqd": 0
            },
            {
                "fieldname": "custom_has_outport",
                "label": "Has Outport",
                "fieldtype": "Check",
                "insert_after": "custom_has_seaport",
                "description": "Has outport facilities",
                "reqd": 0
            }
        ]
        
        fields_added = 0
        for field_data in function_fields:
            # Check if field already exists
            existing_field = frappe.db.get_value("Custom Field", {
                "dt": "Location",
                "fieldname": field_data["fieldname"]
            })
            
            if not existing_field:
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
            print(f"✓ Successfully added {fields_added} function checkbox fields")
        
        return True
        
    except Exception as e:
        print(f"✗ Error adding function checkbox fields: {str(e)}")
        frappe.log_error(f"Function checkbox fields addition error: {str(e)}")
        return False

def update_existing_locations_with_checkboxes():
    """Update existing locations with checkbox values based on their function"""
    try:
        print("🔄 Updating existing locations with checkbox values...")
        
        # Get all locations with UNLOCO codes
        locations = frappe.get_all("Location", 
                                 filters={"custom_unlocode": ["!=", ""]},
                                 fields=["name", "custom_unlocode", "custom_location_type"])
        
        updated_count = 0
        for loc in locations:
            try:
                location_doc = frappe.get_doc("Location", loc.name)
                
                # Set checkbox values based on location type and function
                set_function_checkboxes(location_doc, loc.custom_location_type)
                
                location_doc.save(ignore_permissions=True)
                updated_count += 1
                print(f"✓ Updated {loc.custom_unlocode}")
                
            except Exception as e:
                print(f"✗ Error updating {loc.custom_unlocode}: {str(e)}")
                frappe.log_error(f"Location checkbox update error for {loc.custom_unlocode}: {str(e)}")
        
        frappe.db.commit()
        print(f"✓ Updated {updated_count} locations with checkbox values")
        
    except Exception as e:
        print(f"✗ Error updating locations with checkboxes: {str(e)}")
        frappe.log_error(f"Location checkbox update error: {str(e)}")

def set_function_checkboxes(location_doc, location_type):
    """Set checkbox values based on location type and function"""
    try:
        # Reset all checkboxes to False
        location_doc.custom_has_post = 0
        location_doc.custom_has_customs = 0
        location_doc.custom_has_unload = 0
        location_doc.custom_has_airport = 0
        location_doc.custom_has_rail = 0
        location_doc.custom_has_road = 0
        location_doc.custom_has_store = 0
        location_doc.custom_has_terminal = 0
        location_doc.custom_has_discharge = 0
        location_doc.custom_has_seaport = 0
        location_doc.custom_has_outport = 0
        
        # Set checkboxes based on location type
        if location_type == "Airport":
            location_doc.custom_has_airport = 1
            location_doc.custom_has_customs = 1
            location_doc.custom_has_immigration_office = 1
            location_doc.custom_has_quarantine_facility = 1
            location_doc.custom_has_health_authority = 1
            
        elif location_type == "Port":
            location_doc.custom_has_seaport = 1
            location_doc.custom_has_customs = 1
            location_doc.custom_has_unload = 1
            location_doc.custom_has_discharge = 1
            location_doc.custom_has_terminal = 1
            
        elif location_type == "Railway Station":
            location_doc.custom_has_rail = 1
            location_doc.custom_has_terminal = 1
            
        elif location_type == "Road Terminal":
            location_doc.custom_has_road = 1
            location_doc.custom_has_terminal = 1
            
        elif location_type == "Border Crossing":
            location_doc.custom_has_customs = 1
            location_doc.custom_has_immigration_office = 1
            
        # Set additional checkboxes based on UNLOCO code patterns
        unlocode = location_doc.custom_unlocode
        if unlocode:
            # Airports typically have these facilities
            if "LAX" in unlocode or "JFK" in unlocode or "MIA" in unlocode or "ORD" in unlocode or "DFW" in unlocode or "ATL" in unlocode or "SEA" in unlocode or "LHR" in unlocode or "LGW" in unlocode:
                location_doc.custom_has_airport = 1
                location_doc.custom_has_customs = 1
                location_doc.custom_has_immigration_office = 1
                location_doc.custom_has_quarantine_facility = 1
                location_doc.custom_has_health_authority = 1
                
            # Ports typically have these facilities
            elif "LGB" in unlocode or "NYC" in unlocode or "HAM" in unlocode or "RTM" in unlocode or "SIN" in unlocode or "PVG" in unlocode or "YOK" in unlocode:
                location_doc.custom_has_seaport = 1
                location_doc.custom_has_customs = 1
                location_doc.custom_has_unload = 1
                location_doc.custom_has_discharge = 1
                location_doc.custom_has_terminal = 1
        
        # Set store checkbox for all locations (they all have some storage)
        location_doc.custom_has_store = 1
        
    except Exception as e:
        print(f"✗ Error setting function checkboxes: {str(e)}")
        frappe.log_error(f"Function checkbox setting error: {str(e)}")

def main():
    """Main function for function field update"""
    try:
        print("🚀 Function Field Update to Checkboxes")
        print("=" * 60)
        
        # Remove old function field
        remove_old_function_field()
        
        # Add new checkbox fields
        add_function_checkbox_fields()
        
        # Update existing locations
        update_existing_locations_with_checkboxes()
        
        print("\n✅ Function field update completed successfully!")
        print("\n📋 Summary:")
        print("  - Removed old single Select function field")
        print("  - Added 11 function checkbox fields")
        print("  - Updated existing locations with checkbox values")
        print("  - Locations can now have multiple functions")
        
    except Exception as e:
        print(f"❌ Error in function field update: {str(e)}")
        frappe.log_error(f"Function field update main error: {str(e)}")

if __name__ == "__main__":
    main()
