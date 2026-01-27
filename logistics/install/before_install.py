# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _


def before_install():
    """Run before installation of the logistics app
    
    This is called before single doctypes are initialized, so we can create
    required UOM records that are referenced by Transport Capacity Settings.
    """
    try:
        # Create required UOM records for Transport Capacity Settings
        # These must exist before the single doctype is initialized
        install_required_uoms()
        
    except Exception as e:
        frappe.log_error(f"Error in logistics app before_install: {str(e)}", "Logistics Install Error")
        # Don't raise - allow installation to continue if UOMs already exist
        pass


def install_required_uoms():
    """Install required UOM records for Transport Capacity Settings
    
    Reads default UOM values from Transport Capacity Settings doctype definition
    and creates those UOM records if they don't exist. This ensures the UOMs
    referenced by default values in the settings exist before the single doctype
    is initialized.
    """
    try:
        # Read the Transport Capacity Settings doctype to get default UOM values
        doctype_path = frappe.get_app_path("logistics", "transport", "doctype", 
                                          "transport_capacity_settings", "transport_capacity_settings.json")
        
        import json
        with open(doctype_path, 'r') as f:
            doctype_def = json.load(f)
        
        # Extract default UOM values from field definitions
        uom_names = set()
        for field in doctype_def.get("fields", []):
            if field.get("fieldname") in ["default_dimension_uom", "default_volume_uom", "default_weight_uom"]:
                default_value = field.get("default")
                if default_value:
                    uom_names.add(default_value)
        
        # Create UOM records if they don't exist
        for uom_name in uom_names:
            try:
                # Check if UOM already exists
                if frappe.db.exists("UOM", uom_name):
                    continue
                
                # Create UOM record
                uom_doc = frappe.new_doc("UOM")
                uom_doc.uom_name = uom_name
                uom_doc.must_be_whole_number = 0
                uom_doc.insert(ignore_permissions=True)
                
            except Exception as e:
                # Log but don't fail - UOM might already exist or be created elsewhere
                frappe.log_error(f"Error creating UOM {uom_name}: {str(e)}", "Logistics Install")
        
        frappe.db.commit()
        
    except Exception as e:
        # Log error but don't fail installation - user can create UOMs manually
        frappe.log_error(f"Error reading Transport Capacity Settings defaults: {str(e)}", "Logistics Install")
