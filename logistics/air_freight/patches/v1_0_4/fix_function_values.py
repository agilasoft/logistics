"""
Fix function values to use proper UNLOCO format
"""

import frappe
from frappe import _

def execute():
    """Fix function values to use proper UNLOCO format"""
    
    print("🔧 Fixing UNLOCO Function Values...")
    print("=" * 50)
    
    # Update existing locations with correct function values
    update_function_values()
    
    print("✅ Function values fixed successfully!")

def update_function_values():
    """Update function values to use proper UNLOCO format"""
    try:
        # Get all locations with UNLOCO codes
        locations = frappe.get_all("Location", 
                                 filters={"custom_unlocode": ["!=", ""]},
                                 fields=["name", "custom_unlocode", "custom_location_type"])
        
        for loc in locations:
            try:
                location_doc = frappe.get_doc("Location", loc.name)
                
                # Set function based on location type
                if loc.custom_location_type == "Airport":
                    location_doc.custom_function = "4 - Airport"
                elif loc.custom_location_type == "Port":
                    location_doc.custom_function = "1 - Port"
                else:
                    location_doc.custom_function = "0 - Not known"
                
                # Set status to approved
                location_doc.custom_status = "AA - Approved by competent national government agency"
                
                # Save the location
                location_doc.save(ignore_permissions=True)
                print(f"✓ Updated {loc.custom_unlocode}: Function = {location_doc.custom_function}")
                
            except Exception as e:
                print(f"✗ Error updating {loc.custom_unlocode}: {str(e)}")
        
        frappe.db.commit()
        print(f"✓ Updated {len(locations)} locations with correct function values")
        
    except Exception as e:
        print(f"✗ Error updating function values: {str(e)}")
        frappe.log_error(f"Function values update error: {str(e)}")
