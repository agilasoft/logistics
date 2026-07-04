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
from logistics.utils.freight_agent_location_validation import (
	get_freight_agent_covered_unlocos,
	validate_freight_agent_covers_ports,
	validate_sales_quote_freight_agent_locations,
)


def create_test_freight_agent(
	code="TEST-FA",
	freight_agent_name="Test Freight Agent",
	covered_unlocs=None,
	default_unloco=None,
):
	"""Create a test freight agent with optional covered UNLOCOs."""
	if frappe.db.exists("Freight Agent", code):
		return code

	doc = frappe.get_doc(
		{
			"doctype": "Freight Agent",
			"code": code,
			"freight_agent_name": freight_agent_name,
			"default_unloco": default_unloco,
			"is_active": 1,
		}
	)
	for unloco in covered_unlocs or []:
		doc.append("covered_unlocs", {"unloco": unloco})
	doc.insert(ignore_permissions=True)
	return code


class TestFreightAgentLocationValidation(FrappeTestCase):
	def setUp(self):
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		self.shipper = create_test_shipper()
		self.consignee = create_test_consignee()
		create_test_unloco("HKHKG", "Hong Kong", country_code="HK")
		create_test_unloco("PHMNL", "Manila", "MNL", "PH", "Airport")
		create_test_unloco("PHCEB", "Cebu", "CEB", "PH", "Airport")
		self.agent = create_test_freight_agent(
			covered_unlocs=["PHMNL", "PHCEB"],
			default_unloco="PHMNL",
		)

	def tearDown(self):
		frappe.db.rollback()

	def test_get_freight_agent_covered_unlocos(self):
		self.assertEqual(get_freight_agent_covered_unlocos(self.agent), {"PHMNL", "PHCEB"})

	def test_import_valid_destination_in_coverage(self):
		validate_freight_agent_covers_ports(
			self.agent,
			"HKHKG",
			"PHMNL",
			"Import",
		)

	def test_import_invalid_destination_outside_coverage(self):
		with self.assertRaises(frappe.ValidationError):
			validate_freight_agent_covers_ports(
				self.agent,
				"HKHKG",
				"HKHKG",
				"Import",
			)

	def test_export_valid_origin_in_coverage(self):
		validate_freight_agent_covers_ports(
			self.agent,
			"PHMNL",
			"HKHKG",
			"Export",
		)

	def test_export_invalid_origin_outside_coverage(self):
		with self.assertRaises(frappe.ValidationError):
			validate_freight_agent_covers_ports(
				self.agent,
				"HKHKG",
				"PHMNL",
				"Export",
			)

	def test_domestic_requires_both_ports_in_coverage(self):
		validate_freight_agent_covers_ports(
			self.agent,
			"PHMNL",
			"PHCEB",
			"Domestic",
		)
		with self.assertRaises(frappe.ValidationError):
			validate_freight_agent_covers_ports(
				self.agent,
				"PHMNL",
				"HKHKG",
				"Domestic",
			)

	def test_sales_quote_sea_import_passes(self):
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
				"main_service": "Sea",
				"direction": "Import",
				"origin_port": "HKHKG",
				"destination_port": "PHMNL",
				"freight_agent_sea": self.agent,
			}
		)
		sq.append("charges", {"service_type": "Sea"})
		validate_sales_quote_freight_agent_locations(sq)

	def test_sales_quote_sea_import_fails_for_uncovered_destination(self):
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
				"origin_port": "HKHKG",
				"destination_port": "HKHKG",
				"freight_agent_sea": self.agent,
			}
		)
		sq.append("charges", {"service_type": "Sea"})
		with self.assertRaises(frappe.ValidationError):
			validate_sales_quote_freight_agent_locations(sq)

	def test_freight_agent_rejects_duplicate_covered_unloco(self):
		doc = frappe.get_doc(
			{
				"doctype": "Freight Agent",
				"code": "TEST-FA-DUP",
				"freight_agent_name": "Duplicate Coverage Agent",
				"is_active": 1,
			}
		)
		doc.append("covered_unlocs", {"unloco": "PHMNL"})
		doc.append("covered_unlocs", {"unloco": "PHMNL"})
		with self.assertRaises(frappe.ValidationError):
			doc.insert(ignore_permissions=True)
