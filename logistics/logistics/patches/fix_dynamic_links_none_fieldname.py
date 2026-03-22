# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Patch to fix Frappe's fetch_distinct_link_doctypes function to handle None fieldnames.
This fixes the error: MySQLdb.OperationalError: (1054, "Unknown column 'None' in 'SELECT'")
that occurs when deleting documents that have Dynamic Link fields with None as fieldname.
"""

import frappe


def patch_fetch_distinct_link_doctypes():
	"""Monkey patch frappe.model.dynamic_links.fetch_distinct_link_doctypes to handle None fieldnames"""
	from frappe.model import dynamic_links
	
	# Store the original function
	original_fetch_distinct_link_doctypes = dynamic_links.fetch_distinct_link_doctypes
	
	def patched_fetch_distinct_link_doctypes(doctype, fieldname):
		"""
		Patched version that skips fields with None fieldname to prevent SQL errors.
		"""
		# If fieldname is None or empty, return empty list
		if not fieldname:
			frappe.log_error(
				f"fetch_distinct_link_doctypes called with None/empty fieldname for doctype {doctype}. "
				"This may indicate a malformed Dynamic Link field definition.",
				"Dynamic Links: None Fieldname"
			)
			return []
		
		# Call the original function
		try:
			return original_fetch_distinct_link_doctypes(doctype, fieldname)
		except Exception as e:
			error_msg = str(e)
			# Check if this is the specific SQL error about 'None' column
			if "Unknown column 'None'" in error_msg or ("1054" in error_msg and "None" in error_msg):
				frappe.log_error(
					f"Error in fetch_distinct_link_doctypes for {doctype}.{fieldname}: {error_msg}\n"
					"This may be due to a Dynamic Link field with None as fieldname.",
					"Dynamic Links: SQL Error"
				)
				return []
			# Re-raise other errors
			raise
	
	# Apply the patch
	dynamic_links.fetch_distinct_link_doctypes = patched_fetch_distinct_link_doctypes


def execute():
	"""Apply the patch when this migration runs"""
	patch_fetch_distinct_link_doctypes()
	frappe.db.commit()
