#!/usr/bin/env python3
"""
Quick fix script for dangerous goods fields
Run this script to add the dangerous goods fields to the database
"""

import frappe

def fix_dg_fields():
    """Add dangerous goods fields to the database"""
    
    print("Starting dangerous goods fields migration...")
    
    try:
        # Check if the dangerous goods fields already exist
        if not frappe.db.has_column("tabAir Freight Job", "contains_dangerous_goods"):
            print("Adding dangerous goods fields to Air Freight Job table...")
            
            # Add the dangerous goods fields to the main table
            frappe.db.sql("""
                ALTER TABLE `tabAir Freight Job` 
                ADD COLUMN `contains_dangerous_goods` INT(1) NOT NULL DEFAULT 0,
                ADD COLUMN `dg_declaration_complete` INT(1) NOT NULL DEFAULT 0,
                ADD COLUMN `dg_compliance_status` VARCHAR(140),
                ADD COLUMN `dg_emergency_contact` VARCHAR(140),
                ADD COLUMN `dg_emergency_phone` VARCHAR(140),
                ADD COLUMN `dg_emergency_email` VARCHAR(140)
            """)
            
            print("✅ Added dangerous goods fields to Air Freight Job table")
        else:
            print("✅ Dangerous goods fields already exist in Air Freight Job table")
        
        # Check if the dangerous goods fields exist in packages table
        if not frappe.db.has_column("tabAir Freight Job Packages", "dg_division"):
            print("Adding enhanced dangerous goods fields to Air Freight Job Packages table...")
            
            # Add the enhanced dangerous goods fields to packages table
            frappe.db.sql("""
                ALTER TABLE `tabAir Freight Job Packages` 
                ADD COLUMN `dg_division` VARCHAR(140),
                ADD COLUMN `subsidiary_risks` VARCHAR(140),
                ADD COLUMN `packing_instruction` VARCHAR(140),
                ADD COLUMN `net_quantity_per_package` DECIMAL(18,6),
                ADD COLUMN `emergency_contact_name` VARCHAR(140),
                ADD COLUMN `emergency_contact_phone` VARCHAR(140),
                ADD COLUMN `emergency_contact_email` VARCHAR(140),
                ADD COLUMN `handling_instructions` LONGTEXT,
                ADD COLUMN `segregation_requirements` LONGTEXT,
                ADD COLUMN `special_provisions` LONGTEXT,
                ADD COLUMN `transport_mode_restrictions` LONGTEXT,
                ADD COLUMN `cargo_aircraft_only` INT(1) NOT NULL DEFAULT 0,
                ADD COLUMN `passenger_aircraft_allowed` INT(1) NOT NULL DEFAULT 1,
                ADD COLUMN `erg_code` VARCHAR(140),
                ADD COLUMN `environmental_hazards` LONGTEXT,
                ADD COLUMN `is_radioactive` INT(1) NOT NULL DEFAULT 0,
                ADD COLUMN `transport_index` DECIMAL(18,6),
                ADD COLUMN `radiation_level` DECIMAL(18,6),
                ADD COLUMN `criticality_safety_index` DECIMAL(18,6),
                ADD COLUMN `shippers_declaration_status` INT(1) NOT NULL DEFAULT 0,
                ADD COLUMN `dg_declaration_number` VARCHAR(140),
                ADD COLUMN `additional_handling_instructions` LONGTEXT
            """)
            
            print("✅ Added enhanced dangerous goods fields to Air Freight Job Packages table")
        else:
            print("✅ Enhanced dangerous goods fields already exist in Air Freight Job Packages table")
        
        # Update existing records to set default values
        print("Updating existing records with default values...")
        frappe.db.sql("""
            UPDATE `tabAir Freight Job` 
            SET `contains_dangerous_goods` = 0,
                `dg_declaration_complete` = 0,
                `dg_compliance_status` = 'Pending Documentation'
            WHERE `contains_dangerous_goods` IS NULL
        """)
        
        print("✅ Updated existing Air Freight Job records with default values")
        
        # Create indexes for better performance
        print("Creating indexes for better performance...")
        try:
            frappe.db.sql("""
                CREATE INDEX IF NOT EXISTS `idx_contains_dangerous_goods` 
                ON `tabAir Freight Job` (`contains_dangerous_goods`)
            """)
            
            frappe.db.sql("""
                CREATE INDEX IF NOT EXISTS `idx_dg_compliance_status` 
                ON `tabAir Freight Job` (`dg_compliance_status`)
            """)
            
            frappe.db.sql("""
                CREATE INDEX IF NOT EXISTS `idx_dg_substance` 
                ON `tabAir Freight Job Packages` (`dg_substance`)
            """)
            
            frappe.db.sql("""
                CREATE INDEX IF NOT EXISTS `idx_un_number` 
                ON `tabAir Freight Job Packages` (`un_number`)
            """)
            
            frappe.db.sql("""
                CREATE INDEX IF NOT EXISTS `idx_is_radioactive` 
                ON `tabAir Freight Job Packages` (`is_radioactive`)
            """)
            
            print("✅ Created indexes for dangerous goods fields")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not create indexes: {str(e)}")
        
        # Commit all changes
        frappe.db.commit()
        
        print("\n🎉 Dangerous Goods migration completed successfully!")
        print("The dangerous goods functionality should now work without errors.")
        
    except Exception as e:
        print(f"❌ Error during migration: {str(e)}")
        frappe.db.rollback()
        raise

if __name__ == "__main__":
    fix_dg_fields()


