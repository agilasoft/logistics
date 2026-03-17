# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Apply patch to fix Frappe's fetch_distinct_link_doctypes function on app initialization.
This should be imported in hooks.py to ensure it runs when the app loads.
"""

import frappe

# Apply patch when module is imported (if Frappe is initialized)
_patch_applied = False


def apply_patch():
	"""Apply the monkey patch to fix dynamic links None fieldname issue"""
	global _patch_applied
	
	# Avoid applying patch multiple times
	if _patch_applied:
		return
		
	try:
		from frappe.model import dynamic_links
		
		# Check if already patched (avoid double patching)
		if hasattr(dynamic_links.fetch_distinct_link_doctypes, '_patched_by_logistics'):
			_patch_applied = True
			return
		
		# Store the original function
		original_fetch_distinct_link_doctypes = dynamic_links.fetch_distinct_link_doctypes
		
		def patched_fetch_distinct_link_doctypes(doctype, fieldname):
			"""
			Patched version that skips fields with None fieldname to prevent SQL errors.
			"""
			# If fieldname is None or empty, return empty list
			if not fieldname:
				# Only log in development mode to avoid log spam
				if frappe.conf.developer_mode:
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
				error_type = type(e).__name__
				error_module = type(e).__module__
				
				# Check if this is the specific SQL error about 'None' column
				# Handle both MySQLdb.OperationalError and pymysql.err.OperationalError
				is_operational_error = (
					error_type == "OperationalError" or
					"OperationalError" in error_module or
					"MySQLdb" in error_module or
					"pymysql" in error_module
				)
				
				if ("Unknown column 'None'" in error_msg or 
					("1054" in error_msg and "None" in error_msg) or
					(is_operational_error and "None" in error_msg)):
					frappe.log_error(
						f"Error in fetch_distinct_link_doctypes for {doctype}.{fieldname}: {error_msg}\n"
						"This may be due to a Dynamic Link field with None as fieldname.",
						"Dynamic Links: SQL Error"
					)
					return []
				# Re-raise other errors
				raise
		
		# Mark as patched
		patched_fetch_distinct_link_doctypes._patched_by_logistics = True
		
		# Apply the patch
		dynamic_links.fetch_distinct_link_doctypes = patched_fetch_distinct_link_doctypes
		_patch_applied = True
	except ImportError:
		# Module not available yet, will be patched later
		pass
	except Exception as e:
		# Log error but don't fail app initialization
		frappe.log_error(
			f"Failed to apply dynamic links patch: {str(e)}",
			"Dynamic Links Patch Error"
		)

# Try to apply patch on module import (if Frappe is initialized)
def _try_apply_patch():
	"""Try to apply patch if Frappe is initialized"""
	try:
		# Check if Frappe is initialized
		if not frappe:
			return
		
		# Try to access frappe.db to ensure database is ready
		if not hasattr(frappe, 'db') or not frappe.db:
			return
		
		# Apply the patch
		apply_patch()
	except Exception:
		# Silently fail if Frappe is not initialized yet
		pass

# Try to apply immediately if possible
_try_apply_patch()

# Also register to apply when Frappe is ready (via after_migrate hook)
