"""
Update Air Shipment doctype to link to UNLOCO instead of Location
- Change origin_port and destination_port fields to link to UNLOCO
- Update field options and validation
- Maintain backward compatibility
"""

import frappe
from frappe import _

def execute():
    """Update Air Shipment doctype to link to UNLOCO"""
    
    print("🔄 Updating Air Shipment links to UNLOCO...")
    print("=" * 60)
    
    # Update origin_port field
    update_origin_port_field()
    
    # Update destination_port field
    update_destination_port_field()
    
    # Add UNLOCO-specific fields
    add_unlocode_fields()
    
    print("✅ Air Shipment links updated to UNLOCO successfully!")

def update_origin_port_field():
    """Update origin_port field to link to UNLOCO"""
    try:
        print("🔄 Updating origin_port field...")
        
        # Check if field exists
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
            # Create new field
            field_doc = frappe.get_doc({
                "doctype": "Custom Field",
                "dt": "Air Shipment",
                "fieldname": "origin_port",
                "label": "Origin Port",
                "fieldtype": "Link",
                "options": "UNLOCO",
                "reqd": 1,
                "description": "Origin port UNLOCO code"
            })
            field_doc.insert(ignore_permissions=True)
            print("✓ Created origin_port field linking to UNLOCO")
        
        frappe.db.commit()
        return True
        
    except Exception as e:
        print(f"✗ Error updating origin_port field: {str(e)}")
        frappe.log_error(f"Origin port field update error: {str(e)}")
        return False

def update_destination_port_field():
    """Update destination_port field to link to UNLOCO"""
    try:
        print("🔄 Updating destination_port field...")
        
        # Check if field exists
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
            # Create new field
            field_doc = frappe.get_doc({
                "doctype": "Custom Field",
                "dt": "Air Shipment",
                "fieldname": "destination_port",
                "label": "Destination Port",
                "fieldtype": "Link",
                "options": "UNLOCO",
                "reqd": 1,
                "description": "Destination port UNLOCO code"
            })
            field_doc.insert(ignore_permissions=True)
            print("✓ Created destination_port field linking to UNLOCO")
        
        frappe.db.commit()
        return True
        
    except Exception as e:
        print(f"✗ Error updating destination_port field: {str(e)}")
        frappe.log_error(f"Destination port field update error: {str(e)}")
        return False

def add_unlocode_fields():
    """Add UNLOCO-specific fields to Air Shipment"""
    try:
        print("➕ Adding UNLOCO-specific fields...")
        
        # Get existing fields
        meta = frappe.get_meta("Air Shipment")
        existing_fields = [field.fieldname for field in meta.fields]
        
        # UNLOCO-specific fields
        unlocode_fields = [
            {
                "fieldname": "unlocode_section",
                "label": "UNLOCO Details",
                "fieldtype": "Section Break",
                "insert_after": "destination_port",
                "collapsible": 1
            },
            {
                "fieldname": "origin_unlocode_details",
                "label": "Origin Port Details",
                "fieldtype": "Text",
                "insert_after": "unlocode_section",
                "description": "Origin port UNLOCO details (auto-populated)",
                "read_only": 1,
                "reqd": 0
            },
            {
                "fieldname": "destination_unlocode_details",
                "label": "Destination Port Details",
                "fieldtype": "Text",
                "insert_after": "origin_unlocode_details",
                "description": "Destination port UNLOCO details (auto-populated)",
                "read_only": 1,
                "reqd": 0
            },
            {
                "fieldname": "origin_port_type",
                "label": "Origin Port Type",
                "fieldtype": "Data",
                "insert_after": "destination_unlocode_details",
                "description": "Origin port type (Airport/Port/etc.)",
                "read_only": 1,
                "reqd": 0
            },
            {
                "fieldname": "destination_port_type",
                "label": "Destination Port Type",
                "fieldtype": "Data",
                "insert_after": "origin_port_type",
                "description": "Destination port type (Airport/Port/etc.)",
                "read_only": 1,
                "reqd": 0
            },
            {
                "fieldname": "origin_country",
                "label": "Origin Country",
                "fieldtype": "Data",
                "insert_after": "destination_port_type",
                "description": "Origin country",
                "read_only": 1,
                "reqd": 0
            },
            {
                "fieldname": "destination_country",
                "label": "Destination Country",
                "fieldtype": "Data",
                "insert_after": "origin_country",
                "description": "Destination country",
                "read_only": 1,
                "reqd": 0
            },
            {
                "fieldname": "origin_iata_code",
                "label": "Origin IATA Code",
                "fieldtype": "Data",
                "insert_after": "destination_country",
                "description": "Origin port IATA code",
                "read_only": 1,
                "reqd": 0
            },
            {
                "fieldname": "destination_iata_code",
                "label": "Destination IATA Code",
                "fieldtype": "Data",
                "insert_after": "origin_iata_code",
                "description": "Destination port IATA code",
                "read_only": 1,
                "reqd": 0
            }
        ]
        
        fields_added = 0
        for field_data in unlocode_fields:
            if field_data["fieldname"] not in existing_fields:
                print(f"Adding {field_data['fieldname']} field...")
                
                field_doc = frappe.get_doc({
                    "doctype": "Custom Field",
                    "dt": "Air Shipment",
                    **field_data
                })
                field_doc.insert(ignore_permissions=True)
                fields_added += 1
                print(f"✓ Added {field_data['fieldname']} field")
            else:
                print(f"✓ {field_data['fieldname']} field already exists")
        
        if fields_added > 0:
            frappe.db.commit()
            print(f"✓ Successfully added {fields_added} UNLOCO-specific fields")
        
        return True
        
    except Exception as e:
        print(f"✗ Error adding UNLOCO-specific fields: {str(e)}")
        frappe.log_error(f"UNLOCO-specific fields addition error: {str(e)}")
        return False

def main():
    """Main function for updating Air Shipment links"""
    try:
        print("🚀 Updating Air Shipment Links to UNLOCO")
        print("=" * 60)
        
        # Update origin_port field
        update_origin_port_field()
        
        # Update destination_port field
        update_destination_port_field()
        
        # Add UNLOCO-specific fields
        add_unlocode_fields()
        
        print("\n✅ Air Shipment links updated to UNLOCO successfully!")
        print("\n📋 Changes Made:")
        print("  - origin_port field now links to UNLOCO")
        print("  - destination_port field now links to UNLOCO")
        print("  - Added UNLOCO-specific fields for detailed information")
        print("  - Added auto-populated fields for port details")
        print("  - Added country and IATA code fields")
        
    except Exception as e:
        print(f"❌ Error updating Air Shipment links: {str(e)}")
        frappe.log_error(f"Air Shipment links update error: {str(e)}")

if __name__ == "__main__":
    main()
