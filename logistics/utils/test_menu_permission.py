# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

"""Tests for custom menu permission helpers and gated whitelist methods."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import unittest

import frappe

from logistics.utils.menu_permission import assert_create_from_source, assert_perm, can_create


def _deny(*_args, **kwargs):
	if kwargs.get("throw"):
		raise frappe.PermissionError("Not permitted")
	return False


class TestMenuPermission(unittest.TestCase):
	def test_assert_perm_throws_when_denied(self):
		with patch("logistics.utils.menu_permission.frappe.has_permission", side_effect=_deny):
			with self.assertRaises(frappe.PermissionError):
				assert_perm("Air Shipment", "create")

	def test_assert_perm_passes_when_allowed(self):
		with patch("logistics.utils.menu_permission.frappe.has_permission", return_value=True) as hp:
			assert_perm("Air Booking", "write", doc=MagicMock())
			hp.assert_called()

	def test_assert_create_from_source_requires_target_create(self):
		src = MagicMock()
		src.doctype = "Air Booking"
		with patch("logistics.utils.menu_permission.frappe.has_permission", side_effect=_deny):
			with self.assertRaises(frappe.PermissionError):
				assert_create_from_source("Air Shipment", source_doc=src)

	def test_can_create_false_when_denied(self):
		with patch("logistics.utils.menu_permission.frappe.has_permission", return_value=False):
			self.assertFalse(can_create("Air Shipment"))

	def test_convert_to_shipment_api_denied_without_create(self):
		booking = MagicMock()
		booking.doctype = "Air Booking"
		with patch(
			"logistics.air_freight.doctype.air_booking.air_booking.frappe.get_doc",
			return_value=booking,
		), patch("logistics.utils.menu_permission.frappe.has_permission", side_effect=_deny):
			from logistics.air_freight.doctype.air_booking.air_booking import convert_to_shipment_api

			with self.assertRaises(frappe.PermissionError):
				convert_to_shipment_api("ABK-TEST")
			booking.convert_to_shipment.assert_not_called()

	def test_create_sales_invoice_from_job_denied_without_create(self):
		job = MagicMock()
		job.doctype = "Air Shipment"
		with patch(
			"logistics.invoice_integration.sales_invoice_api.frappe.db.exists",
			return_value=True,
		), patch(
			"logistics.invoice_integration.sales_invoice_api.frappe.get_doc",
			return_value=job,
		), patch("logistics.utils.menu_permission.frappe.has_permission", side_effect=_deny):
			from logistics.invoice_integration.sales_invoice_api import create_sales_invoice_from_job

			with self.assertRaises(frappe.PermissionError):
				create_sales_invoice_from_job("Air Shipment", "ASP-TEST", customer="CUST")

	def test_populate_documents_denied_without_write(self):
		doc = MagicMock()
		doc.doctype = "Air Booking"
		with patch(
			"logistics.document_management.api.frappe.get_doc",
			return_value=doc,
		), patch("logistics.utils.menu_permission.frappe.has_permission", side_effect=_deny):
			from logistics.document_management.api import populate_documents_from_template

			with self.assertRaises(frappe.PermissionError):
				populate_documents_from_template("Air Booking", "ABK-TEST")

	def test_create_declaration_from_order_denied_without_create(self):
		order = MagicMock()
		order.doctype = "Declaration Order"
		with patch(
			"logistics.customs.doctype.declaration.declaration.frappe.get_doc",
			return_value=order,
		), patch("logistics.utils.menu_permission.frappe.has_permission", side_effect=_deny):
			from logistics.customs.doctype.declaration.declaration import (
				create_declaration_from_declaration_order,
			)

			with self.assertRaises(frappe.PermissionError):
				create_declaration_from_declaration_order("DCO-TEST")

	def test_regenerate_routing_denied_without_write(self):
		leg = MagicMock()
		leg.doctype = "Transport Leg"
		with patch(
			"logistics.transport.doctype.transport_leg.transport_leg.frappe.get_doc",
			return_value=leg,
		), patch("logistics.utils.menu_permission.frappe.has_permission", side_effect=_deny):
			from logistics.transport.doctype.transport_leg.transport_leg import regenerate_routing

			with self.assertRaises(frappe.PermissionError):
				regenerate_routing("TL-TEST")

	def test_get_linked_document_requires_quote_read(self):
		from logistics.pricing_center.doctype.sales_quote.sales_quote import (
			get_linked_document_for_sales_quote,
		)

		quote = MagicMock()
		quote.doctype = "Sales Quote"
		with patch(
			"logistics.pricing_center.doctype.sales_quote.sales_quote.frappe.db.exists",
			return_value=True,
		), patch(
			"logistics.pricing_center.doctype.sales_quote.sales_quote.frappe.get_doc",
			return_value=quote,
		), patch("logistics.utils.menu_permission.frappe.has_permission", side_effect=_deny):
			with self.assertRaises(frappe.PermissionError):
				get_linked_document_for_sales_quote("SQU-TEST", "Air Booking")

	def test_get_linked_document_rejects_unknown_doctype(self):
		from logistics.pricing_center.doctype.sales_quote.sales_quote import (
			get_linked_document_for_sales_quote,
		)

		with self.assertRaises(Exception):
			get_linked_document_for_sales_quote("SQU-TEST", "User")

	def test_create_booking_or_order_denied_without_target_create(self):
		from logistics.pricing_center.sales_quote_booking_creation import (
			create_booking_or_order_from_sales_quote,
		)

		def _deny_create(doctype, ptype="read", *args, **kwargs):
			if str(ptype).lower() == "create":
				if kwargs.get("throw"):
					raise frappe.PermissionError("Not permitted")
				return False
			return True

		sq = MagicMock()
		sq.doctype = "Sales Quote"
		sq.name = "SQU-TEST"
		sq.docstatus = 1
		sq.quotation_type = "Regular"
		sq.main_service = "Air"
		sq.check_permission = MagicMock()
		row = MagicMock()
		with patch(
			"logistics.pricing_center.sales_quote_booking_creation.frappe.db.exists",
			return_value=True,
		), patch(
			"logistics.pricing_center.sales_quote_booking_creation._load_sales_quote_for_booking",
			return_value=sq,
		), patch(
			"logistics.pricing_center.sales_quote_booking_creation.quotation_type_supports_booking_creation",
			return_value=True,
		), patch(
			"logistics.pricing_center.sales_quote_booking_creation._main_service_job_type",
			return_value="Air Booking",
		), patch(
			"logistics.pricing_center.sales_quote_booking_creation._main_service_virtual_row",
			return_value=row,
		), patch(
			"logistics.pricing_center.sales_quote_booking_creation._preview_main_service_creatability",
			return_value={"creatable": True},
		), patch(
			"logistics.pricing_center.sales_quote_booking_creation._merge_creation_parameters",
			return_value=row,
		), patch("logistics.utils.menu_permission.frappe.has_permission", side_effect=_deny_create):
			with self.assertRaises(frappe.PermissionError):
				create_booking_or_order_from_sales_quote("SQU-TEST", "Air Booking")


def run():
	suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestMenuPermission)
	result = unittest.TextTestRunner(verbosity=2).run(suite)
	if not result.wasSuccessful():
		raise AssertionError(f"{len(result.failures) + len(result.errors)} test(s) failed")
