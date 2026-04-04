# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
import unittest
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today, add_days
from logistics.air_freight.tests.test_helpers import (
	setup_basic_master_data, create_test_shipper, create_test_consignee,
	create_test_branch, create_test_cost_center, create_test_profit_center
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
			"origin_port": "USLAX",
			"destination_port": "USJFK"
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
			"origin_port": "USLAX",
			"destination_port": "USJFK",
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
			"origin_port": "USLAX",
			"destination_port": "USJFK"
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
			"origin_port": "USLAX",
			"destination_port": "USJFK"
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

	def test_air_booking_applies_air_freight_settings_defaults(self):
		"""New Air Booking should use Air Freight Settings defaults when fields are empty."""
		branch = create_test_branch(self.company, "ABK Default Branch")
		cost_center = create_test_cost_center(self.company, "ABK Default Cost Center")
		profit_center = create_test_profit_center(self.company, "ABK Default Profit Center", code="ABK-DEFAULT-PC")

		settings_name = frappe.db.get_value("Air Freight Settings", {"company": self.company}, "name")
		if settings_name:
			settings = frappe.get_doc("Air Freight Settings", settings_name)
		else:
			settings = frappe.get_doc({"doctype": "Air Freight Settings", "company": self.company})

		settings.default_branch = branch
		settings.default_cost_center = cost_center
		settings.default_profit_center = profit_center
		settings.default_direction = "Export"
		settings.default_entry_type = "Direct"
		settings.save(ignore_permissions=True)

		booking = frappe.get_doc({
			"doctype": "Air Booking",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "USLAX",
			"destination_port": "USJFK",
		})
		booking.insert()

		self.assertEqual(booking.branch, branch)
		self.assertEqual(booking.cost_center, cost_center)
		self.assertEqual(booking.profit_center, profit_center)
		self.assertEqual(booking.direction, "Export")
		self.assertEqual(booking.entry_type, "Direct")

	def test_air_booking_defaults_do_not_override_existing_values(self):
		"""Defaults should only fill blanks, not overwrite manually provided values."""
		branch = create_test_branch(self.company, "ABK Settings Branch")
		cost_center = create_test_cost_center(self.company, "ABK Settings Cost Center")
		profit_center = create_test_profit_center(self.company, "ABK Settings Profit Center", code="ABK-SETTINGS-PC")
		manual_branch = create_test_branch(self.company, "ABK Manual Branch")

		settings_name = frappe.db.get_value("Air Freight Settings", {"company": self.company}, "name")
		if settings_name:
			settings = frappe.get_doc("Air Freight Settings", settings_name)
		else:
			settings = frappe.get_doc({"doctype": "Air Freight Settings", "company": self.company})

		settings.default_branch = branch
		settings.default_cost_center = cost_center
		settings.default_profit_center = profit_center
		settings.default_direction = "Export"
		settings.save(ignore_permissions=True)

		booking = frappe.get_doc({
			"doctype": "Air Booking",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"direction": "Domestic",
			"branch": manual_branch,
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "USLAX",
			"destination_port": "USJFK",
		})
		booking.insert()

		self.assertEqual(booking.branch, manual_branch)
		self.assertEqual(booking.direction, "Domestic")
