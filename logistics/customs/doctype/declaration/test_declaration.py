# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase


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
