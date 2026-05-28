# Copyright (c) 2026, AgilaSoft and Contributors

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from logistics.air_freight.tests.test_helpers import (
	create_test_consignee,
	create_test_shipper,
	setup_basic_master_data,
)
from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal
from logistics.utils.sales_quote_programme_charges import (
	fetch_sales_quote_charges_for_programme,
	map_sales_quote_charge_to_programme_charge_dict,
	programme_charge_service_types_for_parent,
)


class TestSalesQuoteProgrammeCharges(FrappeTestCase):
	def setUp(self):
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		self.shipper = create_test_shipper()
		self.consignee = create_test_consignee()

	def tearDown(self):
		frappe.db.rollback()

	def test_map_charge_includes_service_type_and_sales_quote_link(self):
		sq_row = {
			"service_type": "Special Project",
			"item_code": "Item-Test",
			"unit_rate": 100,
		}
		mapped = map_sales_quote_charge_to_programme_charge_dict(
			sq_row, "SQU-TEST-001", "Special Project Charges"
		)
		self.assertEqual(mapped.get("sales_quote_link"), "SQU-TEST-001")
		self.assertEqual(mapped.get("service_type"), "Special Project")
		self.assertTrue(
			sales_quote_charge_service_types_equal(mapped.get("service_type"), "Special Project")
		)

	def test_docket_programme_populate_uses_all_quote_charge_lines(self):
		self.assertEqual(programme_charge_service_types_for_parent("Docket"), "__all__")
		self.assertIsNone(programme_charge_service_types_for_parent("Exhibit"))

	def test_map_charge_for_docket_exhibit_charges(self):
		sq_row = {
			"service_type": "Exhibits",
			"item_code": "Item-Test",
			"unit_rate": 50,
		}
		mapped = map_sales_quote_charge_to_programme_charge_dict(
			sq_row, "SQU-TEST-002", "Exhibit Charges"
		)
		self.assertEqual(mapped.get("sales_quote_link"), "SQU-TEST-002")
		self.assertEqual(mapped.get("rate"), 50)
		self.assertTrue(
			sales_quote_charge_service_types_equal(mapped.get("service_type"), "Exhibits")
		)
