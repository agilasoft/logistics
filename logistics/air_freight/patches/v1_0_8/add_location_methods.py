"""
Add custom methods for Location auto-populate functionality
- Add custom method for UNLOCO lookup
- Add custom method for auto-populate
- Add custom method for manual populate
"""

import frappe
from frappe import _

def execute():
    """Add custom methods for Location auto-populate functionality"""
    
    print("🔧 Adding Location Auto-Populate Methods...")
    print("=" * 60)
    
    # Add custom method for UNLOCO lookup
    add_unlocode_lookup_method()
    
    # Add custom method for auto-populate
    add_auto_populate_method()
    
    # Add custom method for manual populate
    add_manual_populate_method()
    
    print("✅ Location auto-populate methods added successfully!")

def add_unlocode_lookup_method():
    """Add custom method for UNLOCO lookup"""
    try:
        print("➕ Adding UNLOCO lookup method...")
        
        # Check if method already exists
        existing_method = frappe.db.get_value("Custom Method", {
            "dt": "Location",
            "method_name": "lookup_unlocode"
        })
        
        if existing_method:
            print("✓ UNLOCO lookup method already exists")
            return True
        
        # Create custom method
        custom_method = frappe.get_doc({
            "doctype": "Custom Method",
            "dt": "Location",
            "method_name": "lookup_unlocode",
            "enabled": 1,
            "script": """
# UNLOCO lookup method
@frappe.whitelist()
def lookup_unlocode(unlocode):
    \"\"\"
    Look up UNLOCO details for a given code
    
    Args:
        unlocode: UNLOCO code (e.g., "USLAX")
    
    Returns:
        Dictionary of UNLOCO details
    \"\"\"
    try:
        from logistics.air_freight.utils.unlocode_utils import populate_unlocode_details
        
        # Get UNLOCO details
        details = populate_unlocode_details(unlocode)
        
        return {
            "status": "success",
            "data": details
        }
        
    except Exception as e:
        frappe.log_error(f"UNLOCO lookup error: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
"""
        })
        
        custom_method.insert(ignore_permissions=True)
        frappe.db.commit()
        print("✓ UNLOCO lookup method added successfully")
        return True
        
    except Exception as e:
        print(f"✗ Error adding UNLOCO lookup method: {str(e)}")
        frappe.log_error(f"UNLOCO lookup method addition error: {str(e)}")
        return False

def add_auto_populate_method():
    """Add custom method for auto-populate"""
    try:
        print("➕ Adding auto-populate method...")
        
        # Check if method already exists
        existing_method = frappe.db.get_value("Custom Method", {
            "dt": "Location",
            "method_name": "auto_populate_unlocode"
        })
        
        if existing_method:
            print("✓ Auto-populate method already exists")
            return True
        
        # Create custom method
        custom_method = frappe.get_doc({
            "doctype": "Custom Method",
            "dt": "Location",
            "method_name": "auto_populate_unlocode",
            "enabled": 1,
            "script": """
# Auto-populate UNLOCO method
@frappe.whitelist()
def auto_populate_unlocode(doc):
    \"\"\"
    Auto-populate UNLOCO details for a location
    
    Args:
        doc: Location document
    
    Returns:
        Dictionary of populated fields
    \"\"\"
    try:
        from logistics.air_freight.utils.unlocode_utils import populate_unlocode_details
        
        if not doc.get('custom_unlocode'):
            return {
                "status": "error",
                "message": "No UNLOCO code provided"
            }
        
        # Get UNLOCO details
        details = populate_unlocode_details(doc['custom_unlocode'])
        
        if details:
            # Update document with populated details
            for field_name, field_value in details.items():
                if field_name in doc:
                    doc[field_name] = field_value
            
            # Update last updated timestamp
            doc['custom_last_updated'] = frappe.utils.now()
            
            return {
                "status": "success",
                "data": details,
                "message": "UNLOCO details populated successfully"
            }
        else:
            return {
                "status": "warning",
                "message": "No UNLOCO data found for the provided code"
            }
        
    except Exception as e:
        frappe.log_error(f"Auto-populate UNLOCO error: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
"""
        })
        
        custom_method.insert(ignore_permissions=True)
        frappe.db.commit()
        print("✓ Auto-populate method added successfully")
        return True
        
    except Exception as e:
        print(f"✗ Error adding auto-populate method: {str(e)}")
        frappe.log_error(f"Auto-populate method addition error: {str(e)}")
        return False

