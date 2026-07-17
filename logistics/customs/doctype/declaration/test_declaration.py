# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase

from logistics.customs.doctype.declaration.declaration import (
	_copy_order_to_declaration,
	apply_currency_and_exchange_rates_from_declaration_order,
	calculate_commercial_invoice_balance,
	payment_amount_to_invoice_currency,
)


def _declaration_doc(**kwargs):
	data = {"doctype": "Declaration"}
	data.update(kwargs)
	return frappe.get_doc(data)


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


class UnitTestDeclarationCommercialInvoiceBalance(UnitTestCase):
	"""Unit tests for commercial-invoice balance and settlement currency conversion."""

	def _declaration(self, **kwargs):
		data = {"doctype": "Declaration"}
		data.update(kwargs)
		return frappe.get_doc(data)

	def test_balance_usd_invoice_php_payment_converts_via_inv_exchange_rate(self):
		"""Issue #1248: USD invoice with PHP settlement must not compare raw amounts."""
		d = self._declaration(
			currency="PHP",
			inv_currency="USD",
			inv_total_amount=55000,
			inv_exchange_rate=58,
			payment_currency="PHP",
			payment_amount=55000,
		)
		paid_in_inv = payment_amount_to_invoice_currency(d)
		self.assertAlmostEqual(paid_in_inv, 55000 / 58, places=2)
		calculate_commercial_invoice_balance(d)
		self.assertEqual(d.balance, f"{55000 - (55000 / 58):.2f}")

	def test_balance_same_currency_subtracts_directly(self):
		d = self._declaration(
			currency="USD",
			inv_currency="USD",
			inv_total_amount=55000,
			payment_currency="USD",
			payment_amount=10000,
		)
		calculate_commercial_invoice_balance(d)
		self.assertEqual(d.balance, "45000.00")

	def test_balance_empty_when_cross_currency_payment_missing_rate(self):
		d = self._declaration(
			currency="PHP",
			inv_currency="USD",
			inv_total_amount=55000,
			payment_currency="EUR",
			payment_amount=1000,
		)
		calculate_commercial_invoice_balance(d)
		self.assertIsNone(d.balance)

	def test_balance_zero_when_fully_paid_in_same_currency(self):
		d = self._declaration(
			currency="USD",
			inv_currency="USD",
			inv_total_amount=55000,
			payment_currency="USD",
			payment_amount=55000,
		)
		calculate_commercial_invoice_balance(d)
		self.assertEqual(d.balance, "0.00")


class UnitTestDeclarationProcessingDates(UnitTestCase):
	"""Unit tests for mutually exclusive approval / rejection dates."""

	def _declaration(self, **kwargs):
		data = {"doctype": "Declaration"}
		data.update(kwargs)
		return frappe.get_doc(data)

	def test_rejection_date_clears_approval_date(self):
		d = self._declaration(approval_date="2026-07-01", rejection_date="2026-07-10")
		d._enforce_mutually_exclusive_processing_dates()
		self.assertIsNone(d.approval_date)
		self.assertEqual(str(d.rejection_date), "2026-07-10")

	def test_rejection_date_takes_precedence_when_both_set(self):
		d = self._declaration(approval_date="2026-07-10", rejection_date="2026-07-01")
		d._enforce_mutually_exclusive_processing_dates()
		self.assertIsNone(d.approval_date)
		self.assertEqual(str(d.rejection_date), "2026-07-01")

	def test_validate_rejects_both_processing_dates(self):
		d = self._declaration(approval_date="2026-07-01", rejection_date="2026-07-10")
		with self.assertRaises(frappe.ValidationError):
			d._validate_processing_event_dates()

	def test_update_processing_dates_skips_approval_when_rejected(self):
		d = self._declaration(status="Cleared", rejection_date="2026-07-10")
		d.update_processing_dates()
		self.assertIsNone(d.approval_date)


class UnitTestDeclarationPaymentStatus(UnitTestCase):
	"""Payment status must follow Invoice Total and Payment Amount, not customs charges."""

	def test_payment_status_paid_when_fully_settled(self):
		d = _declaration_doc(inv_total_amount=100, payment_amount=100)
		d.update_payment_status()
		self.assertEqual(d.payment_status, "Paid")

	def test_payment_status_partially_paid(self):
		d = _declaration_doc(inv_total_amount=100, payment_amount=40)
		d.update_payment_status()
		self.assertEqual(d.payment_status, "Partially Paid")

	def test_payment_status_pending_when_unpaid(self):
		d = _declaration_doc(inv_total_amount=100, payment_amount=0)
		d.update_payment_status()
		self.assertEqual(d.payment_status, "Pending")

	def test_payment_status_overdue_when_unpaid_past_due_date(self):
		d = _declaration_doc(
			inv_total_amount=100,
			payment_amount=0,
			payment_date="2020-01-01",
		)
		d.update_payment_status()
		self.assertEqual(d.payment_status, "Overdue")

	def test_customs_charges_do_not_drive_payment_status(self):
		d = _declaration_doc(
			inv_total_amount=100,
			payment_amount=0,
			duty_amount=9,
			tax_amount=9,
			other_charges=9,
		)
		d.calculate_total_payable()
		self.assertEqual(d.total_payable, 27)
		d.update_payment_status()
		self.assertEqual(d.payment_status, "Pending")
