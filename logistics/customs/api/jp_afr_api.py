# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
JP AFR (Japan Advance Filing Rules) API Integration.

Filing actions do not write a mock status. They refuse unless Manifest Settings
has a live Japan Customs endpoint, and they still leave the document unchanged
because this client does not call that endpoint yet.
"""

import frappe
from typing import Dict, Any
from .base_api import BaseCustomsAPI
from frappe import _


class JPAFRAPI(BaseCustomsAPI):
	"""API client for JP AFR (Japan Customs Advance Filing Rules)"""
	
	def __init__(self, company: str = None):
		super().__init__(company)
		self.api_name = "JP AFR"
		self.endpoint_field = "japan_customs_api_endpoint"
		self.endpoint = self.configured_endpoint()
		self.credentials = self._get_credentials()
	
	def _get_credentials(self) -> Dict[str, str]:
		"""Get API credentials from settings"""
		if not self.settings:
			return {}
		
		return {
			"filer_code": getattr(self.settings, 'japan_customs_filer_code', '')
		}
	
	def submit(self, filing_doc: str) -> Dict[str, Any]:
		"""
		Submit JP AFR filing to Japan Customs.
		
		Args:
			filing_doc: Name of the JP AFR document
			
		Returns:
			dict: Response with Japan Customs number, status, etc.
		"""
		try:
			afr_doc = frappe.get_doc("JP AFR", filing_doc)
			
			# Validate document
			if afr_doc.status != "Draft":
				return {
					"success": False,
					"message": _("Only Draft AFR can be submitted.")
				}
			
			return self.block_filing()
			
		except frappe.DoesNotExistError:
			return {
				"success": False,
				"message": _("JP AFR document {0} not found.").format(filing_doc)
			}
		except Exception as e:
			frappe.log_error(f"Error submitting JP AFR: {str(e)}", "JP AFR API Error")
			return {
				"success": False,
				"message": _("Error submitting JP AFR: {0}").format(str(e))
			}
	
	def check_status(self, filing_doc: str) -> Dict[str, Any]:
		"""
		Check status of submitted JP AFR filing.
		
		Args:
			filing_doc: Name of the JP AFR document
			
		Returns:
			dict: Current status information
		"""
		try:
			afr_doc = frappe.get_doc("JP AFR", filing_doc)
			
			return self.block_filing()
			
		except frappe.DoesNotExistError:
			return {
				"success": False,
				"message": _("JP AFR document {0} not found.").format(filing_doc)
			}
		except Exception as e:
			frappe.log_error(f"Error checking JP AFR status: {str(e)}", "JP AFR API Error")
			return {
				"success": False,
				"message": _("Error checking JP AFR status: {0}").format(str(e))
			}
	
	def amend(self, filing_doc: str, amendment_data: Dict = None) -> Dict[str, Any]:
		"""
		Submit an amendment to JP AFR filing.
		
		Args:
			filing_doc: Name of the JP AFR document
			amendment_data: Data for the amendment
			
		Returns:
			dict: Amendment response
		"""
		try:
			afr_doc = frappe.get_doc("JP AFR", filing_doc)
			
			# Validate document
			if afr_doc.submission_type != "Amendment":
				return {
					"success": False,
					"message": _("Submission type must be 'Amendment' for amendments.")
				}
			
			return self.block_filing()
			
		except frappe.DoesNotExistError:
			return {
				"success": False,
				"message": _("JP AFR document {0} not found.").format(filing_doc)
			}
		except Exception as e:
			frappe.log_error(f"Error amending JP AFR: {str(e)}", "JP AFR API Error")
			return {
				"success": False,
				"message": _("Error amending JP AFR: {0}").format(str(e))
			}
	
	def cancel(self, filing_doc: str, reason: str = None) -> Dict[str, Any]:
		"""
		Cancel JP AFR filing.
		
		Args:
			filing_doc: Name of the JP AFR document
			reason: Reason for cancellation
			
		Returns:
			dict: Cancellation response
		"""
		try:
			afr_doc = frappe.get_doc("JP AFR", filing_doc)
			
			# Validate document
			if afr_doc.submission_type != "Cancellation":
				return {
					"success": False,
					"message": _("Submission type must be 'Cancellation' for cancellation.")
				}
			
			return self.block_filing()
			
		except frappe.DoesNotExistError:
			return {
				"success": False,
				"message": _("JP AFR document {0} not found.").format(filing_doc)
			}
		except Exception as e:
			frappe.log_error(f"Error cancelling JP AFR: {str(e)}", "JP AFR API Error")
			return {
				"success": False,
				"message": _("Error cancelling JP AFR: {0}").format(str(e))
			}

