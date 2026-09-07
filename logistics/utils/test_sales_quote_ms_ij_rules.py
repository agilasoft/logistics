# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from logistics.utils.sales_quote_ms_ij_rules import (
	apply_sales_quote_ms_ij_rules,
	has_created_internal_job_children,
	is_internal_job_satellite,
	main_service_has_created_internal_jobs,
)
from logistics.utils.service_role_rules import SERVICE_ROLE_LINKED, SERVICE_ROLE_MAIN


class TestSalesQuoteMsIjRules(UnitTestCase):
	def test_is_internal_job_satellite(self):
		doc = frappe._dict(
			service_role="Linked",
			main_service_type="Sea Shipment",
			main_service="SSP-001",
		)
		self.assertTrue(is_internal_job_satellite(doc))

	def test_main_service_has_created_internal_jobs(self):
		doc = frappe._dict(
			doctype="Air Shipment",
			service_role="Main",
			internal_job_details=[
				frappe._dict(job_no="TRO-CHILD-001"),
			],
		)
		self.assertTrue(main_service_has_created_internal_jobs(doc))
		self.assertTrue(has_created_internal_job_children(doc))

	def test_main_service_locked_when_children_exist(self):
		doc = frappe._dict(
			doctype="Air Shipment",
			service_role="Standalone",
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

	def test_one_off_forces_main_only(self):
		doc = frappe._dict(
			doctype="Air Booking",
			service_role="Standalone",
			main_service_type=None,
			main_service=None,
		)
		with patch(
			"logistics.utils.sales_quote_ms_ij_rules.get_sales_quote_quotation_type",
			return_value="One-off",
		):
			apply_sales_quote_ms_ij_rules(doc)
		self.assertEqual(doc.service_role, SERVICE_ROLE_MAIN)

	def test_project_clears_both(self):
		doc = frappe._dict(
			doctype="Air Booking",
			service_role="Main",
			main_service_type="Sea Shipment",
			main_service="SS-1",
		)
		with patch(
			"logistics.utils.sales_quote_ms_ij_rules.get_sales_quote_quotation_type",
			return_value="Project",
		):
			apply_sales_quote_ms_ij_rules(doc)
		self.assertEqual(doc.service_role, "Standalone")
		self.assertFalse(doc.main_service)

	def test_satellite_clears_main_service(self):
		doc = frappe._dict(
			doctype="Transport Order",
			service_role="Linked",
			main_service_type="Sea Shipment",
			main_service="SS-1",
		)
		apply_sales_quote_ms_ij_rules(doc)
		self.assertEqual(doc.service_role, SERVICE_ROLE_LINKED)
		self.assertEqual(doc.main_service_type, "Sea Shipment")
		self.assertEqual(doc.main_service, "SS-1")

	def test_no_quote_standalone_with_linked_services_allowed(self):
		"""Time Sensitive / standalone jobs may keep Linked Services without a Sales Quote."""
		doc = frappe._dict(
			doctype="Transport Job",
			service_role="Standalone",
			internal_job_details=[
				frappe._dict(job_type="Transport Order", job_no="TRO-TS-001"),
			],
		)
		with patch(
			"logistics.utils.sales_quote_ms_ij_rules.get_sales_quote_quotation_type",
			return_value=None,
		):
			apply_sales_quote_ms_ij_rules(doc)
		self.assertEqual(doc.service_role, "Standalone")
