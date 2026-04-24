# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

"""Unit tests for Get Charges from Quotation corridor helpers.

Integration tests for list filtering live in
``logistics.pricing_center.doctype.sales_quote.test_sales_quote.TestSalesQuote.test_get_charges_from_quotation_list_filters_by_air_corridor``
and
``logistics.pricing_center.doctype.sales_quote.test_sales_quote.TestSalesQuote.test_get_charges_from_quotation_list_filters_by_airline_when_set``.

Manual check (initialized bench site):

  bench --site <site> execute logistics.utils.test_get_charges_from_quotation.run
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from frappe.tests.utils import FrappeTestCase

from logistics.utils.get_charges_from_quotation import (
	_corridor_mismatch_message_for_preview,
	_effective_declaration_order_filter_fields,
	_effective_sea_air_transport_corridor,
)


class TestGetChargesCorridorHelpers(FrappeTestCase):
	"""Pure helpers; no DB."""

	def tearDown(self):
		import frappe

		frappe.db.rollback()

	def test_effective_corridor_air_strips(self):
		d = MagicMock()
		d.doctype = "Air Booking"
		d.origin_port = " USLAX "
		d.destination_port = "USJFK"
		d.airline = ""
		self.assertEqual(_effective_sea_air_transport_corridor(d, {}), ("USLAX", "USJFK", None))

	def test_effective_corridor_transport(self):
		d = MagicMock()
		d.doctype = "Transport Order"
		d.location_from = "A"
		d.location_to = "B"
		self.assertEqual(_effective_sea_air_transport_corridor(d, {}), ("A", "B", None))

	def test_effective_corridor_override(self):
		d = MagicMock()
		d.doctype = "Air Booking"
		d.origin_port = "A"
		d.destination_port = "B"
		d.airline = "AL1"
		self.assertEqual(
			_effective_sea_air_transport_corridor(d, {"origin_port": "O1"}),
			("O1", "B", "AL1"),
		)

	def test_effective_declaration_order_fields(self):
		d = MagicMock()
		d.doctype = "Declaration Order"
		d.customs_authority = " CA "
		d.declaration_type = "Import"
		d.customs_broker = "BR"
		d.transport_mode = "TM"
		d.port_of_loading = " USNYC "
		d.port_of_discharge = "USLAX"
		self.assertEqual(
			_effective_declaration_order_filter_fields(d, {}),
			("CA", "Import", "BR", "TM", "USNYC", "USLAX"),
		)

	@patch("logistics.utils.get_charges_from_quotation.sales_quote_matches_job_corridor", return_value=False)
	def test_corridor_mismatch_message_when_quote_no_match(self, _mock):
		doc = MagicMock()
		doc.doctype = "Air Booking"
		doc.origin_port = "USLAX"
		doc.destination_port = "USJFK"
		doc.airline = ""
		msg = _corridor_mismatch_message_for_preview(doc, "Air", "SQ-TEST-001", {})
		self.assertIsNotNone(msg)
		self.assertIn("SQ-TEST-001", msg)


def run():
	"""Smoke-test helpers on a live site (no DB writes)."""
	from unittest.mock import MagicMock

	from logistics.utils.get_charges_from_quotation import _effective_sea_air_transport_corridor

	d = MagicMock()
	d.doctype = "Air Booking"
	d.origin_port = " X "
	d.destination_port = "Y"
	d.airline = ""
	assert _effective_sea_air_transport_corridor(d, {}) == ("X", "Y", None), _effective_sea_air_transport_corridor(
		d, {}
	)
	print("logistics.utils.test_get_charges_from_quotation.run: OK")
