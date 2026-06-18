# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for service_scope auto-tagging on Sales Quote child rows."""

from __future__ import unicode_literals

import frappe
from frappe.tests import IntegrationTestCase


class TestServiceScopeTagging(IntegrationTestCase):
	def test_stamp_service_scope_on_child_rows_without_save(self):
		sq = frappe.new_doc("Sales Quote")
		sq.name = "OOQ-TEST-SCOPE-001"
		sq.append("charges", {"service_type": "Air", "charge_scope": "Main"})
		ls_field = "linked_services" if sq.meta.has_field("linked_services") else "internal_job_details"
		sq.append(ls_field, {"service_type": "Customs"})
		sq.stamp_service_scope_on_child_rows()
		self.assertEqual(sq.charges[0].service_scope, sq.name)
		self.assertEqual(sq.get(ls_field)[0].service_scope, sq.name)

	def test_linked_charge_scope_requires_linked_service(self):
		sq = frappe.new_doc("Sales Quote")
		sq.name = "OOQ-TEST-SCOPE-002"
		sq.append("charges", {"service_type": "Transport", "charge_scope": "Linked"})
		with self.assertRaises(frappe.ValidationError):
			sq.validate_linked_service_charge_tagging()
