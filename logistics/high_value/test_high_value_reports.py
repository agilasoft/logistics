# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import date

from frappe.tests.utils import FrappeTestCase

from logistics.high_value.hv_analytics import (
	apply_job_filters,
	apply_quote_filters,
	brand_board_rows,
	sla_age_bucket,
	sort_jobs_by_sla,
)
from logistics.high_value.report.high_value_brand_board import high_value_brand_board
from logistics.high_value.report.high_value_job_health import high_value_job_health
from logistics.high_value.report.high_value_modality_mix import high_value_modality_mix
from logistics.high_value.report.high_value_quote_pipeline import high_value_quote_pipeline
from logistics.high_value.report.high_value_sla_aging import high_value_sla_aging


class TestHighValueReportsHelpers(FrappeTestCase):
	def test_sla_age_bucket(self):
		as_on = date(2026, 9, 16)
		self.assertEqual(sla_age_bucket(None, as_on), "No target")
		self.assertEqual(sla_age_bucket("", as_on), "No target")
		self.assertEqual(sla_age_bucket("2026-09-15", as_on), "Overdue")
		self.assertEqual(sla_age_bucket("2026-09-16", as_on), "Due today")
		self.assertEqual(sla_age_bucket("2026-09-17", as_on), "1-3 days")
		self.assertEqual(sla_age_bucket("2026-09-19", as_on), "1-3 days")
		self.assertEqual(sla_age_bucket("2026-09-20", as_on), "4-7 days")
		self.assertEqual(sla_age_bucket("2026-09-23", as_on), "4-7 days")
		self.assertEqual(sla_age_bucket("2026-09-24", as_on), "8+ days")

	def test_apply_job_filters_live_sla_brand(self):
		jobs = [
			{"name": "A", "job_status": "In Progress", "sla_status": "Breached", "hv_brand": "ROLEX"},
			{"name": "B", "job_status": "Draft", "sla_status": "On Track", "hv_brand": "ROLEX"},
			{"name": "C", "job_status": "Submitted", "sla_status": "At Risk", "hv_brand": "CARTIER"},
			{"name": "D", "job_status": "Completed", "sla_status": "Breached", "hv_brand": "ROLEX"},
		]
		self.assertEqual(
			{r["name"] for r in apply_job_filters(jobs, {"live_only": 1})},
			{"A", "C"},
		)
		self.assertEqual(
			[r["name"] for r in apply_job_filters(jobs, {"sla_status": "Breached"})],
			["A", "D"],
		)
		self.assertEqual(
			[r["name"] for r in apply_job_filters(jobs, {"hv_brand": "CARTIER"})],
			["C"],
		)
		self.assertEqual(
			[r["name"] for r in apply_job_filters(jobs, {"job_status": "Draft"})],
			["B"],
		)

	def test_apply_quote_filters_and_sla_sort(self):
		quotes = [
			{"name": "SQ-1", "hv_brand": "ROLEX"},
			{"name": "SQ-2", "hv_brand": "CARTIER"},
		]
		self.assertEqual(
			[q["name"] for q in apply_quote_filters(quotes, {"hv_brand": "ROLEX"})],
			["SQ-1"],
		)
		jobs = [
			{"name": "ON", "sla_status": "On Track", "sla_target_date": "2026-09-10"},
			{"name": "BR", "sla_status": "Breached", "sla_target_date": "2026-09-20"},
			{"name": "AR", "sla_status": "At Risk", "sla_target_date": "2026-09-01"},
		]
		self.assertEqual([j["name"] for j in sort_jobs_by_sla(jobs)], ["BR", "AR", "ON"])

	def test_brand_board_rows_from_fixtures(self):
		brands = [
			{"name": "ROLEX", "brand_name": "Rolex"},
			{"name": "IDLE", "brand_name": "Idle"},
		]
		quotes = [
			{
				"name": "SQ-1",
				"hv_brand": "ROLEX",
				"docstatus": 0,
				"total_estimated_revenue": 100,
				"estimated_profit": 20,
				"owner": "Administrator",
			}
		]
		jobs = [
			{
				"name": "AIR-1",
				"hv_brand": "ROLEX",
				"job_status": "In Progress",
				"sla_status": "Breached",
				"owner": "Administrator",
			}
		]
		rows = brand_board_rows(brands, quotes, jobs)
		by_name = {r["name"]: r for r in rows}
		self.assertEqual(by_name["ROLEX"]["severity"], "overdue")
		self.assertEqual(by_name["ROLEX"]["estimated_revenue"], 100)
		self.assertEqual(by_name["ROLEX"]["estimated_profit"], 20)
		self.assertEqual(by_name["ROLEX"]["sla_breached"], 1)
		self.assertEqual(by_name["ROLEX"]["live_job_count"], 1)
		self.assertEqual(by_name["IDLE"]["severity"], "idle")
		self.assertEqual(rows[0]["name"], "ROLEX")

	def test_execute_returns_columns_and_list(self):
		modules = (
			high_value_job_health,
			high_value_sla_aging,
			high_value_brand_board,
			high_value_quote_pipeline,
			high_value_modality_mix,
		)
		for mod in modules:
			result = mod.execute({})
			self.assertGreaterEqual(len(result), 2)
			columns, data = result[0], result[1]
			self.assertTrue(columns)
			self.assertIsInstance(data, list)
			self.assertTrue(all("fieldname" in c for c in columns))
