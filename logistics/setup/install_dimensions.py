# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute():
    """Install accounting dimensions for logistics integration"""
    
    print("Installing logistics accounting dimensions...")
    
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
    
    print(f"\\n✅ Successfully created {created_count} accounting dimensions")
    print("\\nERPNext will automatically:")
    print("1. Add dimension fields to GL Entry and other relevant doctypes")
    print("2. Populate dimensions in GL entries when transactions are created")
    print("3. Enable dimension-wise reporting and analysis")
    print("\\nNext steps:")
    print("1. Go to Accounting > Accounting Dimensions to configure settings")
    print("2. Set default dimensions for companies if needed")
    print("3. Configure mandatory dimensions for specific accounts if required")
    
    return {
        "success": True,
        "created_count": created_count,
        "message": f"Created {created_count} accounting dimensions successfully"
    }


if __name__ == "__main__":
    execute()













