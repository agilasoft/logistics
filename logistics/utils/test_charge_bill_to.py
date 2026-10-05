# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase

from logistics.utils.charge_bill_to import (
	CHARGE_PARENT_DOCTYPES,
	charge_parent_has_bill_to,
	get_default_bill_to,
	get_parent_customer,
)


class TestChargeBillTo(IntegrationTestCase):
	def test_get_parent_customer_prefers_local_customer(self):
		doc = frappe._dict(local_customer="LC-1", customer="C-1")
		self.assertEqual(get_parent_customer(doc), "LC-1")

	def test_get_parent_customer_falls_back_to_customer(self):
		doc = frappe._dict(customer="C-1")
		self.assertEqual(get_parent_customer(doc), "C-1")

	def test_get_default_bill_to_matches_parent_customer(self):
		doc = frappe._dict(local_customer="LC-1")
		self.assertEqual(get_default_bill_to(doc), "LC-1")

	def test_charge_bill_to_meta_has_no_customer_link_filters(self):
		"""Regression #1266: Customer.disabled link_filters require Customer.0 read."""
		for parent_doctype in CHARGE_PARENT_DOCTYPES:
			if not charge_parent_has_bill_to(parent_doctype):
				continue
			child_doctype = frappe.get_meta(parent_doctype).get_field("charges").options
			df = frappe.get_meta(child_doctype).get_field("bill_to")
			self.assertIsNotNone(df, f"missing bill_to on {child_doctype}")
			self.assertFalse(
				df.link_filters,
				f"{child_doctype}.bill_to must not use Customer link_filters (permission error Customer.0)",
			)
