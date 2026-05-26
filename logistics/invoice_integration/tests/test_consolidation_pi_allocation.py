# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import unittest
from unittest.mock import patch

import frappe
from frappe.utils import flt

from logistics.invoice_integration.consolidation_pi_allocation import (
    allocation_factor_for_attached_job,
    count_attached_jobs,
    distribute_amounts_with_rounding,
)


def _air_doc(packages=None, **fields):
    """Build a fake Air Consolidation doc whose ``consolidation_packages`` drive allocation."""
    return frappe._dict(
        doctype="Air Consolidation",
        consolidation_packages=[frappe._dict(p) for p in (packages or [])],
        **fields,
    )


def _sea_doc(rows=None, **fields):
    return frappe._dict(
        doctype="Sea Consolidation",
        attached_sea_shipments=[frappe._dict(r) for r in (rows or [])],
        **fields,
    )


class TestConsolidationPiAllocation(unittest.TestCase):
    def test_count_attached_jobs_air_distinct_packages(self):
        doc = _air_doc(packages=[
            {"air_freight_job": "AS-A", "package_weight": 10},
            {"air_freight_job": "AS-A", "package_weight": 5},
            {"air_freight_job": "AS-B", "package_weight": 7},
        ])
        self.assertEqual(count_attached_jobs(doc), 2)

    def test_count_attached_jobs_sea(self):
        doc = _sea_doc(rows=[{"sea_shipment": "SS-A"}])
        self.assertEqual(count_attached_jobs(doc), 1)

    def test_count_attached_jobs_sea_from_packages_when_attached_empty(self):
        doc = frappe._dict(
            doctype="Sea Consolidation",
            attached_sea_shipments=[],
            consolidation_packages=[
                frappe._dict(sea_shipment="SS-A", package_weight=10),
                frappe._dict(sea_shipment="SS-B", package_weight=20),
            ],
        )
        self.assertEqual(count_attached_jobs(doc), 2)

    def test_weight_based_sea_aggregates_packages_per_shipment(self):
        doc = frappe._dict(
            doctype="Sea Consolidation",
            total_weight=0,
            attached_sea_shipments=[],
            consolidation_packages=[
                frappe._dict(sea_shipment="SS-A", package_weight=10),
                frappe._dict(sea_shipment="SS-A", package_weight=15),
                frappe._dict(sea_shipment="SS-B", package_weight=75),
            ],
        )
        charge = frappe._dict(allocation_method="Weight-based")
        att_a = frappe._dict(sea_shipment="SS-A", weight=25)
        f = allocation_factor_for_attached_job(doc, charge, att_a)
        self.assertAlmostEqual(f, 0.25, places=6)

    def test_equal_allocation_air(self):
        doc = _air_doc(packages=[
            {"air_freight_job": "AS-A"},
            {"air_freight_job": "AS-B"},
            {"air_freight_job": "AS-C"},
            {"air_freight_job": "AS-D"},
        ])
        charge = frappe._dict(allocation_method="Equal")
        att = frappe._dict()
        f = allocation_factor_for_attached_job(doc, charge, att)
        self.assertAlmostEqual(f, 0.25, places=6)

    def test_weight_based_uses_header_total(self):
        doc = _air_doc(
            total_weight=200,
            packages=[
                {"air_freight_job": "AS-A", "package_weight": 50},
                {"air_freight_job": "AS-B", "package_weight": 150},
            ],
        )
        charge = frappe._dict(allocation_method="Weight-based")
        att = frappe._dict(air_freight_job="AS-A", weight=50)
        f = allocation_factor_for_attached_job(doc, charge, att)
        self.assertAlmostEqual(f, 0.25, places=6)

    def test_weight_based_sums_attached_when_header_weight_zero(self):
        rows = [frappe._dict(weight=40), frappe._dict(weight=60)]
        doc = frappe._dict(
            doctype="Sea Consolidation",
            total_weight=0,
            attached_sea_shipments=rows,
        )
        charge = frappe._dict(allocation_method="Weight-based")
        f = allocation_factor_for_attached_job(doc, charge, rows[0])
        self.assertAlmostEqual(f, 0.4, places=6)

    def test_weight_based_air_aggregates_packages_per_shipment(self):
        # AS-A has two package rows summing to 25; AS-B has 75. Header total is unset
        # so allocation falls back to summing across attached weights.
        doc = _air_doc(packages=[
            {"air_freight_job": "AS-A", "package_weight": 10},
            {"air_freight_job": "AS-A", "package_weight": 15},
            {"air_freight_job": "AS-B", "package_weight": 75},
        ])
        charge = frappe._dict(allocation_method="Weight-based")
        att_a = frappe._dict(air_freight_job="AS-A", weight=25)
        f = allocation_factor_for_attached_job(doc, charge, att_a)
        self.assertAlmostEqual(f, 0.25, places=6)

    def test_volume_based_from_header_total(self):
        doc = _air_doc(
            total_volume=10,
            packages=[
                {"air_freight_job": "AS-A", "package_volume": 2.5},
                {"air_freight_job": "AS-B", "package_volume": 7.5},
            ],
        )
        charge = frappe._dict(allocation_method="Volume-based")
        att = frappe._dict(air_freight_job="AS-A", volume=2.5)
        f = allocation_factor_for_attached_job(doc, charge, att)
        self.assertAlmostEqual(f, 0.25, places=6)

    def test_volume_based_fallback_sums_attached_volumes(self):
        rows = [frappe._dict(volume=3), frappe._dict(volume=7)]
        doc = frappe._dict(
            doctype="Sea Consolidation",
            total_volume=0,
            attached_sea_shipments=rows,
        )
        charge = frappe._dict(allocation_method="Volume-based")
        f = allocation_factor_for_attached_job(doc, charge, rows[0])
        self.assertAlmostEqual(f, 0.3, places=6)

    @patch("logistics.invoice_integration.consolidation_pi_allocation.frappe.get_all")
    def test_weight_based_air_prefers_package_weight_when_packages_differ_even_if_chargeable_equal(
        self, mock_get_all
    ):
        """Consolidation package weights (750 vs 550) must win over equal shipment chargeable."""

        def _get_all(doctype, filters=None, fields=None, **kwargs):
            if doctype != "Air Shipment" or not filters:
                return []
            inn = filters.get("name")
            if not isinstance(inn, tuple) or inn[0] != "in":
                return []
            return [
                {"name": n, "chargeable": 84543.75, "total_weight": flt(750 if "A" in n else 550)}
                for n in inn[1]
            ]

        mock_get_all.side_effect = _get_all
        doc = _air_doc(
            packages=[
                {"air_freight_job": "AS-A", "package_weight": 750},
                {"air_freight_job": "AS-B", "package_weight": 550},
            ],
        )
        charge = frappe._dict(allocation_method="Weight-based")
        f_a = allocation_factor_for_attached_job(
            doc, charge, frappe._dict(air_freight_job="AS-A", weight=750)
        )
        f_b = allocation_factor_for_attached_job(
            doc, charge, frappe._dict(air_freight_job="AS-B", weight=550)
        )
        self.assertAlmostEqual(f_a, 750 / 1300, places=6)
        self.assertAlmostEqual(f_b, 550 / 1300, places=6)

    @patch("logistics.invoice_integration.consolidation_pi_allocation.frappe.get_all")
    def test_weight_based_air_prefers_shipment_chargeable_over_equal_package_gross(self, mock_get_all):
        """Issue #875: equal gross package weights must not force equal split when chargeable differs."""

        def _get_all(doctype, filters=None, fields=None, **kwargs):
            if doctype != "Air Shipment" or not filters:
                return []
            inn = filters.get("name")
            if not isinstance(inn, tuple) or inn[0] != "in":
                return []
            out = []
            for n in inn[1]:
                if n == "AS-A":
                    out.append({"name": n, "chargeable": 800.0, "total_weight": 400.0})
                elif n == "AS-B":
                    out.append({"name": n, "chargeable": 200.0, "total_weight": 400.0})
            return out

        mock_get_all.side_effect = _get_all
        doc = _air_doc(
            total_weight=800,
            packages=[
                {"air_freight_job": "AS-A", "package_weight": 400},
                {"air_freight_job": "AS-B", "package_weight": 400},
            ],
        )
        charge = frappe._dict(allocation_method="Weight-based")
        f_a = allocation_factor_for_attached_job(
            doc, charge, frappe._dict(air_freight_job="AS-A", weight=400)
        )
        f_b = allocation_factor_for_attached_job(
            doc, charge, frappe._dict(air_freight_job="AS-B", weight=400)
        )
        self.assertAlmostEqual(f_a, 0.8, places=6)
        self.assertAlmostEqual(f_b, 0.2, places=6)
        self.assertAlmostEqual(f_a + f_b, 1.0, places=6)

    @patch("logistics.invoice_integration.consolidation_pi_allocation.frappe.get_all")
    def test_weight_based_sea_prefers_shipment_chargeable_over_equal_package_gross(self, mock_get_all):
        def _get_all(doctype, filters=None, fields=None, **kwargs):
            if doctype != "Sea Shipment" or not filters:
                return []
            inn = filters.get("name")
            if not isinstance(inn, tuple) or inn[0] != "in":
                return []
            out = []
            for n in inn[1]:
                if n == "SS-A":
                    out.append({"name": n, "chargeable": 300.0, "total_weight": 100.0})
                elif n == "SS-B":
                    out.append({"name": n, "chargeable": 100.0, "total_weight": 100.0})
            return out

        mock_get_all.side_effect = _get_all
        doc = frappe._dict(
            doctype="Sea Consolidation",
            total_weight=200,
            attached_sea_shipments=[],
            consolidation_packages=[
                frappe._dict(sea_shipment="SS-A", package_weight=100),
                frappe._dict(sea_shipment="SS-B", package_weight=100),
            ],
        )
        charge = frappe._dict(allocation_method="Weight-based")
        f_a = allocation_factor_for_attached_job(
            doc, charge, frappe._dict(sea_shipment="SS-A", weight=100)
        )
        f_b = allocation_factor_for_attached_job(
            doc, charge, frappe._dict(sea_shipment="SS-B", weight=100)
        )
        self.assertAlmostEqual(f_a, 0.75, places=6)
        self.assertAlmostEqual(f_b, 0.25, places=6)

    @patch("logistics.invoice_integration.consolidation_pi_allocation.frappe.get_all")
    def test_volume_based_air_prefers_shipment_total_volume_when_package_volumes_equal(self, mock_get_all):
        def _get_all(doctype, filters=None, fields=None, **kwargs):
            if doctype != "Air Shipment" or not filters:
                return []
            inn = filters.get("name")
            if not isinstance(inn, tuple) or inn[0] != "in":
                return []
            out = []
            for n in inn[1]:
                if n == "AS-A":
                    out.append({"name": n, "total_volume": 40.0})
                elif n == "AS-B":
                    out.append({"name": n, "total_volume": 10.0})
            return out

        mock_get_all.side_effect = _get_all
        doc = _air_doc(
            total_volume=20,
            packages=[
                {"air_freight_job": "AS-A", "package_volume": 10},
                {"air_freight_job": "AS-B", "package_volume": 10},
            ],
        )
        charge = frappe._dict(allocation_method="Volume-based")
        f_a = allocation_factor_for_attached_job(
            doc, charge, frappe._dict(air_freight_job="AS-A", volume=10)
        )
        f_b = allocation_factor_for_attached_job(
            doc, charge, frappe._dict(air_freight_job="AS-B", volume=10)
        )
        self.assertAlmostEqual(f_a, 0.8, places=6)
        self.assertAlmostEqual(f_b, 0.2, places=6)

    def test_custom_uses_cost_allocation_percentage_from_packages(self):
        doc = _air_doc(packages=[
            {"air_freight_job": "AS-A", "cost_allocation": 40},
            {"air_freight_job": "AS-B", "cost_allocation": 60},
        ])
        charge = frappe._dict(allocation_method="Custom")
        att_a = frappe._dict(air_freight_job="AS-A", cost_allocation_percentage=40)
        f = allocation_factor_for_attached_job(doc, charge, att_a)
        self.assertAlmostEqual(f, 0.4, places=6)

    def test_custom_equal_split_when_all_row_percentages_are_zero(self):
        doc = _air_doc(packages=[
            {"air_freight_job": "AS-A", "cost_allocation": 0},
            {"air_freight_job": "AS-B", "cost_allocation": 0},
        ])
        charge = frappe._dict(allocation_method="Custom")
        att = frappe._dict(air_freight_job="AS-A", cost_allocation_percentage=0)
        f = allocation_factor_for_attached_job(doc, charge, att)
        self.assertAlmostEqual(f, 0.5, places=6)

    def test_value_based_equal_when_no_value_anywhere(self):
        rows = [frappe._dict(value=0), frappe._dict(value=0)]
        doc = frappe._dict(doctype="Sea Consolidation", attached_sea_shipments=rows)
        charge = frappe._dict(allocation_method="Value-based")
        f = allocation_factor_for_attached_job(doc, charge, rows[0])
        self.assertAlmostEqual(f, 0.5, places=6)

    @patch("logistics.invoice_integration.consolidation_pi_allocation.frappe.db.get_value")
    def test_value_based_loads_goods_value_from_sea_shipment_link(self, mock_gv):
        mock_gv.return_value = 4000
        rows = [
            frappe._dict(sea_shipment="SS-A", value=0),
            frappe._dict(sea_shipment="SS-B", value=6000),
        ]
        doc = frappe._dict(doctype="Sea Consolidation", attached_sea_shipments=rows)
        charge = frappe._dict(allocation_method="Value-based")
        f = allocation_factor_for_attached_job(doc, charge, rows[0])
        self.assertAlmostEqual(f, 0.4, places=6)

    @patch("logistics.invoice_integration.consolidation_pi_allocation.frappe.db.get_value")
    def test_value_based_air_uses_package_values_then_air_shipment_goods_value(self, mock_gv):
        # AS-A package values sum to 0 → fall back to Air Shipment.goods_value via db.get_value.
        # AS-B has package value of 6000 → no fallback for that row.
        mock_gv.return_value = 4000
        doc = _air_doc(packages=[
            {"air_freight_job": "AS-A", "value": 0},
            {"air_freight_job": "AS-B", "value": 6000},
        ])
        charge = frappe._dict(allocation_method="Value-based")
        att_a = frappe._dict(air_freight_job="AS-A", value=0)
        f = allocation_factor_for_attached_job(doc, charge, att_a)
        self.assertAlmostEqual(f, 0.4, places=6)

    def test_blank_allocation_method_defaults_to_equal(self):
        doc = _air_doc(packages=[
            {"air_freight_job": "AS-A"},
            {"air_freight_job": "AS-B"},
            {"air_freight_job": "AS-C"},
        ])
        charge = frappe._dict(allocation_method="")
        f = allocation_factor_for_attached_job(doc, charge, frappe._dict())
        self.assertAlmostEqual(f, 1.0 / 3.0, places=6)


    def test_custom_sea_uses_cost_allocation_percentage_from_planning_when_packages_exist(self):
        doc = frappe._dict(
            doctype="Sea Consolidation",
            consolidation_planning_lines=[
                frappe._dict(sea_shipment="SS-A", cost_allocation_percentage=40),
                frappe._dict(sea_shipment="SS-B", cost_allocation_percentage=60),
            ],
            consolidation_packages=[
                frappe._dict(sea_shipment="SS-A", package_weight=10),
                frappe._dict(sea_shipment="SS-B", package_weight=20),
            ],
        )
        charge = frappe._dict(allocation_method="Custom")
        att_a = frappe._dict(sea_shipment="SS-A", cost_allocation_percentage=40)
        f_a = allocation_factor_for_attached_job(doc, charge, att_a)
        att_b = frappe._dict(sea_shipment="SS-B", cost_allocation_percentage=60)
        f_b = allocation_factor_for_attached_job(doc, charge, att_b)
        self.assertAlmostEqual(f_a, 0.4, places=6)
        self.assertAlmostEqual(f_b, 0.6, places=6)

    def test_custom_sea_equal_split_when_all_percentages_zero_with_packages(self):
        doc = frappe._dict(
            doctype="Sea Consolidation",
            consolidation_planning_lines=[
                frappe._dict(sea_shipment="SS-A", cost_allocation_percentage=0),
                frappe._dict(sea_shipment="SS-B", cost_allocation_percentage=0),
            ],
            consolidation_packages=[
                frappe._dict(sea_shipment="SS-A", package_weight=10),
                frappe._dict(sea_shipment="SS-B", package_weight=20),
            ],
        )
        charge = frappe._dict(allocation_method="Custom")
        att = frappe._dict(sea_shipment="SS-A", cost_allocation_percentage=0)
        f = allocation_factor_for_attached_job(doc, charge, att)
        self.assertAlmostEqual(f, 0.5, places=6)

    def test_distribute_amounts_rounding(self):
        raw = [33.333333, 33.333333, 33.333333]
        out = distribute_amounts_with_rounding(raw, 100.0)
        self.assertAlmostEqual(sum(out), 100.0, places=2)
