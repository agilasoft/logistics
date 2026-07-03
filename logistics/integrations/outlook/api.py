# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Whitelisted API methods for Outlook calendar connection and sync."""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import get_url_to_form

from logistics.integrations.outlook.graph_client import (
	OutlookGraphClient,
	get_outlook_calendar_settings,
	is_outlook_sync_enabled,
)
from logistics.integrations.outlook.utils import ensure_outlook_connected_app_name, get_outlook_connected_app_name
from logistics.integrations.outlook.task_sync import sync_all_tasks_for_user


@frappe.whitelist()
def get_connection_status(user: str | None = None) -> dict:
	user = user or frappe.session.user
	settings = get_outlook_calendar_settings()
	connected_app_name = settings.connected_app or get_outlook_connected_app_name()
	connected = OutlookGraphClient(user).has_token() if connected_app_name else False
	opted_in = bool(frappe.db.get_value("User", user, "sync_erpnext_tasks_to_outlook"))
	return {
		"connected": connected,
		"opted_in": opted_in,
		"sync_enabled": is_outlook_sync_enabled(),
		"connected_app": connected_app_name,
	}


@frappe.whitelist()
def connect_outlook(user: str | None = None) -> str:
	user = user or frappe.session.user
	_ensure_self_or_manager(user)

	settings = get_outlook_calendar_settings()
	connected_app_name = settings.connected_app or ensure_outlook_connected_app_name()
	if not frappe.db.get_value("Connected App", connected_app_name, "client_id"):
		frappe.throw(
			_("Configure Client ID and Client Secret on Connected App {0} before connecting.").format(
				connected_app_name
			)
		)

	connected_app = frappe.get_doc("Connected App", connected_app_name)
	success_uri = get_url_to_form("User", user)
	return connected_app.initiate_web_application_flow(user=user, success_uri=success_uri)


@frappe.whitelist()
def disconnect_outlook(user: str | None = None) -> dict:
	user = user or frappe.session.user
	_ensure_self_or_manager(user)

	settings = get_outlook_calendar_settings()
	connected_app_name = settings.connected_app or ensure_outlook_connected_app_name()
	token_cache_name = f"{connected_app_name}-{user}"
	if frappe.db.exists("Token Cache", token_cache_name):
		frappe.delete_doc("Token Cache", token_cache_name, ignore_permissions=True)

	frappe.db.set_value("User", user, "sync_erpnext_tasks_to_outlook", 0, update_modified=False)
	frappe.db.commit()
	return {"disconnected": True}


@frappe.whitelist()
def sync_now(user: str | None = None) -> dict:
	user = user or frappe.session.user
	_ensure_self_or_manager(user)

	if not is_outlook_sync_enabled():
		frappe.throw(_("Outlook task sync is disabled in Outlook Calendar Settings."))

	if not OutlookGraphClient(user).has_token():
		frappe.throw(_("Connect Outlook before running sync."))

	if not frappe.db.get_value("User", user, "sync_erpnext_tasks_to_outlook"):
		frappe.db.set_value("User", user, "sync_erpnext_tasks_to_outlook", 1, update_modified=False)

	frappe.enqueue(
		"logistics.integrations.outlook.task_sync.sync_all_tasks_for_user",
		user=user,
		queue="long",
	)
	return {"queued": True}


def _ensure_self_or_manager(user: str) -> None:
	if user != frappe.session.user and "System Manager" not in frappe.get_roles():
		frappe.throw(_("Not permitted to manage Outlook connection for another user."))
