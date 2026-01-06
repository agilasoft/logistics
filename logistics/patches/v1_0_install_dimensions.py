# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe


def execute():
    """Install dimensions for logistics GL Entry integration"""
    
    print("Installing logistics dimensions...")
    
    # Define dimensions to create
    dimensions = [
        {
            "name": "Job Costing Number",
            "document_type": "Job Costing Number",
            "disabled": 0,
            "is_mandatory": 0,
            "default_dimension": None,
            "company": None,
            "applicable_for": "GL Entry"
        },
        {
            "name": "Item",
            "document_type": "Item", 
            "disabled": 0,
            "is_mandatory": 0,
            "default_dimension": None,
            "company": None,
            "applicable_for": "GL Entry"
        },
        {
            "name": "Profit Center",
            "document_type": "Profit Center",
            "disabled": 0,
            "is_mandatory": 0,
            "default_dimension": None,
            "company": None,
            "applicable_for": "GL Entry"
        },
        {
            "name": "Branch",
            "document_type": "Branch",
            "disabled": 0,
            "is_mandatory": 0,
            "default_dimension": None,
            "company": None,
            "applicable_for": "GL Entry"
        }
    ]
    
    created_count = 0
    
    for dim_config in dimensions:
        try:
            # Check if dimension already exists
            if frappe.db.exists("Accounting Dimension", dim_config["name"]):
                print(f"✅ Dimension '{dim_config['name']}' already exists")
                continue
            
            # Create the dimension
            dimension = frappe.new_doc("Accounting Dimension")
            dimension.update(dim_config)
            dimension.insert()
            
            print(f"✅ Created dimension: {dim_config['name']}")
            created_count += 1
            
        except Exception as e:
            print(f"❌ Error creating dimension '{dim_config['name']}': {e}")
    
    frappe.db.commit()
    
    print(f"\\n✅ Successfully created {created_count} dimensions")
    print("\\nNext steps:")
    print("1. Go to Accounting > Accounting Dimensions")
    print("2. Configure the dimensions as needed")
    print("3. The hook functions will automatically populate these dimensions")
    
    return True













