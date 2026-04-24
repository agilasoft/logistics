# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today
from logistics.air_freight.tests.test_helpers import (
	setup_basic_master_data,
	create_test_airline,
	create_test_shipper,
	create_test_consignee,
	create_test_unloco,
)


class TestSalesQuote(FrappeTestCase):
	"""Test cases for Sales Quote doctype"""

	def setUp(self):
		"""Set up test data"""
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		self.shipper = create_test_shipper()
		self.consignee = create_test_consignee()
		create_test_unloco("USLAX", "Los Angeles", "LAX", "US", "Airport")
		create_test_unloco("USJFK", "New York JFK", "JFK", "US", "Airport")

	def tearDown(self):
		frappe.db.rollback()

	def test_sales_quote_creation(self):
		"""Test creating a basic Sales Quote with Air charges"""
		sq = frappe.get_doc({
			"doctype": "Sales Quote",
			"company": self.company,
			"customer": self.customer,
			"date": today(),
			"valid_until": today(),
			"shipper": self.shipper,
			"consignee": self.consignee,
			"main_service": "Air",
		})
		sq.append("charges", {
			"service_type": "Air",
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"direction": "Export",
		})
		sq.insert()

		self.assertIsNotNone(sq.name)
		self.assertEqual(sq.customer, self.customer)
		self.assertEqual(len(sq.charges), 1)

	def test_sales_quote_required_fields(self):
		"""Test that required fields are enforced"""
		sq = frappe.get_doc({"doctype": "Sales Quote"})
		with self.assertRaises((frappe.ValidationError, frappe.MandatoryError)):
			sq.insert()

	def test_sales_quote_validation_methods(self):
		"""Test that Sales Quote has expected validation methods"""
		sq = frappe.get_doc({
			"doctype": "Sales Quote",
			"company": self.company,
			"customer": self.customer,
			"date": today(),
			"valid_until": today(),
			"shipper": self.shipper,
			"consignee": self.consignee,
			"main_service": "Air",
		})
		sq.append("charges", {
			"service_type": "Air",
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"direction": "Export",
		})
		self.assertTrue(hasattr(sq, "validate"))
		sq.insert()
		self.assertIsNotNone(sq.name)

	def test_expired_sales_quote_blocks_creation_guard(self):
		"""Valid Until in the past must raise when creating jobs from the quote."""
		from logistics.utils.sales_quote_validity import throw_if_sales_quote_expired_for_creation

		class _Expired:
			valid_until = add_days(today(), -5)

		with self.assertRaises(frappe.ValidationError):
			throw_if_sales_quote_expired_for_creation(_Expired())

		class _Open:
			valid_until = add_days(today(), 7)

		throw_if_sales_quote_expired_for_creation(_Open())

		class _NoEnd:
			valid_until = None

		throw_if_sales_quote_expired_for_creation(_NoEnd())

	def test_extend_sales_quote_validity(self):
		"""Extend Validity updates valid_until on draft; rejects shorten and past dates."""
		from logistics.pricing_center.doctype.sales_quote.sales_quote import extend_sales_quote_validity

		sq = frappe.get_doc({
			"doctype": "Sales Quote",
			"company": self.company,
			"customer": self.customer,
			"date": today(),
			"valid_until": add_days(today(), 7),
			"shipper": self.shipper,
			"consignee": self.consignee,
			"main_service": "Air",
		})
		sq.append("charges", {
			"service_type": "Air",
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"direction": "Export",
		})
		sq.insert()

		target = add_days(today(), 30)
		out = extend_sales_quote_validity(sq.name, target)
		self.assertTrue(out.get("success"))
		sq.reload()
		self.assertEqual(sq.valid_until, target)

		with self.assertRaises(frappe.ValidationError):
			extend_sales_quote_validity(sq.name, add_days(today(), 15))

		with self.assertRaises(frappe.ValidationError):
			extend_sales_quote_validity(sq.name, add_days(today(), -1))

	def test_get_charges_from_quotation_list_filters_by_air_corridor(self):
		"""Action → Get Charges from Quotation lists only quotes matching booking origin/destination."""
		from logistics.utils.get_charges_from_quotation import list_sales_quotes_for_job

		create_test_unloco("USORD", "Chicago", "ORD", "US", "Airport")

		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"quotation_type": "Regular",
				"company": self.company,
				"customer": self.customer,
				"date": today(),
				"valid_until": today(),
				"shipper": self.shipper,
				"consignee": self.consignee,
				"main_service": "Air",
			}
		)
		sq.append(
			"charges",
			{
				"service_type": "Air",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"direction": "Export",
			},
		)
		sq.insert()
		sq.submit()

		booking = frappe.get_doc(
			{
				"doctype": "Air Booking",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"direction": "Export",
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
			}
		)
		booking.insert()

		out = list_sales_quotes_for_job("Air Booking", booking.name)
		names = [r["name"] for r in (out.get("quotes") or [])]
		self.assertIn(sq.name, names)

		booking_wrong = frappe.get_doc(
			{
				"doctype": "Air Booking",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"direction": "Export",
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USORD",
			}
		)
		booking_wrong.insert()

		out2 = list_sales_quotes_for_job("Air Booking", booking_wrong.name)
		names2 = [r["name"] for r in (out2.get("quotes") or [])]
		self.assertNotIn(sq.name, names2)

	def test_get_charges_from_quotation_list_filters_by_airline_when_set(self):
		"""When Air Booking has airline, only quotes matching that airline (or blank line airline) are listed."""
		from logistics.utils.get_charges_from_quotation import list_sales_quotes_for_job

		create_test_airline("TST-AA", "Test Air A")
		create_test_airline("TST-BB", "Test Air B")

		sq_specific = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"quotation_type": "Regular",
				"company": self.company,
				"customer": self.customer,
				"date": today(),
				"valid_until": today(),
				"shipper": self.shipper,
				"consignee": self.consignee,
				"main_service": "Air",
			}
		)
		sq_specific.append(
			"charges",
			{
				"service_type": "Air",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"direction": "Export",
				"airline": "TST-AA",
			},
		)
		sq_specific.insert()
		sq_specific.submit()

		sq_any = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"quotation_type": "Regular",
				"company": self.company,
				"customer": self.customer,
				"date": today(),
				"valid_until": today(),
				"shipper": self.shipper,
				"consignee": self.consignee,
				"main_service": "Air",
			}
		)
		sq_any.append(
			"charges",
			{
				"service_type": "Air",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"direction": "Export",
			},
		)
		sq_any.insert()
		sq_any.submit()

		booking_aa = frappe.get_doc(
			{
				"doctype": "Air Booking",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"direction": "Export",
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"airline": "TST-AA",
			}
		)
		booking_aa.insert()
		out_aa = list_sales_quotes_for_job("Air Booking", booking_aa.name)
		names_aa = [r["name"] for r in (out_aa.get("quotes") or [])]
		self.assertIn(sq_specific.name, names_aa)
		self.assertIn(sq_any.name, names_aa)

		booking_bb = frappe.get_doc(
			{
				"doctype": "Air Booking",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"direction": "Export",
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"airline": "TST-BB",
			}
		)
		booking_bb.insert()
		out_bb = list_sales_quotes_for_job("Air Booking", booking_bb.name)
		names_bb = [r["name"] for r in (out_bb.get("quotes") or [])]
		self.assertNotIn(sq_specific.name, names_bb)
		self.assertIn(sq_any.name, names_bb)

	def test_get_charges_from_quotation_excludes_draft_sales_quote(self):
		"""Draft Sales Quotes must not appear in Get Charges from Quotation."""
		from logistics.utils.get_charges_from_quotation import list_sales_quotes_for_job

		sq_draft = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"quotation_type": "Regular",
				"company": self.company,
				"customer": self.customer,
				"date": today(),
				"valid_until": today(),
				"shipper": self.shipper,
				"consignee": self.consignee,
				"main_service": "Air",
			}
		)
		sq_draft.append(
			"charges",
			{
				"service_type": "Air",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"direction": "Export",
			},
		)
		sq_draft.insert()

		sq_sub = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"quotation_type": "Regular",
				"company": self.company,
				"customer": self.customer,
				"date": today(),
				"valid_until": today(),
				"shipper": self.shipper,
				"consignee": self.consignee,
				"main_service": "Air",
			}
		)
		sq_sub.append(
			"charges",
			{
				"service_type": "Air",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"direction": "Export",
			},
		)
		sq_sub.insert()
		sq_sub.submit()

		booking = frappe.get_doc(
			{
				"doctype": "Air Booking",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"direction": "Export",
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
			}
		)
		booking.insert()

		out = list_sales_quotes_for_job("Air Booking", booking.name)
		names = [r["name"] for r in (out.get("quotes") or [])]
		self.assertNotIn(sq_draft.name, names)
		self.assertIn(sq_sub.name, names)
		filters = out.get("filters") or {}
		self.assertEqual(filters.get("customer"), self.customer)
		self.assertEqual(filters.get("origin"), "USLAX")
		self.assertEqual(filters.get("destination"), "USJFK")

	def _minimal_sales_quote_doc(self, main_service):
		return frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"quotation_type": "Regular",
				"naming_series": "SQU.#########",
				"company": self.company,
				"customer": self.customer,
				"date": today(),
				"valid_until": today(),
				"shipper": self.shipper,
				"consignee": self.consignee,
				"main_service": main_service,
			}
		)

	def test_submit_blocked_when_main_service_has_no_matching_charges(self):
		"""Cannot submit when Main Service is Sea but no Sea charge rows (e.g. only Air)."""
		sq = self._minimal_sales_quote_doc("Sea")
		sq.append(
			"charges",
			{
				"service_type": "Air",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"direction": "Export",
			},
		)
		sq.insert()
		with self.assertRaises(frappe.ValidationError):
			sq.submit()

	def test_submit_allowed_when_main_service_has_matching_charges(self):
		"""Submit succeeds when at least one charge line matches Main Service."""
		sq = self._minimal_sales_quote_doc("Sea")
		sq.append(
			"charges",
			{
				"service_type": "Sea",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"direction": "Export",
			},
		)
		sq.insert()
		sq.submit()
		sq.reload()
		self.assertEqual(sq.docstatus, 1)

	def test_submit_blocked_warehousing_main_without_warehousing_charges(self):
		"""Warehousing main requires legacy warehousing rows or a Warehousing charge line."""
		sq = self._minimal_sales_quote_doc("Warehousing")
		sq.append(
			"charges",
			{
				"service_type": "Air",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"direction": "Export",
			},
		)
		sq.insert()
		with self.assertRaises(frappe.ValidationError):
			sq.submit()

	def test_submit_blocked_when_air_charge_missing_ports_and_no_quote_fallback(self):
		"""Air/Sea charges cannot be submitted without origin/destination on line or quote."""
		sq = self._minimal_sales_quote_doc("Air")
		sq.append(
			"charges",
			{
				"service_type": "Air",
				"direction": "Export",
			},
		)
		sq.insert()
		with self.assertRaises(frappe.ValidationError):
			sq.submit()

	def test_submit_allowed_when_air_ports_only_on_quote(self):
		"""Charge row may leave ports blank if quote-level ports supply both ends."""
		sq = self._minimal_sales_quote_doc("Air")
		sq.origin_port = "USLAX"
		sq.destination_port = "USJFK"
		sq.append(
			"charges",
			{
				"service_type": "Air",
				"direction": "Export",
			},
		)
		sq.insert()
		sq.submit()
		sq.reload()
		self.assertEqual(sq.docstatus, 1)

	def test_submit_allowed_when_air_ports_from_location_fallback_on_quote(self):
		"""Location From / To on the quote fill missing charge ports (aligned with bookings)."""
		sq = self._minimal_sales_quote_doc("Air")
		sq.location_type = "UNLOCO"
		sq.location_from = "USLAX"
		sq.location_to = "USJFK"
		sq.append(
			"charges",
			{
				"service_type": "Air",
				"direction": "Export",
			},
		)
		sq.insert()
		sq.submit()
		sq.reload()
		self.assertEqual(sq.docstatus, 1)

	def test_submit_allowed_when_only_one_air_row_has_ports(self):
		"""Not every Air line needs ports if at least one line defines Origin and Destination."""
		sq = self._minimal_sales_quote_doc("Air")
		sq.append(
			"charges",
			{
				"service_type": "Air",
				"direction": "Export",
			},
		)
		sq.append(
			"charges",
			{
				"service_type": "Air",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"direction": "Export",
			},
		)
		sq.insert()
		sq.submit()
		sq.reload()
		self.assertEqual(sq.docstatus, 1)
