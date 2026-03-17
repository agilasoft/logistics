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


class TestSeaShipment(FrappeTestCase):
	"""Test cases for Sea Shipment doctype"""

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
			self.profit_center = frappe.db.get_value("Profit Center", {"company": self.company}, "name")

	def tearDown(self):
		frappe.db.rollback()

	def test_sea_shipment_creation(self):
		"""Test creating a basic Sea Shipment"""
		shipment = frappe.get_doc({
			"doctype": "Sea Shipment",
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

		self.assertIsNotNone(shipment.name)
		self.assertEqual(shipment.company, self.company)
		self.assertEqual(shipment.local_customer, self.customer)

	def test_sea_shipment_required_fields(self):
		"""Test that required fields are enforced"""
		shipment = frappe.get_doc({"doctype": "Sea Shipment", "booking_date": today()})
		with self.assertRaises((frappe.ValidationError, frappe.MandatoryError)):
			shipment.insert()

	def test_sea_shipment_with_packages(self):
		"""Test creating Sea Shipment with packages"""
		shipment = frappe.get_doc({
			"doctype": "Sea Shipment",
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
		shipment.append("packages", {
			"package_type": "Box",
			"quantity": 10,
			"weight": 100,
			"volume": 0.5,
		})
		shipment.insert()

		self.assertEqual(len(shipment.packages), 1)
		self.assertEqual(shipment.packages[0].quantity, 10)
