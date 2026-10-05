# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
US ISF (Importer Security Filing) API Integration.

Filing actions do not write a mock status. They refuse unless Manifest Settings
has a live CBP endpoint, and they still leave the document unchanged because
this client does not call that endpoint yet.
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
		self.endpoint_field = "cbp_api_endpoint"
		self.endpoint = self._get_endpoint()
		self.credentials = self._get_credentials()
	
	def _get_endpoint(self) -> str:
		"""Derive the ISF URL from a live CBP endpoint on Manifest Settings."""
		value = self.configured_endpoint()
		if not value:
			return ""
		return value.replace("/ams/", "/isf/")
	
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
			
			return self.block_filing()
			
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
			
			return self.block_filing()
			
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
			
			return self.block_filing()
			
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
			
			return self.block_filing()
			
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

