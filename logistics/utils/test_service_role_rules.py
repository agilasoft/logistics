# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for service_role rules on operational documents."""

from __future__ import unicode_literals

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from logistics.utils.service_role_rules import (
	SERVICE_ROLE_LINKED,
	SERVICE_ROLE_MAIN,
	apply_linked_service_satellite_flags,
	apply_service_role_rules,
	get_main_service_name,
	get_main_service_type,
	get_service_role,
	sync_main_service_refs,
)


class TestServiceRoleRules(IntegrationTestCase):
	def test_legacy_flags_map_to_service_role(self):
		doc = frappe._dict(is_main_service=1, is_internal_job=0)
		self.assertEqual(get_service_role(doc), SERVICE_ROLE_MAIN)
		doc = frappe._dict(
			is_main_service=0,
			is_internal_job=1,
			main_job_type="Transport Order",
			main_job="TO-00001",
		)
		self.assertEqual(get_service_role(doc), SERVICE_ROLE_LINKED)

	def test_main_service_fields_map_to_linked_role(self):
		doc = frappe._dict(
			service_role="Linked",
			main_service_type="Sea Shipment",
			main_service="SS-00001",
		)
		self.assertEqual(get_service_role(doc), SERVICE_ROLE_LINKED)
		self.assertEqual(get_main_service_type(doc), "Sea Shipment")
		self.assertEqual(get_main_service_name(doc), "SS-00001")

	def test_sync_main_service_refs_writes_main_service_fields(self):
		doc = frappe._dict(
			service_role="Linked",
			main_job_type="Air Shipment",
			main_job="AS-00001",
			main_service_type=None,
			main_service=None,
		)
		sync_main_service_refs(doc)
		self.assertEqual(doc.main_service_type, "Air Shipment")
		self.assertEqual(doc.main_service, "AS-00001")

	def test_apply_linked_service_satellite_flags(self):
		doc = frappe._dict(
			service_role="Standalone",
			main_service_type=None,
			main_service=None,
		)
		apply_linked_service_satellite_flags(doc, "Transport Job", "TJ-00001")
		self.assertEqual(doc.service_role, SERVICE_ROLE_LINKED)
		self.assertEqual(doc.main_service_type, "Transport Job")
		self.assertEqual(doc.main_service, "TJ-00001")


class TestOneOffQuoteValidateOrder(UnitTestCase):
	"""One-off MS/IJ stamping must run before assert_one_off_sales_quote_job_rules."""

	def test_one_off_sales_quote_stamps_main_service_before_assert(self):
		doc = frappe._dict(
			doctype="Air Booking",
			sales_quote="OOQ-VALIDATE-ORDER",
			service_role="Standalone",
			main_service_type=None,
			main_service=None,
		)
		with patch(
			"logistics.utils.sales_quote_ms_ij_rules.get_sales_quote_quotation_type",
			return_value="One-off",
		):
			apply_service_role_rules(doc)
		self.assertEqual(doc.service_role, SERVICE_ROLE_MAIN)
