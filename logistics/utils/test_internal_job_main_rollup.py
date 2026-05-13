# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Unit tests for the internal-job → Main Service rollup helpers.

These cover the pure-Python calculation helpers without requiring a full operational document
fixture. End-to-end behavior (DB writes from ``sync_internal_job_rollup_to_main``) is exercised
manually via ``bench --site SITE execute ... .refresh_main_service_internal_job_rollup`` and
verified by the test that follows ``calculate_internal_job_rollup_totals`` against shaped
``frappe._dict`` charge rows.

Run from a Frappe bench:

    bench --site SITE run-tests --module logistics.utils.test_internal_job_main_rollup
"""

from __future__ import annotations

import unittest

import frappe

from logistics.utils.internal_job_main_rollup import (
	_charge_actual_cost,
	_charge_actual_revenue,
	_charge_planned_cost,
	_charge_planned_revenue,
	_doc_is_internal_job,
	_is_disbursement_charge,
	calculate_internal_job_rollup_totals,
)


def _row(**kw):
	return frappe._dict(kw)


class TestChargeAmountResolvers(unittest.TestCase):
	"""Field-fallback helpers should pick the first non-zero attribute available on each row."""

	def test_planned_revenue_prefers_estimated_revenue(self):
		row = _row(estimated_revenue=120, base_amount=999, total=55, charge_type="Standard")
		self.assertEqual(_charge_planned_revenue(row), 120)

	def test_planned_revenue_falls_back_to_total_when_estimated_zero(self):
		row = _row(estimated_revenue=0, base_amount=0, total=88, charge_type="Standard")
		self.assertEqual(_charge_planned_revenue(row), 88)

	def test_planned_revenue_total_amount_fallback(self):
		row = _row(estimated_revenue=0, total_amount=42, charge_type="Standard")
		self.assertEqual(_charge_planned_revenue(row), 42)

	def test_planned_cost_prefers_estimated_cost(self):
		row = _row(estimated_cost=75, cost_base_amount=999, charge_type="Standard")
		self.assertEqual(_charge_planned_cost(row), 75)

	def test_planned_cost_falls_back_to_cost_base_amount(self):
		row = _row(estimated_cost=0, cost_base_amount=33, charge_type="Standard")
		self.assertEqual(_charge_planned_cost(row), 33)

	def test_actual_revenue_zero_when_field_missing(self):
		"""Booking / order charge schemas without ``actual_revenue`` should resolve to zero."""
		row = _row(estimated_revenue=120)
		self.assertEqual(_charge_actual_revenue(row), 0)

	def test_actual_revenue_uses_actual_revenue_when_present(self):
		row = _row(actual_revenue=140, estimated_revenue=120)
		self.assertEqual(_charge_actual_revenue(row), 140)

	def test_actual_cost_zero_when_field_missing(self):
		row = _row(estimated_cost=80)
		self.assertEqual(_charge_actual_cost(row), 0)

	def test_actual_cost_uses_actual_cost_when_present(self):
		row = _row(actual_cost=95, estimated_cost=80)
		self.assertEqual(_charge_actual_cost(row), 95)


class TestDisbursementExclusion(unittest.TestCase):
	def test_disbursement_charge_excluded(self):
		row = _row(charge_type="Disbursement", estimated_revenue=200, estimated_cost=200)
		self.assertTrue(_is_disbursement_charge(row))

	def test_non_disbursement_charge_included(self):
		row = _row(charge_type="Standard", estimated_revenue=100, estimated_cost=80)
		self.assertFalse(_is_disbursement_charge(row))

	def test_blank_charge_type_treated_as_non_disbursement(self):
		row = _row(charge_type=None, estimated_revenue=100, estimated_cost=80)
		self.assertFalse(_is_disbursement_charge(row))


class TestCalculateInternalJobRollupTotals(unittest.TestCase):
	def test_sums_planned_and_actual_across_rows(self):
		doc = _row(
			charges=[
				_row(charge_type="Standard", estimated_revenue=120, estimated_cost=80, actual_revenue=130, actual_cost=85),
				_row(charge_type="Standard", estimated_revenue=40, estimated_cost=30, actual_revenue=42, actual_cost=31),
			]
		)
		planned_cost, planned_revenue, actual_cost, actual_revenue = (
			calculate_internal_job_rollup_totals(doc)
		)
		self.assertEqual(planned_cost, 110)
		self.assertEqual(planned_revenue, 160)
		self.assertEqual(actual_cost, 116)
		self.assertEqual(actual_revenue, 172)

	def test_skips_disbursement_rows(self):
		doc = _row(
			charges=[
				_row(charge_type="Standard", estimated_revenue=100, estimated_cost=70),
				_row(charge_type="Disbursement", estimated_revenue=5000, estimated_cost=5000),
			]
		)
		planned_cost, planned_revenue, _ac, _ar = calculate_internal_job_rollup_totals(doc)
		self.assertEqual(planned_cost, 70)
		self.assertEqual(planned_revenue, 100)

	def test_handles_charges_without_actual_fields(self):
		"""Air Booking / Sea Booking / Transport Order / Declaration Order charge rows have estimated only."""
		doc = _row(
			charges=[
				_row(charge_type="Standard", estimated_revenue=200, estimated_cost=150),
			]
		)
		planned_cost, planned_revenue, actual_cost, actual_revenue = (
			calculate_internal_job_rollup_totals(doc)
		)
		self.assertEqual(planned_cost, 150)
		self.assertEqual(planned_revenue, 200)
		# No actual_* attribute on the row → actuals are zero (not a fallback to estimated).
		self.assertEqual(actual_cost, 0)
		self.assertEqual(actual_revenue, 0)

	def test_no_charges_returns_zeros(self):
		doc = _row(charges=[])
		self.assertEqual(calculate_internal_job_rollup_totals(doc), (0, 0, 0, 0))


class TestDocIsInternalJob(unittest.TestCase):
	def test_true_when_flag_and_main_link_set(self):
		doc = _row(is_internal_job=1, main_job_type="Air Shipment", main_job="ASP-000000001")
		self.assertTrue(_doc_is_internal_job(doc))

	def test_false_when_flag_off(self):
		doc = _row(is_internal_job=0, main_job_type="Air Shipment", main_job="ASP-000000001")
		self.assertFalse(_doc_is_internal_job(doc))

	def test_false_when_main_job_missing(self):
		doc = _row(is_internal_job=1, main_job_type="Air Shipment", main_job="")
		self.assertFalse(_doc_is_internal_job(doc))

	def test_false_when_main_job_type_missing(self):
		doc = _row(is_internal_job=1, main_job_type="", main_job="ASP-000000001")
		self.assertFalse(_doc_is_internal_job(doc))


if __name__ == "__main__":
	unittest.main()
