# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import validate_url

from logistics.air_freight.utils.iata_settings_utils import (
	PUBLIC_SETTINGS_FIELDS,
	default_settings,
	get_public_settings,
	get_settings,
	resolve_company,
)


class IATASettings(Document):
	resolve_company = staticmethod(resolve_company)
	get_settings = staticmethod(get_settings)
	get_public_settings = staticmethod(get_public_settings)
	_default_settings = staticmethod(default_settings)

	def validate(self):
		"""Validate IATA Settings"""
		if not self.company:
			frappe.throw(_("Company is required"))

		if self.test_mode and self.test_endpoint:
			validate_url(
				self.test_endpoint,
				throw=True,
				fieldname="test_endpoint",
			)

		if self.cargo_xml_enabled and not self.test_mode:
			if not self.cargo_xml_endpoint:
				frappe.throw(_("Cargo-XML Endpoint URL is required when Cargo-XML is enabled"))
			if not self.cargo_xml_username:
				frappe.throw(_("Username is required when Cargo-XML is enabled"))
			if not self.cargo_xml_password and not self.get_password("cargo_xml_password"):
				frappe.throw(_("Password is required when Cargo-XML is enabled"))

		if self.dg_autocheck_enabled and not self.dg_autocheck_api_key:
			frappe.throw(_("DG AutoCheck API Key is required when DG AutoCheck is enabled"))

		if self.cass_enabled and not self.cass_participant_code:
			frappe.throw(_("CASS Participant Code is required when CASSLink is enabled"))

		if self.cass_enabled and not self.cass_api_endpoint:
			frappe.throw(_("CASS API Endpoint is required when CASSLink is enabled"))

		if self.tact_subscription and not self.tact_api_key:
			frappe.throw(_("TACT API Key is required when TACT Subscription is enabled"))

		if self.tact_subscription and not self.tact_endpoint:
			frappe.throw(_("TACT Endpoint is required when TACT Subscription is enabled"))

	def on_update(self):
		"""Called after saving"""
		frappe.msgprint(_("IATA Settings updated successfully"))

		frappe.clear_cache()
		frappe.logger().info(
			f"IATA Settings updated for company {self.company} by {frappe.session.user}"
		)
