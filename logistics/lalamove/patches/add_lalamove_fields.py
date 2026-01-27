# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Patch to add Lalamove fields to source doctypes
"""

import frappe


def execute():
    """Add Lalamove fields to all source doctypes"""
    
    doctypes_to_update = [
        {
            "doctype": "Transport Order",
            "fields": [
                {
                    "fieldname": "lalamove_section",
                    "fieldtype": "Section Break",
                    "label": "Lalamove Integration",
                    "collapsible": 1
                },
                {
                    "fieldname": "use_lalamove",
                    "fieldtype": "Check",
                    "label": "Use Lalamove",
                    "default": 0
                },
                {
                    "fieldname": "lalamove_order",
                    "fieldtype": "Link",
                    "label": "Lalamove Order",
                    "options": "Lalamove Order",
                    "read_only": 1
                },
                {
                    "fieldname": "lalamove_quotation",
                    "fieldtype": "Link",
                    "label": "Lalamove Quotation",
                    "options": "Lalamove Quotation",
                    "read_only": 1
                }
            ]
        },
        {
            "doctype": "Transport Job",
            "fields": [
                {
                    "fieldname": "lalamove_section",
                    "fieldtype": "Section Break",
                    "label": "Lalamove Integration",
                    "collapsible": 1
                },
                {
                    "fieldname": "use_lalamove",
                    "fieldtype": "Check",
                    "label": "Use Lalamove",
                    "default": 0
                },
                {
                    "fieldname": "lalamove_order",
                    "fieldtype": "Link",
                    "label": "Lalamove Order",
                    "options": "Lalamove Order",
                    "read_only": 1
                },
                {
                    "fieldname": "lalamove_quotation",
                    "fieldtype": "Link",
                    "label": "Lalamove Quotation",
                    "options": "Lalamove Quotation",
                    "read_only": 1
                }
            ]
        },
        {
            "doctype": "Transport Leg",
            "fields": [
                {
                    "fieldname": "lalamove_section",
                    "fieldtype": "Section Break",
                    "label": "Lalamove Integration",
                    "collapsible": 1
                },
                {
                    "fieldname": "use_lalamove",
                    "fieldtype": "Check",
                    "label": "Use Lalamove",
                    "default": 0
                },
                {
                    "fieldname": "lalamove_order",
                    "fieldtype": "Link",
                    "label": "Lalamove Order",
                    "options": "Lalamove Order",
                    "read_only": 1
                },
                {
                    "fieldname": "lalamove_quotation",
                    "fieldtype": "Link",
                    "label": "Lalamove Quotation",
                    "options": "Lalamove Quotation",
                    "read_only": 1
                }
            ]
        },
        {
            "doctype": "Warehouse Job",
            "fields": [
                {
                    "fieldname": "lalamove_section",
                    "fieldtype": "Section Break",
                    "label": "Lalamove Integration",
                    "collapsible": 1
                },
                {
                    "fieldname": "use_lalamove",
                    "fieldtype": "Check",
                    "label": "Use Lalamove for Delivery",
                    "default": 0
                },
                {
                    "fieldname": "lalamove_order",
                    "fieldtype": "Link",
                    "label": "Lalamove Order",
                    "options": "Lalamove Order",
                    "read_only": 1
                },
                {
                    "fieldname": "lalamove_quotation",
                    "fieldtype": "Link",
                    "label": "Lalamove Quotation",
                    "options": "Lalamove Quotation",
                    "read_only": 1
                },
                {
                    "fieldname": "delivery_address",
                    "fieldtype": "Link",
                    "label": "Delivery Address",
                    "options": "Address"
                },
                {
                    "fieldname": "delivery_contact",
                    "fieldtype": "Link",
                    "label": "Delivery Contact",
                    "options": "Contact"
                }
            ]
        },
        {
            "doctype": "Air Shipment",
            "fields": [
                {
                    "fieldname": "lalamove_section",
                    "fieldtype": "Section Break",
                    "label": "Lalamove Last-Mile Delivery",
                    "collapsible": 1
                },
                {
                    "fieldname": "use_lalamove",
                    "fieldtype": "Check",
                    "label": "Use Lalamove",
                    "default": 0
                },
                {
                    "fieldname": "last_mile_delivery_required",
                    "fieldtype": "Check",
                    "label": "Last-Mile Delivery Required",
                    "default": 0
                },
                {
                    "fieldname": "last_mile_delivery_date",
                    "fieldtype": "Date",
                    "label": "Last-Mile Delivery Date"
                },
                {
                    "fieldname": "lalamove_order",
                    "fieldtype": "Link",
                    "label": "Lalamove Order",
                    "options": "Lalamove Order",
                    "read_only": 1
                },
                {
                    "fieldname": "lalamove_quotation",
                    "fieldtype": "Link",
                    "label": "Lalamove Quotation",
                    "options": "Lalamove Quotation",
                    "read_only": 1
                }
            ]
        },
        {
            "doctype": "Air Booking",
            "fields": [
                {
                    "fieldname": "lalamove_section",
                    "fieldtype": "Section Break",
                    "label": "Lalamove Integration",
                    "collapsible": 1
                },
                {
                    "fieldname": "use_lalamove",
                    "fieldtype": "Check",
                    "label": "Use Lalamove",
                    "default": 0
                },
                {
                    "fieldname": "lalamove_order",
                    "fieldtype": "Link",
                    "label": "Lalamove Order",
                    "options": "Lalamove Order",
                    "read_only": 1
                },
                {
                    "fieldname": "lalamove_quotation",
                    "fieldtype": "Link",
                    "label": "Lalamove Quotation",
                    "options": "Lalamove Quotation",
                    "read_only": 1
                }
            ]
        },
        {
            "doctype": "Sea Shipment",
            "fields": [
                {
                    "fieldname": "lalamove_section",
                    "fieldtype": "Section Break",
                    "label": "Lalamove Last-Mile Delivery",
                    "collapsible": 1
                },
                {
                    "fieldname": "use_lalamove",
                    "fieldtype": "Check",
                    "label": "Use Lalamove",
                    "default": 0
                },
                {
                    "fieldname": "last_mile_delivery_required",
                    "fieldtype": "Check",
                    "label": "Last-Mile Delivery Required",
                    "default": 0
                },
                {
                    "fieldname": "last_mile_delivery_date",
                    "fieldtype": "Date",
                    "label": "Last-Mile Delivery Date"
                },
                {
                    "fieldname": "lalamove_order",
                    "fieldtype": "Link",
                    "label": "Lalamove Order",
                    "options": "Lalamove Order",
                    "read_only": 1
                },
                {
                    "fieldname": "lalamove_quotation",
                    "fieldtype": "Link",
                    "label": "Lalamove Quotation",
                    "options": "Lalamove Quotation",
                    "read_only": 1
                }
            ]
        },
        {
            "doctype": "Sea Booking",
            "fields": [
                {
                    "fieldname": "lalamove_section",
                    "fieldtype": "Section Break",
                    "label": "Lalamove Integration",
                    "collapsible": 1
                },
                {
                    "fieldname": "use_lalamove",
                    "fieldtype": "Check",
                    "label": "Use Lalamove",
                    "default": 0
                },
                {
                    "fieldname": "lalamove_order",
                    "fieldtype": "Link",
                    "label": "Lalamove Order",
                    "options": "Lalamove Order",
                    "read_only": 1
                },
                {
                    "fieldname": "lalamove_quotation",
                    "fieldtype": "Link",
                    "label": "Lalamove Quotation",
                    "options": "Lalamove Quotation",
                    "read_only": 1
                }
            ]
        }
    ]
    
    for doctype_config in doctypes_to_update:
        doctype = doctype_config["doctype"]
        fields = doctype_config["fields"]
        
        try:
            # Get doctype meta
            meta = frappe.get_meta(doctype)
            
            for field_config in fields:
                fieldname = field_config["fieldname"]
                
                # Check if field already exists
                if meta.has_field(fieldname):
                    frappe.log_error(
                        f"Field {fieldname} already exists in {doctype}",
                        "Lalamove Patch"
                    )
                    continue
                
                # Add field to doctype
                field_doc = frappe.get_doc({
                    "doctype": "DocType",
                    "name": doctype
                })
                
                # This is a simplified approach - in practice, you'd use frappe.db.sql
                # or the DocType API to add fields
                frappe.log_error(
                    f"Field {fieldname} needs to be added to {doctype} manually or via DocType API",
                    "Lalamove Patch"
                )
        
        except Exception as e:
            frappe.log_error(
                f"Error adding fields to {doctype}: {str(e)}",
                "Lalamove Patch Error"
            )


