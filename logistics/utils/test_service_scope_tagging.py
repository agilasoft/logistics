# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for Sales Quote charge scope / linked service tagging."""

from __future__ import unicode_literals

import frappe
from frappe.tests import IntegrationTestCase


class TestServiceScopeTagging(IntegrationTestCase):
	def test_linked_charge_scope_requires_linked_service(self):
		sq = frappe.new_doc("Sales Quote")
		sq.name = "OOQ-TEST-SCOPE-002"
		sq.append("charges", {"service_type": "Transport", "charge_scope": "Linked"})
		with self.assertRaises(frappe.ValidationError):
			sq.validate_linked_service_charge_tagging()
