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
	apply_service_role_rules,
	get_service_role,
)


class TestServiceRoleRules(IntegrationTestCase):
	def test_legacy_flags_map_to_service_role(self):
		doc = frappe._dict(is_main_service=1, is_internal_job=0)
		self.assertEqual(get_service_role(doc), SERVICE_ROLE_MAIN)
		doc = frappe._dict(is_main_service=0, is_internal_job=1, main_job_type="Transport Order", main_job="TO-00001")
		self.assertEqual(get_service_role(doc), SERVICE_ROLE_LINKED)


class TestOneOffQuoteValidateOrder(UnitTestCase):
	"""One-off MS/IJ stamping must run before assert_one_off_sales_quote_job_rules."""

	def test_one_off_sales_quote_stamps_main_service_before_assert(self):
		doc = frappe._dict(
			doctype="Air Booking",
			sales_quote="OOQ-VALIDATE-ORDER",
			is_main_service=0,
			is_internal_job=0,
		)
		with patch(
			"logistics.utils.sales_quote_ms_ij_rules.get_sales_quote_quotation_type",
			return_value="One-off",
		):
			apply_service_role_rules(doc)
		self.assertEqual(doc.is_main_service, 1)
		self.assertEqual(doc.is_internal_job, 0)
