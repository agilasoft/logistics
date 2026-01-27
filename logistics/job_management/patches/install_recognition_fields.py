"""
Install custom fields for Revenue and Cost Recognition

This patch adds recognition fields to:
- Air Shipment, Sea Shipment, Transport Job, Warehouse Job, Customs Declaration, General Job
- Air Shipment Charges, Sea Shipment Charges, Warehouse Job Charges, Customs Declaration Charges
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    """Install recognition custom fields on all job documents."""
    
    # Define recognition fields for job documents
    job_recognition_fields = get_job_recognition_fields()
    
    # Define estimated revenue/cost fields for charges tables
    charges_fields = get_charges_fields()
    
    # Combine all fields
    all_fields = {}
    all_fields.update(job_recognition_fields)
    all_fields.update(charges_fields)
    
    # Create all custom fields
    create_custom_fields(all_fields, update=True)
    
    frappe.db.commit()
    print("Recognition fields installed successfully")


def get_job_recognition_fields():
    """Get recognition fields definition for job documents."""
    
    job_doctypes = [
        "Air Shipment",
        "Sea Shipment",
        "Transport Job",
        "Warehouse Job",
        "Customs Declaration",
        "General Job"
    ]
    
    fields = {}
    
    for dt in job_doctypes:
        if not frappe.db.exists("DocType", dt):
            continue
            
        fields[dt] = [
            {
                "fieldname": "recognition_section",
                "fieldtype": "Section Break",
                "label": "Revenue & Cost Recognition",
                "insert_after": "amended_from",
                "collapsible": 1
            },
            {
                "fieldname": "wip_recognition_enabled",
                "fieldtype": "Check",
                "label": "Enable WIP Recognition",
                "insert_after": "recognition_section"
            },
            {
                "fieldname": "wip_recognition_date_basis",
                "fieldtype": "Select",
                "label": "WIP Recognition Date Basis",
                "options": "\nATA\nATD\nJob Booking Date\nJob Creation\nUser Specified",
                "insert_after": "wip_recognition_enabled"
            },
            {
                "fieldname": "accrual_recognition_enabled",
                "fieldtype": "Check",
                "label": "Enable Accrual Recognition",
                "insert_after": "wip_recognition_date_basis"
            },
            {
                "fieldname": "accrual_recognition_date_basis",
                "fieldtype": "Select",
                "label": "Accrual Recognition Date Basis",
                "options": "\nATA\nATD\nJob Booking Date\nJob Creation\nUser Specified",
                "insert_after": "accrual_recognition_enabled"
            },
            {
                "fieldname": "recognition_date",
                "fieldtype": "Date",
                "label": "Recognition Date",
                "description": "Used when date basis is 'User Specified'",
                "insert_after": "accrual_recognition_date_basis"
            },
            {
                "fieldname": "column_break_recognition",
                "fieldtype": "Column Break",
                "insert_after": "recognition_date"
            },
            {
                "fieldname": "estimated_revenue",
                "fieldtype": "Currency",
                "label": "Estimated Revenue",
                "read_only": 1,
                "insert_after": "column_break_recognition"
            },
            {
                "fieldname": "wip_amount",
                "fieldtype": "Currency",
                "label": "WIP Amount",
                "read_only": 1,
                "insert_after": "estimated_revenue"
            },
            {
                "fieldname": "recognized_revenue",
                "fieldtype": "Currency",
                "label": "Recognized Revenue",
                "read_only": 1,
                "insert_after": "wip_amount"
            },
            {
                "fieldname": "wip_journal_entry",
                "fieldtype": "Link",
                "label": "WIP Journal Entry",
                "options": "Journal Entry",
                "read_only": 1,
                "insert_after": "recognized_revenue"
            },
            {
                "fieldname": "wip_adjustment_journal_entry",
                "fieldtype": "Link",
                "label": "WIP Adjustment JE",
                "options": "Journal Entry",
                "read_only": 1,
                "insert_after": "wip_journal_entry"
            },
            {
                "fieldname": "wip_closed",
                "fieldtype": "Check",
                "label": "WIP Closed",
                "read_only": 1,
                "insert_after": "wip_adjustment_journal_entry"
            },
            {
                "fieldname": "column_break_accrual",
                "fieldtype": "Column Break",
                "insert_after": "wip_closed"
            },
            {
                "fieldname": "estimated_costs",
                "fieldtype": "Currency",
                "label": "Estimated Costs",
                "read_only": 1,
                "insert_after": "column_break_accrual"
            },
            {
                "fieldname": "accrual_amount",
                "fieldtype": "Currency",
                "label": "Accrual Amount",
                "read_only": 1,
                "insert_after": "estimated_costs"
            },
            {
                "fieldname": "recognized_costs",
                "fieldtype": "Currency",
                "label": "Recognized Costs",
                "read_only": 1,
                "insert_after": "accrual_amount"
            },
            {
                "fieldname": "accrual_journal_entry",
                "fieldtype": "Link",
                "label": "Accrual Journal Entry",
                "options": "Journal Entry",
                "read_only": 1,
                "insert_after": "recognized_costs"
            },
            {
                "fieldname": "accrual_adjustment_journal_entry",
                "fieldtype": "Link",
                "label": "Accrual Adjustment JE",
                "options": "Journal Entry",
                "read_only": 1,
                "insert_after": "accrual_journal_entry"
            },
            {
                "fieldname": "accrual_closed",
                "fieldtype": "Check",
                "label": "Accrual Closed",
                "read_only": 1,
                "insert_after": "accrual_adjustment_journal_entry"
            }
        ]
    
    return fields


def get_charges_fields():
    """Get estimated revenue/cost fields for charges tables."""
    
    charges_doctypes = [
        "Air Shipment Charges",
        "Sea Shipment Charges",
        "Warehouse Job Charges",
        "Customs Declaration Charges"
    ]
    
    fields = {}
    
    for dt in charges_doctypes:
        if not frappe.db.exists("DocType", dt):
            continue
        
        # Find appropriate insert_after field
        insert_after = "amount"
        if not frappe.db.exists("Custom Field", {"dt": dt, "fieldname": "amount"}):
            # Try to find another suitable field
            meta = frappe.get_meta(dt)
            for field in meta.fields:
                if field.fieldtype == "Currency":
                    insert_after = field.fieldname
                    break
        
        fields[dt] = [
            {
                "fieldname": "estimated_revenue",
                "fieldtype": "Currency",
                "label": "Estimated Revenue",
                "insert_after": insert_after
            },
            {
                "fieldname": "estimated_cost",
                "fieldtype": "Currency",
                "label": "Estimated Cost",
                "insert_after": "estimated_revenue"
            }
        ]
    
    return fields
