# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.utils.rename_field import rename_field

def execute():
	"""
	Migration script for Dangerous Goods enhancements
	This script handles the database migration for new dangerous goods fields
	"""
	
	# Check if the dangerous goods fields already exist
	if not frappe.db.has_column("tabAir Freight Job", "contains_dangerous_goods"):
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
		
		frappe.db.commit()
		print("Added dangerous goods fields to Air Freight Job table")
	
	# Check if the dangerous goods fields exist in packages table
	if not frappe.db.has_column("tabAir Freight Job Packages", "dg_division"):
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
		
		frappe.db.commit()
		print("Added enhanced dangerous goods fields to Air Freight Job Packages table")
	
	# Update existing records to set default values
	frappe.db.sql("""
		UPDATE `tabAir Freight Job` 
		SET `contains_dangerous_goods` = 0,
			`dg_declaration_complete` = 0,
			`dg_compliance_status` = 'Pending Documentation'
		WHERE `contains_dangerous_goods` IS NULL
	""")
	
	frappe.db.commit()
	print("Updated existing Air Freight Job records with default values")
	
	# Create indexes for better performance
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
		
		frappe.db.commit()
		print("Created indexes for dangerous goods fields")
		
	except Exception as e:
		print(f"Warning: Could not create indexes: {str(e)}")
	
	print("Dangerous Goods migration completed successfully!")


