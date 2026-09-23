# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

from frappe.tests.utils import FrappeTestCase

from logistics.netting.netting_dashboard import (
	build_org_row,
	is_ready,
	nettable_amount,
	rank_orgs,
	sum_for_parties,
	summarize_orgs,
)


class TestNettingDashboardHelpers(FrappeTestCase):
	def test_nettable_is_the_overlap_of_ar_and_ap(self):
		self.assertEqual(nettable_amount(100, 40), 40)
		self.assertEqual(nettable_amount(25, 80), 25)
		self.assertEqual(nettable_amount(0, 50), 0)
		self.assertTrue(is_ready(10, 5))
		self.assertFalse(is_ready(10, 0))
		self.assertFalse(is_ready(0, 8))

	def test_sum_for_parties_skips_missing(self):
		amount_map = {
			"CUST-A": {"amount": 120, "invoices": 2},
			"CUST-B": {"amount": 30, "invoices": 1},
		}
		total, invoices = sum_for_parties(amount_map, ["CUST-A", "CUST-B", None, "CUST-Z"])
		self.assertEqual(total, 150)
		self.assertEqual(invoices, 3)

	def test_rank_ready_orgs_by_nettable(self):
		rows = [
			build_org_row(
				{"name": "LOW", "settlement_group_name": "Low"},
				["C1"],
				["S1"],
				{"C1": {"amount": 50, "invoices": 1}},
				{"S1": {"amount": 20, "invoices": 1}},
				{},
			),
			build_org_row(
				{"name": "HIGH", "settlement_group_name": "High"},
				["C2"],
				["S2"],
				{"C2": {"amount": 400, "invoices": 3}},
				{"S2": {"amount": 250, "invoices": 2}},
				{"HIGH": 1},
			),
			build_org_row(
				{"name": "ARONLY", "settlement_group_name": "AR Only"},
				["C3"],
				["S3"],
				{"C3": {"amount": 900, "invoices": 1}},
				{},
				{},
			),
		]
		ranked = rank_orgs(rows, ready_only=True, limit=10)
		self.assertEqual([r["name"] for r in ranked], ["HIGH", "LOW"])
		self.assertEqual(ranked[0]["nettable"], 250)
		self.assertEqual(ranked[0]["drafts"], 1)

		kpis = summarize_orgs(rows, ranked)
		self.assertEqual(kpis["groups"], 3)
		self.assertEqual(kpis["ready"], 2)
		self.assertEqual(kpis["nettable"], 270)
		self.assertEqual(kpis["drafts"], 1)

		all_ranked = rank_orgs(rows, ready_only=False, limit=2)
		self.assertEqual(len(all_ranked), 2)
		self.assertEqual(all_ranked[0]["name"], "HIGH")
