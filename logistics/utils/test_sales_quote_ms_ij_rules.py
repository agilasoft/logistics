# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from logistics.utils.sales_quote_ms_ij_rules import (
	apply_sales_quote_ms_ij_rules,
	is_internal_job_satellite,
	main_service_has_created_internal_jobs,
)


class TestSalesQuoteMsIjRules(UnitTestCase):
	def test_satellite_clears_main_service(self):
		doc = frappe._dict(
			is_internal_job=1,
			is_main_service=1,
			main_job_type="Air Shipment",
			main_job="ASP-TEST-001",
		)
		apply_sales_quote_ms_ij_rules(doc)
		self.assertEqual(doc.is_main_service, 0)
		self.assertEqual(doc.is_internal_job, 1)

	def test_one_off_forces_main_only(self):
		doc = frappe._dict(
			doctype="Transport Order",
			sales_quote="OOQ-TEST-RULES-001",
			is_main_service=0,
			is_internal_job=0,
		)
		with (
			patch(
				"logistics.utils.sales_quote_ms_ij_rules.get_sales_quote_quotation_type",
				return_value="One-off",
			),
		):
			apply_sales_quote_ms_ij_rules(doc)
		self.assertEqual(doc.is_main_service, 1)
		self.assertEqual(doc.is_internal_job, 0)

	def test_project_clears_both(self):
		doc = frappe._dict(
			doctype="Transport Order",
			sales_quote="PQ-TEST-RULES-001",
			is_main_service=1,
			is_internal_job=1,
		)
		with patch(
			"logistics.utils.sales_quote_ms_ij_rules.get_sales_quote_quotation_type",
			return_value="Project",
		):
			apply_sales_quote_ms_ij_rules(doc)
		self.assertEqual(doc.is_main_service, 0)
		self.assertEqual(doc.is_internal_job, 0)

	def test_main_service_has_created_internal_jobs(self):
		doc = frappe._dict(
			doctype="Air Shipment",
			is_main_service=1,
			internal_job_details=[
				frappe._dict(job_no="TRO-CHILD-001"),
			],
		)
		self.assertTrue(main_service_has_created_internal_jobs(doc))

	def test_is_internal_job_satellite(self):
		doc = frappe._dict(
			is_internal_job=1,
			main_job_type="Sea Shipment",
			main_job="SSP-001",
		)
		self.assertTrue(is_internal_job_satellite(doc))

	def test_main_service_locked_when_children_exist(self):
		doc = frappe._dict(
			doctype="Air Shipment",
			is_main_service=0,
			is_internal_job=0,
			internal_job_details=[
				frappe._dict(job_type="Transport Order", job_no="TRO-LOCK-001"),
			],
		)
		with patch(
			"logistics.utils.sales_quote_ms_ij_rules.get_sales_quote_quotation_type",
			return_value="Regular",
		):
			with self.assertRaises(frappe.ValidationError):
				apply_sales_quote_ms_ij_rules(doc)
