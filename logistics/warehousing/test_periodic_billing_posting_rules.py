# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Periodic Billing charge lines choose internal billing or intercompany from the linked job."""

from __future__ import annotations

import unittest

from logistics.warehousing.periodic_billing_posting_rules import (
	classify_periodic_billing_charges,
	groups_for_selection,
	invoice_line_from_charge,
)


def _charge(**kwargs):
	row = {
		"idx": 1,
		"item_code": "STORAGE",
		"item_name": "Storage",
		"description": "Weekly storage",
		"uom": "Day",
		"quantity": 2,
		"rate": 10,
		"total": 20,
		"warehouse_job": "WJ-1",
	}
	row.update(kwargs)
	return row


def _job(**kwargs):
	row = {
		"company": "Warehouse Co",
		"is_linked": True,
		"main_service_type": "Air Shipment",
		"main_service": "AS-1",
		"main_company": "Main Co",
	}
	row.update(kwargs)
	return row


class TestPeriodicBillingPostingRules(unittest.TestCase):
	def test_invoice_line_uses_total_when_rate_is_empty(self):
		line = invoice_line_from_charge(
			{"item_code": "STORAGE", "quantity": 4, "rate": 0, "total": 40, "item_name": "Storage"}
		)
		self.assertEqual(line["qty"], 4)
		self.assertEqual(line["rate"], 10)

	def test_unlinked_charge_is_customer_only(self):
		result = classify_periodic_billing_charges(
			[_charge(warehouse_job="")],
			{},
			intercompany_enabled=True,
			relationships=[],
		)
		self.assertEqual(result["charges"][0]["posting"], "")
		self.assertFalse(result["show_internal_billing"])
		self.assertFalse(result["show_intercompany"])

	def test_same_company_linked_job_offers_internal_billing(self):
		result = classify_periodic_billing_charges(
			[_charge()],
			{"WJ-1": _job(company="Main Co", main_company="Main Co")},
			intercompany_enabled=True,
			relationships=[],
		)
		self.assertEqual(result["charges"][0]["posting"], "internal")
		self.assertTrue(result["show_internal_billing"])
		self.assertFalse(result["show_intercompany"])

	def test_different_company_offers_intercompany_when_enabled(self):
		result = classify_periodic_billing_charges(
			[_charge()],
			{"WJ-1": _job()},
			intercompany_enabled=True,
			relationships=[
				{
					"billing_company": "Main Co",
					"operating_company": "Warehouse Co",
					"internal_customer": "Main Customer",
					"internal_supplier": "Warehouse Supplier",
				}
			],
		)
		row = result["charges"][0]
		self.assertEqual(row["posting"], "intercompany")
		self.assertEqual(row["relationship"]["internal_customer"], "Main Customer")
		self.assertTrue(result["show_intercompany"])
		self.assertFalse(result["intercompany_disabled"])

	def test_different_company_hides_intercompany_when_disabled(self):
		result = classify_periodic_billing_charges(
			[_charge()],
			{"WJ-1": _job()},
			intercompany_enabled=False,
			relationships=[],
		)
		self.assertEqual(result["charges"][0]["posting"], "")
		self.assertFalse(result["show_intercompany"])
		self.assertTrue(result["intercompany_disabled"])

	def test_zero_amount_is_not_a_linked_posting(self):
		result = classify_periodic_billing_charges(
			[_charge(quantity=0, rate=0, total=0)],
			{"WJ-1": _job(company="Main Co", main_company="Main Co")},
			intercompany_enabled=True,
			relationships=[],
		)
		self.assertEqual(result["charges"][0]["posting"], "")
		self.assertFalse(result["show_internal_billing"])

	def test_selection_keeps_only_checked_lines(self):
		result = classify_periodic_billing_charges(
			[
				_charge(idx=1, warehouse_job="WJ-INT"),
				_charge(idx=2, warehouse_job="WJ-IC", item_code="VAS"),
				_charge(idx=3, warehouse_job="", item_code="OTHER"),
			],
			{
				"WJ-INT": _job(company="Main Co", main_company="Main Co"),
				"WJ-IC": _job(),
			},
			intercompany_enabled=True,
			relationships=[
				{
					"billing_company": "Main Co",
					"operating_company": "Warehouse Co",
					"internal_customer": "Main Customer",
					"internal_supplier": "Warehouse Supplier",
				}
			],
		)
		groups = groups_for_selection(result["charges"], [2, 3])
		self.assertEqual(len(groups["customer_lines"]), 2)
		self.assertEqual(groups["internal"], [])
		self.assertEqual(len(groups["intercompany"]), 1)
		self.assertEqual(groups["intercompany"][0]["warehouse_job"], "WJ-IC")
		self.assertEqual(groups["intercompany"][0]["lines"][0]["item_code"], "VAS")
		self.assertEqual(groups["intercompany"][0]["internal_supplier"], "Warehouse Supplier")


if __name__ == "__main__":
	unittest.main()
