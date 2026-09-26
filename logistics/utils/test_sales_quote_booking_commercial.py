# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from logistics.utils.sales_quote_booking_commercial import (
	apply_sales_quote_commercial_fields_to_operational_doc,
	resolve_sales_quote_customs_broker,
)


class TestSalesQuoteBookingCommercial(UnitTestCase):
	def test_resolve_broker_from_linked_service(self):
		sq = frappe._dict(name="SQU-TEST", customs_broker="")
		ls = frappe._dict(customs_broker="MARICAR PAPINA")
		with patch(
			"logistics.logistics.doctype.linked_service.linked_service.get_linked_services_for_sales_quote",
			return_value=[ls],
		):
			self.assertEqual(resolve_sales_quote_customs_broker(sq), "MARICAR PAPINA")

	def test_resolve_broker_prefers_scope_row(self):
		sq = frappe._dict(name="SQU-TEST", customs_broker="HEADER-BROKER")
		row = frappe._dict(customs_broker="ROW-BROKER")
		self.assertEqual(resolve_sales_quote_customs_broker(sq, row), "ROW-BROKER")

	def test_apply_incoterm_and_broker_to_air_booking(self):
		sq = frappe._dict(name="SQU-TEST", incoterm="EXW", customs_broker="")
		ls = frappe._dict(customs_broker="MARICAR PAPINA")
		booking = frappe.new_doc("Air Booking")
		booking.incoterm = "CIF"
		with patch(
			"logistics.logistics.doctype.linked_service.linked_service.get_linked_services_for_sales_quote",
			return_value=[ls],
		):
			apply_sales_quote_commercial_fields_to_operational_doc(
				booking, sq, overwrite_incoterm=True
			)
		self.assertEqual(booking.incoterm, "EXW")
		self.assertEqual(booking.broker, "MARICAR PAPINA")
