# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""One-off Sales Quote chain allowances for multimodal internal jobs (#927)."""

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.pricing_center.doctype.sales_quote.sales_quote import (
	_allow_linked_transport_order_for_shipment_hub,
	resolve_allow_linked_internal_job_freight_satellites_from_converted,
	resolve_allow_linked_transport_order_for_internal_job_satellite,
	resolve_one_off_chain_freight_booking_allowances,
	resolve_one_off_declaration_order_chain_allowance,
	should_persist_one_off_quote_conversion_on_submit,
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

	def test_air_shipment_allowed_with_declaration_order_chain_allowance(self):
		"""Booking → Shipment conversion: internal-job shipment shares DO-converted quote."""
		from types import SimpleNamespace

		doc = SimpleNamespace(
			is_main_service=0,
			is_internal_job=1,
			main_job_type="Declaration Order",
			main_job="DCO-TEST-001",
			sales_quote="OOQ-TEST-001",
		)
		with patch.object(frappe.db, "exists", return_value=True):
			allow, linked_do = resolve_one_off_declaration_order_chain_allowance(doc)
		self.assertTrue(allow)
		self.assertEqual(linked_do, "DCO-TEST-001")

		with self._mock_one_off_converted_quote("Declaration Order DCO-TEST-001"), patch.object(
			frappe.db, "exists", return_value=True
		):
			validate_one_off_quote_not_converted(
				"OOQ-TEST-001",
				"Air Shipment",
				"ASM-NEW",
				allow_main_transport_if_converted_to_declaration_order=allow,
			)

	def test_air_shipment_raises_without_declaration_order_chain_allowance(self):
		with self._mock_one_off_converted_quote("Declaration Order DCO-TEST-001"):
			with self.assertRaises(frappe.ValidationError):
				validate_one_off_quote_not_converted(
					"OOQ-TEST-001",
					"Air Shipment",
					"ASM-NEW",
				)


class TestIssue1037InternalJobFreightSatellites(FrappeTestCase):
	"""Transport Order after internal-job Air Booking / Air Shipment on the same hub (#1037)."""

	def test_should_not_persist_conversion_for_internal_job_air_booking(self):
		with patch.object(frappe.db, "get_value") as gv, patch.object(
			frappe.db, "exists", return_value=True
		), patch.object(frappe, "get_meta") as gm:

			gv.return_value = 0
			gm.return_value.has_field = lambda _f: True
			self.assertFalse(
				should_persist_one_off_quote_conversion_on_submit("Air Booking", "ABK-IJ-001")
			)

	def test_should_persist_conversion_for_main_service_air_booking(self):
		with patch.object(frappe.db, "get_value") as gv, patch.object(
			frappe.db, "exists", return_value=True
		), patch.object(frappe, "get_meta") as gm:

			gv.return_value = 1
			gm.return_value.has_field = lambda _f: True
			self.assertTrue(
				should_persist_one_off_quote_conversion_on_submit("Air Booking", "ABK-MAIN-001")
			)

	def test_ij_air_booking_on_hub_allowed_for_transport_order(self):
		hub = "ASM-HUB-1037"
		ij_booking = "ABK-IJ-1037"
		sq = "OOQ-1037"

		def _mock_exists(doctype, name):
			return name in (hub, ij_booking, sq)

		with patch.object(frappe.db, "get_value") as gv, patch.object(
			frappe.db, "exists", side_effect=_mock_exists
		):

			def side_effect(doctype, name, fieldname=None, *args, **kwargs):
				if doctype == "Sales Quote" and fieldname == "converted_to_doc":
					return f"Air Booking {ij_booking}"
				if doctype == "Air Booking" and name == ij_booking:
					if isinstance(fieldname, list):
						return {
							"is_internal_job": 1,
							"main_job_type": "Air Shipment",
							"main_job": hub,
							"sales_quote": sq,
							"docstatus": 1,
						}
				return None

			gv.side_effect = side_effect
			_, allow_air = resolve_allow_linked_internal_job_freight_satellites_from_converted(
				sq, "Air Shipment", hub
			)
		self.assertEqual(allow_air, ij_booking)

	def test_transport_order_validate_allows_ij_air_booking_conversion(self):
		with patch(
			"logistics.pricing_center.doctype.sales_quote.sales_quote.frappe.get_doc",
			return_value=frappe._dict(
				quotation_type="One-off",
				status="Converted",
				converted_to_doc="Air Booking ABK-IJ-1037",
			),
		):
			validate_one_off_quote_not_converted(
				"OOQ-1037",
				"Transport Order",
				"TRO-NEW",
				allow_linked_air_booking="ABK-IJ-1037",
			)

	def test_chain_helper_prefers_ij_converted_booking_over_hub_parent(self):
		"""Hub parent ABK-700 must not block conv/ij allowance ABK-701 (#1037 production case)."""
		hub = "ASP-000000291"
		main_booking = "ABK-000000700"
		ij_booking = "ABK-000000701"
		sq = "OOQ00343"
		doc = frappe._dict(
			doctype="Transport Order",
			is_internal_job=1,
			main_job_type="Air Shipment",
			main_job=hub,
			air_shipment=hub,
			sales_quote=sq,
			name="TRO-NEW",
		)

		known = {
			("Air Shipment", hub, "air_booking"): main_booking,
			("Air Booking", ij_booking): {
				"is_internal_job": 1,
				"main_job_type": "Air Shipment",
				"main_job": hub,
				"sales_quote": sq,
				"docstatus": 1,
			},
			("Air Booking", main_booking): {
				"is_internal_job": 0,
				"main_job_type": None,
				"main_job": None,
				"sales_quote": sq,
				"docstatus": 1,
			},
		}

		def _mock_exists(doctype, name):
			return (doctype, name) in known or name in (hub, main_booking, ij_booking, sq)

		with patch.object(frappe.db, "get_value") as gv, patch.object(
			frappe.db, "exists", side_effect=_mock_exists
		), patch.object(
			frappe.db,
			"get_all",
			return_value=[{"name": main_booking}],
		):

			def side_effect(doctype, name, fieldname=None, *args, **kwargs):
				if doctype == "Sales Quote" and fieldname == "converted_to_doc":
					return f"Air Booking {ij_booking}"
				key = (doctype, name)
				if isinstance(fieldname, str) and key in known:
					val = known[key]
					if isinstance(val, dict):
						return val.get(fieldname)
					return val
				if isinstance(fieldname, list) and key in known:
					return known[key]
				return None

			gv.side_effect = side_effect
			_, allow_air = resolve_one_off_chain_freight_booking_allowances(doc, sq)

		self.assertEqual(allow_air, ij_booking)

	def test_chain_helper_allows_transport_order_validate(self):
		hub = "ASP-000000291"
		ij_booking = "ABK-000000701"
		sq = "OOQ00343"
		doc = frappe._dict(
			doctype="Transport Order",
			is_internal_job=1,
			main_job_type="Air Shipment",
			main_job=hub,
			air_shipment=hub,
			sales_quote=sq,
			name="TRO-NEW",
		)

		with patch(
			"logistics.pricing_center.doctype.sales_quote.sales_quote.resolve_one_off_chain_freight_booking_allowances",
			return_value=(None, ij_booking),
		), patch(
			"logistics.pricing_center.doctype.sales_quote.sales_quote.frappe.get_doc",
			return_value=frappe._dict(
				quotation_type="One-off",
				status="Converted",
				converted_to_doc=f"Air Booking {ij_booking}",
			),
		):
			_, allow_air = resolve_one_off_chain_freight_booking_allowances(doc, sq)
			validate_one_off_quote_not_converted(
				sq,
				"Transport Order",
				"TRO-NEW",
				allow_linked_air_booking=allow_air,
			)
