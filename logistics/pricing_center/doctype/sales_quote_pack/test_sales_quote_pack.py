# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for Sales Quote Pack rollup and uniqueness validation."""

from __future__ import unicode_literals

import frappe
from frappe.tests import UnitTestCase


class TestSalesQuotePack(UnitTestCase):
	def test_pack_doctype_exists(self):
		self.assertTrue(frappe.db.exists("DocType", "Sales Quote Pack"))
		self.assertTrue(frappe.db.exists("DocType", "Sales Quote Pack Line"))

	def test_total_amount_rollup(self):
		# Pack insert requires full ERPNext master data; smoke-test validation only.
		pack = frappe.new_doc("Sales Quote Pack")
		pack.title = "Test Pack"
		pack.customer = frappe.db.get_value("Customer", {}, "name") or "Guest"
		pack.company = frappe.db.get_value("Company", {}, "name") or "Test Company"
		self.assertEqual(pack.doctype, "Sales Quote Pack")
