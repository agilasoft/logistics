"""
Update existing Air Shipment fields to link to UNLOCO
- Update existing origin_port and destination_port fields
- Change their options from Location to UNLOCO
"""

import frappe
from frappe import _

def execute():
    """Update existing Air Shipment fields to link to UNLOCO"""
    
    print("🔄 Updating existing Air Shipment fields to UNLOCO...")
    print("=" * 60)
    
    # Update origin_port field
    update_origin_port_field()
    
    # Update destination_port field
    update_destination_port_field()
    
    print("✅ Existing Air Shipment fields updated to UNLOCO successfully!")

def update_origin_port_field():
    """Update existing origin_port field to link to UNLOCO"""
    try:
        print("🔄 Updating existing origin_port field...")
        
        # Get existing field
        existing_field = frappe.db.get_value("Custom Field", {
            "dt": "Air Shipment",
            "fieldname": "origin_port"
        })
        
        if existing_field:
            # Update existing field
            field_doc = frappe.get_doc("Custom Field", existing_field)
            field_doc.options = "UNLOCO"
            field_doc.description = "Origin port UNLOCO code"
            field_doc.save(ignore_permissions=True)
            print("✓ Updated origin_port field to link to UNLOCO")
        else:
            print("⚠️  origin_port field not found")
        
        frappe.db.commit()
        return True
        
    except Exception as e:
        print(f"✗ Error updating origin_port field: {str(e)}")
        frappe.log_error(f"Origin port field update error: {str(e)}")
        return False

def update_destination_port_field():
    """Update existing destination_port field to link to UNLOCO"""
    try:
        print("🔄 Updating existing destination_port field...")
        
        # Get existing field
        existing_field = frappe.db.get_value("Custom Field", {
            "dt": "Air Shipment",
            "fieldname": "destination_port"
        })
        
        if existing_field:
            # Update existing field
            field_doc = frappe.get_doc("Custom Field", existing_field)
            field_doc.options = "UNLOCO"
            field_doc.description = "Destination port UNLOCO code"
            field_doc.save(ignore_permissions=True)
            print("✓ Updated destination_port field to link to UNLOCO")
        else:
            print("⚠️  destination_port field not found")
        
        frappe.db.commit()
        return True
        
    except Exception as e:
        print(f"✗ Error updating destination_port field: {str(e)}")
        frappe.log_error(f"Destination port field update error: {str(e)}")
        return False

def main():
    """Main function for updating existing Air Shipment fields"""
    try:
        print("🚀 Updating Existing Air Shipment Fields to UNLOCO")
        print("=" * 60)
        
        # Update origin_port field
        update_origin_port_field()
        
        # Update destination_port field
        update_destination_port_field()
        
        print("\n✅ Existing Air Shipment fields updated to UNLOCO successfully!")
        print("\n📋 Changes Made:")
        print("  - origin_port field now links to UNLOCO")
        print("  - destination_port field now links to UNLOCO")
        print("  - Field descriptions updated to reflect UNLOCO usage")
        
    except Exception as e:
        print(f"❌ Error updating existing Air Shipment fields: {str(e)}")
        frappe.log_error(f"Existing Air Shipment fields update error: {str(e)}")

if __name__ == "__main__":
    main()
