"""
IATA Cargo-XML Base Connector
Base class for all IATA integrations providing common functionality
"""

import frappe
import requests
import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, Tuple
from datetime import datetime


class IATAConnector:
	"""Base class for IATA API integrations"""

	def __init__(self, company=None):
		from logistics.air_freight.utils.iata_settings_utils import default_settings, get_settings

		self.company = company
		self.settings = get_settings(company=company) or default_settings()
		self.session = requests.Session()
		self.session.headers.update({
			"Content-Type": "application/xml",
			"Accept": "application/xml",
		})

	@staticmethod
	def _default_settings():
		return frappe._dict(
			test_mode=0,
			test_endpoint=None,
			cargo_xml_enabled=0,
			cargo_xml_endpoint=None,
			cargo_xml_username=None,
			connection_mode="Direct",
			ccs_provider=None,
			ccs_participant_code=None,
			ccs_endpoint=None,
			ccs_test_endpoint=None,
			debug_logging=0,
		)

	def _get_cargo_xml_password(self):
		if isinstance(self.settings, frappe._dict) or not hasattr(self.settings, "get_password"):
			return None
		return self.settings.get_password("cargo_xml_password", raise_exception=False)

	def _get_ccs_password(self):
		if isinstance(self.settings, frappe._dict) or not hasattr(self.settings, "get_password"):
			return None
		return self.settings.get_password("ccs_password", raise_exception=False)

	def get_sandbox_mode(self) -> str:
		"""Return sandbox_mock, sandbox_endpoint, or production."""
		if self.settings.test_mode:
			if self._has_test_endpoint():
				return "sandbox_endpoint"
			return "sandbox_mock"
		return "production"

	def uses_ccs_hub(self) -> bool:
		from logistics.air_freight.iata_cargo_xml.ccs.factory import uses_ccs_hub

		return uses_ccs_hub(self.settings)

	def _has_test_endpoint(self) -> bool:
		if self.settings.test_endpoint:
			return True
		if self.uses_ccs_hub():
			if getattr(self.settings, "ccs_test_endpoint", None):
				return True
			provider = getattr(self.settings, "ccs_provider", None)
			if provider and frappe.db.get_value("CCS Provider", provider, "test_endpoint"):
				return True
		return False

	def _resolve_endpoint(self, endpoint_override: Optional[str] = None) -> Tuple[Optional[str], str]:
		mode = self.get_sandbox_mode()
		if mode == "sandbox_mock":
			return None, mode

		if self.uses_ccs_hub():
			from logistics.air_freight.iata_cargo_xml.ccs.factory import resolve_ccs_endpoint

			test_mode = mode == "sandbox_endpoint"
			endpoint, route_mode = resolve_ccs_endpoint(self.settings, test_mode=test_mode)
			if endpoint_override:
				endpoint = endpoint_override
			return endpoint, route_mode if not test_mode else f"{route_mode}_test"

		if mode == "sandbox_endpoint":
			return endpoint_override or self.settings.test_endpoint, mode
		return endpoint_override or self.settings.cargo_xml_endpoint, mode

	def authenticate(self, sandbox_mode: Optional[str] = None) -> bool:
		"""Handle IATA API authentication."""
		try:
			mode = sandbox_mode or self.get_sandbox_mode()
			if mode in ("sandbox_mock", "sandbox_endpoint"):
				password = self._get_cargo_xml_password()
				if self.settings.cargo_xml_username and password:
					self.session.auth = (self.settings.cargo_xml_username, password)
				ccs_password = self._get_ccs_password()
				ccs_username = getattr(self.settings, "ccs_username", None)
				if ccs_username and ccs_password:
					self.session.auth = (ccs_username, ccs_password)
				return True

			if self.uses_ccs_hub():
				ccs_password = self._get_ccs_password()
				ccs_username = getattr(self.settings, "ccs_username", None) or getattr(
					self.settings, "cargo_xml_username", None
				)
				password = ccs_password or self._get_cargo_xml_password()
				if ccs_username and password:
					self.session.auth = (ccs_username, password)
				return True

			if not self.settings.cargo_xml_enabled:
				frappe.throw("IATA Cargo-XML is not enabled")

			password = self._get_cargo_xml_password()
			if self.settings.cargo_xml_username and password:
				self.session.auth = (self.settings.cargo_xml_username, password)

			return True
		except Exception as e:
			frappe.log_error(f"IATA Authentication Error: {str(e)}")
			return False

	def validate_message(self, message: str, schema_type: str = "FWB") -> Dict[str, Any]:
		"""Validate XML message against IATA schema."""
		try:
			root = ET.fromstring(message)

			if schema_type == "FWB":
				return self._validate_fwb_message(root)
			if schema_type == "XFWB":
				return self._validate_xfwb_message(root)
			if schema_type == "FSU":
				return self._validate_fsu_message(root)
			if schema_type == "FMA":
				return self._validate_fma_message(root)

			return {"valid": True, "errors": [], "warnings": []}

		except ET.ParseError as e:
			return {
				"valid": False,
				"errors": [f"XML Parse Error: {str(e)}"],
				"warnings": [],
			}
		except Exception as e:
			frappe.log_error(f"Message validation error: {str(e)}")
			return {
				"valid": False,
				"errors": [f"Validation Error: {str(e)}"],
				"warnings": [],
			}

	def send_message(
		self,
		message_type: str,
		content: str,
		endpoint: Optional[str] = None,
		reference_doctype: Optional[str] = None,
		reference_name: Optional[str] = None,
		airline: Optional[str] = None,
	) -> Dict[str, Any]:
		"""Send message to IATA platform (production, sandbox endpoint, CCS hub, or in-app mock)."""
		try:
			from logistics.air_freight.iata_cargo_xml.ccs.routing import (
				build_routing_context,
				resolve_airline_from_reference,
			)

			resolved_endpoint, mode = self._resolve_endpoint(endpoint)
			self._debug_log(f"send_message mode={mode} type={message_type} ref={reference_name}")

			if mode != "sandbox_mock":
				if not self.authenticate(sandbox_mode=mode):
					raise Exception("Authentication failed")

			validation = self.validate_message(content, message_type)
			if not validation["valid"]:
				raise Exception(f"Message validation failed: {validation['errors']}")

			if mode == "sandbox_mock":
				return self._send_sandbox_mock(
					message_type,
					content,
					validation,
					reference_doctype=reference_doctype,
					reference_name=reference_name,
				)

			if not resolved_endpoint:
				raise Exception("No endpoint configured")

			routing_airline = airline or resolve_airline_from_reference(
				reference_doctype, reference_name
			)
			routing_context = build_routing_context(
				airline=routing_airline,
				reference_doctype=reference_doctype,
				reference_name=reference_name,
				awb_number=self._extract_awb_from_content(content),
			)

			if self.uses_ccs_hub() and mode not in ("sandbox_mock",):
				from logistics.air_freight.iata_cargo_xml.ccs.factory import get_ccs_connector

				ccs_result = get_ccs_connector(self.settings).send(
					message_type=message_type,
					content=content,
					session=self.session,
					routing_context=routing_context,
					validation=validation,
					test_mode=mode.endswith("_test") or mode == "sandbox_endpoint",
				)
				self.log_transaction({
					"message_type": message_type,
					"direction": "outbound",
					"status": "Sent" if ccs_result.get("success") else "Failed",
					"message_content": content[:5000],
					"response_content": (ccs_result.get("response") or "")[:1000],
					"reference_doctype": reference_doctype,
					"reference_name": reference_name,
					"timestamp": datetime.now().isoformat(),
				})
				return ccs_result

			response = self.session.post(resolved_endpoint, data=content, timeout=30)

			self.log_transaction({
				"message_type": message_type,
				"direction": "outbound",
				"status": "Sent" if response.status_code == 200 else "Failed",
				"message_content": content[:5000],
				"response_content": response.text[:1000],
				"reference_doctype": reference_doctype,
				"reference_name": reference_name,
				"timestamp": datetime.now().isoformat(),
			})

			accepted = self._response_indicates_acceptance(response.status_code, response.text)

			return {
				"success": response.status_code == 200,
				"accepted": accepted,
				"status_code": response.status_code,
				"response": response.text,
				"validation": validation,
				"sandbox_mode": mode,
			}

		except Exception as e:
			frappe.log_error(f"Send message error: {str(e)}")
			return {
				"success": False,
				"accepted": False,
				"error": str(e),
				"validation": {"valid": False, "errors": [str(e)], "warnings": []},
				"sandbox_mode": self.get_sandbox_mode(),
			}

	def _send_sandbox_mock(
		self,
		message_type: str,
		content: str,
		validation: Dict[str, Any],
		reference_doctype: Optional[str] = None,
		reference_name: Optional[str] = None,
	) -> Dict[str, Any]:
		"""Simulate IATA acceptance without external HTTP."""
		awb_no = self._extract_awb_from_content(content)
		message_id = f"SANDBOX_{message_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
		response_xml = (
			f'<Acknowledgement xmlns="http://www.iata.org/IATA/CargoXML/1.0" '
			f'Status="Accepted" MessageId="{message_id}" AWBNo="{awb_no or ""}" />'
		)

		queue_name = self.log_transaction({
			"message_type": message_type,
			"direction": "outbound",
			"status": "Sent",
			"message_content": content[:5000],
			"response_content": response_xml,
			"reference_doctype": reference_doctype,
			"reference_name": reference_name,
			"message_id": message_id,
			"timestamp": datetime.now().isoformat(),
		})

		return {
			"success": True,
			"accepted": True,
			"status_code": 200,
			"response": response_xml,
			"validation": validation,
			"sandbox_mode": "sandbox_mock",
			"message_id": message_id,
			"message_queue": queue_name,
		}

	def _extract_awb_from_content(self, content: str) -> Optional[str]:
		try:
			root = ET.fromstring(content)
			awb = self._find_element(root, "AirWaybill")
			if awb is not None:
				return awb.get("AWBNo")
		except Exception:
			pass
		return None

	def _response_indicates_acceptance(self, status_code: int, response_text: str) -> bool:
		if status_code != 200:
			return False
		if not response_text:
			return True
		lower = response_text.lower()
		if "rejected" in lower or "error" in lower:
			return False
		if "accepted" in lower or "acknowledgement" in lower or "success" in lower:
			return True
		return True

	def _debug_log(self, message: str) -> None:
		if self.settings.debug_logging:
			frappe.log_error(message, "IATA Sandbox")

	def receive_message(self, message_type: str, content: str) -> Dict[str, Any]:
		"""Receive and process incoming messages."""
		try:
			root = ET.fromstring(content)
			message_data = self._extract_message_data(root, message_type)

			self.log_transaction({
				"message_type": message_type,
				"direction": "inbound",
				"status": "Received",
				"message_data": message_data,
				"timestamp": datetime.now().isoformat(),
			})

			return {"success": True, "data": message_data}

		except Exception as e:
			frappe.log_error(f"Receive message error: {str(e)}")
			return {"success": False, "error": str(e)}

	def log_transaction(self, transaction_data: Dict[str, Any]) -> Optional[str]:
		"""Log all API transactions for audit. Returns queue document name."""
		try:
			message_queue = frappe.get_doc({
				"doctype": "IATA Message Queue",
				"message_type": transaction_data.get("message_type"),
				"direction": transaction_data.get("direction", "").title()
				if transaction_data.get("direction")
				else None,
				"status": transaction_data.get("status"),
				"message_content": transaction_data.get("message_content")
				or transaction_data.get("response_content", ""),
				"response_content": transaction_data.get("response_content"),
				"reference_doctype": transaction_data.get("reference_doctype"),
				"reference_name": transaction_data.get("reference_name"),
				"message_id": transaction_data.get("message_id"),
				"error_log": json.dumps(transaction_data.get("errors", [])),
				"retry_count": 0,
			})
			message_queue.insert(ignore_permissions=True)
			return message_queue.name

		except Exception as e:
			frappe.log_error(f"Transaction logging error: {str(e)}")
			return None

	def _find_element(self, root: ET.Element, local_name: str) -> Optional[ET.Element]:
		found = root.find(local_name)
		if found is not None:
			return found
		for elem in root.iter():
			if elem.tag.split("}")[-1] == local_name:
				return elem
		return None

	def _validate_fwb_message(self, root: ET.Element) -> Dict[str, Any]:
		errors = []
		required_elements = [
			"MessageHeader",
			"AirWaybill",
			"Origin",
			"Destination",
			"Shipper",
			"Consignee",
		]
		for element in required_elements:
			if self._find_element(root, element) is None:
				errors.append(f"Missing required element: {element}")
		return {"valid": len(errors) == 0, "errors": errors, "warnings": []}

	def _validate_xfwb_message(self, root: ET.Element) -> Dict[str, Any]:
		errors = []
		required_elements = [
			"MessageHeader",
			"AirWaybill",
			"Origin",
			"Destination",
			"FlightInfo",
		]
		for element in required_elements:
			if self._find_element(root, element) is None:
				errors.append(f"Missing required element: {element}")
		awb = self._find_element(root, "AirWaybill")
		if awb is not None and awb.get("AWBType") != "M":
			errors.append("Master e-AWB requires AWBType M")
		return {"valid": len(errors) == 0, "errors": errors, "warnings": []}

	def _validate_fsu_message(self, root: ET.Element) -> Dict[str, Any]:
		errors = []
		required_elements = ["MessageHeader", "AirWaybill", "StatusUpdate"]
		for element in required_elements:
			if self._find_element(root, element) is None:
				errors.append(f"Missing required element: {element}")
		return {"valid": len(errors) == 0, "errors": errors, "warnings": []}

	def _validate_fma_message(self, root: ET.Element) -> Dict[str, Any]:
		errors = []
		required_elements = ["MessageHeader", "FlightInfo", "CargoManifest"]
		for element in required_elements:
			if self._find_element(root, element) is None:
				errors.append(f"Missing required element: {element}")
		return {"valid": len(errors) == 0, "errors": errors, "warnings": []}

	def _extract_message_data(self, root: ET.Element, message_type: str) -> Dict[str, Any]:
		data = {}
		try:
			if root.find("MessageHeader") is not None:
				header = root.find("MessageHeader")
			else:
				header = self._find_element(root, "MessageHeader")
			if header is not None:
				data["message_id"] = header.get("MessageId")
				data["sender_id"] = header.get("SenderId")
				data["recipient_id"] = header.get("RecipientId")
				data["timestamp"] = header.get("Timestamp")

			if message_type in ("FWB", "XFWB"):
				data.update(self._extract_fwb_data(root))
			elif message_type == "FSU":
				data.update(self._extract_fsu_data(root))
			elif message_type == "FMA":
				data.update(self._extract_fma_data(root))

		except Exception as e:
			frappe.log_error(f"Data extraction error: {str(e)}")

		return data

	def _extract_fwb_data(self, root: ET.Element) -> Dict[str, Any]:
		data = {}
		if root.find("AirWaybill") is not None:
			awb = root.find("AirWaybill")
			data["awb_number"] = awb.get("AWBNo")
			data["awb_type"] = awb.get("AWBType")
		if root.find("Origin") is not None:
			data["origin_airport"] = root.find("Origin").get("AirportCode")
		if root.find("Destination") is not None:
			data["destination_airport"] = root.find("Destination").get("AirportCode")
		return data

	def _extract_fsu_data(self, root: ET.Element) -> Dict[str, Any]:
		data = {}
		if root.find("AirWaybill") is not None:
			data["awb_number"] = root.find("AirWaybill").get("AWBNo")
		if root.find("StatusUpdate") is not None:
			status = root.find("StatusUpdate")
			data["status_code"] = status.get("StatusCode")
			data["status_description"] = status.get("StatusDescription")
			data["timestamp"] = status.get("Timestamp")
		return data

	def _extract_fma_data(self, root: ET.Element) -> Dict[str, Any]:
		data = {}
		if root.find("FlightInfo") is not None:
			flight = root.find("FlightInfo")
			data["flight_number"] = flight.get("FlightNo")
			data["flight_date"] = flight.get("FlightDate")
		return data
