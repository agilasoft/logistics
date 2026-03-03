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


class TestTransportOrder(FrappeTestCase):
	"""Test cases for Transport Order doctype"""

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

	def test_transport_order_creation(self):
		"""Test creating a basic Transport Order"""
		order = frappe.get_doc({
			"doctype": "Transport Order",
			"company": self.company,
			"customer": self.customer,
			"booking_date": today(),
			"scheduled_date": today(),
			"location_type": "UNLOCO",
			"location_from": "USLAX",
			"location_to": "USJFK",
			"transport_job_type": "Non-Container",
			"branch": self.branch,
			"cost_center": self.cost_center,
			"profit_center": self.profit_center,
		})
		order.append("legs", {
			"facility_type_from": "Shipper",
			"facility_from": self.shipper,
			"facility_type_to": "Consignee",
			"facility_to": self.consignee,
			"scheduled_date": today(),
			"transport_job_type": "Non-Container",
		})
		order.insert()

		self.assertIsNotNone(order.name)
		self.assertEqual(order.company, self.company)
		self.assertEqual(order.customer, self.customer)
		self.assertEqual(len(order.legs), 1)

	def test_transport_order_required_fields(self):
		"""Test that required fields are enforced"""
		order = frappe.get_doc({"doctype": "Transport Order", "booking_date": today()})
		with self.assertRaises((frappe.ValidationError, frappe.MandatoryError)):
			order.insert()

	def test_transport_order_validate_leg_facilities(self):
		"""Test that legs with same from/to facilities are rejected"""
		order = frappe.get_doc({
			"doctype": "Transport Order",
			"company": self.company,
			"customer": self.customer,
			"booking_date": today(),
			"scheduled_date": today(),
			"location_type": "UNLOCO",
			"location_from": "USLAX",
			"location_to": "USJFK",
			"transport_job_type": "Non-Container",
			"branch": self.branch,
			"cost_center": self.cost_center,
			"profit_center": self.profit_center,
		})
		order.append("legs", {
			"facility_type_from": "Shipper",
			"facility_from": self.shipper,
			"facility_type_to": "Shipper",
			"facility_to": self.shipper,
			"scheduled_date": today(),
			"transport_job_type": "Non-Container",
		})
		with self.assertRaises((frappe.ValidationError, Exception)):
			order.insert()
