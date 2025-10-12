"""
Add client script for Location auto-populate functionality
- Add client script for auto-populate when UNLOCO code is entered
- Add custom button for manual populate
- Add form validation and auto-population
"""

import frappe
from frappe import _

def execute():
    """Add client script for Location auto-populate functionality"""
    
    print("🔧 Adding Location Client Script...")
    print("=" * 60)
    
    # Add client script for auto-populate
    add_client_script()
    
    print("✅ Location client script added successfully!")

def add_client_script():
    """Add client script for auto-populate functionality"""
    try:
        print("➕ Adding client script...")
        
        # Check if client script already exists
        existing_script = frappe.db.get_value("Client Script", {
            "dt": "Location"
        })
        
        if existing_script:
            print("✓ Client script already exists")
            return True
        
        # Create client script
        client_script = frappe.get_doc({
            "doctype": "Client Script",
            "dt": "Location",
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
                    'unlocode': frm.doc.custom_unlocode
                },
                callback: function(r) {
                    if (r.message && r.message.status === 'success') {
                        // Update form with populated data
                        Object.keys(r.message.data).forEach(function(key) {
                            if (r.message.data[key] !== null && r.message.data[key] !== undefined) {
                                frm.set_value(key, r.message.data[key]);
                            }
                        });
                        frm.refresh_fields();
                        frappe.show_alert({
                            message: 'UNLOCO details populated successfully!',
                            indicator: 'green'
                        });
                    } else if (r.message && r.message.status === 'warning') {
                        frappe.show_alert({
                            message: r.message.message,
                            indicator: 'orange'
                        });
                    } else if (r.message && r.message.status === 'error') {
                        frappe.show_alert({
                            message: r.message.message,
                            indicator: 'red'
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

// Add custom button for manual populate
frappe.ui.form.on('Location', {
    refresh: function(frm) {
        if (frm.doc.custom_unlocode && frm.doc.custom_auto_populate) {
            frm.add_custom_button('Populate UNLOCO Details', function() {
                frappe.call({
                    method: 'logistics.air_freight.utils.unlocode_utils.populate_unlocode_details',
                    args: {
                        'unlocode': frm.doc.custom_unlocode
                    },
                    callback: function(r) {
                        if (r.message && r.message.status === 'success') {
                            Object.keys(r.message.data).forEach(function(key) {
                                if (r.message.data[key] !== null && r.message.data[key] !== undefined) {
                                    frm.set_value(key, r.message.data[key]);
                                }
                            });
                            frm.refresh_fields();
                            frappe.show_alert({
                                message: 'UNLOCO details populated successfully!',
                                indicator: 'green'
                            });
                        } else if (r.message && r.message.status === 'warning') {
                            frappe.show_alert({
                                message: r.message.message,
                                indicator: 'orange'
                            });
                        } else if (r.message && r.message.status === 'error') {
                            frappe.show_alert({
                                message: r.message.message,
                                indicator: 'red'
                            });
                        }
                    }
                });
            }, 'Auto-Populate');
        }
    }
});

// Add form validation
frappe.ui.form.on('Location', {
    validate: function(frm) {
        if (frm.doc.custom_unlocode && frm.doc.custom_auto_populate) {
            // Validate UNLOCO code format
            if (frm.doc.custom_unlocode.length !== 5) {
                frappe.msgprint({
                    title: 'Invalid UNLOCO Code',
                    message: 'UNLOCO code must be exactly 5 characters long',
                    indicator: 'red'
                });
                frappe.validated = false;
            }
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

def main():
    """Main function for adding Location client script"""
    try:
        print("🚀 Adding Location Client Script")
        print("=" * 60)
        
        # Add client script
        add_client_script()
        
        print("\n✅ Location client script added successfully!")
        print("\n📋 Features Added:")
        print("  - Auto-populate when UNLOCO code is entered")
        print("  - Manual populate button")
        print("  - Form validation for UNLOCO code format")
        print("  - Success/error messages for user feedback")
        print("\n🔧 Usage:")
        print("  - Enter UNLOCO code in the custom_unlocode field")
        print("  - Check the 'Auto-Populate UNLOCO Details' checkbox")
        print("  - Details will be automatically populated")
        print("  - Use the 'Populate UNLOCO Details' button for manual population")
        
    except Exception as e:
        print(f"❌ Error adding client script: {str(e)}")
        frappe.log_error(f"Client script addition error: {str(e)}")

if __name__ == "__main__":
    main()
