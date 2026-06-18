# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from logistics.customs.doctype.declaration.declaration import (
	_copy_order_to_declaration,
	apply_currency_and_exchange_rates_from_declaration_order,
)


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestDeclaration(IntegrationTestCase):
	"""
	Integration tests for Declaration.
	Use this class for testing interactions between multiple components.
	"""

	pass


class UnitTestDeclarationValue(UnitTestCase):
	"""Unit tests for ``calculate_declaration_value`` (no DB records required)."""

	def test_declaration_value_converts_inv_total_to_document_currency(self):
		"""Total Declaration Value must be in ``currency``, not raw ``inv_total_amount`` when currencies differ."""
		d = frappe.get_doc(
			{
				"doctype": "Declaration",
				"currency": "PHP",
				"inv_currency": "USD",
				"inv_total_amount": 2000,
				"inv_exchange_rate": 59,
			}
		)
		d.calculate_declaration_value()
		self.assertEqual(d.declaration_value, 118000)

	def test_declaration_value_same_currency_no_conversion(self):
		d = frappe.get_doc(
			{
				"doctype": "Declaration",
				"currency": "USD",
				"inv_currency": "USD",
				"inv_total_amount": 2000,
				"inv_exchange_rate": 59,
			}
		)
		d.calculate_declaration_value()
		self.assertEqual(d.declaration_value, 2000)

	def test_apply_currency_and_exchange_rates_from_order_overwrite(self):
		declaration = frappe.get_doc({"doctype": "Declaration", "currency": "EUR", "exchange_rate": 1})
		order = {
			"currency": "PHP",
			"exchange_rate": 59,
			"inv_currency": "USD",
			"inv_exchange_rate": 58.5,
		}
		apply_currency_and_exchange_rates_from_declaration_order(declaration, order, overwrite=True)
		self.assertEqual(declaration.currency, "PHP")
		self.assertEqual(declaration.exchange_rate, 59)
		self.assertEqual(declaration.inv_currency, "USD")
		self.assertEqual(declaration.inv_exchange_rate, 58.5)

	def test_apply_currency_and_exchange_rates_from_order_fills_blanks_only(self):
		declaration = frappe.get_doc(
			{
				"doctype": "Declaration",
				"currency": "EUR",
				"exchange_rate": 1.2,
				"inv_currency": "",
				"inv_exchange_rate": 0,
			}
		)
		order = {
			"currency": "PHP",
			"exchange_rate": 59,
			"inv_currency": "USD",
			"inv_exchange_rate": 58.5,
		}
		apply_currency_and_exchange_rates_from_declaration_order(declaration, order, overwrite=False)
		self.assertEqual(declaration.currency, "EUR")
		self.assertEqual(declaration.exchange_rate, 1.2)
		self.assertEqual(declaration.inv_currency, "USD")
		self.assertEqual(declaration.inv_exchange_rate, 58.5)

	def test_copy_order_to_declaration_propagates_is_high_value_from_order(self):
		declaration = frappe.get_doc({"doctype": "Declaration"})
		order = frappe.get_doc(
			{
				"doctype": "Declaration Order",
				"name": "DO-TEST-001",
				"sales_quote": "SQ-TEST-001",
				"order_date": "2026-06-10",
				"customs_authority": "CA-TEST",
				"is_high_value": 1,
			}
		)
		sales_quote = frappe.get_doc(
			{"doctype": "Sales Quote", "name": "SQ-TEST-001", "is_high_value": 0}
		)
		_copy_order_to_declaration(declaration, order, sales_quote)
		self.assertEqual(declaration.is_high_value, 1)

	def test_copy_order_to_declaration_falls_back_to_sales_quote_is_high_value(self):
		declaration = frappe.get_doc({"doctype": "Declaration"})
		order = frappe.get_doc(
			{
				"doctype": "Declaration Order",
				"name": "DO-TEST-002",
				"sales_quote": "SQ-TEST-002",
				"order_date": "2026-06-10",
				"customs_authority": "CA-TEST",
				"is_high_value": 0,
			}
		)
		sales_quote = frappe.get_doc(
			{"doctype": "Sales Quote", "name": "SQ-TEST-002", "is_high_value": 1}
		)
		_copy_order_to_declaration(declaration, order, sales_quote)
		self.assertEqual(declaration.is_high_value, 1)
