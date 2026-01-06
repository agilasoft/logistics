# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
import unittest
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today, add_days
from logistics.air_freight.tests.test_helpers import (
	setup_basic_master_data, create_test_shipper, create_test_consignee
)


class TestAirBooking(FrappeTestCase):
	"""Test cases for Air Booking doctype"""
	
	def setUp(self):
		"""Set up test data"""
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		
		# Create shipper and consignee
		self.shipper = create_test_shipper()
		self.consignee = create_test_consignee()
	
	def tearDown(self):
		"""Clean up test data"""
		frappe.db.rollback()
	
	def test_air_booking_creation(self):
		"""Test creating a basic Air Booking"""
		booking = frappe.get_doc({
			"doctype": "Air Booking",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"direction": "Export",
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "LAX",
			"destination_port": "JFK"
		})
		booking.insert()
		
		self.assertIsNotNone(booking.name)
		self.assertEqual(booking.booking_date, today())
		self.assertEqual(booking.direction, "Export")
	
	def test_air_booking_required_fields(self):
		"""Test that required fields are enforced"""
		booking = frappe.get_doc({
			"doctype": "Air Booking",
			"booking_date": today()
		})
		
		with self.assertRaises(frappe.ValidationError):
			booking.insert()
	
	def test_air_booking_date_validation(self):
		"""Test validation of ETD and ETA dates"""
		booking = frappe.get_doc({
			"doctype": "Air Booking",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"direction": "Export",
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "LAX",
			"destination_port": "JFK",
			"etd": add_days(today(), 5),
			"eta": add_days(today(), 3)  # ETA before ETD
		})
		
		with self.assertRaises(frappe.ValidationError):
			booking.insert()
	
	def test_air_booking_accounts_validation(self):
		"""Test validation of accounts (company, cost center, etc.)"""
		booking = frappe.get_doc({
			"doctype": "Air Booking",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"direction": "Export",
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "LAX",
			"destination_port": "JFK"
		})
		
		# Should insert successfully with valid company
		booking.insert()
		self.assertIsNotNone(booking.name)
	
	def test_air_booking_with_packages(self):
		"""Test creating booking with packages"""
		booking = frappe.get_doc({
			"doctype": "Air Booking",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"direction": "Export",
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "LAX",
			"destination_port": "JFK"
		})
		
		# Add packages
		booking.append("packages", {
			"package_type": "Box",
			"quantity": 10,
			"weight": 100,
			"volume": 0.5
		})
		
		booking.insert()
		
		self.assertEqual(len(booking.packages), 1)
		self.assertEqual(booking.packages[0].quantity, 10)
