# Fix legacy "Direct" and "Consolidation" house_type values
# Updates all existing records with legacy values to normalized values
from __future__ import unicode_literals

import frappe


def execute():
	"""Fix legacy house_type values in all relevant doctypes"""
	
	# Mapping of legacy values to normalized values
	revert_map = {
		"Direct": "Standard House",
		"Consolidation": "Co-load Master",
	}
	
	# List of doctypes and their house_type field names
	doctype_fields = [
		("Sea Booking", "house_type"),
		("Sea Shipment", "house_type"),
		("Air Booking", "house_type"),
		("Air Shipment", "house_type"),
	]
	
	# Update each doctype
	for doctype, fieldname in doctype_fields:
		_migrate_doctype(doctype, fieldname, revert_map)
	
	# Update One-Off Quote if it has sea_house_type field
	if frappe.db.table_exists("One-Off Quote"):
		meta = frappe.get_meta("One-Off Quote")
		if meta.has_field("sea_house_type"):
			_migrate_doctype("One-Off Quote", "sea_house_type", revert_map)
		if meta.has_field("air_house_type"):
			_migrate_doctype("One-Off Quote", "air_house_type", revert_map)
	
	# Update Sales Quote Sea Freight if it exists
	if frappe.db.table_exists("Sales Quote Sea Freight"):
		meta = frappe.get_meta("Sales Quote Sea Freight")
		if meta.has_field("sea_house_type"):
			_migrate_doctype("Sales Quote Sea Freight", "sea_house_type", revert_map)
	
	# Update Sales Quote Air Freight if it exists
	if frappe.db.table_exists("Sales Quote Air Freight"):
		meta = frappe.get_meta("Sales Quote Air Freight")
		if meta.has_field("air_house_type"):
			_migrate_doctype("Sales Quote Air Freight", "air_house_type", revert_map)
	
	frappe.db.commit()


def _migrate_doctype(doctype, fieldname, revert_map):
	"""Migrate house_type values for a specific doctype"""
	if not frappe.db.table_exists(doctype):
		return
	
	# Check if field exists
	try:
		meta = frappe.get_meta(doctype)
		if not meta.has_field(fieldname):
			return
	except Exception:
		# If we can't get meta, skip this doctype
		return
	
	# Update each legacy value
	for old_value, new_value in revert_map.items():
		# Count records to update before updating
		count_result = frappe.db.sql("""
			SELECT COUNT(*) as count
			FROM `tab{doctype}`
			WHERE `{fieldname}` = %s
		""".format(doctype=doctype, fieldname=fieldname), (old_value,), as_dict=True)
		
		count = count_result[0].get("count", 0) if count_result else 0
		
		if count > 0:
			# Update main table
			frappe.db.sql("""
				UPDATE `tab{doctype}`
				SET `{fieldname}` = %s
				WHERE `{fieldname}` = %s
			""".format(doctype=doctype, fieldname=fieldname), (new_value, old_value))
			
			frappe.logger().info(
				"Updated {count} {doctype} records: {old} -> {new}".format(
					count=count,
					doctype=doctype,
					old=old_value,
					new=new_value
				)
			)
