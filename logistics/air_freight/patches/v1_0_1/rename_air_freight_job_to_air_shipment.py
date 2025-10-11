# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.rename_doc import rename_doc

def execute():
	"""Rename Air Freight Job doctype to Air Shipment"""
	
	# Check if the old doctype exists
	if frappe.db.exists("DocType", "Air Freight Job"):
		try:
			# Rename the doctype
			rename_doc("DocType", "Air Freight Job", "Air Shipment", force=True)
			frappe.db.commit()
			print("✓ Successfully renamed 'Air Freight Job' to 'Air Shipment'")
			
			# Update related doctypes
			if frappe.db.exists("DocType", "Air Freight Job Services"):
				rename_doc("DocType", "Air Freight Job Services", "Air Shipment Services", force=True)
				frappe.db.commit()
				print("✓ Successfully renamed 'Air Freight Job Services' to 'Air Shipment Services'")
			
			if frappe.db.exists("DocType", "Air Freight Job Packages"):
				rename_doc("DocType", "Air Freight Job Packages", "Air Shipment Packages", force=True)
				frappe.db.commit()
				print("✓ Successfully renamed 'Air Freight Job Packages' to 'Air Shipment Packages'")
			
			# Update any custom fields that reference the old doctype
			update_custom_fields()
			
			# Update any links in other doctypes
			update_doctype_links()
			
		except Exception as e:
			frappe.log_error(f"Error renaming Air Freight Job doctype: {str(e)}")
			raise
	else:
		print("Air Freight Job doctype not found - may have been already renamed")

def update_custom_fields():
	"""Update custom fields that reference the old doctype"""
	try:
		# Update custom fields
		frappe.db.sql("""
			UPDATE `tabCustom Field` 
			SET options = 'Air Shipment' 
			WHERE options = 'Air Freight Job'
		""")
		
		frappe.db.sql("""
			UPDATE `tabCustom Field` 
			SET options = 'Air Shipment Services' 
			WHERE options = 'Air Freight Job Services'
		""")
		
		frappe.db.sql("""
			UPDATE `tabCustom Field` 
			SET options = 'Air Shipment Packages' 
			WHERE options = 'Air Freight Job Packages'
		""")
		
		print("✓ Updated custom fields")
	except Exception as e:
		frappe.log_error(f"Error updating custom fields: {str(e)}")

def update_doctype_links():
	"""Update links in other doctypes"""
	try:
		# Update Job Milestone doctype link filters
		frappe.db.sql("""
			UPDATE `tabDocField` 
			SET link_filters = '[[\"DocType\",\"name\",\"in\",[\"Air Shipment\",\"Sea Freight Job\",\"Transport\"]]]'
			WHERE parent = 'Job Milestone' AND fieldname = 'job_type'
		""")
		
		# Update Dangerous Goods Declaration
		frappe.db.sql("""
			UPDATE `tabDocField` 
			SET options = 'Air Shipment', label = 'Air Shipment'
			WHERE parent = 'Dangerous Goods Declaration' AND fieldname = 'air_shipment'
		""")
		
		# Update Master Air Waybill links
		frappe.db.sql("""
			UPDATE `tabDocLink` 
			SET link_doctype = 'Air Shipment'
			WHERE parent = 'Master Air Waybill' AND link_doctype = 'Air Freight Job'
		""")
		
		print("✓ Updated doctype links")
	except Exception as e:
		frappe.log_error(f"Error updating doctype links: {str(e)}")
