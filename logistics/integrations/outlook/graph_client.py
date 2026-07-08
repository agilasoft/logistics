# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Microsoft Graph API client using Frappe Connected App OAuth tokens."""

from __future__ import annotations

import json

import frappe
import requests
from frappe import _

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
ERPNext_TASK_PROPERTY_ID = (
	"String {a1b2c3d4-e5f6-7890-abcd-ef1234567890} Name erpnext_task_id"
)


class OutlookGraphError(Exception):
	def __init__(self, message, status_code=None, response=None):
		super().__init__(message)
		self.status_code = status_code
		self.response = response


from logistics.integrations.outlook.utils import ensure_outlook_connected_app_name, get_outlook_connected_app_name


class OutlookGraphClient:
	def __init__(self, user: str):
		self.user = user
		self.settings = get_outlook_calendar_settings()
		connected_app_name = self.settings.connected_app or get_outlook_connected_app_name()
		if not connected_app_name:
			raise OutlookGraphError(_("Microsoft Outlook Connected App is not configured."))
		self.connected_app = frappe.get_doc("Connected App", connected_app_name)

	def has_token(self) -> bool:
		token_cache = self.connected_app.get_token_cache(self.user)
		return bool(token_cache and token_cache.get_password("access_token", raise_exception=False))

	def _get_access_token(self) -> str:
		token_cache = self.connected_app.get_active_token(self.user)
		if not token_cache:
			raise OutlookGraphError(
				_("Outlook is not connected for user {0}. Please connect Outlook first.").format(self.user),
				status_code=401,
			)
		token = token_cache.get_password("access_token", raise_exception=False)
		if not token:
			raise OutlookGraphError(
				_("Outlook access token is missing for user {0}.").format(self.user),
				status_code=401,
			)
		return token

	def _request(self, method: str, path: str, **kwargs) -> dict | None:
		url = f"{GRAPH_BASE_URL}{path}"
		headers = kwargs.pop("headers", {})
		headers.setdefault("Content-Type", "application/json")
		headers["Authorization"] = f"Bearer {self._get_access_token()}"

		response = requests.request(method, url, headers=headers, timeout=30, **kwargs)
		if response.status_code == 204:
			return None

		if response.ok:
			if not response.content:
				return {}
			return response.json()

		message = response.text
		try:
			payload = response.json()
			message = payload.get("error", {}).get("message") or message
		except Exception:
			pass
		raise OutlookGraphError(message, status_code=response.status_code, response=response)

	def create_event(self, payload: dict) -> dict:
		return self._request("POST", "/me/events", data=json.dumps(payload))

	def update_event(self, event_id: str, payload: dict) -> dict:
		return self._request("PATCH", f"/me/events/{event_id}", data=json.dumps(payload))

	def delete_event(self, event_id: str) -> None:
		self._request("DELETE", f"/me/events/{event_id}")

	def get_event(self, event_id: str) -> dict:
		return self._request("GET", f"/me/events/{event_id}")


def get_outlook_calendar_settings():
	return frappe.get_single("Outlook Calendar Settings")


def is_outlook_sync_enabled() -> bool:
	try:
		settings = get_outlook_calendar_settings()
	except Exception:
		return False
	return bool(settings.enable_sync and get_outlook_connected_app_name())
