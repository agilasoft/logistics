# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def setup_bir_2307_fields():
    """
    Setup custom fields required for BIR Form 2307 compliance.
    This adds necessary fields to Sales Invoice, Purchase Invoice, and related doctypes.
    """
    
    # Custom fields for Sales Invoice (for withholding tax certificates issued)
    sales_invoice_fields = {
        "Sales Invoice": [
            {
                "fieldname": "bir_2307_section",
                "label": "BIR 2307 Details",
                "fieldtype": "Section Break",
                "insert_after": "taxes_and_charges",
                "collapsible": 1
            },
            {
                "fieldname": "payee_tin",
                "label": "Payee TIN",
                "fieldtype": "Data",
                "insert_after": "bir_2307_section",
                "description": "Customer's Tax Identification Number"
            },
            {
                "fieldname": "payee_branch_code",
                "label": "Payee Branch Code",
                "fieldtype": "Data",
                "insert_after": "payee_tin",
                "description": "Customer's Branch Code (if applicable)"
            },
            {
                "fieldname": "column_break_bir1",
                "fieldtype": "Column Break",
                "insert_after": "payee_branch_code"
            },
            {
                "fieldname": "payor_tin",
                "label": "Payor TIN",
                "fieldtype": "Data",
                "insert_after": "column_break_bir1",
                "description": "Company's Tax Identification Number"
            },
            {
                "fieldname": "payor_branch_code",
                "label": "Payor Branch Code",
                "fieldtype": "Data",
                "insert_after": "payor_tin",
                "description": "Company's Branch Code (if applicable)"
            }
        ]
    }
    
    # Custom fields for Sales Taxes and Charges (withholding tax line items)
    tax_fields = {
        "Sales Taxes and Charges": [
            {
                "fieldname": "atc_code",
                "label": "ATC Code",
                "fieldtype": "Link",
                "options": "ATC Code",
                "insert_after": "account_head",
                "description": "Alphanumeric Tax Code as per BIR"
            },
            {
                "fieldname": "nature_of_income",
                "label": "Nature of Income",
                "fieldtype": "Data",
                "insert_after": "atc_code",
                "description": "Description of the nature of income payment"
            },
            {
                "fieldname": "is_withholding_tax",
                "label": "Is Withholding Tax",
                "fieldtype": "Check",
                "insert_after": "nature_of_income",
                "description": "Check if this is a withholding tax entry"
            }
        ],
        "Purchase Taxes and Charges": [
            {
                "fieldname": "atc_code",
                "label": "ATC Code",
                "fieldtype": "Link",
                "options": "ATC Code",
                "insert_after": "account_head",
                "description": "Alphanumeric Tax Code as per BIR"
            },
            {
                "fieldname": "nature_of_income",
                "label": "Nature of Income",
                "fieldtype": "Data",
                "insert_after": "atc_code",
                "description": "Description of the nature of income payment"
            },
            {
                "fieldname": "is_withholding_tax",
                "label": "Is Withholding Tax",
                "fieldtype": "Check",
                "insert_after": "nature_of_income",
                "description": "Check if this is a withholding tax entry"
            }
        ]
    }
    
    # Custom fields for Purchase Invoice (for withholding tax received)
    purchase_invoice_fields = {
        "Purchase Invoice": [
            {
                "fieldname": "bir_2307_section",
                "label": "BIR 2307 Details",
                "fieldtype": "Section Break",
                "insert_after": "taxes_and_charges",
                "collapsible": 1
            },
            {
                "fieldname": "payor_tin",
                "label": "Payor TIN",
                "fieldtype": "Data",
                "insert_after": "bir_2307_section",
                "description": "Supplier's Tax Identification Number"
            },
            {
                "fieldname": "payor_branch_code",
                "label": "Payor Branch Code",
                "fieldtype": "Data",
                "insert_after": "payor_tin",
                "description": "Supplier's Branch Code (if applicable)"
            },
            {
                "fieldname": "column_break_bir2",
                "fieldtype": "Column Break",
                "insert_after": "payor_branch_code"
            },
            {
                "fieldname": "payee_tin",
                "label": "Payee TIN",
                "fieldtype": "Data",
                "insert_after": "column_break_bir2",
                "description": "Company's Tax Identification Number"
            },
            {
                "fieldname": "payee_branch_code",
                "label": "Payee Branch Code",
                "fieldtype": "Data",
                "insert_after": "payee_tin",
                "description": "Company's Branch Code (if applicable)"
            }
        ]
    }
    
    # Custom fields for Company (to store TIN and Branch Code)
    company_fields = {
        "Company": [
            {
                "fieldname": "bir_details_section",
                "label": "BIR Details",
                "fieldtype": "Section Break",
                "insert_after": "default_finance_book",
                "collapsible": 1
            },
            {
                "fieldname": "tin",
                "label": "TIN (Tax Identification Number)",
                "fieldtype": "Data",
                "insert_after": "bir_details_section",
                "description": "Company's Tax Identification Number"
            },
            {
                "fieldname": "branch_code",
                "label": "Branch Code",
                "fieldtype": "Data",
                "insert_after": "tin",
                "description": "Company's Branch Code (if applicable)"
            }
        ]
    }
    
    # Custom fields for Customer (to store TIN and Branch Code)
    customer_fields = {
        "Customer": [
            {
                "fieldname": "bir_details_section",
                "label": "BIR Details",
                "fieldtype": "Section Break",
                "insert_after": "more_info",
                "collapsible": 1
            },
            {
                "fieldname": "tin",
                "label": "TIN (Tax Identification Number)",
                "fieldtype": "Data",
                "insert_after": "bir_details_section",
                "description": "Customer's Tax Identification Number"
            },
            {
                "fieldname": "branch_code",
                "label": "Branch Code",
                "fieldtype": "Data",
                "insert_after": "tin",
                "description": "Customer's Branch Code (if applicable)"
            }
        ]
    }
    
    # Custom fields for Supplier (to store TIN and Branch Code)
    supplier_fields = {
        "Supplier": [
            {
                "fieldname": "bir_details_section",
                "label": "BIR Details",
                "fieldtype": "Section Break",
                "insert_after": "more_info",
                "collapsible": 1
            },
            {
                "fieldname": "tin",
                "label": "TIN (Tax Identification Number)",
                "fieldtype": "Data",
                "insert_after": "bir_details_section",
                "description": "Supplier's Tax Identification Number"
            },
            {
                "fieldname": "branch_code",
                "label": "Branch Code",
                "fieldtype": "Data",
                "insert_after": "tin",
                "description": "Supplier's Branch Code (if applicable)"
            }
        ]
    }
    
    # Combine all field definitions
    all_fields = {}
    all_fields.update(sales_invoice_fields)
    all_fields.update(tax_fields)
    all_fields.update(purchase_invoice_fields)
    all_fields.update(company_fields)
    all_fields.update(customer_fields)
    all_fields.update(supplier_fields)
    
    # Create custom fields
    create_custom_fields(all_fields)
    
    print("✅ BIR 2307 custom fields created successfully")


