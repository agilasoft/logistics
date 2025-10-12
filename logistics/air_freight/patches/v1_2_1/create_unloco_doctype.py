"""
Create UNLOCO DocType in the correct location
"""

import frappe
import os
import json

def execute():
    """Create UNLOCO DocType"""
    
    print("🌍 Creating UNLOCO DocType...")
    print("=" * 60)
    
    # Check if UNLOCO doctype already exists
    if frappe.db.exists("DocType", "UNLOCO"):
        print("✓ UNLOCO DocType already exists")
        return
    
    try:
        # Read the UNLOCO JSON file
        unloco_json_path = frappe.get_app_path("logistics", "logistics", "logistics", "doctype", "unloco", "unloco.json")
        
        if not os.path.exists(unloco_json_path):
            print(f"✗ UNLOCO JSON file not found at {unloco_json_path}")
            return
        
        with open(unloco_json_path, 'r') as f:
            unloco_data = json.load(f)
        
        # Create the UNLOCO DocType
        unloco_doctype = frappe.get_doc(unloco_data)
        unloco_doctype.insert(ignore_permissions=True)
        frappe.db.commit()
        
        print("✓ UNLOCO DocType created successfully")
        
        # Create the database table
        frappe.db.commit()
        print("✓ UNLOCO database table created")
        
    except Exception as e:
        print(f"✗ Error creating UNLOCO DocType: {str(e)}")
        frappe.log_error(f"UNLOCO DocType creation error: {str(e)}")
        raise

if __name__ == "__main__":
    execute()
