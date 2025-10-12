"""
Create client script for UNLOCO doctype
- Add auto-populate functionality
- Add manual populate button
- Add form validation
"""

import frappe
from frappe import _

def execute():
    """Create client script for UNLOCO doctype"""
    
    print("🔧 Creating UNLOCO client script...")
    print("=" * 60)
    
    # Create client script for UNLOCO
    create_unlocode_client_script()
    
    print("✅ UNLOCO client script created successfully!")

def create_unlocode_client_script():
    """Create client script for UNLOCO doctype"""
    try:
        print("➕ Creating UNLOCO client script...")
        
        # Check if client script already exists
        existing_script = frappe.db.get_value("Client Script", {"dt": "UNLOCO"})
        
        if existing_script:
            print("✓ UNLOCO client script already exists")
            return True
        
        # Create client script
        client_script = frappe.get_doc({
            "doctype": "Client Script",
            "dt": "UNLOCO",
            "enabled": 1,
            "script": """
// Auto-populate UNLOCO details when UNLOCO code is entered
frappe.ui.form.on('UNLOCO', {
    unlocode: function(frm) {
        if (frm.doc.unlocode && frm.doc.auto_populate) {
            // Call server method to populate details
            frappe.call({
                method: 'logistics.air_freight.utils.unlocode_utils.populate_unlocode_details',
                args: {
                    'unlocode': frm.doc.unlocode
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
    
    auto_populate: function(frm) {
        if (frm.doc.auto_populate && frm.doc.unlocode) {
            // Trigger auto-populate if UNLOCO code exists
            frm.trigger('unlocode');
        }
    }
});

// Add custom button for manual populate
frappe.ui.form.on('UNLOCO', {
    refresh: function(frm) {
        if (frm.doc.unlocode && frm.doc.auto_populate) {
            frm.add_custom_button('Populate UNLOCO Details', function() {
                frappe.call({
                    method: 'logistics.air_freight.utils.unlocode_utils.populate_unlocode_details',
                    args: {
                        'unlocode': frm.doc.unlocode
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
frappe.ui.form.on('UNLOCO', {
    validate: function(frm) {
        if (frm.doc.unlocode && frm.doc.auto_populate) {
            // Validate UNLOCO code format
            if (frm.doc.unlocode.length !== 5) {
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
        print("✓ UNLOCO client script created successfully")
        return True
        
    except Exception as e:
        print(f"✗ Error creating UNLOCO client script: {str(e)}")
        frappe.log_error(f"UNLOCO client script creation error: {str(e)}")
        return False

def main():
    """Main function for creating UNLOCO client script"""
    try:
        print("🚀 Creating UNLOCO Client Script")
        print("=" * 60)
        
        # Create client script
        create_unlocode_client_script()
        
        print("\n✅ UNLOCO client script created successfully!")
        print("\n📋 Features Added:")
        print("  - Auto-populate when UNLOCO code is entered")
        print("  - Manual populate button")
        print("  - Form validation for UNLOCO code format")
        print("  - Success/error messages for user feedback")
        
    except Exception as e:
        print(f"❌ Error creating UNLOCO client script: {str(e)}")
        frappe.log_error(f"UNLOCO client script creation error: {str(e)}")

if __name__ == "__main__":
    main()
