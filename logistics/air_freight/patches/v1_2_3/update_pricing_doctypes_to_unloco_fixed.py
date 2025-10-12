"""
Update Pricing Center doctypes to use UNLOCO instead of Location
- Transport Rate: Update location_type link filter
- Sales Quote: Update location_from and location_to fields
- Air Freight Rate: Update origin_port and destination_port fields
- Sea Freight Rate: Update origin_port and destination_port fields
"""

import frappe
import os
import json

def execute():
    """Update Pricing Center doctypes to use UNLOCO"""
    
    print("🔄 Updating Pricing Center doctypes to use UNLOCO...")
    print("=" * 60)
    
    # Update Transport Rate
    update_transport_rate()
    
    # Update Sales Quote
    update_sales_quote()
    
    # Update Air Freight Rate
    update_air_freight_rate()
    
    # Update Sea Freight Rate
    update_sea_freight_rate()
    
    print("✅ Pricing Center doctypes updated to use UNLOCO successfully!")

def update_transport_rate():
    """Update Transport Rate doctype to include UNLOCO in location_type options"""
    try:
        print("🔄 Updating Transport Rate doctype...")
        
        doctype_path = frappe.get_app_path("logistics", "logistics", "pricing_center", "doctype", "transport_rate", "transport_rate.json")
        
        if not os.path.exists(doctype_path):
            print(f"✗ Transport Rate doctype JSON not found at {doctype_path}")
            return
        
        with open(doctype_path, 'r') as f:
            doctype_json = json.load(f)
        
        # Update the location_type field to include UNLOCO
        for field in doctype_json.get("fields", []):
            if field.get("fieldname") == "location_type":
                # Update the link_filters to include UNLOCO
                field["link_filters"] = "[[\"DocType\",\"name\",\"in\",[\"Location\",\"Transport Zone\",\"UNLOCO\"]]]"
                print("✓ Updated Transport Rate location_type to include UNLOCO")
                break
        
        # Save the updated JSON
        with open(doctype_path, 'w') as f:
            json.dump(doctype_json, f, indent=1)
        
        # Reload the doctype
        frappe.reload_doc("logistics", "pricing_center", "transport_rate")
        print("✓ Transport Rate doctype updated and reloaded")
        
    except Exception as e:
        print(f"✗ Error updating Transport Rate: {str(e)}")
        frappe.log_error(f"Transport Rate update error: {str(e)}")

def update_sales_quote():
    """Update Sales Quote doctype to use UNLOCO for location fields"""
    try:
        print("🔄 Updating Sales Quote doctype...")
        
        doctype_path = frappe.get_app_path("logistics", "logistics", "pricing_center", "doctype", "sales_quote", "sales_quote.json")
        
        if not os.path.exists(doctype_path):
            print(f"✗ Sales Quote doctype JSON not found at {doctype_path}")
            return
        
        with open(doctype_path, 'r') as f:
            doctype_json = json.load(f)
        
        # Update location_from and location_to fields to use UNLOCO
        fields_updated = 0
        for field in doctype_json.get("fields", []):
            if field.get("fieldname") in ["location_from", "location_to"]:
                if field.get("options") == "Location":
                    field["options"] = "UNLOCO"
                    print(f"✓ Updated Sales Quote {field['fieldname']} to use UNLOCO")
                    fields_updated += 1
        
        if fields_updated > 0:
            # Save the updated JSON
            with open(doctype_path, 'w') as f:
                json.dump(doctype_json, f, indent=1)
            
            # Reload the doctype
            frappe.reload_doc("logistics", "pricing_center", "sales_quote")
            print(f"✓ Sales Quote doctype updated and reloaded ({fields_updated} fields)")
        else:
            print("✓ No changes needed for Sales Quote doctype")
        
    except Exception as e:
        print(f"✗ Error updating Sales Quote: {str(e)}")
        frappe.log_error(f"Sales Quote update error: {str(e)}")

def update_air_freight_rate():
    """Update Air Freight Rate doctype to use UNLOCO for port fields"""
    try:
        print("🔄 Updating Air Freight Rate doctype...")
        
        doctype_path = frappe.get_app_path("logistics", "logistics", "pricing_center", "doctype", "air_freight_rate", "air_freight_rate.json")
        
        if not os.path.exists(doctype_path):
            print(f"✗ Air Freight Rate doctype JSON not found at {doctype_path}")
            return
        
        with open(doctype_path, 'r') as f:
            doctype_json = json.load(f)
        
        # Update origin_port and destination_port fields to use UNLOCO
        fields_updated = 0
        for field in doctype_json.get("fields", []):
            if field.get("fieldname") in ["origin_port", "destination_port"]:
                if field.get("options") == "Location":
                    field["options"] = "UNLOCO"
                    print(f"✓ Updated Air Freight Rate {field['fieldname']} to use UNLOCO")
                    fields_updated += 1
        
        if fields_updated > 0:
            # Save the updated JSON
            with open(doctype_path, 'w') as f:
                json.dump(doctype_json, f, indent=1)
            
            # Reload the doctype
            frappe.reload_doc("logistics", "pricing_center", "air_freight_rate")
            print(f"✓ Air Freight Rate doctype updated and reloaded ({fields_updated} fields)")
        else:
            print("✓ No changes needed for Air Freight Rate doctype")
        
    except Exception as e:
        print(f"✗ Error updating Air Freight Rate: {str(e)}")
        frappe.log_error(f"Air Freight Rate update error: {str(e)}")

def update_sea_freight_rate():
    """Update Sea Freight Rate doctype to use UNLOCO for port fields"""
    try:
        print("🔄 Updating Sea Freight Rate doctype...")
        
        doctype_path = frappe.get_app_path("logistics", "logistics", "pricing_center", "doctype", "sea_freight_rate", "sea_freight_rate.json")
        
        if not os.path.exists(doctype_path):
            print(f"✗ Sea Freight Rate doctype JSON not found at {doctype_path}")
            return
        
        with open(doctype_path, 'r') as f:
            doctype_json = json.load(f)
        
        # Update origin_port and destination_port fields to use UNLOCO
        fields_updated = 0
        for field in doctype_json.get("fields", []):
            if field.get("fieldname") in ["origin_port", "destination_port"]:
                if field.get("options") == "Location":
                    field["options"] = "UNLOCO"
                    print(f"✓ Updated Sea Freight Rate {field['fieldname']} to use UNLOCO")
                    fields_updated += 1
        
        if fields_updated > 0:
            # Save the updated JSON
            with open(doctype_path, 'w') as f:
                json.dump(doctype_json, f, indent=1)
            
            # Reload the doctype
            frappe.reload_doc("logistics", "pricing_center", "sea_freight_rate")
            print(f"✓ Sea Freight Rate doctype updated and reloaded ({fields_updated} fields)")
        else:
            print("✓ No changes needed for Sea Freight Rate doctype")
        
    except Exception as e:
        print(f"✗ Error updating Sea Freight Rate: {str(e)}")
        frappe.log_error(f"Sea Freight Rate update error: {str(e)}")

if __name__ == "__main__":
    execute()
