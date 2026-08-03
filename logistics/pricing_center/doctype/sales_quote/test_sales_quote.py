# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today
from logistics.air_freight.tests.test_helpers import (
	setup_basic_master_data,
	create_test_airline,
	create_test_cost_center,
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
			"service_type": "air",
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
			"service_type": "air",
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"direction": "Export",
		})
		self.assertTrue(hasattr(sq, "validate"))
		sq.insert()
		self.assertIsNotNone(sq.name)

	def test_transport_mode_must_match_main_service(self):
		"""Regular / One-off quotes reject Transport Mode incompatible with Main Service."""
		sfx = frappe.generate_hash(length=6)
		sea_mode = frappe.get_doc(
			{
				"doctype": "Transport Mode",
				"mode_code": f"TST-SQ-SEA-{sfx}",
				"mode_name": f"TST Sea {sfx}",
				"primary_document": "Sea Shipment",
				"sea": 1,
				"air": 0,
			}
		).insert(ignore_permissions=True).name
		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"company": self.company,
				"customer": self.customer,
				"date": today(),
				"valid_until": today(),
				"shipper": self.shipper,
				"consignee": self.consignee,
				"quotation_type": "Regular",
				"main_service": "Air",
				"transport_mode": sea_mode,
			}
		)
		sq.append(
			"charges",
			{
				"service_type": "air",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"direction": "Export",
			},
		)
		with self.assertRaises(frappe.ValidationError):
			sq.insert()

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
			"service_type": "air",
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
				"service_type": "air",
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

	def test_get_charges_from_quotation_list_filters_by_cost_center_when_set(self):
		"""When booking Cost Center is set, only quotations with the same header Cost Center are listed."""
		from logistics.utils.get_charges_from_quotation import list_sales_quotes_for_job

		cc_match = create_test_cost_center(self.company, "GCFQ List CC Match")
		cc_other = create_test_cost_center(self.company, "GCFQ List CC Other")

		def _submitted_air_quote(cc_name):
			doc = frappe.get_doc(
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
					"cost_center": cc_name,
				}
			)
			doc.append(
				"charges",
				{
					"service_type": "air",
					"origin_port": "USLAX",
					"destination_port": "USJFK",
					"direction": "Export",
				},
			)
			doc.insert()
			doc.submit()
			return doc.name

		sq_ok = _submitted_air_quote(cc_match)
		sq_wrong = _submitted_air_quote(cc_other)

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
				"cost_center": cc_match,
			}
		)
		booking.insert()

		out = list_sales_quotes_for_job("Air Booking", booking.name)
		names = [r["name"] for r in (out.get("quotes") or [])]
		self.assertIn(sq_ok, names)
		self.assertNotIn(sq_wrong, names)

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
				"service_type": "air",
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
				"service_type": "air",
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

	def test_get_charges_from_quotation_list_airline_only_when_ports_unset(self):
		"""Air Booking: airline set without origin/destination lists quotes by airline, not O/D."""
		from logistics.utils.get_charges_from_quotation import list_sales_quotes_for_job

		create_test_airline("TST-OC", "Test Airline OC")

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
				"service_type": "air",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"direction": "Export",
				"airline": "TST-OC",
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
				"airline": "TST-OC",
			}
		)
		booking.insert()

		out = list_sales_quotes_for_job("Air Booking", booking.name)
		names = [r["name"] for r in (out.get("quotes") or [])]
		self.assertIn(sq.name, names)
		self.assertIsNone(out.get("message"))
		filters = out.get("filters") or {}
		extra = filters.get("extra_criteria") or []
		self.assertTrue(any((e.get("value") == "TST-OC") for e in extra if isinstance(e, dict)))

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
				"service_type": "air",
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
				"service_type": "air",
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
				"service_type": "air",
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
				"service_type": "sea",
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
				"service_type": "air",
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
				"service_type": "air",
				"direction": "Export",
			},
		)
		sq.insert()
		with self.assertRaises(frappe.ValidationError):
			sq.submit()

	def test_project_quote_submit_allowed_without_air_sea_charge_ports(self):
		"""Project quotes skip the Air/Sea charge port corridor check on submit."""
		import uuid

		sq = self._minimal_sales_quote_doc("Air")
		sq.quotation_type = "Project"
		sq.naming_series = "PQ.#####"
		sq.project_name = f"SQ Test Project Air {uuid.uuid4().hex[:8]}"
		rep = frappe.db.get_value("Employee", {}, "name")
		sq.branch = frappe.db.get_value("Branch", {"custom_company": self.company}, "name")
		sq.cost_center = frappe.db.get_value("Cost Center", {"company": self.company}, "name")
		sq.profit_center = frappe.db.get_value("Profit Center", {}, "name")
		sq.sales_rep = rep
		sq.operations_rep = rep
		sq.customer_service_rep = rep
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

	def test_special_project_main_service_submit_allowed_without_air_sea_charge_ports(self):
		"""Special Project main service skips Air/Sea port check (ports collected at booking create)."""
		import uuid

		sq = self._minimal_sales_quote_doc("Special Project")
		sq.quotation_type = "One-off"
		sq.naming_series = "OOQ.#####"
		sq.project_name = f"SQ Test SP Ports {uuid.uuid4().hex[:8]}"
		sq.append(
			"charges",
			{
				"service_type": "Special Project",
			},
		)
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
				"service_type": "Sea",
				"direction": "Export",
			},
		)
		sq.insert()
		sq.submit()
		sq.reload()
		self.assertEqual(sq.docstatus, 1)

	def test_submit_allowed_when_air_ports_only_on_quote(self):
		"""Charge row may leave ports blank if quote-level ports supply both ends."""
		sq = self._minimal_sales_quote_doc("Air")
		sq.origin_port = "USLAX"
		sq.destination_port = "USJFK"
		sq.append(
			"charges",
			{
				"service_type": "air",
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
				"service_type": "air",
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
				"service_type": "air",
				"direction": "Export",
			},
		)
		sq.append(
			"charges",
			{
				"service_type": "air",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"direction": "Export",
			},
		)
		sq.insert()
		sq.submit()
		sq.reload()
		self.assertEqual(sq.docstatus, 1)

	def test_one_off_sea_create_booking_idempotent(self):
		"""One-off Sea: second create returns existing main Sea Booking instead of failing."""
		from logistics.pricing_center.doctype.sales_quote.sales_quote import (
			create_sea_booking_from_sales_quote,
		)

		sq = self._minimal_sales_quote_doc("Sea")
		sq.quotation_type = "One-off"
		sq.naming_series = "OOQ.#####"
		sq.origin_port = "USLAX"
		sq.destination_port = "USJFK"
		sq.append(
			"charges",
			{
				"service_type": "sea",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"direction": "Export",
			},
		)
		sq.insert()
		sq.submit()

		first = create_sea_booking_from_sales_quote(sq.name)
		self.assertTrue(first.get("success"))
		self.assertTrue(first.get("sea_booking"))
		self.assertFalse(first.get("already_exists"))

		second = create_sea_booking_from_sales_quote(sq.name)
		self.assertTrue(second.get("already_exists"))
		self.assertEqual(second.get("sea_booking"), first.get("sea_booking"))

	def test_internal_air_booking_allows_do_converted_one_off_via_hub_shipment(self):
		"""Internal-job Air Booking under Sea Shipment may share quote converted to Declaration Order."""
		from types import SimpleNamespace

		from logistics.pricing_center.doctype.sales_quote.sales_quote import (
			resolve_one_off_declaration_order_chain_allowance,
		)

		doc = SimpleNamespace(
			is_main_service=0,
			is_internal_job=1,
			main_job_type="Sea Shipment",
			main_job="SS-TEST-001",
			sales_quote="OOQ-TEST-001",
		)
		allow, linked_do = resolve_one_off_declaration_order_chain_allowance(
			doc, allow_sea="SB-TEST-001", allow_air=None
		)
		self.assertTrue(allow)
		self.assertIsNone(linked_do)

	def test_exhibits_canonical_service_type_matches_main_service(self):
		from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal

		self.assertTrue(sales_quote_charge_service_types_equal("MICE", "MICE"))
		self.assertTrue(sales_quote_charge_service_types_equal("Events", "MICE"))
		self.assertFalse(sales_quote_charge_service_types_equal("MICE", "Air"))

	def test_exhibits_quote_requires_show_fields(self):
		sq = self._minimal_sales_quote_doc("MICE")
		sq.append(
			"charges",
			{
				"service_type": "MICE",
				"sp_site": self._test_site_address(),
			},
		)
		with self.assertRaises(frappe.ValidationError):
			sq.insert()

	def test_exhibits_quote_submit_with_show_fields_and_charge(self):
		sq = self._minimal_sales_quote_doc("MICE")
		ex = frappe.new_doc("MICE Project")
		ex.project_name = "Test Expo 2026"
		ex.customer = self.customer
		ex.show_open_date = today()
		ex.show_close_date = add_days(today(), 3)
		ex.insert(ignore_permissions=True)
		sq.exhibit = ex.name
		sq.exhibit_show_open_date = today()
		sq.exhibit_show_close_date = add_days(today(), 3)
		sq.append(
			"charges",
			{
				"service_type": "MICE",
				"sp_site": self._test_site_address(),
			},
		)
		sq.insert()
		sq.submit()
		sq.reload()
		self.assertEqual(sq.docstatus, 1)

	def test_project_exhibits_quote_blocks_create_special_project_without_sp_content(self):
		"""Project Exhibits quotes without Special Project charges/resources cannot create SP."""
		from logistics.pricing_center.doctype.sales_quote.sales_quote import (
			create_special_project_from_sales_quote,
		)

		sq = self._minimal_sales_quote_doc("MICE")
		sq.quotation_type = "Project"
		sq.naming_series = "PQ.#####"
		sq.project_name = "SQ Exhibits Programme"
		ex = frappe.new_doc("MICE Project")
		ex.project_name = "Test Expo Programme"
		ex.customer = self.customer
		ex.show_open_date = today()
		ex.show_close_date = add_days(today(), 3)
		ex.insert(ignore_permissions=True)
		sq.exhibit = ex.name
		sq.exhibit_show_open_date = today()
		sq.exhibit_show_close_date = add_days(today(), 3)
		sq.append(
			"charges",
			{
				"service_type": "MICE",
				"sp_site": self._test_site_address(),
			},
		)
		sq.insert()
		sq.submit()
		with self.assertRaises(frappe.ValidationError):
			create_special_project_from_sales_quote(sq.name)

	def test_special_project_submit_with_project_resources_only(self):
		sq = self._minimal_sales_quote_doc("Special Project")
		sq.quotation_type = "Project"
		sq.naming_series = "PQ.#####"
		sq.project_name = "SQ Test Project"
		sq.append(
			"project_resources",
			{
				"resource_type": "Personnel",
				"resource_role": "PM",
				"quantity": 1,
			},
		)
		sq.insert()
		sq.submit()
		sq.reload()
		self.assertEqual(sq.docstatus, 1)

	def test_special_project_submit_blocked_when_erpnext_project_name_exists(self):
		"""Project programme quotes cannot submit when ERPNext Project.project_name is taken."""
		import uuid

		project_name = f"SQ Dup Proj {uuid.uuid4().hex[:8]}"
		if frappe.db.exists("DocType", "Project"):
			proj = frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": project_name,
					"customer": self.customer,
					"company": self.company,
				}
			)
			proj.flags.ignore_mandatory = True
			proj.insert(ignore_permissions=True)

		sq = self._minimal_sales_quote_doc("Special Project")
		sq.quotation_type = "Project"
		sq.naming_series = "PQ.#####"
		sq.project_name = project_name
		sq.append(
			"project_resources",
			{
				"resource_type": "Personnel",
				"resource_role": "PM",
				"quantity": 1,
			},
		)
		sq.insert()
		with self.assertRaises(frappe.ValidationError):
			sq.submit()

	def test_mice_project_quote_submit_allowed_when_customer_project_name_exists(self):
		"""MICE Project (PQ) quotes without SP content must not block on customer-name collision."""
		import uuid

		project_name = f"SQ MICE Cust Dup {uuid.uuid4().hex[:8]}"
		if frappe.db.exists("DocType", "Project"):
			proj = frappe.get_doc(
				{
					"doctype": "Project",
					"project_name": project_name,
					"customer": self.customer,
					"company": self.company,
				}
			)
			proj.flags.ignore_mandatory = True
			proj.insert(ignore_permissions=True)

		customer_name = frappe.db.get_value("Customer", self.customer, "customer_name") or self.customer
		frappe.db.set_value("Customer", self.customer, "customer_name", project_name)

		try:
			ex = frappe.new_doc("MICE Project")
			ex.project_name = f"SQ MICE Expo {uuid.uuid4().hex[:8]}"
			ex.customer = self.customer
			ex.show_open_date = today()
			ex.show_close_date = add_days(today(), 3)
			ex.insert(ignore_permissions=True)

			sq = self._minimal_sales_quote_doc("MICE")
			sq.quotation_type = "Project"
			sq.naming_series = "PQ.#####"
			sq.exhibit = ex.name
			sq.exhibit_show_open_date = today()
			sq.exhibit_show_close_date = add_days(today(), 3)
			sq.append(
				"charges",
				{
					"service_type": "MICE",
					"sp_site": self._test_site_address(),
				},
			)
			sq.insert()
			sq.submit()
			sq.reload()
			self.assertEqual(sq.docstatus, 1)
		finally:
			frappe.db.set_value("Customer", self.customer, "customer_name", customer_name)

	def test_charge_row_parameters_display_from_main_scope(self):
		sq = self._minimal_sales_quote_doc("Sea")
		sq.origin_port = "MNL"
		sq.destination_port = "SIN"
		sq.append("charges", {"service_type": "Sea", "charge_scope": "Main"})
		sq.insert()
		row = sq.charges[0]
		self.assertIn("MNL", row.parameters or "")
		self.assertIn("SIN", row.parameters or "")

	def _test_site_address(self):
		existing = frappe.db.get_value("Address", {}, "name")
		if existing:
			return existing
		addr = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": "SQ Test Site",
				"address_type": "Office",
				"address_line1": "1 Test St",
				"city": "Testville",
			}
		)
		addr.flags.ignore_mandatory = True
		addr.insert(ignore_permissions=True)
		return addr.name

	def _test_special_project_name(self):
		sp = frappe.get_doc(
			{
				"doctype": "Special Project",
				"project_name": "SQ Test Programme",
				"customer": self.customer,
			}
		)
		sp.flags.ignore_mandatory = True
		sp.insert(ignore_permissions=True)
		return sp.name


