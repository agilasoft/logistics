# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Bench Command: Create UOM Records for Capacity Management
=========================================================

This command creates the necessary UOM (Unit of Measure) records for capacity management.

Usage:
    bench --site your-site execute logistics.warehousing.commands.create_uom_records.create_uom_records
"""

import frappe


def create_uom_records():
    """Create UOM records for capacity management"""
    
    print("🚀 Creating UOM records for capacity management...")
    
    # UOM records to create
    uom_records = [
        {"uom_name": "CBM", "must_be_whole_number": 0},
        {"uom_name": "Kg", "must_be_whole_number": 0},
        {"uom_name": "M", "must_be_whole_number": 0},
        {"uom_name": "CM", "must_be_whole_number": 0},
        {"uom_name": "MM", "must_be_whole_number": 0},
    ]
    
    for uom_data in uom_records:
        try:
            # Check if UOM already exists
            if frappe.db.exists("UOM", uom_data["uom_name"]):
                print(f"  ℹ️  UOM {uom_data['uom_name']} already exists")
                continue
            
            # Create UOM record
            uom_doc = frappe.get_doc({
                "doctype": "UOM",
                "uom_name": uom_data["uom_name"],
                "must_be_whole_number": uom_data["must_be_whole_number"]
            })
            uom_doc.insert(ignore_permissions=True)
            print(f"  ✅ Created UOM: {uom_data['uom_name']}")
            
        except Exception as e:
            print(f"  ⚠️  Error creating UOM {uom_data['uom_name']}: {str(e)}")
    
    frappe.db.commit()
    print("✅ UOM records creation completed!")
