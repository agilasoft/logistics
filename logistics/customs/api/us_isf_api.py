# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
US ISF (Importer Security Filing) API Integration
Stub implementation - returns mock responses
"""

import frappe
from typing import Dict, Any
from .base_api import BaseCustomsAPI
from frappe import _


class USISFAPI(BaseCustomsAPI):
	"""API client for US ISF (CBP Importer Security Filing)"""
	
	def __init__(self, company: str = None):
		super().__init__(company)
		self.api_name = "US ISF"
		self.endpoint = self._get_endpoint()
		self.credentials = self._get_credentials()
	
	def _get_endpoint(self) -> str:
		"""Get API endpoint from settings"""
		if self.settings and hasattr(self.settings, 'cbp_api_endpoint') and self.settings.cbp_api_endpoint:
			return self.settings.cbp_api_endpoint.replace("/ams/", "/isf/")  # ISF endpoint
		return "https://api.cbp.gov/isf/v1"  # Mock endpoint
	
	def _get_credentials(self) -> Dict[str, str]:
		"""Get API credentials from settings"""
		if not self.settings:
			return {}
		
		return {
			"username": getattr(self.settings, 'cbp_api_username', ''),
			"password": getattr(self.settings, 'cbp_api_password', ''),
			"filer_code": getattr(self.settings, 'isf_filer_code', '')
		}
	
	def submit(self, filing_doc: str) -> Dict[str, Any]:
		"""
		Submit US ISF filing to CBP.
		
		Args:
			filing_doc: Name of the US ISF document
			
		Returns:
			dict: Response with ISF number, status, etc.
		"""
		try:
			isf_doc = frappe.get_doc("US ISF", filing_doc)
			
			# Validate document
			if isf_doc.status != "Draft":
				return {
					"success": False,
					"message": _("Only Draft ISF can be submitted.")
				}
			
			# API integration: configure Manifest Settings for production.
			mock_response = self.get_mock_response("submit", success=True)
			mock_response["isf_number"] = mock_response["transaction_number"]
			
			# Update document with response
			isf_doc.status = mock_response["status"]
			isf_doc.submission_date = mock_response["submission_date"]
			isf_doc.submission_time = mock_response["submission_time"]
			isf_doc.save(ignore_permissions=True)
			
			return mock_response
			
		except frappe.DoesNotExistError:
			return {
				"success": False,
				"message": _("US ISF document {0} not found.").format(filing_doc)
			}
		except Exception as e:
			frappe.log_error(f"Error submitting US ISF: {str(e)}", "US ISF API Error")
			return {
				"success": False,
				"message": _("Error submitting US ISF: {0}").format(str(e))
			}
	
	def check_status(self, filing_doc: str) -> Dict[str, Any]:
		"""
		Check status of submitted US ISF filing.
		
		Args:
			filing_doc: Name of the US ISF document
			
		Returns:
			dict: Current status information
		"""
		try:
			isf_doc = frappe.get_doc("US ISF", filing_doc)
			
			# API integration: configure Manifest Settings for production.
			mock_response = self.get_mock_response("status", success=True)
			mock_response["status"] = isf_doc.status
			mock_response["isf_number"] = isf_doc.isf_number
			
			# Update document if status changed
			if mock_response.get("status") != isf_doc.status:
				isf_doc.status = mock_response["status"]
				isf_doc.save(ignore_permissions=True)
			
			return mock_response
			
		except frappe.DoesNotExistError:
			return {
				"success": False,
				"message": _("US ISF document {0} not found.").format(filing_doc)
			}
		except Exception as e:
			frappe.log_error(f"Error checking US ISF status: {str(e)}", "US ISF API Error")
			return {
				"success": False,
				"message": _("Error checking US ISF status: {0}").format(str(e))
			}
	
	def amend(self, filing_doc: str, amendment_data: Dict = None) -> Dict[str, Any]:
		"""
		Submit an amendment to US ISF filing.
		
		Args:
			filing_doc: Name of the US ISF document
			amendment_data: Data for the amendment
			
		Returns:
			dict: Amendment response
		"""
		try:
			isf_doc = frappe.get_doc("US ISF", filing_doc)
			
			# API integration: configure Manifest Settings for production.
			mock_response = self.get_mock_response("amend", success=True)
			
			# Update document
			isf_doc.status = "Amended"
			isf_doc.save(ignore_permissions=True)
			
			return mock_response
			
		except frappe.DoesNotExistError:
			return {
				"success": False,
				"message": _("US ISF document {0} not found.").format(filing_doc)
			}
		except Exception as e:
			frappe.log_error(f"Error amending US ISF: {str(e)}", "US ISF API Error")
			return {
				"success": False,
				"message": _("Error amending US ISF: {0}").format(str(e))
			}
	
	def cancel(self, filing_doc: str, reason: str = None) -> Dict[str, Any]:
		"""
		Cancel US ISF filing.
		
		Args:
			filing_doc: Name of the US ISF document
			reason: Reason for cancellation
			
		Returns:
			dict: Cancellation response
		"""
		try:
			isf_doc = frappe.get_doc("US ISF", filing_doc)
			
			# API integration: configure Manifest Settings for production.
			mock_response = self.get_mock_response("cancel", success=True)
			
			# Update document
			isf_doc.status = "Cancelled"
			if reason:
				isf_doc.notes = f"Cancelled: {reason}"
			isf_doc.save(ignore_permissions=True)
			
			return mock_response
			
		except frappe.DoesNotExistError:
			return {
				"success": False,
				"message": _("US ISF document {0} not found.").format(filing_doc)
			}
		except Exception as e:
			frappe.log_error(f"Error cancelling US ISF: {str(e)}", "US ISF API Error")
			return {
				"success": False,
				"message": _("Error cancelling US ISF: {0}").format(str(e))
			}

