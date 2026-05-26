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
	map_sales_quote_charge_to_programme_charge_dict,
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
