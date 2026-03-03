# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today
from logistics.air_freight.tests.test_helpers import (
	setup_basic_master_data,
	create_test_shipper,
	create_test_consignee,
	create_test_unloco,
	create_test_branch,
	create_test_cost_center,
	create_test_profit_center,
)


class TestDangerousGoodsDeclaration(FrappeTestCase):
	"""Test cases for Dangerous Goods Declaration doctype"""

	def setUp(self):
		"""Set up test data"""
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		self.shipper = create_test_shipper()
		self.consignee = create_test_consignee()
		create_test_unloco("USLAX", "Los Angeles", "LAX", "US", "Airport")
		create_test_unloco("USJFK", "New York JFK", "JFK", "US", "Airport")
		try:
			self.branch = create_test_branch(self.company)
			self.cost_center = create_test_cost_center(self.company)
			self.profit_center = create_test_profit_center(self.company)
		except Exception:
			self.branch = frappe.db.get_value("Branch", {"custom_company": self.company}, "name")
			self.cost_center = frappe.db.get_value("Cost Center", {"company": self.company, "is_group": 0}, "name")
		self.air_shipment = self._create_air_shipment()

	def tearDown(self):
		frappe.db.rollback()

	def _create_air_shipment(self):
		"""Create Air Shipment with UNLOCO ports for DG Declaration"""
		shipment = frappe.get_doc({
			"doctype": "Air Shipment",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"branch": self.branch,
			"cost_center": self.cost_center,
			"profit_center": self.profit_center,
		})
		shipment.insert()
		return shipment.name

	def test_dangerous_goods_declaration_creation(self):
		"""Test creating DG Declaration with UNLOCO origin/destination"""
		dg = frappe.get_doc({
			"doctype": "Dangerous Goods Declaration",
			"air_shipment": self.air_shipment,
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"emergency_contact": "Test Contact",
			"emergency_phone": "+1234567890",
		})
		dg.append("packages", {
			"un_number": "1266",
			"proper_shipping_name": "Perfumery products",
			"dg_class": "3",
			"emergency_contact": "Test Contact",
			"emergency_phone": "+1234567890",
		})
		dg.insert()

		self.assertIsNotNone(dg.name)
		self.assertEqual(dg.air_shipment, self.air_shipment)
		self.assertEqual(dg.origin_port, "USLAX")
		self.assertEqual(dg.destination_port, "USJFK")

	def test_dangerous_goods_declaration_required_fields(self):
		"""Test that required fields are enforced"""
		dg = frappe.get_doc({"doctype": "Dangerous Goods Declaration"})
		with self.assertRaises((frappe.ValidationError, frappe.MandatoryError)):
			dg.insert()
