# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Outlook integration install helpers."""

from __future__ import annotations

import frappe

from logistics.integrations.outlook.utils import OUTLOOK_PROVIDER_NAME

OUTLOOK_SCOPES = [
	"openid",
	"profile",
	"offline_access",
	"User.Read",
	"Calendars.ReadWrite",
]


def create_connected_app() -> str:
	"""Create the Microsoft Outlook Connected App skeleton if missing."""
	connected_app_name = OUTLOOK_PROVIDER_NAME
	existing_name = frappe.db.get_value(
		"Connected App", {"provider_name": connected_app_name}, "name"
	)
	if existing_name:
		if existing_name != connected_app_name:
			frappe.rename_doc("Connected App", existing_name, connected_app_name, force=True)
		return connected_app_name

	if frappe.db.exists("Connected App", connected_app_name):
		return connected_app_name

	doc = frappe.new_doc("Connected App")
	doc.name = connected_app_name
	doc.provider_name = connected_app_name
	doc.client_id = ""
	doc.authorization_uri = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
	doc.token_uri = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
	for scope in OUTLOOK_SCOPES:
		doc.append("scopes", {"scope": scope})
	doc.insert(ignore_permissions=True)
	return connected_app_name


def before_install():
	"""Seed Connected App before singles init during fresh app install."""
	create_connected_app()
	frappe.db.commit()
