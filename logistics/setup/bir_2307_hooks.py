# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def validate_bir_2307_fields(doc, method):
    """
    Validate BIR 2307 required fields for withholding tax compliance
    """
    
    if doc.doctype not in ["Sales Invoice", "Purchase Invoice"]:
        return
    
    # Check if document has withholding tax entries
    has_withholding_tax = False
    
    if hasattr(doc, 'taxes') and doc.taxes:
        for tax in doc.taxes:
            if getattr(tax, 'is_withholding_tax', 0):
                has_withholding_tax = True
                
                # Validate ATC Code
                if not getattr(tax, 'atc_code', None):
                    frappe.throw(_("ATC Code is required for withholding tax entries in row {0}").format(tax.idx))
                
                # Validate Nature of Income
                if not getattr(tax, 'nature_of_income', None):
                    frappe.throw(_("Nature of Income is required for withholding tax entries in row {0}").format(tax.idx))
    
    if has_withholding_tax:
        # Validate TIN fields based on document type
        if doc.doctype == "Sales Invoice":
            # For Sales Invoice, we are the payor, customer is payee
            if not getattr(doc, 'payee_tin', None):
                frappe.throw(_("Payee TIN is required when withholding tax is applied"))
                
        elif doc.doctype == "Purchase Invoice":
            # For Purchase Invoice, supplier is payor, we are payee
            if not getattr(doc, 'payor_tin', None):
                frappe.throw(_("Payor TIN is required when withholding tax is applied"))


def auto_populate_tin_fields(doc, method):
    """
    Auto-populate TIN and Branch Code fields from Customer/Supplier/Company
    """
    
    if doc.doctype == "Sales Invoice":
        # Auto-populate from customer and company
        if doc.customer and not getattr(doc, 'payee_tin', None):
            customer_tin = frappe.db.get_value("Customer", doc.customer, "tin")
            customer_branch = frappe.db.get_value("Customer", doc.customer, "branch_code")
            
            if customer_tin:
                doc.payee_tin = customer_tin
            if customer_branch:
                doc.payee_branch_code = customer_branch
        
        if doc.company and not getattr(doc, 'payor_tin', None):
            company_tin = frappe.db.get_value("Company", doc.company, "tin")
            company_branch = frappe.db.get_value("Company", doc.company, "branch_code")
            
            if company_tin:
                doc.payor_tin = company_tin
            if company_branch:
                doc.payor_branch_code = company_branch
                
    elif doc.doctype == "Purchase Invoice":
        # Auto-populate from supplier and company
        if doc.supplier and not getattr(doc, 'payor_tin', None):
            supplier_tin = frappe.db.get_value("Supplier", doc.supplier, "tin")
            supplier_branch = frappe.db.get_value("Supplier", doc.supplier, "branch_code")
            
            if supplier_tin:
                doc.payor_tin = supplier_tin
            if supplier_branch:
                doc.payor_branch_code = supplier_branch
        
        if doc.company and not getattr(doc, 'payee_tin', None):
            company_tin = frappe.db.get_value("Company", doc.company, "tin")
            company_branch = frappe.db.get_value("Company", doc.company, "branch_code")
            
            if company_tin:
                doc.payee_tin = company_tin
            if company_branch:
                doc.payee_branch_code = company_branch


def auto_populate_atc_details(doc, method):
    """
    Auto-populate nature of income and tax rate from ATC Code
    """
    
    if not hasattr(doc, 'taxes') or not doc.taxes:
        return
    
    for tax in doc.taxes:
        if getattr(tax, 'atc_code', None) and getattr(tax, 'is_withholding_tax', 0):
            # Get ATC details
            atc_details = frappe.db.get_value("ATC Code", tax.atc_code, 
                ["nature_of_income", "tax_rate"], as_dict=True)
            
            if atc_details:
                # Auto-populate nature of income if not set
                if not getattr(tax, 'nature_of_income', None) and atc_details.nature_of_income:
                    tax.nature_of_income = atc_details.nature_of_income
                
                # Auto-populate tax rate if not set
                if not tax.rate and atc_details.tax_rate:
                    tax.rate = -abs(atc_details.tax_rate)  # Negative for withholding


