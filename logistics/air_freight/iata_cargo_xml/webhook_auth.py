# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

import frappe
from frappe import _


def verify_inbound_webhook(company: str = None) -> bool:
	"""Validate inbound Cargo-XML webhook using API key or logged-in system user."""
	from logistics.air_freight.utils.iata_settings_utils import get_settings

	if frappe.session.user and frappe.session.user != "Guest":
		return True

	settings = get_settings(company=company)
	if not settings:
		frappe.throw(_("IATA Settings not found"), frappe.AuthenticationError)

	expected_key = settings.get_password("webhook_api_key", raise_exception=False)
	header_key = frappe.get_request_header("X-IATA-Webhook-Key")
	if expected_key:
		if header_key and header_key == expected_key:
			return True
		frappe.throw(_("Invalid webhook API key"), frappe.AuthenticationError)

	# No key configured — require Authorization bearer matching site config fallback.
	auth_header = frappe.get_request_header("Authorization") or ""
	site_key = frappe.conf.get("iata_webhook_api_key")
	if site_key and auth_header == f"Bearer {site_key}":
		return True

	frappe.throw(
		_("Inbound IATA webhook requires authentication. Configure Webhook API Key in IATA Settings."),
		frappe.AuthenticationError,
	)
