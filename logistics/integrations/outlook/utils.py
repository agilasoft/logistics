# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Shared helpers for Outlook calendar integration."""

from __future__ import annotations

import frappe

OUTLOOK_PROVIDER_NAME = "Microsoft Outlook"


def get_outlook_connected_app_name() -> str | None:
	name = frappe.db.get_value("Connected App", {"provider_name": OUTLOOK_PROVIDER_NAME}, "name")
	if name:
		return name
	if frappe.db.exists("Connected App", OUTLOOK_PROVIDER_NAME):
		return OUTLOOK_PROVIDER_NAME
	return None


def ensure_outlook_connected_app_name() -> str:
	name = get_outlook_connected_app_name()
	if name:
		return name
	frappe.throw(
		frappe._(
			"Connected App for Microsoft Outlook is not configured. Run migrate or create it in Integrations."
		)
	)
