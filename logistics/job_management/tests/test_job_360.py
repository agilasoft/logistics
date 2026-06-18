# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Unit tests for the Job 360 cross-module analytics layer.

These tests are intentionally light-weight: they exercise the pure helper
functions (aging math, status normalization, filter parsing, summary roll-up)
and validate the public API surface so a regression in any of the helpers is
caught quickly. They do not attempt to construct full Sea/Air/Transport
shipments — those flows already have dedicated integration tests elsewhere.
"""

from __future__ import unicode_literals

import unittest
from unittest.mock import patch

import frappe

from logistics.job_management import job_360


class TestJob360Helpers(unittest.TestCase):

    def test_aging_bucket_thresholds(self):
        self.assertEqual(job_360._aging_bucket(0), "0-30")
        self.assertEqual(job_360._aging_bucket(30), "0-30")
        self.assertEqual(job_360._aging_bucket(31), "31-60")
        self.assertEqual(job_360._aging_bucket(60), "31-60")
        self.assertEqual(job_360._aging_bucket(61), "61-90")
        self.assertEqual(job_360._aging_bucket(90), "61-90")
        self.assertEqual(job_360._aging_bucket(91), "91+")
        self.assertEqual(job_360._aging_bucket(500), "91+")
        # negatives bucket as 0-30
        self.assertEqual(job_360._aging_bucket(-5), "0-30")

    def test_to_dict_with_string(self):
        self.assertEqual(job_360._to_dict(None), {})
        self.assertEqual(job_360._to_dict(""), {})
        self.assertEqual(job_360._to_dict({"company": "C"}), {"company": "C"})
        self.assertEqual(job_360._to_dict('{"company":"C"}'), {"company": "C"})
        # invalid JSON falls back to empty dict
        self.assertEqual(job_360._to_dict("not json"), {})

    def test_aging_summary_rolls_up(self):
        rows = [
            {"job_number": "J1", "outstanding_amount": 100, "age_bucket": "0-30", "days_overdue": 5},
            {"job_number": "J1", "outstanding_amount": 50, "age_bucket": "61-90", "days_overdue": 75},
            {"job_number": "J2", "outstanding_amount": 200, "age_bucket": "91+", "days_overdue": 120},
            {"job_number": "", "outstanding_amount": 999, "age_bucket": "0-30", "days_overdue": 1},
        ]
        summary = job_360._aging_summary(rows)
        self.assertIn("J1", summary)
        self.assertIn("J2", summary)
        self.assertEqual(summary["J1"]["0-30"], 100)
        self.assertEqual(summary["J1"]["61-90"], 50)
        self.assertEqual(summary["J1"]["total"], 150)
        self.assertEqual(summary["J1"]["invoice_count"], 2)
        self.assertEqual(summary["J2"]["91+"], 200)
        self.assertEqual(summary["J2"]["total"], 200)
        # Empty job_number is skipped
        self.assertNotIn("", summary)

    def test_normalize_status(self):
        self.assertIsNone(job_360._normalize_status(None))
        self.assertIsNone(job_360._normalize_status(""))
        self.assertEqual(job_360._normalize_status("Submitted"), "Submitted")
        self.assertEqual(job_360._normalize_status("Custom Status"), "Custom Status")

    def test_operational_row_handles_missing_fields(self):
        spec_keys = job_360.JOB_TYPE_FIELD_MAP["Sea Shipment"].keys()
        row = job_360._operational_row("Sea Shipment", {})
        # Always returns the canonical schema even if source is empty
        for key in [
            "customer", "origin", "destination", "ops_status", "etd", "eta",
            "mode", "vehicle_or_carrier", "estimated_revenue", "estimated_costs",
            "wip_amount_doc", "accrual_amount_doc", "recognized_revenue",
            "recognized_costs", "billing_status", "sla_status",
        ]:
            self.assertIn(key, row)
        self.assertEqual(row["estimated_revenue"], 0.0)

    def test_operational_row_projects_known_fields(self):
        source = {
            "name": "JOB-001",
            "local_customer": "ACME",
            "origin_port": "USNYC",
            "destination_port": "PHMNL",
            "job_status": "Submitted",
            "shipping_status": "In Transit",
            "estimated_revenue": 1000,
            "estimated_costs": 800,
            "wip_amount": 500,
            "accrual_amount": 600,
        }
        row = job_360._operational_row("Sea Shipment", source)
        self.assertEqual(row["customer"], "ACME")
        self.assertEqual(row["origin"], "USNYC")
        self.assertEqual(row["destination"], "PHMNL")
        self.assertEqual(row["estimated_revenue"], 1000.0)
        self.assertEqual(row["estimated_costs"], 800.0)
        self.assertEqual(row["wip_amount_doc"], 500.0)
        self.assertEqual(row["accrual_amount_doc"], 600.0)

    def test_meta_has_field_safe_when_doctype_missing(self):
        # Should not raise; should return False
        self.assertFalse(job_360._meta_has_field("__nonexistent_doctype__", "name"))
        self.assertFalse(job_360._meta_has_field("Job Number", None))
        self.assertFalse(job_360._meta_has_field("Job Number", "__field_that_doesnt_exist__"))

    def test_safe_field_list_drops_unknown_fields(self):
        out = job_360._safe_field_list("Job Number", ["job_type", "__nope__", "company"])
        # name is always added; only valid columns are included
        self.assertIn("name", out)
        self.assertIn("job_type", out)
        self.assertIn("company", out)
        self.assertNotIn("__nope__", out)

    def test_scope_clause_emits_expected_sql(self):
        clause, values = job_360._scope_clause(
            {"company": "Test Co", "branch": "B1", "job_type": "Sea Shipment"}
        )
        self.assertIn("company = %(j360_company)s", clause)
        self.assertIn("branch = %(j360_branch)s", clause)
        self.assertIn("job_type = %(j360_jt)s", clause)
        self.assertEqual(values["j360_company"], "Test Co")

    def test_chart_for_returns_none_for_empty(self):
        self.assertIsNone(job_360.chart_for([], "k", "v"))
        ch = job_360.chart_for([{"k": "a", "v": 1}], "k", "v")
        self.assertEqual(ch["data"]["labels"], ["a"])
        self.assertEqual(ch["data"]["datasets"][0]["values"], [1.0])


class TestJob360API(unittest.TestCase):
    """API-level smoke tests that verify wrapper signatures and return shapes."""

    def test_get_dashboard_kpis_returns_expected_keys(self):
        with patch.object(job_360, "get_job_360_rows", return_value=[]):
            kpis = job_360.get_dashboard_kpis()
        for key in [
            "open_jobs", "at_risk_jobs", "total_jobs", "revenue", "cost",
            "gross_profit", "margin_pct", "wip", "accrual", "ar_outstanding",
            "ap_outstanding",
        ]:
            self.assertIn(key, kpis)

    def test_get_dashboard_kpis_aggregates(self):
        rows = [
            {
                "job_number": "J1", "ops_status": "Submitted",
                "gl_revenue": 100, "gl_cost": 60, "gross_profit": 40,
                "profit_margin_pct": 40.0, "wip_amount": 10,
                "accrual_amount": 5, "ar_outstanding": 0, "ap_outstanding": 0,
                "ar_91_plus": 0,
            },
            {
                "job_number": "J2", "ops_status": "Closed",
                "gl_revenue": 200, "gl_cost": 220, "gross_profit": -20,
                "profit_margin_pct": -10.0, "wip_amount": 0,
                "accrual_amount": 0, "ar_outstanding": 50, "ap_outstanding": 25,
                "ar_91_plus": 30,
            },
        ]
        with patch.object(job_360, "get_job_360_rows", return_value=rows):
            kpis = job_360.get_dashboard_kpis()
        self.assertEqual(kpis["open_jobs"], 1)
        self.assertEqual(kpis["total_jobs"], 2)
        self.assertEqual(kpis["revenue"], 300.0)
        self.assertEqual(kpis["cost"], 280.0)
        self.assertEqual(kpis["gross_profit"], 20.0)
        # J2 has negative GP and 91+ AR → at-risk
        self.assertEqual(kpis["at_risk_jobs"], 1)

    def test_get_jobs_below_margin_filters(self):
        rows = [
            {"job_number": "J1", "gl_revenue": 100, "gross_profit": 5, "profit_margin_pct": 5.0},
            {"job_number": "J2", "gl_revenue": 100, "gross_profit": 50, "profit_margin_pct": 50.0},
            {"job_number": "J3", "gl_revenue": 100, "gross_profit": -20, "profit_margin_pct": -20.0},
            {"job_number": "J4", "gl_revenue": 0, "gross_profit": 5, "profit_margin_pct": 0.0},
        ]
        with patch.object(job_360, "get_job_360_rows", return_value=rows):
            below = job_360.get_jobs_below_margin({"margin_threshold": 10})
        names = sorted(r["job_number"] for r in below)
        # J1 is < threshold; J3 has negative GP; J2 above threshold; J4 has no revenue
        self.assertEqual(names, ["J1", "J3"])

    def test_get_closed_jobs_with_open_balances(self):
        rows = [
            {"job_number": "J1", "ops_status": "Closed",
             "wip_amount": 5, "accrual_amount": 0, "ar_outstanding": 0, "ap_outstanding": 0},
            {"job_number": "J2", "ops_status": "Closed",
             "wip_amount": 0, "accrual_amount": 0, "ar_outstanding": 0, "ap_outstanding": 0},
            {"job_number": "J3", "ops_status": "Submitted",
             "wip_amount": 100, "accrual_amount": 0, "ar_outstanding": 0, "ap_outstanding": 0},
        ]
        with patch.object(job_360, "get_job_360_rows", return_value=rows):
            out = job_360.get_closed_jobs_with_open_balances()
        self.assertEqual([r["job_number"] for r in out], ["J1"])


class TestJob360Modules(unittest.TestCase):
    """Verify the module's public surface matches what the reports expect."""

    def test_job_type_map_has_required_keys(self):
        for jt, spec in job_360.JOB_TYPE_FIELD_MAP.items():
            for k in [
                "customer", "status", "estimated_revenue", "estimated_costs",
                "wip_amount", "accrual_amount",
            ]:
                self.assertIn(k, spec, "{0} missing key {1}".format(jt, k))

    def test_common_filter_meta_has_expected_fields(self):
        meta = job_360.common_filters_meta()
        names = {m["fieldname"] for m in meta}
        for required in {"company", "branch", "from_date", "to_date", "job_type"}:
            self.assertIn(required, names)
