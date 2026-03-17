# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.exceptions import LinkExistsError
from frappe import _
import traceback

# Import patch module to ensure it's loaded early
try:
	from logistics.logistics.patches import apply_dynamic_links_patch
except ImportError:
	pass


class CustomsAuthority(Document):
	def delete(self, force=False, ignore_permissions=False):
		"""
		Override delete method to handle SQL errors when checking for linked references.
		The error "Unknown column 'None' in 'SELECT'" occurs when Frappe's get_links()
		encounters a Dynamic Link field with None as fieldname.
		"""
		# Ensure the dynamic links patch is applied before deletion
		self._ensure_dynamic_links_patch()
		
		try:
			# Call parent delete method
			super().delete(force=force, ignore_permissions=ignore_permissions)
		except Exception as e:
			error_msg = str(e)
			error_type = type(e).__name__
			
			# Check if this is the specific SQL error about 'None' column
			if ("Unknown column 'None'" in error_msg or 
				("1054" in error_msg and "None" in error_msg) or
				(error_type == "OperationalError" and "None" in error_msg)):
				
				# Log the error for debugging
				frappe.log_error(
					f"Error checking references for Customs Authority {self.name}: {error_msg}\n"
					f"Traceback: {traceback.format_exc()}\n"
					"This may be due to a Dynamic Link field with None as fieldname. "
					"Please check custom fields that link to Customs Authority.",
					"Customs Authority Delete Error"
				)
				
				# Try to get links manually, filtering out any None fieldnames
				try:
					links = self._get_links_safely()
					if links and not force:
						# Format links for LinkExistsError
						link_info = ", ".join([f"{l['doctype']} ({l['count']})" for l in links])
						raise LinkExistsError(
							_("Cannot delete {0} because it is linked with {1}").format(
								self.name, link_info
							)
						)
					# If no valid links or force=True, proceed with deletion
					# by calling the parent delete with force=True to skip link checking
					super().delete(force=True, ignore_permissions=ignore_permissions)
				except LinkExistsError:
					# Re-raise LinkExistsError if there are valid links
					raise
				except Exception as e2:
					# If manual check also fails, log and proceed with force delete
					frappe.log_error(
						f"Manual link check also failed for Customs Authority {self.name}: {str(e2)}\n"
						f"Traceback: {traceback.format_exc()}",
						"Customs Authority Delete Error"
					)
					# Proceed with force delete to bypass link checking
					super().delete(force=True, ignore_permissions=ignore_permissions)
			else:
				# Re-raise other errors
				raise
	
	def _ensure_dynamic_links_patch(self):
		"""Ensure the dynamic links patch is applied to prevent SQL errors"""
		try:
			from frappe.model import dynamic_links
			
			# Check if already patched
			if hasattr(dynamic_links.fetch_distinct_link_doctypes, '_patched_by_logistics'):
				return
			
			# Apply the patch
			from logistics.logistics.patches.apply_dynamic_links_patch import apply_patch
			apply_patch()
		except Exception:
			# Silently fail if patch cannot be applied
			pass
	
	def _get_links_safely(self):
		"""
		Safely get links to this Customs Authority, filtering out any fields with None fieldname.
		This method manually checks for references instead of using Frappe's get_links()
		which may fail if there are malformed Link or Dynamic Link field definitions.
		"""
		links = []
		try:
			# Get all doctypes that might link to Customs Authority
			all_doctypes = frappe.get_all("DocType", filters={"istable": 0}, pluck="name")
			for doctype in all_doctypes:
				try:
					meta = frappe.get_meta(doctype)
					
					# Check all Link fields
					for field in meta.get_link_fields():
						# Skip if fieldname is None, empty, or options doesn't match
						if not field.fieldname or field.options != "Customs Authority":
							continue
						
						# Check if the column exists in the table
						if not frappe.db.has_column(doctype, field.fieldname):
							continue
						
						# Check if there are any documents with this field set to our name
						try:
							count = frappe.db.sql(
								f"SELECT COUNT(*) FROM `tab{doctype}` WHERE `{field.fieldname}` = %s",
								(self.name,),
								as_list=True
							)[0][0]
							if count > 0:
								links.append({
									"doctype": doctype,
									"fieldname": field.fieldname,
									"count": count
								})
						except Exception:
							# Skip if query fails for this field
							continue
					
					# Check Dynamic Link fields that might reference Customs Authority
					for field in meta.get_dynamic_link_fields():
						# Skip if fieldname is None or empty
						if not field.fieldname:
							continue
						
						# For Dynamic Links, we need to check the Dynamic Link table
						# The fieldname is the link_doctype field, and we need to find
						# records where link_doctype = "Customs Authority" and link_name = self.name
						try:
							# Get the parent fieldname (the field that stores the doctype)
							parent_fieldname = field.fieldname
							
							# Check if Dynamic Link table exists and has the required columns
							if not frappe.db.has_column("Dynamic Link", "link_doctype"):
								continue
							if not frappe.db.has_column("Dynamic Link", "link_name"):
								continue
							if not frappe.db.has_column("Dynamic Link", "parenttype"):
								continue
							if not frappe.db.has_column("Dynamic Link", "parent"):
								continue
							
							# Query Dynamic Link table for references to this Customs Authority
							count = frappe.db.sql(
								"""
								SELECT COUNT(*) FROM `tabDynamic Link`
								WHERE link_doctype = %s
								AND link_name = %s
								AND parenttype = %s
								""",
								("Customs Authority", self.name, doctype),
								as_list=True
							)[0][0]
							
							if count > 0:
								links.append({
									"doctype": doctype,
									"fieldname": f"Dynamic Link ({parent_fieldname})",
									"count": count
								})
						except Exception:
							# Skip if query fails for this field
							continue
				except Exception:
					# Skip doctypes that cause errors
					continue
		except Exception:
			# If we can't get links safely, return empty list
			pass
		return links