def create_atc_code_doctype():
    """
    Create ATC Code doctype for managing Alphanumeric Tax Codes
    """
    
    if frappe.db.exists("DocType", "ATC Code"):
        print("✅ ATC Code doctype already exists")
        return
    
    # Create ATC Code DocType
    doctype = frappe.get_doc({
        "doctype": "DocType",
        "name": "ATC Code",
        "module": "Logistics",
        "custom": 1,
        "naming_rule": "By fieldname",
        "autoname": "field:code",
        "title_field": "description",
        "fields": [
            {
                "fieldname": "code",
                "label": "ATC Code",
                "fieldtype": "Data",
                "reqd": 1,
                "unique": 1,
                "description": "Alphanumeric Tax Code (e.g., WI010, WI020)"
            },
            {
                "fieldname": "description",
                "label": "Description",
                "fieldtype": "Data",
                "reqd": 1,
                "in_list_view": 1,
                "description": "Description of the tax code"
            },
            {
                "fieldname": "tax_rate",
                "label": "Tax Rate (%)",
                "fieldtype": "Percent",
                "description": "Standard tax rate for this ATC code"
            },
            {
                "fieldname": "nature_of_income",
                "label": "Nature of Income",
                "fieldtype": "Data",
                "description": "Standard nature of income for this ATC code"
            },
            {
                "fieldname": "is_active",
                "label": "Is Active",
                "fieldtype": "Check",
                "default": 1
            }
        ],
        "permissions": [
            {
                "role": "System Manager",
                "read": 1,
                "write": 1,
                "create": 1,
                "delete": 1
            },
            {
                "role": "Accounts Manager",
                "read": 1,
                "write": 1,
                "create": 1,
                "delete": 1
            },
            {
                "role": "Accounts User",
                "read": 1,
                "write": 1,
                "create": 1
            }
        ]
    })
    
    doctype.insert(ignore_permissions=True)
    print("✅ ATC Code doctype created successfully")


def setup_default_atc_codes():
    """
    Setup common ATC codes used in Philippines
    """
    
    common_atc_codes = [
        {
            "code": "WI010",
            "description": "Professional Fees",
            "tax_rate": 10,
            "nature_of_income": "Professional Fees"
        },
        {
            "code": "WI020",
            "description": "Professional Fees (Lawyers)",
            "tax_rate": 15,
            "nature_of_income": "Professional Fees - Legal Services"
        },
        {
            "code": "WI030",
            "description": "Professional Fees (Medical)",
            "tax_rate": 10,
            "nature_of_income": "Professional Fees - Medical Services"
        },
        {
            "code": "WI040",
            "description": "Rental Income",
            "tax_rate": 5,
            "nature_of_income": "Rental Income"
        },
        {
            "code": "WI050",
            "description": "Goods/Services",
            "tax_rate": 1,
            "nature_of_income": "Goods and Services"
        },
        {
            "code": "WI070",
            "description": "Directors Fees",
            "tax_rate": 10,
            "nature_of_income": "Directors Fees"
        },
        {
            "code": "WI080",
            "description": "Talent Fees",
            "tax_rate": 10,
            "nature_of_income": "Talent Fees"
        },
        {
            "code": "WI090",
            "description": "Management/Technical Fees",
            "tax_rate": 15,
            "nature_of_income": "Management and Technical Fees"
        }
    ]
    
    for atc_data in common_atc_codes:
        if not frappe.db.exists("ATC Code", atc_data["code"]):
            atc_doc = frappe.get_doc({
                "doctype": "ATC Code",
                **atc_data
            })
            atc_doc.insert(ignore_permissions=True)
            print(f"✅ Created ATC Code: {atc_data['code']} - {atc_data['description']}")
        else:
            print(f"✅ ATC Code {atc_data['code']} already exists")


def execute():
    """
    Main function to setup BIR 2307 compliance
    """
    print("Setting up BIR Form 2307 compliance...")
    
    try:
        # Create ATC Code doctype first
        create_atc_code_doctype()
        frappe.db.commit()
        
        # Setup default ATC codes
        setup_default_atc_codes()
        frappe.db.commit()
        
        # Create custom fields
        setup_bir_2307_fields()
        frappe.db.commit()
        
        print("✅ BIR Form 2307 setup completed successfully!")
        
    except Exception as e:
        frappe.db.rollback()
        print(f"❌ Error setting up BIR 2307: {e}")
        raise


if __name__ == "__main__":
    execute()












