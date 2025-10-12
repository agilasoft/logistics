"""
Create Location doctype for UNLOCO integration
"""

import frappe
from frappe import _

def execute():
    """Create Location doctype if it doesn't exist"""
    
    if not frappe.db.exists("DocType", "Location"):
        print("Creating Location doctype...")
        
        # Create Location doctype
        location_doctype = frappe.get_doc({
            "doctype": "DocType",
            "name": "Location",
            "module": "Air Freight",
            "custom": 0,
            "istable": 0,
            "issingle": 0,
            "autoname": "field:location_name",
            "naming_rule": "By fieldname",
            "fields": [
                {
                    "fieldname": "location_name",
                    "fieldtype": "Data",
                    "label": "Location Name",
                    "reqd": 1,
                    "search_index": 1
                },
                {
                    "fieldname": "is_logistics_location",
                    "fieldtype": "Check",
                    "label": "Is Logistics Location",
                    "default": 0
                },
                {
                    "fieldname": "latitude",
                    "fieldtype": "Float",
                    "label": "Latitude",
                    "precision": 8
                },
                {
                    "fieldname": "longitude", 
                    "fieldtype": "Float",
                    "label": "Longitude",
                    "precision": 8
                },
                {
                    "fieldname": "custom_unlocode",
                    "fieldtype": "Data",
                    "label": "UNLOCO Code",
                    "description": "United Nations Code for Trade and Transport Locations"
                },
                {
                    "fieldname": "custom_country",
                    "fieldtype": "Data",
                    "label": "Country"
                },
                {
                    "fieldname": "custom_country_code",
                    "fieldtype": "Data",
                    "label": "Country Code",
                    "description": "ISO 3166-1 alpha-2 country code"
                },
                {
                    "fieldname": "custom_location_type",
                    "fieldtype": "Select",
                    "label": "Location Type",
                    "options": "Airport\nPort\nRailway Station\nRoad Terminal\nOther",
                    "description": "Type of transport location"
                },
                {
                    "fieldname": "custom_iata_code",
                    "fieldtype": "Data",
                    "label": "IATA Code"
                },
                {
                    "fieldname": "custom_description",
                    "fieldtype": "Text",
                    "label": "Description"
                }
            ],
            "permissions": [
                {
                    "role": "System Manager",
                    "create": 1,
                    "delete": 1,
                    "email": 1,
                    "export": 1,
                    "print": 1,
                    "read": 1,
                    "report": 1,
                    "share": 1,
                    "submit": 1,
                    "write": 1
                }
            ],
            "sort_field": "location_name",
            "sort_order": "ASC"
        })
        
        location_doctype.insert(ignore_permissions=True)
        frappe.db.commit()
        print("✓ Location doctype created successfully")
    else:
        print("✓ Location doctype already exists")
        
        # Add missing custom fields if they don't exist
        meta = frappe.get_meta("Location")
        existing_fields = [field.fieldname for field in meta.fields]
        
        custom_fields_to_add = [
            {
                "fieldname": "custom_unlocode",
                "label": "UNLOCO Code",
                "fieldtype": "Data",
                "description": "United Nations Code for Trade and Transport Locations"
            },
            {
                "fieldname": "custom_country",
                "label": "Country",
                "fieldtype": "Data"
            },
            {
                "fieldname": "custom_country_code",
                "label": "Country Code",
                "fieldtype": "Data",
                "description": "ISO 3166-1 alpha-2 country code"
            },
            {
                "fieldname": "custom_location_type",
                "label": "Location Type",
                "fieldtype": "Select",
                "options": "Airport\nPort\nRailway Station\nRoad Terminal\nOther",
                "description": "Type of transport location"
            },
            {
                "fieldname": "custom_iata_code",
                "label": "IATA Code",
                "fieldtype": "Data"
            },
            {
                "fieldname": "custom_description",
                "label": "Description",
                "fieldtype": "Text"
            }
        ]
        
        for field_data in custom_fields_to_add:
            if field_data["fieldname"] not in existing_fields:
                print(f"Adding {field_data['fieldname']} field...")
                
                field_doc = frappe.get_doc({
                    "doctype": "Custom Field",
                    "dt": "Location",
                    **field_data
                })
                field_doc.insert(ignore_permissions=True)
                print(f"✓ Added {field_data['fieldname']} field")
            else:
                print(f"✓ {field_data['fieldname']} field already exists")
        
        frappe.db.commit()
