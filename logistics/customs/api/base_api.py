# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Base API class for Global Customs integrations.
Provides common functionality for all country-specific API implementations.
"""

import frappe
import requests
import json
import time
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from frappe import _
from frappe.utils import now_datetime


class BaseCustomsAPI(ABC):
	"""Base class for all customs API integrations"""
	
	def __init__(self, company: str = None):
		"""
		Initialize the API client.
		
		Args:
			company: Company name for settings lookup
		"""
		self.company = company or frappe.defaults.get_user_default("Company")
		self.settings = self._get_settings()
		self.session = requests.Session()
		self.session.headers.update({
			'Accept': 'application/json',
			'Content-Type': 'application/json',
			'User-Agent': 'Frappe-Logistics/1.0'
		})
		self.api_calls_count = 0
		self.max_retries = 3
		self.retry_delay = 1  # seconds
		
	def _get_settings(self) -> Optional[Dict]:
		"""Get manifest settings for the company"""
		try:
			return frappe.get_doc("Manifest Settings", self.company)
		except frappe.DoesNotExistError:
			frappe.log_error(
				f"Manifest Settings not found for company {self.company}",
				"Customs API Settings Error"
			)
			return None
	
	def make_request(
		self,
		method: str,
		url: str,
		data: Optional[Dict] = None,
		headers: Optional[Dict] = None,
		timeout: int = 30,
		retry: bool = True
	) -> requests.Response:
		"""
		Make HTTP request with retry logic and error handling.
		
		Args:
			method: HTTP method (GET, POST, PUT, DELETE)
			url: API endpoint URL
			data: Request payload
			headers: Additional headers
			timeout: Request timeout in seconds
			retry: Whether to retry on failure
			
		Returns:
			requests.Response: API response
		"""
		if headers:
			request_headers = {**self.session.headers, **headers}
		else:
			request_headers = self.session.headers
		
		attempt = 0
		last_exception = None
		
		while attempt < (self.max_retries if retry else 1):
			try:
				self.api_calls_count += 1
				
				response = self.session.request(
					method=method,
					url=url,
					json=data,
					headers=request_headers,
					timeout=timeout
				)
				
				# Log the request
				self._log_request(method, url, data, response)
				
				# Check for HTTP errors
				response.raise_for_status()
				
				return response
				
			except requests.exceptions.RequestException as e:
				last_exception = e
				attempt += 1
				
				if attempt < self.max_retries and retry:
					# Wait before retrying
					time.sleep(self.retry_delay * attempt)
					frappe.log_error(
						f"API request failed (attempt {attempt}/{self.max_retries}): {str(e)}",
						"Customs API Request Error"
					)
				else:
					# Final attempt failed
					frappe.log_error(
						f"API request failed after {attempt} attempts: {str(e)}",
						"Customs API Request Error"
					)
					raise
		
		# Should not reach here, but just in case
		if last_exception:
			raise last_exception
	
	def _log_request(
		self,
		method: str,
		url: str,
		data: Optional[Dict],
		response: requests.Response
	):
		"""Log API request and response"""
		log_data = {
			"method": method,
			"url": url,
			"status_code": response.status_code,
			"timestamp": str(now_datetime())
		}
		
		# Log request data (sanitized)
		if data:
			log_data["request_data"] = self._sanitize_data(data)
		
		# Log response (sanitized)
		try:
			response_data = response.json()
			log_data["response_data"] = self._sanitize_data(response_data)
		except:
			log_data["response_data"] = response.text[:500]  # First 500 chars
		
		frappe.logger().info(f"Customs API Request: {json.dumps(log_data)}")
	
	def _sanitize_data(self, data: Dict) -> Dict:
		"""Remove sensitive information from log data"""
		sanitized = data.copy()
		sensitive_keys = ['password', 'api_key', 'token', 'secret', 'credential']
		
		for key in sensitive_keys:
			if key in sanitized:
				sanitized[key] = "***REDACTED***"
		
		return sanitized
	
	@abstractmethod
	def submit(self, filing_doc: str) -> Dict[str, Any]:
		"""
		Submit a filing to the customs authority.
		
		Args:
			filing_doc: Name of the filing document (US AMS, CA eManifest, etc.)
			
		Returns:
			dict: Response with transaction number, status, etc.
		"""
		pass
	
	@abstractmethod
	def check_status(self, filing_doc: str) -> Dict[str, Any]:
		"""
		Check the status of a submitted filing.
		
		Args:
			filing_doc: Name of the filing document
			
		Returns:
			dict: Current status information
		"""
		pass
	
	@abstractmethod
	def amend(self, filing_doc: str, amendment_data: Dict) -> Dict[str, Any]:
		"""
		Submit an amendment to an existing filing.
		
		Args:
			filing_doc: Name of the filing document
			amendment_data: Data for the amendment
			
		Returns:
			dict: Amendment response
		"""
		pass
	
	@abstractmethod
	def cancel(self, filing_doc: str, reason: str = None) -> Dict[str, Any]:
		"""
		Cancel a filing.
		
		Args:
			filing_doc: Name of the filing document
			reason: Reason for cancellation
			
		Returns:
			dict: Cancellation response
		"""
		pass
	
	def get_mock_response(self, action: str, success: bool = True) -> Dict[str, Any]:
		"""
		Generate a mock response for stub methods.
		
		Args:
			action: Action type (submit, status, amend, cancel)
			success: Whether the action was successful
			
		Returns:
			dict: Mock response data
		"""
		timestamp = now_datetime().strftime("%Y%m%d%H%M%S")
		
		if action == "submit":
			return {
				"success": success,
				"transaction_number": f"MOCK-{timestamp}",
				"status": "Accepted" if success else "Rejected",
				"message": "Mock submission successful" if success else "Mock submission failed",
				"submission_date": str(now_datetime().date()),
				"submission_time": str(now_datetime().time())
			}
		elif action == "status":
			return {
				"success": success,
				"status": "Accepted",
				"transaction_number": f"MOCK-{timestamp}",
				"last_updated": str(now_datetime())
			}
		elif action == "amend":
			return {
				"success": success,
				"amendment_number": f"AMEND-{timestamp}",
				"status": "Amended" if success else "Amendment Rejected",
				"message": "Mock amendment successful" if success else "Mock amendment failed"
			}
		elif action == "cancel":
			return {
				"success": success,
				"cancellation_number": f"CANCEL-{timestamp}",
				"status": "Cancelled" if success else "Cancellation Failed",
				"message": "Mock cancellation successful" if success else "Mock cancellation failed"
			}
		else:
			return {
				"success": success,
				"message": f"Mock {action} response"
			}

