# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Cross-Docking service type maps to Cross-Docking Order; Warehousing linked stays VAS."""

from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase

from logistics.pricing_center.sales_quote_booking_creation import (
	SALES_QUOTE_CREATABLE_JOB_TYPES,
	_MAIN_SERVICE_JOB_TYPE,
	_preview_main_service_creatability,
	get_sales_quote_booking_choices,
)
from logistics.utils.charge_service_type import (
	default_job_type_for_internal_job_service_type,
	effective_internal_job_detail_job_type,
	implied_service_type_for_doctype,
)


class TestCrossDockingServiceType(unittest.TestCase):
	def test_default_job_type_is_cross_docking_order(self):
		self.assertEqual(
			default_job_type_for_internal_job_service_type("Cross-Docking"),
			"Cross-Docking Order",
		)
		self.assertEqual(
			default_job_type_for_internal_job_service_type("cross-docking"),
			"Cross-Docking Order",
		)

	def test_warehousing_still_maps_to_vas(self):
		self.assertEqual(default_job_type_for_internal_job_service_type("Warehousing"), "VAS Order")

	def test_effective_job_type_for_cross_docking(self):
		row = SimpleNamespace(service_type="Cross-Docking", job_type="", job_no="")
		self.assertEqual(effective_internal_job_detail_job_type(row), "Cross-Docking Order")

	def test_implied_service_type_for_doctype(self):
		self.assertEqual(implied_service_type_for_doctype("Cross-Docking Order"), "Cross-Docking")

	def test_main_service_job_type_mapping(self):
		self.assertNotIn("Cross-Docking", _MAIN_SERVICE_JOB_TYPE)
		self.assertEqual(_MAIN_SERVICE_JOB_TYPE["Time Sensitive"], "Time Sensitive Case")
		self.assertIn("Cross-Docking Order", SALES_QUOTE_CREATABLE_JOB_TYPES)
		self.assertIn("Time Sensitive Case", SALES_QUOTE_CREATABLE_JOB_TYPES)


class TestSalesQuoteTimeSensitiveBooking(UnitTestCase):
	def _ts_quote(self):
		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"name": "SQU-TEST-TS",
				"quotation_type": "Regular",
				"docstatus": 1,
				"main_service": "Time Sensitive",
				"critical_deadline": "2099-01-01 12:00:00",
				"company": "_Test Company",
				"customer": "_Test Customer",
			}
		)
		sq.append(
			"charges",
			{"service_type": "Air"},
		)
		return sq

	def test_main_service_choice_time_sensitive(self):
		sq = self._ts_quote()
		sq.check_permission = lambda *a, **k: None

		with patch(
			"logistics.pricing_center.sales_quote_booking_creation.frappe.db.exists",
			return_value=True,
		), patch(
			"logistics.pricing_center.sales_quote_booking_creation.frappe.get_doc",
			return_value=sq,
		):
			result = get_sales_quote_booking_choices("SQU-TEST-TS")

		self.assertEqual(len(result["choices"]), 1)
		choice = result["choices"][0]
		self.assertEqual(choice["mode"], "main")
		self.assertEqual(choice["job_type"], "Time Sensitive Case")
		self.assertTrue(choice["creatable"])

	def test_preview_creatable(self):
		sq = self._ts_quote()
		flags = _preview_main_service_creatability(sq)
		self.assertTrue(flags["creatable"])

	def test_preview_requires_deadline(self):
		sq = self._ts_quote()
		sq.critical_deadline = None
		flags = _preview_main_service_creatability(sq)
		self.assertFalse(flags["creatable"])


class TestSalesQuoteCrossDockingNotPrimary(UnitTestCase):
	def test_cross_docking_main_service_not_creatable(self):
		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"name": "SQU-TEST-CDO",
				"quotation_type": "Regular",
				"docstatus": 1,
				"main_service": "Cross-Docking",
				"company": "_Test Company",
				"customer": "_Test Customer",
			}
		)
		sq.append("charges", {"service_type": "Cross-Docking"})
		flags = _preview_main_service_creatability(sq)
		self.assertFalse(flags["creatable"])
		self.assertIsNone(_MAIN_SERVICE_JOB_TYPE.get("Cross-Docking"))


class TestCrossDockingOrderMakeWarehouseJob(UnitTestCase):
	def test_make_warehouse_job_sets_cross_dock_type(self):
		from logistics.warehousing.doctype.cross_docking_order import cross_docking_order as cdo_mod

		source = MagicMock()
		source.name = "WCD-0001"
		source.contract = None
		source.company = "_Test Company"
		source.branch = "Main"
		source.customer = "_Test Customer"
		source.shipper = None
		source.consignee = None

		captured = {}

		def fake_mapped(doctype, name, mapping, target_doc, set_missing):
			job = SimpleNamespace(
				type=None,
				reference_order_type=None,
				reference_order=None,
				company=None,
				branch=None,
				customer=None,
				shipper=None,
				consignee=None,
				warehouse_contract=None,
			)
			set_missing(source, job)
			captured["type"] = job.type
			captured["reference_order_type"] = job.reference_order_type
			captured["reference_order"] = job.reference_order
			job.save = MagicMock()
			return job

		with patch.object(cdo_mod.frappe, "get_doc", return_value=source), patch.object(
			cdo_mod, "get_mapped_doc", side_effect=fake_mapped
		), patch.object(cdo_mod.frappe.db, "commit"), patch.object(
			cdo_mod.frappe, "log_error"
		):
			doc = cdo_mod.make_warehouse_job("WCD-0001")

		self.assertEqual(captured["type"], "Cross Dock")
		self.assertEqual(captured["reference_order_type"], "Cross-Docking Order")
		self.assertEqual(captured["reference_order"], "WCD-0001")
		self.assertTrue(doc.save.called)