def get_bir_2307_data(doc):
    """
    Extract BIR 2307 data from Sales Invoice or Purchase Invoice
    Returns structured data for print format
    """
    
    if doc.doctype not in ["Sales Invoice", "Purchase Invoice"]:
        return {}
    
    # Get withholding tax entries
    withholding_taxes = []
    
    if hasattr(doc, 'taxes') and doc.taxes:
        for tax in doc.taxes:
            if getattr(tax, 'is_withholding_tax', 0):
                withholding_taxes.append({
                    "atc_code": getattr(tax, 'atc_code', ''),
                    "nature_of_income": getattr(tax, 'nature_of_income', ''),
                    "tax_rate": abs(tax.rate) if tax.rate else 0,
                    "tax_amount": abs(tax.tax_amount) if tax.tax_amount else 0,
                    "base_amount": tax.base_amount if hasattr(tax, 'base_amount') else doc.net_total
                })
    
    # Prepare BIR 2307 data structure
    bir_data = {
        "document_type": doc.doctype,
        "document_name": doc.name,
        "posting_date": doc.posting_date,
        "payor": {
            "name": "",
            "address": "",
            "tin": getattr(doc, 'payor_tin', ''),
            "branch_code": getattr(doc, 'payor_branch_code', '')
        },
        "payee": {
            "name": "",
            "address": "",
            "tin": getattr(doc, 'payee_tin', ''),
            "branch_code": getattr(doc, 'payee_branch_code', '')
        },
        "withholding_taxes": withholding_taxes,
        "total_amount_withheld": sum(tax["tax_amount"] for tax in withholding_taxes),
        "total_income_payment": doc.net_total
    }
    
    # Populate payor and payee details based on document type
    if doc.doctype == "Sales Invoice":
        # Company is payor, Customer is payee
        bir_data["payor"]["name"] = doc.company
        bir_data["payee"]["name"] = doc.customer
        
        # Get addresses
        company_address = frappe.db.get_value("Company", doc.company, "company_address")
        if company_address:
            bir_data["payor"]["address"] = frappe.db.get_value("Address", company_address, "address_line1")
        
        customer_address = frappe.db.get_value("Customer", doc.customer, "customer_primary_address")
        if customer_address:
            bir_data["payee"]["address"] = frappe.db.get_value("Address", customer_address, "address_line1")
            
    elif doc.doctype == "Purchase Invoice":
        # Supplier is payor, Company is payee
        bir_data["payor"]["name"] = doc.supplier
        bir_data["payee"]["name"] = doc.company
        
        # Get addresses
        supplier_address = frappe.db.get_value("Supplier", doc.supplier, "supplier_primary_address")
        if supplier_address:
            bir_data["payor"]["address"] = frappe.db.get_value("Address", supplier_address, "address_line1")
        
        company_address = frappe.db.get_value("Company", doc.company, "company_address")
        if company_address:
            bir_data["payee"]["address"] = frappe.db.get_value("Address", company_address, "address_line1")
    
    return bir_data


@frappe.whitelist()
def get_bir_2307_certificate_data(doctype, docname):
    """
    API endpoint to get BIR 2307 certificate data for a document
    """
    
    if not frappe.has_permission(doctype, "read"):
        frappe.throw(_("No permission to read {0}").format(doctype))
    
    doc = frappe.get_doc(doctype, docname)
    return get_bir_2307_data(doc)


def validate_atc_code(doc, method):
    """
    Validate ATC Code exists and is active
    """
    
    if doc.doctype != "ATC Code":
        return
    
    # Ensure code is uppercase
    if doc.code:
        doc.code = doc.code.upper()
    
    # Validate code format (should be alphanumeric)
    if doc.code and not doc.code.replace(" ", "").isalnum():
        frappe.throw(_("ATC Code should be alphanumeric"))












