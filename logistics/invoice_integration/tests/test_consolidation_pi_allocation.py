# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import unittest

import frappe

from logistics.invoice_integration.consolidation_pi_allocation import (
    allocation_factor_for_attached_job,
    count_attached_jobs,
    distribute_amounts_with_rounding,
)


class TestConsolidationPiAllocation(unittest.TestCase):
    def test_count_attached_jobs_air(self):
        doc = frappe._dict(
            doctype="Air Consolidation",
            attached_air_freight_jobs=[frappe._dict(), frappe._dict()],
        )
        self.assertEqual(count_attached_jobs(doc), 2)

    def test_count_attached_jobs_sea(self):
        doc = frappe._dict(
            doctype="Sea Consolidation",
            attached_sea_shipments=[frappe._dict()],
        )
        self.assertEqual(count_attached_jobs(doc), 1)

    def test_equal_allocation_air(self):
        doc = frappe._dict(
            doctype="Air Consolidation",
            attached_air_freight_jobs=[1, 2, 3, 4],
        )
        charge = frappe._dict(allocation_method="Equal")
        att = frappe._dict()
        f = allocation_factor_for_attached_job(doc, charge, att)
        self.assertAlmostEqual(f, 0.25, places=6)

    def test_weight_based(self):
        doc = frappe._dict(
            doctype="Air Consolidation",
            total_weight=200,
            attached_air_freight_jobs=[1, 2],
        )
        charge = frappe._dict(allocation_method="Weight-based")
        att = frappe._dict(weight=50)
        f = allocation_factor_for_attached_job(doc, charge, att)
        self.assertAlmostEqual(f, 0.25, places=6)

    def test_fallback_cost_allocation_percentage(self):
        doc = frappe._dict(doctype="Air Consolidation", attached_air_freight_jobs=[1, 2])
        charge = frappe._dict(allocation_method="Volume-based")
        att = frappe._dict(cost_allocation_percentage=40)
        f = allocation_factor_for_attached_job(doc, charge, att)
        self.assertAlmostEqual(f, 0.4, places=6)

    def test_distribute_amounts_rounding(self):
        raw = [33.333333, 33.333333, 33.333333]
        out = distribute_amounts_with_rounding(raw, 100.0)
        self.assertAlmostEqual(sum(out), 100.0, places=2)

