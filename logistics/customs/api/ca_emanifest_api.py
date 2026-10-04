# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
CA eManifest (Canada Border Services Agency) API Integration.

Filing actions do not write a mock status. They refuse unless Manifest Settings
has a live CBSA endpoint, and they still leave the document unchanged because
this client does not call that endpoint yet.
"""

import frappe
from typing import Dict, Any
from .base_api import BaseCustomsAPI
from frappe import _


class CAeManifestAPI(BaseCustomsAPI):
	"""API client for CA eManifest (CBSA eManifest)"""
	
	def __init__(self, company: str = None):
		super().__init__(company)
		self.api_name = "CA eManifest"
		self.endpoint_field = "cbsa_api_endpoint"
		self.endpoint = self.configured_endpoint()
		self.credentials = self._get_credentials()
	
	def _get_credentials(self) -> Dict[str, str]:
		"""Get API credentials from settings"""
		if not self.settings:
			return {}
		
		return {
			"username": getattr(self.settings, 'cbsa_api_username', ''),
			"password": getattr(self.settings, 'cbsa_api_password', ''),
			"carrier_code": getattr(self.settings, 'cbsa_carrier_code', '')
		}
	
	def submit(self, filing_doc: str) -> Dict[str, Any]:
		"""
		Submit CA eManifest filing to CBSA.
		
		Args:
			filing_doc: Name of the CA eManifest Forwarder document
			
		Returns:
			dict: Response with CBSA transaction number, status, etc.
		"""
		try:
			emanifest_doc = frappe.get_doc("CA eManifest Forwarder", filing_doc)
			
			# Validate document
			if emanifest_doc.status != "Draft":
				return {
					"success": False,
					"message": _("Only Draft eManifest can be submitted.")
				}
			
			return self.block_filing()
			
		except frappe.DoesNotExistError:
			return {
				"success": False,
				"message": _("CA eManifest document {0} not found.").format(filing_doc)
			}
		except Exception as e:
			frappe.log_error(f"Error submitting CA eManifest: {str(e)}", "CA eManifest API Error")
			return {
				"success": False,
				"message": _("Error submitting CA eManifest: {0}").format(str(e))
			}
	
	def check_status(self, filing_doc: str) -> Dict[str, Any]:
		"""
		Check status of submitted CA eManifest filing.
		
		Args:
			filing_doc: Name of the CA eManifest Forwarder document
			
		Returns:
			dict: Current status information
		"""
		try:
			emanifest_doc = frappe.get_doc("CA eManifest Forwarder", filing_doc)
			
			return self.block_filing()
			
		except frappe.DoesNotExistError:
			return {
				"success": False,
				"message": _("CA eManifest document {0} not found.").format(filing_doc)
			}
		except Exception as e:
			frappe.log_error(f"Error checking CA eManifest status: {str(e)}", "CA eManifest API Error")
			return {
				"success": False,
				"message": _("Error checking CA eManifest status: {0}").format(str(e))
			}
	
	def amend(self, filing_doc: str, amendment_data: Dict = None) -> Dict[str, Any]:
		"""
		Submit an amendment to CA eManifest filing.
		
		Args:
			filing_doc: Name of the CA eManifest Forwarder document
			amendment_data: Data for the amendment
			
		Returns:
			dict: Amendment response
		"""
		try:
			emanifest_doc = frappe.get_doc("CA eManifest Forwarder", filing_doc)
			
			# Validate document
			if emanifest_doc.submission_type != "Amendment":
				return {
					"success": False,
					"message": _("Submission type must be 'Amendment' for amendments.")
				}
			
			return self.block_filing()
			
		except frappe.DoesNotExistError:
			return {
				"success": False,
				"message": _("CA eManifest document {0} not found.").format(filing_doc)
			}
		except Exception as e:
			frappe.log_error(f"Error amending CA eManifest: {str(e)}", "CA eManifest API Error")
			return {
				"success": False,
				"message": _("Error amending CA eManifest: {0}").format(str(e))
			}
	
	def cancel(self, filing_doc: str, reason: str = None) -> Dict[str, Any]:
		"""
		Cancel CA eManifest filing.
		
		Args:
			filing_doc: Name of the CA eManifest Forwarder document
			reason: Reason for cancellation
			
		Returns:
			dict: Cancellation response
		"""
		try:
			emanifest_doc = frappe.get_doc("CA eManifest Forwarder", filing_doc)
			
			# Validate document
			if emanifest_doc.submission_type != "Cancellation":
				return {
					"success": False,
					"message": _("Submission type must be 'Cancellation' for cancellation.")
				}
			
			return self.block_filing()
			
		except frappe.DoesNotExistError:
			return {
				"success": False,
				"message": _("CA eManifest document {0} not found.").format(filing_doc)
			}
		except Exception as e:
			frappe.log_error(f"Error cancelling CA eManifest: {str(e)}", "CA eManifest API Error")
			return {
				"success": False,
				"message": _("Error cancelling CA eManifest: {0}").format(str(e))
			}

