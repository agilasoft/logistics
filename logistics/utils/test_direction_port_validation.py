# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from logistics.air_freight.tests.test_helpers import (
	create_test_consignee,
	create_test_shipper,
	create_test_unloco,
	setup_basic_master_data,
)
from logistics.utils.direction_port_validation import (
	get_company_country_code,
	get_unloco_country_code,
	validate_direction_port_alignment,
	validate_sales_quote_direction_ports,
)


class TestDirectionPortValidation(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.us_country = frappe.db.get_value("Country", {"code": "US"}, "name")
		cls.ph_country = frappe.db.get_value("Country", {"code": "PH"}, "name")
		if not cls.us_country:
			raise cls.skipTest("Country master US required")

	def setUp(self):
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		self.shipper = create_test_shipper()
		self.consignee = create_test_consignee()
		create_test_unloco("USLAX", "Los Angeles", "LAX", "US", "Airport")
		create_test_unloco("USJFK", "New York JFK", "JFK", "US", "Airport")
		create_test_unloco("SGSIN", "Singapore", country_code="SG")
		if self.ph_country:
			create_test_unloco("PHMNL", "Manila", "MNL", "PH", "Airport")
			create_test_unloco("PHCEB", "Cebu", "CEB", "PH", "Airport")
		frappe.db.set_value("Company", self.company, "country", self.us_country)

	def tearDown(self):
		frappe.db.rollback()

	def test_country_code_helpers(self):
		self.assertEqual(get_company_country_code(self.company), "US")
		self.assertEqual(get_unloco_country_code("USLAX"), "US")
		self.assertEqual(get_unloco_country_code("SGSIN"), "SG")

	def test_export_valid_us_origin(self):
		validate_direction_port_alignment(
			"Export", "USLAX", "SGSIN", self.company, require_ports=True
		)

	def test_export_invalid_foreign_origin(self):
		with self.assertRaises(frappe.ValidationError):
			validate_direction_port_alignment(
				"Export", "SGSIN", "USJFK", self.company, require_ports=True
			)

	def test_import_valid_us_destination(self):
		validate_direction_port_alignment(
			"Import", "SGSIN", "USJFK", self.company, require_ports=True
		)

	def test_import_invalid_foreign_destination(self):
		with self.assertRaises(frappe.ValidationError):
			validate_direction_port_alignment(
				"Import", "USLAX", "SGSIN", self.company, require_ports=True
			)

	def test_domestic_valid_both_us(self):
		validate_direction_port_alignment(
			"Domestic", "USLAX", "USJFK", self.company, require_ports=True
		)

	def test_domestic_invalid_foreign_destination(self):
		with self.assertRaises(frappe.ValidationError):
			validate_direction_port_alignment(
				"Domestic", "USLAX", "SGSIN", self.company, require_ports=True
			)

	def test_sales_quote_header_export_passes(self):
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
				"direction": "Export",
				"origin_port": "USLAX",
				"destination_port": "SGSIN",
			}
		)
		sq.append("charges", {"service_type": "Air"})
		validate_sales_quote_direction_ports(sq)

	def test_sales_quote_header_import_fails(self):
		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"quotation_type": "One-off",
				"company": self.company,
				"customer": self.customer,
				"date": today(),
				"valid_until": today(),
				"shipper": self.shipper,
				"consignee": self.consignee,
				"main_service": "Sea",
				"direction": "Import",
				"origin_port": "USLAX",
				"destination_port": "SGSIN",
			}
		)
		sq.append("charges", {"service_type": "Sea"})
		with self.assertRaises(frappe.ValidationError):
			validate_sales_quote_direction_ports(sq)

	def test_sales_quote_skips_without_quotation_type(self):
		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
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
				"origin_port": "SGSIN",
				"destination_port": "USJFK",
				"direction": "Export",
			},
		)
		validate_sales_quote_direction_ports(sq)

	@classmethod
	def tearDownClass(cls):
		super().tearDownClass()
