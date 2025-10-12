"""
Create Transport Location doctype for UNLOCO integration
"""

import frappe
from frappe import _

def execute():
    """Create Transport Location doctype if it doesn't exist"""
    
    if not frappe.db.exists("DocType", "Transport Location"):
        print("Creating Transport Location doctype...")
        
        # Create Transport Location doctype
        location_doctype = frappe.get_doc({
            "doctype": "DocType",
            "name": "Transport Location",
            "module": "Air Freight",
            "custom": 1,
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
                    "default": 1
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
                    "fieldname": "unlocode",
                    "fieldtype": "Data",
                    "label": "UNLOCO Code",
                    "description": "United Nations Code for Trade and Transport Locations"
                },
                {
                    "fieldname": "country",
                    "fieldtype": "Data",
                    "label": "Country"
                },
                {
                    "fieldname": "country_code",
                    "fieldtype": "Data",
                    "label": "Country Code",
                    "description": "ISO 3166-1 alpha-2 country code"
                },
                {
                    "fieldname": "location_type",
                    "fieldtype": "Select",
                    "label": "Location Type",
                    "options": "Airport\nPort\nRailway Station\nRoad Terminal\nOther",
                    "description": "Type of transport location"
                },
                {
                    "fieldname": "iata_code",
                    "fieldtype": "Data",
                    "label": "IATA Code"
                },
                {
                    "fieldname": "description",
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
        print("✓ Transport Location doctype created successfully")
    else:
        print("✓ Transport Location doctype already exists")
