# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for service_role rules on operational documents."""

from __future__ import unicode_literals

import frappe
from frappe.tests import IntegrationTestCase

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

	def test_service_scope_backfilled_from_sales_quote(self):
		doc = frappe._dict(
			service_role=SERVICE_ROLE_MAIN,
			sales_quote="OOQ-TEST",
			service_scope=None,
		)
		if not hasattr(frappe.get_meta("Transport Order"), "service_scope"):
			return
		apply_service_role_rules(doc)
		self.assertEqual(doc.service_scope, "OOQ-TEST")
