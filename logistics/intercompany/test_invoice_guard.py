# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Intercompany invoice creation can tell its own Sales Invoice from the customer invoice."""

from __future__ import annotations

import unittest

from logistics.intercompany.invoice_guard import (
	INTERCOMPANY_JOB_TYPES,
	INTERCOMPANY_SI_REMARKS_PREFIX,
	apply_sales_invoice_reference,
	intercompany_sales_invoice_marked,
	release_service_purchase_from_internal_transfer,
	relationship_for_companies,
)


class TestIntercompanyGuard(unittest.TestCase):
	def test_customer_invoice_is_not_the_intercompany_leg(self):
		self.assertFalse(intercompany_sales_invoice_marked(False, "Customer invoice"))
		self.assertFalse(intercompany_sales_invoice_marked(False, None))
		self.assertFalse(intercompany_sales_invoice_marked(None, " intercompany: lower case"))

	def test_creation_flag_marks_the_operating_company_invoice(self):
		self.assertTrue(intercompany_sales_invoice_marked(True, ""))
		self.assertTrue(intercompany_sales_invoice_marked(True, None))

	def test_remarks_prefix_marks_a_saved_intercompany_invoice(self):
		self.assertTrue(
			intercompany_sales_invoice_marked(False, "  Intercompany: from Sales Quote SQ-1.")
		)

	def test_relationship_uses_billing_company_and_operating_company(self):
		rows = [
			{
				"billing_company": "Main Co",
				"operating_company": "Ops Co",
				"internal_customer": "Main as Customer",
				"internal_supplier": "Ops as Supplier",
			},
			{
				"billing_company": "Other",
				"operating_company": "Ops Co",
				"internal_customer": "Wrong",
				"internal_supplier": "Wrong",
			},
		]
		self.assertEqual(
			relationship_for_companies(rows, "Main Co", "Ops Co"),
			{"internal_customer": "Main as Customer", "internal_supplier": "Ops as Supplier"},
		)
		self.assertIsNone(relationship_for_companies(rows, "Ops Co", "Main Co"))
		self.assertIsNone(relationship_for_companies(None, "Main Co", "Ops Co"))

	def test_a_matched_row_keeps_blank_parties(self):
		rows = [{"billing_company": "Main Co", "operating_company": "Ops Co"}]
		self.assertEqual(
			relationship_for_companies(rows, "Main Co", "Ops Co"),
			{"internal_customer": None, "internal_supplier": None},
		)

	def test_eligible_job_types(self):
		self.assertIn("Warehouse Job", INTERCOMPANY_JOB_TYPES)
		self.assertIn("Declaration Order", INTERCOMPANY_JOB_TYPES)
		self.assertNotIn("Transport Order", INTERCOMPANY_JOB_TYPES)
		self.assertNotIn("Sales Quote", INTERCOMPANY_JOB_TYPES)


class _Row:
	def __init__(self, **kwargs):
		self.__dict__.update(kwargs)


class _Flags(dict):
	def get(self, key, default=None):
		return super().get(key, default)


def _purchase(**kwargs):
	doc = _Row(
		doctype="Purchase Invoice",
		company="ALL TRANSPORT",
		supplier="Ops Supplier",
		is_internal_supplier=1,
		represents_company="ALL TRANSPORT",
		update_stock=0,
		items=[_Row(reference_doctype="Transport Job")],
		flags=_Flags(is_intercompany_invoice=True),
		remarks=INTERCOMPANY_SI_REMARKS_PREFIX + " from Sales Quote SQ-1.",
	)
	for key, value in kwargs.items():
		setattr(doc, key, value)
	return doc


def _sales():
	return _Row(
		name="ACC-SINV-2026-00029",
		company="FAST PRIME TRANSPORT CORP.",
		customer="Main as Customer",
		items=[_Row(name="si-item-1"), _Row(name="si-item-2")],
	)


