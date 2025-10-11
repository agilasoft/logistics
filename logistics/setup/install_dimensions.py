# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def execute():
    """Install dimensions for logistics GL Entry integration"""
    
    print("Installing logistics dimensions...")
    
    # Define dimensions to create
    dimensions = [
        {
            "name": "Job Reference",
            "document_type": "Job Reference",
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
    
    return {
        "success": True,
        "created_count": created_count,
        "message": f"Created {created_count} dimensions successfully"
    }


def create_dimension_accounts():
    """Create dimension accounts for the dimensions"""
    
    print("Creating dimension accounts...")
    
    # Get all companies
    companies = frappe.get_all("Company", fields=["name"])
    
    for company in companies:
        company_name = company.name
        print(f"Processing company: {company_name}")
        
        # Create dimension accounts for each company
        dimension_accounts = [
            {
                "company": company_name,
                "account": "Job Reference",
                "dimension": "Job Reference"
            },
            {
                "company": company_name,
                "account": "Item",
                "dimension": "Item"
            },
            {
                "company": company_name,
                "account": "Profit Center", 
                "dimension": "Profit Center"
            }
        ]
        
        for da_config in dimension_accounts:
            try:
                # Check if dimension account already exists
                if frappe.db.exists("Accounting Dimension Account", {
                    "company": da_config["company"],
                    "account": da_config["account"]
                }):
                    print(f"  ✅ Dimension account '{da_config['account']}' already exists for {company_name}")
                    continue
                
                # Create dimension account
                da = frappe.new_doc("Accounting Dimension Account")
                da.update(da_config)
                da.insert()
                
                print(f"  ✅ Created dimension account: {da_config['account']} for {company_name}")
                
            except Exception as e:
                print(f"  ❌ Error creating dimension account '{da_config['account']}': {e}")
    
    frappe.db.commit()
    print("✅ Dimension accounts created successfully")


def verify_dimensions():
    """Verify that dimensions are properly configured"""
    
    print("Verifying dimensions...")
    
    dimensions = frappe.get_all("Accounting Dimension", 
        fields=["name", "document_type", "disabled"],
        filters={"name": ["in", ["Job Reference", "Item", "Profit Center"]]}
    )
    
    print(f"Found {len(dimensions)} dimensions:")
    for dim in dimensions:
        status = "Active" if not dim.disabled else "Disabled"
        print(f"  - {dim.name}: {dim.document_type} ({status})")
    
    return len(dimensions) == 3


if __name__ == "__main__":
    execute()













