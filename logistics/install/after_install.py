# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from logistics.setup.install_master_data import execute as install_master_data

def after_install():
    """Run after installation of the logistics app"""
    frappe.log_error("Starting logistics app after_install process", "Logistics Install")
    
    try:
        # Install master data first
        install_master_data()
        
        # Index Master Air Way Bill DocType
        index_master_air_waybill()
        
        # Create any necessary custom fields or indexes
        create_custom_indexes()
        
        # Set up any required permissions
        setup_permissions()
        
        # Install default print formats
        install_default_print_formats()
        
        frappe.log_error("Logistics app after_install completed successfully", "Logistics Install")
        
    except Exception as e:
        frappe.log_error(f"Error in logistics app after_install: {str(e)}", "Logistics Install Error")
        raise

def index_master_air_waybill():
    """Create database indexes for Master Air Way Bill DocType"""
    try:
        # Check if Master Air Way Bill DocType exists
        if not frappe.db.exists("DocType", "Master Air Waybill"):
            frappe.log_error("Master Air Waybill DocType not found", "Logistics Install")
            return
        
        # Create indexes for better performance
        indexes_to_create = [
            {
                "table": "tabMaster Air Waybill",
                "columns": ["airline", "flight_no"],
                "name": "idx_airline_flight"
            },
            {
                "table": "tabMaster Air Waybill", 
                "columns": ["master_awb_no"],
                "name": "idx_master_awb_no"
            },
            {
                "table": "tabMaster Air Waybill",
                "columns": ["flight_date", "origin_airport", "destination_airport"],
                "name": "idx_flight_route_date"
            },
            {
                "table": "tabMaster Air Waybill",
                "columns": ["flight_schedule"],
                "name": "idx_flight_schedule"
            },
            {
                "table": "tabMaster Air Waybill",
                "columns": ["sending_agent", "receiving_agent"],
                "name": "idx_handling_agents"
            }
        ]
        
        for index in indexes_to_create:
            create_index_if_not_exists(
                index["table"],
                index["columns"], 
                index["name"]
            )
            
        frappe.log_error("Master Air Waybill indexes created successfully", "Logistics Install")
        
    except Exception as e:
        frappe.log_error(f"Error creating Master Air Waybill indexes: {str(e)}", "Logistics Install Error")
        raise

def create_index_if_not_exists(table, columns, index_name):
    """Create database index if it doesn't exist"""
    try:
        # Check if index already exists
        existing_indexes = frappe.db.sql(f"""
            SHOW INDEX FROM `{table}` 
            WHERE Key_name = '{index_name}'
        """, as_dict=True)
        
        if existing_indexes:
            frappe.log_error(f"Index {index_name} already exists on {table}", "Logistics Install")
            return
            
        # Create the index
        columns_str = "`, `".join(columns)
        frappe.db.sql(f"""
            CREATE INDEX `{index_name}` 
            ON `{table}` (`{columns_str}`)
        """)
        
        frappe.log_error(f"Created index {index_name} on {table}", "Logistics Install")
        
    except Exception as e:
        frappe.log_error(f"Error creating index {index_name}: {str(e)}", "Logistics Install Error")
        # Don't raise here to allow other indexes to be created

def create_custom_indexes():
    """Create additional custom indexes for related tables"""
    try:
        # Indexes for Air Consolidation related tables
        consolidation_indexes = [
            {
                "table": "tabAir Consolidation",
                "columns": ["airline", "flight_number"],
                "name": "idx_consolidation_airline_flight"
            },
            {
                "table": "tabAir Consolidation",
                "columns": ["origin_airport", "destination_airport"],
                "name": "idx_consolidation_route"
            },
            {
                "table": "tabAir Consolidation Shipments",
                "columns": ["air_freight_job"],
                "name": "idx_shipments_job"
            },
            {
                "table": "tabAir Consolidation Packages",
                "columns": ["air_freight_job"],
                "name": "idx_packages_job"
            }
        ]
        
        for index in consolidation_indexes:
            create_index_if_not_exists(
                index["table"],
                index["columns"],
                index["name"]
            )
            
        frappe.log_error("Custom indexes created successfully", "Logistics Install")
        
    except Exception as e:
        frappe.log_error(f"Error creating custom indexes: {str(e)}", "Logistics Install Error")

def setup_permissions():
    """Set up any required permissions for the logistics app"""
    try:
        # Ensure Master Air Waybill has proper permissions
        if frappe.db.exists("DocType", "Master Air Waybill"):
            # Check if permissions exist
            existing_permissions = frappe.get_all("DocPerm", 
                filters={"parent": "Master Air Waybill"},
                fields=["role"]
            )
            
            if not existing_permissions:
                # Create default permissions
                create_default_permissions("Master Air Waybill")
                
        frappe.log_error("Permissions setup completed", "Logistics Install")
        
    except Exception as e:
        frappe.log_error(f"Error setting up permissions: {str(e)}", "Logistics Install Error")

def create_default_permissions(doctype):
    """Create default permissions for a DocType"""
    try:
        # Get the DocType document
        doc = frappe.get_doc("DocType", doctype)
        
        # Add System Manager permissions if not exists
        if not any(perm.role == "System Manager" for perm in doc.permissions):
            doc.append("permissions", {
                "role": "System Manager",
                "read": 1,
                "write": 1,
                "create": 1,
                "delete": 1,
                "submit": 1,
                "cancel": 1,
                "amend": 1,
                "print": 1,
                "email": 1,
                "export": 1,
                "report": 1,
                "share": 1
            })
            doc.save()
            
    except Exception as e:
        frappe.log_error(f"Error creating permissions for {doctype}: {str(e)}", "Logistics Install Error")

def install_default_print_formats():
    """Install default print formats for Sales Invoice and Purchase Invoice"""
    try:
        from logistics.print_format.sales_invoice.install_print_format import install_sales_invoice_print_format
        from logistics.print_format.purchase_invoice.install_print_format import install_purchase_invoice_print_format
        
        # Install Sales Invoice print format
        install_sales_invoice_print_format()
        
        # Install Purchase Invoice print format
        install_purchase_invoice_print_format()
        
        frappe.log_error("Default print formats installed successfully", "Logistics Install")
        
    except Exception as e:
        frappe.log_error(f"Error installing print formats: {str(e)}", "Logistics Install Error")
        # Don't raise here to allow installation to continue