class TestInternalSalesReference(unittest.TestCase):
	def test_cross_company_pair_links_each_sales_row(self):
		purchase = _purchase(
			represents_company="FAST PRIME TRANSPORT CORP.",
			items=[_Row(), _Row()],
		)
		linked = apply_sales_invoice_reference(
			purchase,
			_sales(),
			supplier_is_internal=1,
			supplier_represents_company="FAST PRIME TRANSPORT CORP.",
			sales_customer_represents_company="ALL TRANSPORT",
			supplier_found_for_sales_company="Ops Supplier",
		)
		self.assertTrue(linked)
		self.assertEqual(purchase.inter_company_invoice_reference, "ACC-SINV-2026-00029")
		self.assertEqual(purchase.items[0].sales_invoice_item, "si-item-1")
		self.assertEqual(purchase.items[1].sales_invoice_item, "si-item-2")
		self.assertFalse(hasattr(purchase, "unrealized_profit_loss_account"))

	def test_same_company_supplier_without_a_matching_sale_is_not_linked(self):
		"""The supplier represents the purchase company, so ERPNext demands a sales invoice.

		The sales invoice belongs to the other company, so the link would fail
		ERPNext's party check. Leave it unset.
		"""
		purchase = _purchase(items=[_Row(), _Row()])
		linked = apply_sales_invoice_reference(
			purchase,
			_sales(),
			supplier_is_internal=1,
			supplier_represents_company="ALL TRANSPORT",
			sales_customer_represents_company="ALL TRANSPORT",
			supplier_found_for_sales_company="Some Other Supplier",
		)
		self.assertFalse(linked)
		self.assertFalse(hasattr(purchase, "inter_company_invoice_reference"))

	def test_same_company_transfer_links_when_the_unrealized_account_exists(self):
		purchase = _purchase(
			company="ALL TRANSPORT",
			represents_company="ALL TRANSPORT",
			items=[_Row()],
		)
		sales = _Row(
			name="ACC-SINV-2026-00030",
			company="ALL TRANSPORT",
			customer="Main as Customer",
			items=[_Row(name="si-item-1")],
		)
		linked = apply_sales_invoice_reference(
			purchase,
			sales,
			supplier_is_internal=1,
			supplier_represents_company="ALL TRANSPORT",
			sales_customer_represents_company="ALL TRANSPORT",
			supplier_found_for_sales_company="Ops Supplier",
			unrealized_profit_loss_account="Unrealized - ATN",
		)
		self.assertTrue(linked)
		self.assertEqual(purchase.inter_company_invoice_reference, "ACC-SINV-2026-00030")
		self.assertEqual(purchase.items[0].sales_invoice_item, "si-item-1")
		self.assertEqual(purchase.unrealized_profit_loss_account, "Unrealized - ATN")

	def test_same_company_transfer_without_an_account_stays_unlinked(self):
		purchase = _purchase(items=[_Row()])
		sales = _Row(
			name="ACC-SINV-2026-00030",
			company="ALL TRANSPORT",
			customer="Main as Customer",
			items=[_Row(name="si-item-1")],
		)
		linked = apply_sales_invoice_reference(
			purchase,
			sales,
			supplier_is_internal=1,
			supplier_represents_company="ALL TRANSPORT",
			sales_customer_represents_company="ALL TRANSPORT",
			supplier_found_for_sales_company="Ops Supplier",
			unrealized_profit_loss_account=None,
		)
		self.assertFalse(linked)

	def test_screenshot_purchase_is_no_longer_an_internal_transfer(self):
		"""Supplier represents the purchase company and the sale is the other company.

		That is the purchase ERPNext rejects with Internal Sales Reference Missing.
		After before_validate, the internal-supplier flag is clear, so the check
		does not treat the invoice as an internal transfer.
		"""
		purchase = _purchase(
			company="ALL TRANSPORT",
			supplier="Main Supplier",
			represents_company="ALL TRANSPORT",
			items=[_Row(reference_doctype="Transport Job")],
			remarks=INTERCOMPANY_SI_REMARKS_PREFIX + " from Sales Quote SQ-17.",
		)
		linked = apply_sales_invoice_reference(
			purchase,
			_sales(),
			supplier_is_internal=1,
			supplier_represents_company="ALL TRANSPORT",
			sales_customer_represents_company="FAST PRIME TRANSPORT CORP.",
			supplier_found_for_sales_company="Ops Supplier",
		)
		self.assertFalse(linked)
		purchase.is_internal_supplier = 1
		release_service_purchase_from_internal_transfer(purchase)
		internal_transfer = bool(purchase.is_internal_supplier) and (
			purchase.represents_company == purchase.company
		)
		self.assertFalse(internal_transfer)

	def test_service_purchase_drops_the_internal_supplier_flag(self):
		purchase = _purchase()
		release_service_purchase_from_internal_transfer(purchase)
		self.assertEqual(purchase.is_internal_supplier, 0)

	def test_job_cost_purchase_drops_the_internal_supplier_flag(self):
		purchase = _purchase(
			flags=_Flags(logistics_service_purchase=True),
			remarks="Auto-created from Transport Job TRJ000000017",
		)
		release_service_purchase_from_internal_transfer(purchase)
		self.assertEqual(purchase.is_internal_supplier, 0)

	def test_complete_internal_transfer_keeps_the_supplier_flag(self):
		purchase = _purchase(
			inter_company_invoice_reference="ACC-SINV-2026-00030",
			items=[_Row(sales_invoice_item="si-item-1", reference_doctype="Transport Job")],
		)
		release_service_purchase_from_internal_transfer(purchase)
		self.assertEqual(purchase.is_internal_supplier, 1)

	def test_stock_transfer_keeps_the_supplier_flag(self):
		purchase = _purchase(update_stock=1)
		release_service_purchase_from_internal_transfer(purchase)
		self.assertEqual(purchase.is_internal_supplier, 1)

	def test_outside_supplier_is_unchanged(self):
		purchase = _purchase(is_internal_supplier=0, represents_company="")
		release_service_purchase_from_internal_transfer(purchase)
		self.assertEqual(purchase.is_internal_supplier, 0)

	def test_manual_purchase_invoice_is_unchanged(self):
		purchase = _purchase(
			flags=_Flags(),
			remarks="Supplier bill",
			reference_doctype=None,
			items=[_Row()],
		)
		release_service_purchase_from_internal_transfer(purchase)
		self.assertEqual(purchase.is_internal_supplier, 1)


if __name__ == "__main__":
	unittest.main()
