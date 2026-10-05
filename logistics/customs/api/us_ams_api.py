# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
US AMS (Automated Manifest System) API Integration.

Filing actions do not write a mock status. They refuse unless Manifest Settings
has a live CBP endpoint, and they still leave the document unchanged because
this client does not call that endpoint yet.
"""

import frappe
from typing import Dict, Any
from .base_api import BaseCustomsAPI
from frappe import _


class USAMSAPI(BaseCustomsAPI):
	"""API client for US AMS (CBP Automated Manifest System)"""
	
	def __init__(self, company: str = None):
		super().__init__(company)
		self.api_name = "US AMS"
		self.endpoint_field = "cbp_api_endpoint"
		self.endpoint = self.configured_endpoint()
		self.credentials = self._get_credentials()
	
	def _get_credentials(self) -> Dict[str, str]:
		"""Get API credentials from settings"""
		if not self.settings:
			return {}
		
		return {
			"username": getattr(self.settings, 'cbp_api_username', ''),
			"password": getattr(self.settings, 'cbp_api_password', ''),
			"filer_code": getattr(self.settings, 'ams_filer_code', '')
		}
	
	def submit(self, filing_doc: str) -> Dict[str, Any]:
		"""
		Submit US AMS filing to CBP.
		
		Args:
			filing_doc: Name of the US AMS document
			
		Returns:
			dict: Response with AMS transaction number, status, etc.
		"""
		try:
			ams_doc = frappe.get_doc("US AMS", filing_doc)
			
			# Validate document
			if ams_doc.status != "Draft":
				return {
					"success": False,
					"message": _("Only Draft AMS can be submitted.")
				}
			
			return self.block_filing()
			
		except frappe.DoesNotExistError:
			return {
				"success": False,
				"message": _("US AMS document {0} not found.").format(filing_doc)
			}
		except Exception as e:
			frappe.log_error(f"Error submitting US AMS: {str(e)}", "US AMS API Error")
			return {
				"success": False,
				"message": _("Error submitting US AMS: {0}").format(str(e))
			}
	
	def check_status(self, filing_doc: str) -> Dict[str, Any]:
		"""
		Check status of submitted US AMS filing.
		
		Args:
			filing_doc: Name of the US AMS document
			
		Returns:
			dict: Current status information
		"""
		try:
			ams_doc = frappe.get_doc("US AMS", filing_doc)
			
			return self.block_filing()
			
		except frappe.DoesNotExistError:
			return {
				"success": False,
				"message": _("US AMS document {0} not found.").format(filing_doc)
			}
		except Exception as e:
			frappe.log_error(f"Error checking US AMS status: {str(e)}", "US AMS API Error")
			return {
				"success": False,
				"message": _("Error checking US AMS status: {0}").format(str(e))
			}
	
	def amend(self, filing_doc: str, amendment_data: Dict = None) -> Dict[str, Any]:
		"""
		Submit an amendment to US AMS filing.
		
		Args:
			filing_doc: Name of the US AMS document
			amendment_data: Data for the amendment
			
		Returns:
			dict: Amendment response
		"""
		try:
			ams_doc = frappe.get_doc("US AMS", filing_doc)
			
			# Validate document
			if ams_doc.submission_type != "Update":
				return {
					"success": False,
					"message": _("Submission type must be 'Update' for amendments.")
				}
			
			return self.block_filing()
			
		except frappe.DoesNotExistError:
			return {
				"success": False,
				"message": _("US AMS document {0} not found.").format(filing_doc)
			}
		except Exception as e:
			frappe.log_error(f"Error amending US AMS: {str(e)}", "US AMS API Error")
			return {
				"success": False,
				"message": _("Error amending US AMS: {0}").format(str(e))
			}
	
	def cancel(self, filing_doc: str, reason: str = None) -> Dict[str, Any]:
		"""
		Cancel US AMS filing.
		
		Args:
			filing_doc: Name of the US AMS document
			reason: Reason for cancellation
			
		Returns:
			dict: Cancellation response
		"""
		try:
			ams_doc = frappe.get_doc("US AMS", filing_doc)
			
			# Validate document
			if ams_doc.submission_type != "Cancel":
				return {
					"success": False,
					"message": _("Submission type must be 'Cancel' for cancellation.")
				}
			
			return self.block_filing()
			
		except frappe.DoesNotExistError:
			return {
				"success": False,
				"message": _("US AMS document {0} not found.").format(filing_doc)
			}
		except Exception as e:
			frappe.log_error(f"Error cancelling US AMS: {str(e)}", "US AMS API Error")
			return {
				"success": False,
				"message": _("Error cancelling US AMS: {0}").format(str(e))
			}

