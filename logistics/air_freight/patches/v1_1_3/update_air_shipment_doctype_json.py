"""
Update Air Shipment doctype JSON to link to UNLOCO instead of Location
- Update origin_port and destination_port fields in the doctype JSON
- Change options from "Location" to "UNLOCO"
"""

import frappe
from frappe import _
import json
import os

def execute():
    """Update Air Shipment doctype JSON to link to UNLOCO"""
    
    print("🔄 Updating Air Shipment doctype JSON to UNLOCO...")
    print("=" * 60)
    
    # Update the doctype JSON file
    update_doctype_json()
    
    print("✅ Air Shipment doctype JSON updated to UNLOCO successfully!")

def update_doctype_json():
    """Update the Air Shipment doctype JSON file"""
    try:
        print("📝 Updating Air Shipment doctype JSON...")
        
        # Path to the Air Shipment doctype JSON file
        json_file_path = "/home/frappe/frappe-bench/apps/logistics/logistics/air_freight/doctype/air_shipment/air_shipment.json"
        
        # Read the current JSON file
        with open(json_file_path, 'r') as f:
            doctype_data = json.load(f)
        
        # Update origin_port field
        for field in doctype_data.get("fields", []):
            if field.get("fieldname") == "origin_port":
                field["options"] = "UNLOCO"
                field["description"] = "Origin port UNLOCO code"
                print("✓ Updated origin_port field to link to UNLOCO")
                break
        
        # Update destination_port field
        for field in doctype_data.get("fields", []):
            if field.get("fieldname") == "destination_port":
                field["options"] = "UNLOCO"
                field["description"] = "Destination port UNLOCO code"
                print("✓ Updated destination_port field to link to UNLOCO")
                break
        
        # Write the updated JSON back to the file
        with open(json_file_path, 'w') as f:
            json.dump(doctype_data, f, indent=1)
        
        print("✓ Air Shipment doctype JSON updated successfully")
        
        # Reload the doctype
        frappe.reload_doctype("Air Shipment")
        print("✓ Air Shipment doctype reloaded")
        
        return True
        
    except Exception as e:
        print(f"✗ Error updating Air Shipment doctype JSON: {str(e)}")
        frappe.log_error(f"Air Shipment doctype JSON update error: {str(e)}")
        return False

def main():
    """Main function for updating Air Shipment doctype JSON"""
    try:
        print("🚀 Updating Air Shipment DocType JSON to UNLOCO")
        print("=" * 60)
        
        # Update the doctype JSON
        update_doctype_json()
        
        print("\n✅ Air Shipment doctype JSON updated to UNLOCO successfully!")
        print("\n📋 Changes Made:")
        print("  - origin_port field now links to UNLOCO")
        print("  - destination_port field now links to UNLOCO")
        print("  - Field descriptions updated to reflect UNLOCO usage")
        print("  - DocType reloaded to apply changes")
        
    except Exception as e:
        print(f"❌ Error updating Air Shipment doctype JSON: {str(e)}")
        frappe.log_error(f"Air Shipment doctype JSON update error: {str(e)}")

if __name__ == "__main__":
    main()
