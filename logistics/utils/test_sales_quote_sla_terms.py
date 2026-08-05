# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import UnitTestCase

from logistics.utils.sales_quote_sla_terms import (
	apply_sales_quote_sla_and_terms,
	resolve_sales_quote_service_level,
	resolve_sales_quote_terms_link,
)


class TestSalesQuoteSlaTerms(UnitTestCase):
	def test_resolve_prefers_service_code(self):
		sq = frappe._dict(service_code="Express", service_level="Standard")
		self.assertEqual(resolve_sales_quote_service_level(sq), "Express")
		self.assertEqual(resolve_sales_quote_terms_link(frappe._dict(tc_name="NET30")), "NET30")

	def test_air_booking_maps_service_code_and_tc_name(self):
		booking = frappe.new_doc("Air Booking")
		sq = frappe._dict(
			service_code="Express",
			service_level_details="<p>Express SLA</p>",
			tc_name="Standard Terms",
			terms="<p>Payment in 30 days</p>",
		)

		apply_sales_quote_sla_and_terms(booking, sq, overwrite=False)

		self.assertEqual(booking.service_level, "Express")
		self.assertEqual(booking.tc_name, "Standard Terms")
		self.assertEqual(booking.terms, "<p>Payment in 30 days</p>")
		# Air Booking has no service_level_details field; Sea/Transport do.
		self.assertFalse(frappe.get_meta("Air Booking").has_field("service_level_details"))

	def test_sea_booking_maps_service_level_details(self):
		booking = frappe.new_doc("Sea Booking")
		sq = frappe._dict(
			service_code="Express",
			service_level_details="<p>Express SLA</p>",
			tc_name="Standard Terms",
			terms="<p>Payment</p>",
		)

		apply_sales_quote_sla_and_terms(booking, sq, overwrite=False)

		self.assertEqual(booking.service_level, "Express")
		self.assertEqual(booking.service_level_details, "<p>Express SLA</p>")
		self.assertEqual(booking.tc_name, "Standard Terms")
		self.assertEqual(booking.terms, "<p>Payment</p>")

	def test_sea_booking_does_not_overwrite_existing_when_empty_mode(self):
		booking = frappe.new_doc("Sea Booking")
		booking.service_level = "Already Set"
		booking.tc_name = "Keep Me"
		sq = frappe._dict(
			service_code="Express",
			tc_name="Standard Terms",
			terms="<p>New terms</p>",
		)

		apply_sales_quote_sla_and_terms(booking, sq, overwrite=False)

		self.assertEqual(booking.service_level, "Already Set")
		self.assertEqual(booking.tc_name, "Keep Me")

	def test_overwrite_replaces_existing(self):
		booking = frappe.new_doc("Sea Booking")
		booking.service_level = "Old"
		booking.tc_name = "Old Terms"
		sq = frappe._dict(
			service_code="Express",
			tc_name="Standard Terms",
			terms="<p>New</p>",
		)

		apply_sales_quote_sla_and_terms(booking, sq, overwrite=True)

		self.assertEqual(booking.service_level, "Express")
		self.assertEqual(booking.tc_name, "Standard Terms")
		self.assertEqual(booking.terms, "<p>New</p>")

	def test_transport_order_maps_terms_link_field(self):
		order = frappe.new_doc("Transport Order")
		sq = frappe._dict(
			service_code="Express",
			tc_name="Standard Terms",
			terms="<p>Details</p>",
		)

		apply_sales_quote_sla_and_terms(order, sq, overwrite=False)

		self.assertEqual(order.service_level, "Express")
		self.assertEqual(order.terms, "Standard Terms")
		self.assertEqual(order.terms_and_conditions_details, "<p>Details</p>")

	def test_declaration_order_maps_service_level_only(self):
		order = frappe.new_doc("Declaration Order")
		sq = frappe._dict(
			service_code="Express",
			tc_name="Standard Terms",
			terms="<p>Details</p>",
		)

		apply_sales_quote_sla_and_terms(order, sq, overwrite=False)

		self.assertEqual(order.service_level, "Express")
