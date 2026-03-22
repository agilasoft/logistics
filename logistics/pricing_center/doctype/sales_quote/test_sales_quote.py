# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today
from logistics.air_freight.tests.test_helpers import (
	setup_basic_master_data,
	create_test_shipper,
	create_test_consignee,
	create_test_unloco,
)


class TestSalesQuote(FrappeTestCase):
	"""Test cases for Sales Quote doctype"""

	def setUp(self):
		"""Set up test data"""
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		self.shipper = create_test_shipper()
		self.consignee = create_test_consignee()
		create_test_unloco("USLAX", "Los Angeles", "LAX", "US", "Airport")
		create_test_unloco("USJFK", "New York JFK", "JFK", "US", "Airport")

	def tearDown(self):
		frappe.db.rollback()

	def test_sales_quote_creation(self):
		"""Test creating a basic Sales Quote with Air charges"""
		sq = frappe.get_doc({
			"doctype": "Sales Quote",
			"company": self.company,
			"customer": self.customer,
			"date": today(),
			"valid_until": today(),
			"shipper": self.shipper,
			"consignee": self.consignee,
			"main_service": "Air",
		})
		sq.append("charges", {
			"service_type": "Air",
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"direction": "Export",
		})
		sq.insert()

		self.assertIsNotNone(sq.name)
		self.assertEqual(sq.customer, self.customer)
		self.assertEqual(len(sq.charges), 1)

	def test_sales_quote_required_fields(self):
		"""Test that required fields are enforced"""
		sq = frappe.get_doc({"doctype": "Sales Quote"})
		with self.assertRaises((frappe.ValidationError, frappe.MandatoryError)):
			sq.insert()

	def test_sales_quote_validation_methods(self):
		"""Test that Sales Quote has expected validation methods"""
		sq = frappe.get_doc({
			"doctype": "Sales Quote",
			"company": self.company,
			"customer": self.customer,
			"date": today(),
			"valid_until": today(),
			"shipper": self.shipper,
			"consignee": self.consignee,
			"main_service": "Air",
		})
		sq.append("charges", {
			"service_type": "Air",
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"direction": "Export",
		})
		self.assertTrue(hasattr(sq, "validate"))
		sq.insert()
		self.assertIsNotNone(sq.name)

	def test_expired_sales_quote_blocks_creation_guard(self):
		"""Valid Until in the past must raise when creating jobs from the quote."""
		from logistics.utils.sales_quote_validity import throw_if_sales_quote_expired_for_creation

		class _Expired:
			valid_until = add_days(today(), -5)

		with self.assertRaises(frappe.ValidationError):
			throw_if_sales_quote_expired_for_creation(_Expired())

		class _Open:
			valid_until = add_days(today(), 7)

		throw_if_sales_quote_expired_for_creation(_Open())

		class _NoEnd:
			valid_until = None

		throw_if_sales_quote_expired_for_creation(_NoEnd())

	def test_extend_sales_quote_validity(self):
		"""Extend Validity updates valid_until on draft; rejects shorten and past dates."""
		from logistics.pricing_center.doctype.sales_quote.sales_quote import extend_sales_quote_validity

		sq = frappe.get_doc({
			"doctype": "Sales Quote",
			"company": self.company,
			"customer": self.customer,
			"date": today(),
			"valid_until": add_days(today(), 7),
			"shipper": self.shipper,
			"consignee": self.consignee,
			"main_service": "Air",
		})
		sq.append("charges", {
			"service_type": "Air",
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"direction": "Export",
		})
		sq.insert()

		target = add_days(today(), 30)
		out = extend_sales_quote_validity(sq.name, target)
		self.assertTrue(out.get("success"))
		sq.reload()
		self.assertEqual(sq.valid_until, target)

		with self.assertRaises(frappe.ValidationError):
			extend_sales_quote_validity(sq.name, add_days(today(), 15))

		with self.assertRaises(frappe.ValidationError):
			extend_sales_quote_validity(sq.name, add_days(today(), -1))
