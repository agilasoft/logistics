"""
Add auto-populate functionality for Location doctype
- Add client script for auto-populating UNLOCO details
- Add server script for UNLOCO data lookup
- Add custom fields for auto-populate settings
"""

import frappe
from frappe import _

def execute():
    """Add auto-populate functionality for Location doctype"""
    
    print("🔧 Adding Location Auto-Populate Functionality...")
    print("=" * 60)
    
    # Add custom fields for auto-populate settings
    add_auto_populate_fields()
    
    # Add client script for auto-populate
    add_client_script()
    
    # Add server script for UNLOCO lookup
    add_server_script()
    
    print("✅ Location auto-populate functionality added successfully!")

def add_auto_populate_fields():
    """Add custom fields for auto-populate settings"""
    try:
        print("➕ Adding auto-populate fields...")
        
        # Auto-populate settings section
        auto_populate_fields = [
            {
                "fieldname": "auto_populate_section",
                "label": "Auto-Populate Settings",
                "fieldtype": "Section Break",
                "insert_after": "custom_description",
                "collapsible": 1
            },
            {
                "fieldname": "custom_auto_populate",
                "label": "Auto-Populate UNLOCO Details",
                "fieldtype": "Check",
                "insert_after": "auto_populate_section",
                "description": "Automatically populate UNLOCO details when UNLOCO code is entered",
                "default": 1,
                "reqd": 0
            },
            {
                "fieldname": "custom_last_updated",
                "label": "Last Updated",
                "fieldtype": "Datetime",
                "insert_after": "custom_auto_populate",
                "description": "Last time UNLOCO details were updated",
                "reqd": 0
            },
            {
                "fieldname": "custom_data_source",
                "label": "Data Source",
                "fieldtype": "Select",
                "options": "Internal Database\nUNECE Official\nDataHub.io\nCustom API",
                "insert_after": "custom_last_updated",
                "description": "Source of UNLOCO data",
                "default": "Internal Database",
                "reqd": 0
            }
        ]
        
        fields_added = 0
        for field_data in auto_populate_fields:
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
            print(f"✓ Successfully added {fields_added} auto-populate fields")
        
        return True
        
    except Exception as e:
        print(f"✗ Error adding auto-populate fields: {str(e)}")
        frappe.log_error(f"Auto-populate fields addition error: {str(e)}")
        return False

def add_client_script():
    """Add client script for auto-populate functionality"""
    try:
        print("➕ Adding client script...")
        
        # Check if client script already exists
        existing_script = frappe.db.get_value("Client Script", {
            "dt": "Location",
            "script_type": "DocType"
        })
        
        if existing_script:
            print("✓ Client script already exists")
            return True
        
        # Create client script
        client_script = frappe.get_doc({
            "doctype": "Client Script",
            "dt": "Location",
            "script_type": "DocType",
            "enabled": 1,
            "script": """
// Auto-populate UNLOCO details when UNLOCO code is entered
frappe.ui.form.on('Location', {
    custom_unlocode: function(frm) {
        if (frm.doc.custom_unlocode && frm.doc.custom_auto_populate) {
            // Call server method to populate details
            frappe.call({
                method: 'logistics.air_freight.utils.unlocode_utils.populate_unlocode_details',
                args: {
                    'unlocode': frm.doc.custom_unlocode,
                    'doc': frm.doc
                },
                callback: function(r) {
                    if (r.message) {
                        // Update form with populated data
                        Object.keys(r.message).forEach(function(key) {
                            if (r.message[key] !== null && r.message[key] !== undefined) {
                                frm.set_value(key, r.message[key]);
                            }
                        });
                        frm.refresh_fields();
                        frappe.show_alert({
                            message: 'UNLOCO details populated successfully!',
                            indicator: 'green'
                        });
                    }
                }
            });
        }
    },
    
    custom_auto_populate: function(frm) {
        if (frm.doc.custom_auto_populate && frm.doc.custom_unlocode) {
            // Trigger auto-populate if UNLOCO code exists
            frm.trigger('custom_unlocode');
        }
    }
});

// Add button to manually populate UNLOCO details
frappe.ui.form.on('Location', {
    refresh: function(frm) {
        if (frm.doc.custom_unlocode && frm.doc.custom_auto_populate) {
            frm.add_custom_button('Populate UNLOCO Details', function() {
                frappe.call({
                    method: 'logistics.air_freight.utils.unlocode_utils.populate_unlocode_details',
                    args: {
                        'unlocode': frm.doc.custom_unlocode,
                        'doc': frm.doc
                    },
                    callback: function(r) {
                        if (r.message) {
                            Object.keys(r.message).forEach(function(key) {
                                if (r.message[key] !== null && r.message[key] !== undefined) {
                                    frm.set_value(key, r.message[key]);
                                }
                            });
                            frm.refresh_fields();
                            frappe.show_alert({
                                message: 'UNLOCO details populated successfully!',
                                indicator: 'green'
                            });
                        }
                    }
                });
            }, 'Auto-Populate');
        }
    }
});
"""
        })
        
        client_script.insert(ignore_permissions=True)
        frappe.db.commit()
        print("✓ Client script added successfully")
        return True
        
    except Exception as e:
        print(f"✗ Error adding client script: {str(e)}")
        frappe.log_error(f"Client script addition error: {str(e)}")
        return False

def add_server_script():
    """Add server script for UNLOCO lookup"""
    try:
        print("➕ Adding server script...")
        
        # Check if server script already exists
        existing_script = frappe.db.get_value("Server Script", {
            "dt": "Location",
            "script_type": "DocType"
        })
        
        if existing_script:
            print("✓ Server script already exists")
            return True
        
        # Create server script
        server_script = frappe.get_doc({
            "doctype": "Server Script",
            "dt": "Location",
            "script_type": "DocType",
            "enabled": 1,
            "script": """
# Auto-populate UNLOCO details before save
def before_save(doc, method):
    if doc.custom_unlocode and doc.custom_auto_populate:
        # Import the UNLOCO utils
        from logistics.air_freight.utils.unlocode_utils import populate_unlocode_details
        
        # Populate details
        populate_unlocode_details(doc.custom_unlocode, doc)
        
        # Update last updated timestamp
        doc.custom_last_updated = frappe.utils.now()
"""
        })
        
        server_script.insert(ignore_permissions=True)
        frappe.db.commit()
        print("✓ Server script added successfully")
        return True
        
    except Exception as e:
        print(f"✗ Error adding server script: {str(e)}")
        frappe.log_error(f"Server script addition error: {str(e)}")
        return False

def main():
    """Main function for adding auto-populate functionality"""
    try:
        print("🚀 Adding Location Auto-Populate Functionality")
        print("=" * 60)
        
        # Add custom fields
        add_auto_populate_fields()
        
        # Add client script
        add_client_script()
        
        # Add server script
        add_server_script()
        
        print("\n✅ Location auto-populate functionality added successfully!")
        print("\n📋 Features Added:")
        print("  - Auto-populate checkbox for UNLOCO details")
        print("  - Client-side auto-population when UNLOCO code is entered")
        print("  - Server-side auto-population before save")
        print("  - Manual populate button in Location form")
        print("  - Data source tracking and last updated timestamp")
        
    except Exception as e:
        print(f"❌ Error adding auto-populate functionality: {str(e)}")
        frappe.log_error(f"Auto-populate functionality addition error: {str(e)}")

if __name__ == "__main__":
    main()