class TestSalesQuoteEstimatedProfitability(FrappeTestCase):
	"""Unit tests for Sales Quote estimated profitability rollup."""

	def tearDown(self):
		frappe.db.rollback()

	def test_rollup_revenue_cost_profit_margin(self):
		from logistics.pricing_center.doctype.sales_quote.sales_quote import (
			get_sales_quote_estimated_profitability,
			build_sales_quote_profitability_html,
		)

		data = get_sales_quote_estimated_profitability(
			{
				"company": None,
				"charges": [
					{
						"estimated_revenue": 1000,
						"estimated_cost": 600,
						"bill_to_exchange_rate": 1,
						"pay_to_exchange_rate": 1,
					},
					{
						"estimated_revenue": 640,
						"estimated_cost": 430,
						"bill_to_exchange_rate": 1,
						"pay_to_exchange_rate": 1,
					},
				],
			}
		)
		self.assertEqual(data["total_estimated_revenue"], 1640.0)
		self.assertEqual(data["total_estimated_cost"], 1030.0)
		self.assertEqual(data["estimated_profit"], 610.0)
		self.assertEqual(data["estimated_margin_pct"], 37.2)

		html = build_sales_quote_profitability_html(data)
		self.assertIn("Profitability (Estimated)", html)
		self.assertIn("sq-profitability-estimated", html)
		self.assertIn("37.20%", html)

	def test_exchange_rate_conversion(self):
		from logistics.pricing_center.doctype.sales_quote.sales_quote import (
			get_sales_quote_estimated_profitability,
		)

		data = get_sales_quote_estimated_profitability(
			{
				"company": None,
				"charges": [
					{
						"estimated_revenue": 100,
						"estimated_cost": 50,
						"bill_to_exchange_rate": 2,
						"pay_to_exchange_rate": 1.5,
					}
				],
			}
		)
		self.assertEqual(data["total_estimated_revenue"], 200.0)
		self.assertEqual(data["total_estimated_cost"], 75.0)
		self.assertEqual(data["estimated_profit"], 125.0)
