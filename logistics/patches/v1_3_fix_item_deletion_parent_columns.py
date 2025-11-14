# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Patch to fix Item deletion error caused by missing parent columns in child tables.

This patch adds the missing parent, parentfield, and parenttype columns to child table
doctypes that link to Item but were missing these required columns.
"""

import frappe


def execute():
	"""Add missing parent columns to child table doctypes that link to Item"""
	
	print("Fixing Item deletion error: Adding missing parent columns to child tables...")
	
	# List of child table doctypes that link to Item and need parent columns
	tables_to_fix = [
		"tabCustoms Rate",
		"tabSea Freight Rate",
		"tabAir Freight Rate"
	]
	
	fixed_count = 0
	skipped_count = 0
	
	for table_name in tables_to_fix:
		try:
			# Check if table exists using direct SQL (table_name includes "tab" prefix)
			# Use single quotes for string comparison in information_schema
			table_check = frappe.db.sql("""
				SELECT COUNT(*) as count
				FROM information_schema.TABLES 
				WHERE TABLE_SCHEMA = DATABASE()
				AND TABLE_NAME = %s
			""", (table_name,), as_dict=True)
			if table_check[0]['count'] == 0:
				print(f"  [WARNING] Skipping {table_name}: Table does not exist")
				skipped_count += 1
				continue
			
			# Check if parent column already exists
			# Use single quotes for string comparison in information_schema
			columns = frappe.db.sql("""
				SELECT COLUMN_NAME 
				FROM information_schema.COLUMNS 
				WHERE TABLE_SCHEMA = DATABASE()
				AND TABLE_NAME = %s
				AND COLUMN_NAME IN ('parent', 'parentfield', 'parenttype')
			""", (table_name,), as_dict=True)
			
			existing_columns = {col['COLUMN_NAME'] for col in columns}
			required_columns = {'parent', 'parentfield', 'parenttype'}
			
			if existing_columns == required_columns:
				print(f"  [OK] {table_name}: All parent columns already exist")
				skipped_count += 1
				continue
			
			# Build ALTER TABLE statement
			alter_statements = []
			
			if 'parent' not in existing_columns:
				alter_statements.append("ADD COLUMN `parent` VARCHAR(140) NULL DEFAULT NULL")
			
			if 'parentfield' not in existing_columns:
				alter_statements.append("ADD COLUMN `parentfield` VARCHAR(140) NULL DEFAULT NULL")
			
			if 'parenttype' not in existing_columns:
				alter_statements.append("ADD COLUMN `parenttype` VARCHAR(140) NULL DEFAULT NULL")
			
			# Check if parent index exists
			# Use single quotes for string comparison in information_schema
			index_exists = frappe.db.sql("""
				SELECT COUNT(*) as count
				FROM information_schema.statistics 
				WHERE TABLE_SCHEMA = DATABASE()
				AND TABLE_NAME = %s
				AND INDEX_NAME = 'parent'
			""", (table_name,), as_dict=True)
			
			if alter_statements:
				alter_sql = f"ALTER TABLE `{table_name}` {', '.join(alter_statements)}"
				frappe.db.sql(alter_sql)
				
				# Add index if it doesn't exist and parent column was added
				if 'parent' not in existing_columns and index_exists[0]['count'] == 0:
					frappe.db.sql(f"ALTER TABLE `{table_name}` ADD INDEX `parent` (`parent`)")
				
				missing = required_columns - existing_columns
				print(f"  [OK] {table_name}: Added columns {', '.join(missing)}")
				fixed_count += 1
			else:
				# Only missing index
				if index_exists[0]['count'] == 0:
					frappe.db.sql(f"ALTER TABLE `{table_name}` ADD INDEX `parent` (`parent`)")
					print(f"  [OK] {table_name}: Added parent index")
					fixed_count += 1
				else:
					print(f"  [OK] {table_name}: Already fixed")
					skipped_count += 1
					
		except Exception as e:
			print(f"  [ERROR] {table_name}: Error - {str(e)}")
			frappe.log_error(
				f"Error fixing {table_name} in fix_item_deletion_parent_columns patch: {str(e)}",
				"Patch Error"
			)
	
	print(f"\n[SUCCESS] Patch completed: {fixed_count} table(s) fixed, {skipped_count} table(s) skipped")
	
	# Commit the changes
	frappe.db.commit()
	
	return True

