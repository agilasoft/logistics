# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""One-off Sales Quote chain allowances for multimodal internal jobs (#927)."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.pricing_center.doctype.sales_quote.sales_quote import (
	_allow_linked_transport_order_for_shipment_hub,
	resolve_allow_linked_transport_order_for_internal_job_satellite,
	validate_one_off_quote_not_converted,
)


def _declaration_order_satellite(main_job_type, main_job, sales_quote="OOQ-TEST-927"):
	return frappe._dict(
		doctype="Declaration Order",
		is_internal_job=1,
		main_job_type=main_job_type,
		main_job=main_job,
		sales_quote=sales_quote,
		name="DCO-NEW-001",
	)


class TestInternalJobOneOffChainResolvers(FrappeTestCase):
	"""Unit tests for TRO chain resolution on internal-job satellites."""

	def _mock_exists(self, doctype, name):
		n = (name or "").strip()
		if doctype == "Transport Order":
			return n in ("TRO-001", "TRO-002", "TRO-003")
		if doctype == "Declaration":
			return n == "DEC-001"
		return False

	def test_shipment_hub_matches_linked_tro(self):
		with patch.object(frappe.db, "get_value") as gv, patch.object(
			frappe.db, "exists", side_effect=self._mock_exists
		):

			def side_effect(doctype, name, fieldname=None, *args, **kwargs):
				if doctype == "Sales Quote" and fieldname == "converted_to_doc":
					return "Transport Order TRO-001"
				if doctype == "Transport Order" and fieldname == "air_shipment":
					return "ASM-HUB-001"
				return None

			gv.side_effect = side_effect
			tro = _allow_linked_transport_order_for_shipment_hub(
				"OOQ-TEST", "Air Shipment", "ASM-HUB-001"
			)
		self.assertEqual(tro, "TRO-001")

	def test_issue_927_air_shipment_hub_on_declaration_order(self):
		"""Declaration Order under Air Shipment after quote converted to linked TRO."""
		doc = _declaration_order_satellite("Air Shipment", "ASM-HUB-001")
		with patch.object(frappe.db, "get_value") as gv, patch.object(
			frappe.db, "exists", side_effect=self._mock_exists
		):

			def side_effect(doctype, name, fieldname=None, *args, **kwargs):
				if doctype == "Sales Quote" and fieldname == "converted_to_doc":
					return "Transport Order TRO-001"
				if doctype == "Transport Order" and fieldname == "air_shipment":
					return "ASM-HUB-001"
				return None

			gv.side_effect = side_effect
			tro = resolve_allow_linked_transport_order_for_internal_job_satellite(doc)
		self.assertEqual(tro, "TRO-001")

	def test_transport_job_hub_on_declaration_order(self):
		doc = _declaration_order_satellite("Transport Job", "TJ-001")
		with patch.object(frappe.db, "get_value") as gv, patch.object(
			frappe.db, "exists", side_effect=self._mock_exists
		):

			def side_effect(doctype, name, fieldname=None, *args, **kwargs):
				if doctype == "Sales Quote" and fieldname == "converted_to_doc":
					return "TRO-002"
				if doctype == "Transport Order" and name == "TRO-002":
					if isinstance(fieldname, list):
						return {
							"main_job_type": "Transport Job",
							"main_job": "TJ-001",
						}
				return None

			gv.side_effect = side_effect
			tro = resolve_allow_linked_transport_order_for_internal_job_satellite(doc)
		self.assertEqual(tro, "TRO-002")

	def test_declaration_hub_via_linked_air_shipment(self):
		doc = _declaration_order_satellite("Declaration", "DEC-001")
		with patch.object(frappe.db, "get_value") as gv, patch.object(
			frappe.db, "exists", side_effect=self._mock_exists
		):

			def side_effect(doctype, name, fieldname=None, *args, **kwargs):
				if doctype == "Sales Quote" and fieldname == "converted_to_doc":
					return "Transport Order TRO-003"
				if doctype == "Declaration" and isinstance(fieldname, list):
					return {"air_shipment": "ASM-VIA-DEC", "sea_shipment": None}
				if doctype == "Transport Order" and fieldname == "air_shipment":
					return "ASM-VIA-DEC"
				return None

			gv.side_effect = side_effect
			tro = resolve_allow_linked_transport_order_for_internal_job_satellite(doc)
		self.assertEqual(tro, "TRO-003")

	def test_satellite_returns_none_when_tro_unrelated(self):
		doc = _declaration_order_satellite("Transport Job", "TJ-OTHER")
		with patch.object(frappe.db, "get_value") as gv, patch.object(
			frappe.db, "exists", side_effect=self._mock_exists
		):

			def side_effect(doctype, name, fieldname=None, *args, **kwargs):
				if doctype == "Sales Quote" and fieldname == "converted_to_doc":
					return "TRO-002"
				if doctype == "Transport Order" and name == "TRO-002":
					if isinstance(fieldname, list):
						return {
							"main_job_type": "Transport Job",
							"main_job": "TJ-001",
						}
				return None

			gv.side_effect = side_effect
			tro = resolve_allow_linked_transport_order_for_internal_job_satellite(doc)
		self.assertIsNone(tro)


class TestValidateOneOffWithChainAllowances(FrappeTestCase):
	"""validate_one_off_quote_not_converted must allow siblings when allowances are set."""

	def _mock_one_off_converted_quote(self, converted_to_doc):
		sq = frappe._dict(
			quotation_type="One-off",
			status="Converted",
			converted_to_doc=converted_to_doc,
		)
		return patch(
			"logistics.pricing_center.doctype.sales_quote.sales_quote.frappe.get_doc",
			return_value=sq,
		)

	def test_declaration_order_allowed_with_linked_tro(self):
		with self._mock_one_off_converted_quote("Transport Order TRO-001"):
			validate_one_off_quote_not_converted(
				"OOQ-TEST",
				"Declaration Order",
				"DCO-NEW",
				allow_linked_transport_order="TRO-001",
			)

	def test_declaration_order_raises_without_linked_tro(self):
		with self._mock_one_off_converted_quote("Transport Order TRO-001"):
			with self.assertRaises(frappe.ValidationError):
				validate_one_off_quote_not_converted(
					"OOQ-TEST",
					"Declaration Order",
					"DCO-NEW",
				)
