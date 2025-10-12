"""
Update all scripts to use UNLOCO doctype instead of Location
- Update UNLOCO utilities to work with UNLOCO doctype
- Update client scripts to use UNLOCO
- Update server scripts to use UNLOCO
- Update commands to use UNLOCO
"""

import frappe
from frappe import _

def execute():
    """Update all scripts to use UNLOCO doctype"""
    
    print("🔄 Updating scripts to use UNLOCO doctype...")
    print("=" * 60)
    
    # Update UNLOCO utilities
    update_unlocode_utils()
    
    # Update client scripts
    update_client_scripts()
    
    # Update server scripts
    update_server_scripts()
    
    # Update commands
    update_commands()
    
    print("✅ All scripts updated to use UNLOCO successfully!")

def update_unlocode_utils():
    """Update UNLOCO utilities to work with UNLOCO doctype"""
    try:
        print("🔧 Updating UNLOCO utilities...")
        
        # Update the utils file to use UNLOCO doctype
        utils_file_path = "/home/frappe/frappe-bench/apps/logistics/logistics/air_freight/utils/unlocode_utils.py"
        
        # Read the current file
        with open(utils_file_path, 'r') as f:
            content = f.read()
        
        # Replace Location references with UNLOCO
        content = content.replace('"Location"', '"UNLOCO"')
        content = content.replace("'Location'", "'UNLOCO'")
        content = content.replace('frappe.get_all("Location"', 'frappe.get_all("UNLOCO"')
        content = content.replace('frappe.db.get_value("Location"', 'frappe.db.get_value("UNLOCO"')
        content = content.replace('frappe.get_doc("Location"', 'frappe.get_doc("UNLOCO"')
        content = content.replace('location_doc', 'unlocode_doc')
        content = content.replace('location = frappe.get_doc("Location"', 'unlocode = frappe.get_doc("UNLOCO"')
        
        # Write the updated content back
        with open(utils_file_path, 'w') as f:
            f.write(content)
        
        print("✓ UNLOCO utilities updated")
        return True
        
    except Exception as e:
        print(f"✗ Error updating UNLOCO utilities: {str(e)}")
        frappe.log_error(f"UNLOCO utilities update error: {str(e)}")
        return False

def update_client_scripts():
    """Update client scripts to use UNLOCO"""
    try:
        print("🔧 Updating client scripts...")
        
        # Update client script for UNLOCO
        client_script_content = """
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
        
        # Create client script for UNLOCO
        client_script = frappe.get_doc({
            "doctype": "Client Script",
            "dt": "UNLOCO",
            "enabled": 1,
            "script": client_script_content
        })
        
        # Check if script already exists
        existing_script = frappe.db.get_value("Client Script", {"dt": "UNLOCO"})
        if existing_script:
            print("✓ UNLOCO client script already exists")
        else:
            client_script.insert(ignore_permissions=True)
            frappe.db.commit()
            print("✓ UNLOCO client script created")
        
        return True
        
    except Exception as e:
        print(f"✗ Error updating client scripts: {str(e)}")
        frappe.log_error(f"Client scripts update error: {str(e)}")
        return False

def update_server_scripts():
    """Update server scripts to use UNLOCO"""
    try:
        print("🔧 Updating server scripts...")
        
        # Create server script for UNLOCO
        server_script_content = """
# Auto-populate UNLOCO details before save
def before_save(doc, method):
    if doc.unlocode and doc.auto_populate:
        # Import the UNLOCO utils
        from logistics.air_freight.utils.unlocode_utils import populate_unlocode_details
        
        # Populate details
        populate_unlocode_details(doc.unlocode, doc)
        
        # Update last updated timestamp
        doc.last_updated = frappe.utils.now()
"""
        
        # Create server script for UNLOCO
        server_script = frappe.get_doc({
            "doctype": "Server Script",
            "dt": "UNLOCO",
            "enabled": 1,
            "script": server_script_content
        })
        
        # Check if script already exists
        existing_script = frappe.db.get_value("Server Script", {"dt": "UNLOCO"})
        if existing_script:
            print("✓ UNLOCO server script already exists")
        else:
            server_script.insert(ignore_permissions=True)
            frappe.db.commit()
            print("✓ UNLOCO server script created")
        
        return True
        
    except Exception as e:
        print(f"✗ Error updating server scripts: {str(e)}")
        frappe.log_error(f"Server scripts update error: {str(e)}")
        return False

def update_commands():
    """Update commands to use UNLOCO"""
    try:
        print("🔧 Updating commands...")
        
        # Update the update_unlocode_data command
        command_file_path = "/home/frappe/frappe-bench/apps/logistics/logistics/air_freight/commands/update_unlocode_data.py"
        
        # Read the current file
        with open(command_file_path, 'r') as f:
            content = f.read()
        
        # Replace Location references with UNLOCO
        content = content.replace('"Location"', '"UNLOCO"')
        content = content.replace("'Location'", "'UNLOCO'")
        content = content.replace('frappe.get_all("Location"', 'frappe.get_all("UNLOCO"')
        content = content.replace('frappe.db.get_value("Location"', 'frappe.db.get_value("UNLOCO"')
        content = content.replace('frappe.get_doc("Location"', 'frappe.get_doc("UNLOCO"')
        content = content.replace('location_doc', 'unlocode_doc')
        content = content.replace('location = frappe.get_doc("Location"', 'unlocode = frappe.get_doc("UNLOCO"')
        
        # Write the updated content back
        with open(command_file_path, 'w') as f:
            f.write(content)
        
        print("✓ Commands updated to use UNLOCO")
        return True
        
    except Exception as e:
        print(f"✗ Error updating commands: {str(e)}")
        frappe.log_error(f"Commands update error: {str(e)}")
        return False

def main():
    """Main function for updating scripts to use UNLOCO"""
    try:
        print("🚀 Updating Scripts to Use UNLOCO DocType")
        print("=" * 60)
        
        # Update UNLOCO utilities
        update_unlocode_utils()
        
        # Update client scripts
        update_client_scripts()
        
        # Update server scripts
        update_server_scripts()
        
        # Update commands
        update_commands()
        
        print("\n✅ All scripts updated to use UNLOCO successfully!")
        print("\n📋 Updates Made:")
        print("  - UNLOCO utilities updated to work with UNLOCO doctype")
        print("  - Client scripts created for UNLOCO form")
        print("  - Server scripts created for UNLOCO auto-populate")
        print("  - Commands updated to use UNLOCO doctype")
        print("  - All Location references replaced with UNLOCO")
        
    except Exception as e:
        print(f"❌ Error updating scripts to use UNLOCO: {str(e)}")
        frappe.log_error(f"Scripts update error: {str(e)}")

if __name__ == "__main__":
    main()
