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

		if self.test_mode and self.ccs_test_endpoint:
			validate_url(
				self.ccs_test_endpoint,
				throw=True,
				fieldname="ccs_test_endpoint",
			)

		if not self.cargo_xml_enabled:
			return

		connection_mode = self.connection_mode or "Direct"

		if connection_mode == "Direct" and not self.test_mode:
			if not self.cargo_xml_endpoint:
				frappe.throw(_("Cargo-XML Endpoint URL is required when using Direct connection mode"))
			if not self.cargo_xml_username:
				frappe.throw(_("Username is required when Cargo-XML is enabled"))
			if not self.cargo_xml_password and not self.get_password("cargo_xml_password"):
				frappe.throw(_("Password is required when Cargo-XML is enabled"))

		if connection_mode == "CCS Hub" and not self.test_mode:
			self._validate_ccs_hub_settings()

		if connection_mode == "CCS Hub" and self.test_mode and not self.test_endpoint and not self.ccs_test_endpoint:
			provider_test_endpoint = None
			if self.ccs_provider:
				provider_test_endpoint = frappe.db.get_value(
					"CCS Provider", self.ccs_provider, "test_endpoint"
				)
			if not provider_test_endpoint:
				# Sandbox mock is still allowed without a CCS test endpoint.
				pass

	def _validate_ccs_hub_settings(self):
		if not self.ccs_provider:
			frappe.throw(_("CCS Provider is required when Connection Mode is CCS Hub"))
		if not frappe.db.exists("CCS Provider", self.ccs_provider):
			frappe.throw(_("CCS Provider {0} does not exist").format(self.ccs_provider))

		provider_endpoint = frappe.db.get_value(
			"CCS Provider", self.ccs_provider, "default_endpoint"
		)
		if not self.ccs_endpoint and not provider_endpoint:
			frappe.throw(
				_(
					"CCS Endpoint URL is required. Set CCS Endpoint URL Override in IATA Settings "
					"or Default Endpoint URL on CCS Provider {0}."
				).format(self.ccs_provider)
			)

		if not self.ccs_participant_code:
			frappe.throw(_("CCS Participant Code (PIMA) is required when Connection Mode is CCS Hub"))

		ccs_password = self.get_password("ccs_password", raise_exception=False)
		cargo_password = self.get_password("cargo_xml_password", raise_exception=False)
		username = self.ccs_username or self.cargo_xml_username
		if not username:
			frappe.throw(_("CCS Username or Cargo-XML Username is required for CCS Hub connectivity"))
		if not ccs_password and not cargo_password:
			frappe.throw(_("CCS Password or Cargo-XML Password is required for CCS Hub connectivity"))

		if self.ccs_endpoint:
			validate_url(self.ccs_endpoint, throw=True, fieldname="ccs_endpoint")

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
