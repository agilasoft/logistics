# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Add Capacity Management Fields to Storage Location and Handling Unit
==================================================================

This patch adds comprehensive capacity management fields to both Storage Location
and Handling Unit doctypes to enable advanced capacity planning and optimization.
"""

import frappe
from frappe.utils import flt


def execute():
    """Execute the migration to add capacity management fields"""
    
    print("🚀 Starting capacity management fields migration...")
    
    try:
        # Add capacity management fields to Storage Location
        add_storage_location_capacity_fields()
        
        # Add capacity management fields to Handling Unit
        add_handling_unit_capacity_fields()
        
        # Update existing records with default values
        update_existing_records()
        
        frappe.db.commit()
        print("✅ Capacity management fields added successfully")
        
    except Exception as e:
        frappe.db.rollback()
        print(f"❌ Migration failed: {str(e)}")
        raise


def add_storage_location_capacity_fields():
    """Add capacity management fields to Storage Location doctype"""
    
    print("📦 Adding Storage Location capacity fields...")
    
    # Check if fields already exist
    existing_fields = [field.fieldname for field in frappe.get_meta("Storage Location").fields]
    
    fields_to_add = [
        ("capacity_tab", "VARCHAR(140) DEFAULT 'Capacity Management'"),
        ("max_volume", "DECIMAL(20,3) DEFAULT 0"),
        ("max_weight", "DECIMAL(20,2) DEFAULT 0"),
        ("max_height", "DECIMAL(20,2) DEFAULT 0"),
        ("max_width", "DECIMAL(20,2) DEFAULT 0"),
        ("max_length", "DECIMAL(20,2) DEFAULT 0"),
        ("capacity_uom", "VARCHAR(140)"),
        ("weight_uom", "VARCHAR(140)"),
        ("current_volume", "DECIMAL(20,3) DEFAULT 0"),
        ("current_weight", "DECIMAL(20,2) DEFAULT 0"),
        ("utilization_percentage", "DECIMAL(5,2) DEFAULT 0"),
        ("capacity_alerts_tab", "VARCHAR(140) DEFAULT 'Capacity Alerts'"),
        ("enable_capacity_alerts", "INT(1) DEFAULT 0"),
        ("volume_alert_threshold", "DECIMAL(5,2) DEFAULT 80.00"),
        ("weight_alert_threshold", "DECIMAL(5,2) DEFAULT 80.00"),
        ("utilization_alert_threshold", "DECIMAL(5,2) DEFAULT 90.00")
    ]
    
    for field_name, field_definition in fields_to_add:
        if field_name not in existing_fields:
            try:
                frappe.db.sql(f"""
                    ALTER TABLE `tabStorage Location` 
                    ADD COLUMN `{field_name}` {field_definition}
                """)
                print(f"  ✅ Added {field_name}")
            except Exception as e:
                print(f"  ⚠️  Field {field_name} might already exist: {str(e)}")
        else:
            print(f"  ℹ️  Field {field_name} already exists")


def add_handling_unit_capacity_fields():
    """Add capacity management fields to Handling Unit doctype"""
    
    print("📦 Adding Handling Unit capacity fields...")
    
    # Check if fields already exist
    existing_fields = [field.fieldname for field in frappe.get_meta("Handling Unit").fields]
    
    fields_to_add = [
        ("capacity_tab", "VARCHAR(140) DEFAULT 'Capacity Management'"),
        ("max_volume", "DECIMAL(20,3) DEFAULT 0"),
        ("max_weight", "DECIMAL(20,2) DEFAULT 0"),
        ("max_height", "DECIMAL(20,2) DEFAULT 0"),
        ("max_width", "DECIMAL(20,2) DEFAULT 0"),
        ("max_length", "DECIMAL(20,2) DEFAULT 0"),
        ("capacity_uom", "VARCHAR(140)"),
        ("weight_uom", "VARCHAR(140)"),
        ("current_volume", "DECIMAL(20,3) DEFAULT 0"),
        ("current_weight", "DECIMAL(20,2) DEFAULT 0"),
        ("utilization_percentage", "DECIMAL(5,2) DEFAULT 0"),
        ("capacity_alerts_tab", "VARCHAR(140) DEFAULT 'Capacity Alerts'"),
        ("enable_capacity_alerts", "INT(1) DEFAULT 0"),
        ("volume_alert_threshold", "DECIMAL(5,2) DEFAULT 80.00"),
        ("weight_alert_threshold", "DECIMAL(5,2) DEFAULT 80.00"),
        ("utilization_alert_threshold", "DECIMAL(5,2) DEFAULT 90.00")
    ]
    
    for field_name, field_definition in fields_to_add:
        if field_name not in existing_fields:
            try:
                frappe.db.sql(f"""
                    ALTER TABLE `tabHandling Unit` 
                    ADD COLUMN `{field_name}` {field_definition}
                """)
                print(f"  ✅ Added {field_name}")
            except Exception as e:
                print(f"  ⚠️  Field {field_name} might already exist: {str(e)}")
        else:
            print(f"  ℹ️  Field {field_name} already exists")


def update_existing_records():
    """Update existing records with default values"""
    
    print("🔄 Updating existing records...")
    
    # Update Storage Locations
    update_storage_locations()
    
    # Update Handling Units
    update_handling_units()
    
    print("✅ Existing records updated")


def update_storage_locations():
    """Update existing Storage Location records"""
    
    locations = frappe.get_all("Storage Location", fields=["name", "storage_type"])
    print(f"  📍 Found {len(locations)} Storage Locations")
    
    for location in locations:
        try:
            location_doc = frappe.get_doc("Storage Location", location.name)
            
            # Set default UOMs
            if not location_doc.capacity_uom:
                location_doc.capacity_uom = "CBM"
            if not location_doc.weight_uom:
                location_doc.weight_uom = "Kg"
            
            # Set default alert thresholds
            if not location_doc.volume_alert_threshold:
                location_doc.volume_alert_threshold = 80.0
            if not location_doc.weight_alert_threshold:
                location_doc.weight_alert_threshold = 80.0
            if not location_doc.utilization_alert_threshold:
                location_doc.utilization_alert_threshold = 90.0
            
            # Inherit from storage type if available
            if location.storage_type:
                storage_type_doc = frappe.get_doc("Storage Type", location.storage_type)
                
                if not location_doc.max_volume and storage_type_doc.max_capacity:
                    location_doc.max_volume = storage_type_doc.max_capacity
                if not location_doc.max_weight and storage_type_doc.max_weight:
                    location_doc.max_weight = storage_type_doc.max_weight
                if not location_doc.max_height and storage_type_doc.max_height:
                    location_doc.max_height = storage_type_doc.max_height
                if not location_doc.max_width and storage_type_doc.max_width:
                    location_doc.max_width = storage_type_doc.max_width
                if not location_doc.max_length and storage_type_doc.max_length:
                    location_doc.max_length = storage_type_doc.max_length
                if not location_doc.capacity_uom and storage_type_doc.capacity_uom:
                    location_doc.capacity_uom = storage_type_doc.capacity_uom
                if not location_doc.weight_uom and storage_type_doc.billing_uom:
                    location_doc.weight_uom = storage_type_doc.billing_uom
            
            # Calculate current metrics
            calculate_location_metrics(location_doc)
            
            location_doc.save(ignore_permissions=True)
            
        except Exception as e:
            print(f"  ⚠️  Error updating {location.name}: {str(e)}")


def update_handling_units():
    """Update existing Handling Unit records"""
    
    handling_units = frappe.get_all("Handling Unit", fields=["name"])
    print(f"  📦 Found {len(handling_units)} Handling Units")
    
    for hu in handling_units:
        try:
            hu_doc = frappe.get_doc("Handling Unit", hu.name)
            
            # Set default UOMs
            if not hu_doc.capacity_uom:
                hu_doc.capacity_uom = "CBM"
            if not hu_doc.weight_uom:
                hu_doc.weight_uom = "Kg"
            
            # Set default alert thresholds
            if not hu_doc.volume_alert_threshold:
                hu_doc.volume_alert_threshold = 80.0
            if not hu_doc.weight_alert_threshold:
                hu_doc.weight_alert_threshold = 80.0
            if not hu_doc.utilization_alert_threshold:
                hu_doc.utilization_alert_threshold = 90.0
            
            # Calculate current metrics
            calculate_handling_unit_metrics(hu_doc)
            
            hu_doc.save(ignore_permissions=True)
            
        except Exception as e:
            print(f"  ⚠️  Error updating {hu.name}: {str(e)}")


def calculate_location_metrics(location_doc):
    """Calculate current capacity metrics for a storage location"""
    
    try:
        # Get current stock data
        stock_data = frappe.db.sql("""
            SELECT 
                SUM(wi.volume * l.quantity) as total_volume,
                SUM(wi.weight * l.quantity) as total_weight
            FROM `tabWarehouse Stock Ledger` l
            LEFT JOIN `tabWarehouse Item` wi ON wi.name = l.item
            WHERE l.storage_location = %s AND l.quantity > 0
        """, (location_doc.name,), as_dict=True)
        
        if stock_data and stock_data[0]:
            location_doc.current_volume = flt(stock_data[0]["total_volume"])
            location_doc.current_weight = flt(stock_data[0]["total_weight"])
            
            # Calculate utilization percentage
            volume_utilization = 0
            weight_utilization = 0
            
            if location_doc.max_volume > 0:
                volume_utilization = (location_doc.current_volume / location_doc.max_volume) * 100
            
            if location_doc.max_weight > 0:
                weight_utilization = (location_doc.current_weight / location_doc.max_weight) * 100
            
            location_doc.utilization_percentage = max(volume_utilization, weight_utilization)
        
    except Exception as e:
        print(f"  ⚠️  Error calculating metrics for {location_doc.name}: {str(e)}")


def calculate_handling_unit_metrics(hu_doc):
    """Calculate current capacity metrics for a handling unit"""
    
    try:
        # Get current stock data
        stock_data = frappe.db.sql("""
            SELECT 
                SUM(wi.volume * l.quantity) as total_volume,
                SUM(wi.weight * l.quantity) as total_weight
            FROM `tabWarehouse Stock Ledger` l
            LEFT JOIN `tabWarehouse Item` wi ON wi.name = l.item
            WHERE l.handling_unit = %s AND l.quantity > 0
        """, (hu_doc.name,), as_dict=True)
        
        if stock_data and stock_data[0]:
            hu_doc.current_volume = flt(stock_data[0]["total_volume"])
            hu_doc.current_weight = flt(stock_data[0]["total_weight"])
            
            # Calculate utilization percentage
            volume_utilization = 0
            weight_utilization = 0
            
            if hu_doc.max_volume > 0:
                volume_utilization = (hu_doc.current_volume / hu_doc.max_volume) * 100
            
            if hu_doc.max_weight > 0:
                weight_utilization = (hu_doc.current_weight / hu_doc.max_weight) * 100
            
            hu_doc.utilization_percentage = max(volume_utilization, weight_utilization)
        
    except Exception as e:
        print(f"  ⚠️  Error calculating metrics for {hu_doc.name}: {str(e)}")


def rollback():
    """Rollback the migration (remove added fields)"""
    
    try:
        # Remove Storage Location capacity fields
        storage_location_fields = [
            "capacity_tab", "max_volume", "current_volume", "max_weight", "current_weight",
            "max_height", "max_width", "max_length", "capacity_uom", "weight_uom",
            "utilization_percentage", "capacity_alerts_tab", "enable_capacity_alerts",
            "volume_alert_threshold", "weight_alert_threshold", "utilization_alert_threshold"
        ]
        
        for field in storage_location_fields:
            try:
                frappe.db.sql(f"ALTER TABLE `tabStorage Location` DROP COLUMN `{field}`")
            except Exception:
                pass  # Field might not exist
        
        # Remove Handling Unit capacity fields
        handling_unit_fields = [
            "capacity_tab", "max_volume", "current_volume", "max_weight", "current_weight",
            "max_height", "max_width", "max_length", "capacity_uom", "weight_uom",
            "utilization_percentage", "capacity_alerts_tab", "enable_capacity_alerts",
            "volume_alert_threshold", "weight_alert_threshold", "utilization_alert_threshold"
        ]
        
        for field in handling_unit_fields:
            try:
                frappe.db.sql(f"ALTER TABLE `tabHandling Unit` DROP COLUMN `{field}`")
            except Exception:
                pass  # Field might not exist
        
        frappe.db.commit()
        print("✅ Capacity management fields removed (rollback complete)")
        
    except Exception as e:
        frappe.log_error(f"Error during rollback: {str(e)}")
        print(f"❌ Rollback failed: {str(e)}")