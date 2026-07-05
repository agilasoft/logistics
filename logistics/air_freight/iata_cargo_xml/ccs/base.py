# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

import frappe


class BaseCCSConnector(ABC):
	"""Base class for Cargo Community System outbound connectors."""

	provider_code = "GENERIC"

	def __init__(self, settings, provider_doc):
		self.settings = settings
		self.provider = provider_doc

	def send(
		self,
		message_type: str,
		content: str,
		session,
		routing_context: Optional[Dict[str, Any]] = None,
		validation: Optional[Dict[str, Any]] = None,
		test_mode: bool = False,
	) -> Dict[str, Any]:
		routing_context = routing_context or {}
		endpoint, route_mode = self.resolve_endpoint(test_mode=test_mode)
		if not endpoint:
			raise frappe.ValidationError(
				frappe._("No CCS endpoint configured. Set Default Endpoint on the CCS Provider or override it in IATA Settings.")
			)

		payload = self.prepare_payload(message_type, content, routing_context)
		headers = self.build_headers(message_type, payload, routing_context)
		auth = self.get_auth()

		if auth:
			session.auth = auth

		response = session.post(endpoint, data=payload, headers=headers, timeout=30)

		accepted = response.status_code == 200 and self.response_indicates_acceptance(response.text)
		return {
			"success": response.status_code == 200,
			"accepted": accepted,
			"status_code": response.status_code,
			"response": response.text,
			"validation": validation or {},
			"sandbox_mode": route_mode,
			"ccs_provider": self.provider.provider_code,
			"ccs_endpoint": endpoint,
			"routing": {
				"sender_pima": self.get_sender_pima(),
				"recipient_pima": routing_context.get("airline_pima"),
				"airline": routing_context.get("airline"),
			},
		}

	def resolve_endpoint(self, test_mode: bool = False) -> Tuple[Optional[str], str]:
		if test_mode:
			endpoint = (
				getattr(self.settings, "ccs_test_endpoint", None)
				or getattr(self.settings, "test_endpoint", None)
				or getattr(self.provider, "test_endpoint", None)
			)
			return endpoint, "ccs_sandbox_endpoint"

		endpoint = getattr(self.settings, "ccs_endpoint", None) or getattr(
			self.provider, "default_endpoint", None
		)
		return endpoint, "ccs_production"

	def get_sender_pima(self) -> Optional[str]:
		code = getattr(self.settings, "ccs_participant_code", None)
		return str(code).strip().upper() if code else None

	def get_auth(self) -> Optional[Tuple[str, str]]:
		username = getattr(self.settings, "ccs_username", None) or getattr(
			self.settings, "cargo_xml_username", None
		)
		password = self._get_password("ccs_password") or self._get_password("cargo_xml_password")
		if username and password:
			return username, password
		return None

	def _get_password(self, fieldname: str) -> Optional[str]:
		if hasattr(self.settings, "get_password"):
			return self.settings.get_password(fieldname, raise_exception=False)
		return None

	def prepare_payload(
		self,
		message_type: str,
		content: str,
		routing_context: Dict[str, Any],
	) -> str:
		if not getattr(self.provider, "requires_pima_routing", 1):
			return content
		return self._inject_message_routing(content, message_type, routing_context)

	def _inject_message_routing(
		self,
		content: str,
		message_type: str,
		routing_context: Dict[str, Any],
	) -> str:
		try:
			root = ET.fromstring(content)
		except ET.ParseError:
			return content

		header = self._find_element(root, "MessageHeader")
		if header is None:
			header = ET.SubElement(root, "MessageHeader")

		sender_pima = self.get_sender_pima()
		recipient_pima = routing_context.get("airline_pima")
		if sender_pima:
			header.set("SenderId", sender_pima)
		if recipient_pima:
			header.set("RecipientId", recipient_pima)
		if not header.get("Timestamp"):
			header.set("Timestamp", datetime.now().isoformat())
		if not header.get("MessageType"):
			header.set("MessageType", message_type)

		return ET.tostring(root, encoding="unicode", method="xml")

	def build_headers(
		self,
		message_type: str,
		payload: str,
		routing_context: Dict[str, Any],
	) -> Dict[str, str]:
		headers = {
			"Content-Type": "application/xml",
			"Accept": "application/xml",
			"X-Message-Type": message_type,
		}
		sender_pima = self.get_sender_pima()
		recipient_pima = routing_context.get("airline_pima")
		if sender_pima:
			headers["X-Sender-PIMA"] = sender_pima
		if recipient_pima:
			headers["X-Recipient-PIMA"] = recipient_pima
		awb_number = routing_context.get("awb_number")
		if awb_number:
			headers["X-AWB-No"] = awb_number
		return headers

	@staticmethod
	def response_indicates_acceptance(response_text: str) -> bool:
		if not response_text:
			return True
		lower = response_text.lower()
		if "rejected" in lower or "error" in lower:
			return False
		return True

	@staticmethod
	def _find_element(root: ET.Element, local_name: str) -> Optional[ET.Element]:
		found = root.find(local_name)
		if found is not None:
			return found
		for elem in root.iter():
			if elem.tag.split("}")[-1] == local_name:
				return elem
		return None

	@abstractmethod
	def connector_label(self) -> str:
		pass


class ChampTraxonConnector(BaseCCSConnector):
	provider_code = "CHAMP_TRAXON"

	def connector_label(self) -> str:
		return "CHAMP TRAXON cargoHUB"

	def build_headers(
		self,
		message_type: str,
		payload: str,
		routing_context: Dict[str, Any],
	) -> Dict[str, str]:
		headers = super().build_headers(message_type, payload, routing_context)
		headers["X-CHAMP-Provider"] = "TRAXON"
		headers["X-CHAMP-Message-Format"] = "Cargo-XML"
		return headers


class WiseConnector(BaseCCSConnector):
	provider_code = "WISE"

	def connector_label(self) -> str:
		return "WiseTech CCS"

	def build_headers(
		self,
		message_type: str,
		payload: str,
		routing_context: Dict[str, Any],
	) -> Dict[str, str]:
		headers = super().build_headers(message_type, payload, routing_context)
		headers["X-CCS-Provider"] = "WISE"
		return headers


class GenericCCSConnector(BaseCCSConnector):
	provider_code = "GENERIC"

	def connector_label(self) -> str:
		return self.provider.provider_name or "Custom CCS"
