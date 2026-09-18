# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today, cint

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


class TestDeclarationMilestones(FrappeTestCase):
	"""Declaration Order milestones copy onto Declaration like Sea Booking → Sea Shipment."""

	def setUp(self):
		from logistics.air_freight.tests.test_helpers import (
			create_test_branch,
			create_test_consignee,
			create_test_cost_center,
			create_test_profit_center,
			create_test_shipper,
			setup_basic_master_data,
		)

		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		self.shipper = create_test_shipper()
		self.consignee = create_test_consignee()
		try:
			self.branch = create_test_branch(self.company)
			self.cost_center = create_test_cost_center(self.company)
			self.profit_center = create_test_profit_center(self.company)
		except Exception:
			self.branch = frappe.db.get_value("Branch", {"custom_company": self.company}, "name")
			self.cost_center = frappe.db.get_value("Cost Center", {"company": self.company, "is_group": 0}, "name")
			self.profit_center = frappe.db.get_value("Profit Center", {"company": self.company}, "name")

	def tearDown(self):
		frappe.db.rollback()

	def _ensure_logistics_milestone(self, code):
		existing = frappe.db.get_value("Logistics Milestone", {"code": code}, "name")
		if existing:
			return existing
		return (
			frappe.get_doc(
				{
					"doctype": "Logistics Milestone",
					"code": code,
					"description": code,
					"customs": 1,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _order_with_milestones(self, milestone_names, planned_end="2026-10-01 12:00:00"):
		order = frappe.get_doc(
			{
				"doctype": "Declaration Order",
				"company": self.company,
				"customer": self.customer,
				"order_date": today(),
				"exporter_shipper": self.shipper,
				"importer_consignee": self.consignee,
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
			}
		)
		for milestone in milestone_names:
			order.append(
				"milestones",
				{
					"milestone": milestone,
					"status": "Planned",
					"planned_end": planned_end,
					"source": "Fetched",
					"automation_planned_date_basis": "Booking Date",
				},
			)
		order.flags.ignore_documents_milestones_populate = True
		order.flags.ignore_mandatory = True
		order.insert(ignore_permissions=True)
		return order

	def _declaration_for_order(self, order):
		declaration = frappe.get_doc(
			{
				"doctype": "Declaration",
				"company": self.company,
				"customer": self.customer,
				"declaration_date": today(),
				"declaration_order": order.name,
				"exporter_shipper": self.shipper,
				"importer_consignee": self.consignee,
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
			}
		)
		declaration.flags.ignore_documents_milestones_populate = True
		declaration.flags.ignore_mandatory = True
		declaration.insert(ignore_permissions=True)
		return declaration

	def test_order_milestone_row_values_marks_from_booking(self):
		from logistics.customs.doctype.declaration.declaration import order_milestone_row_values

		src = frappe._dict(
			{
				"milestone": "MS-A",
				"status": "Planned",
				"planned_start": None,
				"planned_end": "2026-10-01 12:00:00",
				"actual_start": None,
				"actual_end": None,
				"source": "Fetched",
				"fetched_at": "2026-09-01 08:00:00",
				"automation_planned_date_basis": "Booking Date",
				"automation_update_trigger_type": "Date Based",
			}
		)
		values = order_milestone_row_values(src)
		self.assertEqual(values["from_booking"], 1)
		self.assertEqual(values["milestone"], "MS-A")
		self.assertEqual(values["planned_end"], "2026-10-01 12:00:00")
		self.assertEqual(values["automation_planned_date_basis"], "Booking Date")
		self.assertEqual(values["automation_update_trigger_type"], "Date Based")

	def test_declaration_populates_order_milestones_as_from_booking(self):
		sfx = frappe.generate_hash(length=6)
		ms_order = self._ensure_logistics_milestone(f"TST-DO-MS-{sfx}")
		order = self._order_with_milestones([ms_order])
		declaration = self._declaration_for_order(order)

		self.assertEqual(len(declaration.milestones), 1)
		self.assertEqual(declaration.milestones[0].milestone, ms_order)
		self.assertEqual(cint(declaration.milestones[0].from_booking), 1)
		self.assertEqual(str(declaration.milestones[0].planned_end), "2026-10-01 12:00:00")
		self.assertEqual(declaration.milestones[0].automation_planned_date_basis, "Booking Date")

	def test_declaration_allows_extra_milestone_without_flagging_from_booking(self):
		sfx = frappe.generate_hash(length=6)
		ms_order = self._ensure_logistics_milestone(f"TST-DO-MS-{sfx}")
		ms_extra = self._ensure_logistics_milestone(f"TST-DEC-MS-{sfx}")
		order = self._order_with_milestones([ms_order])
		declaration = self._declaration_for_order(order)

		declaration.append("milestones", {"milestone": ms_extra, "status": "Planned", "source": "Manual"})
		declaration.flags.ignore_documents_milestones_populate = True
		declaration.save()

		by_ms = {row.milestone: row for row in declaration.milestones}
		self.assertIn(ms_order, by_ms)
		self.assertIn(ms_extra, by_ms)
		self.assertEqual(cint(by_ms[ms_order].from_booking), 1)
		self.assertEqual(cint(by_ms[ms_extra].from_booking), 0)

	def test_declaration_adds_missing_order_milestone_on_later_save(self):
		sfx = frappe.generate_hash(length=6)
		ms1 = self._ensure_logistics_milestone(f"TST-DO-MS1-{sfx}")
		ms2 = self._ensure_logistics_milestone(f"TST-DO-MS2-{sfx}")
		order = self._order_with_milestones([ms1])
		declaration = self._declaration_for_order(order)
		self.assertEqual([row.milestone for row in declaration.milestones], [ms1])

		order.reload()
		order.append(
			"milestones",
			{"milestone": ms2, "status": "Planned", "planned_end": "2026-11-01 09:00:00", "source": "Fetched"},
		)
		order.flags.ignore_documents_milestones_populate = True
		order.save()

		declaration.reload()
		declaration.flags.ignore_documents_milestones_populate = True
		declaration.save()

		names = {row.milestone for row in declaration.milestones}
		self.assertEqual(names, {ms1, ms2})
		self.assertTrue(all(cint(row.from_booking) for row in declaration.milestones))

	def test_declaration_rejects_edit_and_delete_of_order_milestones(self):
		sfx = frappe.generate_hash(length=6)
		ms_order = self._ensure_logistics_milestone(f"TST-DO-MS-{sfx}")
		order = self._order_with_milestones([ms_order])
		declaration = self._declaration_for_order(order)

		declaration.milestones[0].planned_end = "2026-12-31 00:00:00"
		declaration.flags.ignore_documents_milestones_populate = True
		with self.assertRaises(frappe.ValidationError) as ctx:
			declaration.save()
		self.assertIn("cannot be edited", str(ctx.exception))

		declaration.reload()
		declaration.remove(declaration.milestones[0])
		declaration.flags.ignore_documents_milestones_populate = True
		with self.assertRaises(frappe.ValidationError) as ctx:
			declaration.save()
		self.assertIn("cannot be deleted", str(ctx.exception))