def add_manual_populate_method():
    """Add custom method for manual populate"""
    try:
        print("➕ Adding manual populate method...")
        
        # Check if method already exists
        existing_method = frappe.db.get_value("Custom Method", {
            "dt": "Location",
            "method_name": "manual_populate_unlocode"
        })
        
        if existing_method:
            print("✓ Manual populate method already exists")
            return True
        
        # Create custom method
        custom_method = frappe.get_doc({
            "doctype": "Custom Method",
            "dt": "Location",
            "method_name": "manual_populate_unlocode",
            "enabled": 1,
            "script": """
# Manual populate UNLOCO method
@frappe.whitelist()
def manual_populate_unlocode(doc_name, unlocode):
    \"\"\"
    Manually populate UNLOCO details for a location
    
    Args:
        doc_name: Location document name
        unlocode: UNLOCO code
    
    Returns:
        Dictionary of populated fields
    \"\"\"
    try:
        from logistics.air_freight.utils.unlocode_utils import populate_unlocode_details
        
        # Get the location document
        location = frappe.get_doc("Location", doc_name)
        
        if not location:
            return {
                "status": "error",
                "message": "Location not found"
            }
        
        # Get UNLOCO details
        details = populate_unlocode_details(unlocode)
        
        if details:
            # Update document with populated details
            for field_name, field_value in details.items():
                if hasattr(location, field_name):
                    setattr(location, field_name, field_value)
            
            # Update last updated timestamp
            location.custom_last_updated = frappe.utils.now()
            
            # Save the document
            location.save(ignore_permissions=True)
            frappe.db.commit()
            
            return {
                "status": "success",
                "data": details,
                "message": "UNLOCO details populated and saved successfully"
            }
        else:
            return {
                "status": "warning",
                "message": "No UNLOCO data found for the provided code"
            }
        
    except Exception as e:
        frappe.log_error(f"Manual populate UNLOCO error: {str(e)}")
        return {
            "status": "error",
            "message": str(e)
        }
"""
        })
        
        custom_method.insert(ignore_permissions=True)
        frappe.db.commit()
        print("✓ Manual populate method added successfully")
        return True
        
    except Exception as e:
        print(f"✗ Error adding manual populate method: {str(e)}")
        frappe.log_error(f"Manual populate method addition error: {str(e)}")
        return False

def main():
    """Main function for adding Location auto-populate methods"""
    try:
        print("🚀 Adding Location Auto-Populate Methods")
        print("=" * 60)
        
        # Add custom methods
        add_unlocode_lookup_method()
        add_auto_populate_method()
        add_manual_populate_method()
        
        print("\n✅ Location auto-populate methods added successfully!")
        print("\n📋 Methods Added:")
        print("  - lookup_unlocode: Look up UNLOCO details for a code")
        print("  - auto_populate_unlocode: Auto-populate UNLOCO details")
        print("  - manual_populate_unlocode: Manually populate UNLOCO details")
        print("\n🔧 Usage:")
        print("  - Call these methods from client-side JavaScript")
        print("  - Use in custom buttons or form events")
        print("  - Integrate with Location form for auto-population")
        
    except Exception as e:
        print(f"❌ Error adding auto-populate methods: {str(e)}")
        frappe.log_error(f"Auto-populate methods addition error: {str(e)}")

if __name__ == "__main__":
    main()
