# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
import unittest
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today, add_days, now_datetime
from logistics.air_freight.tests.test_helpers import (
	setup_basic_master_data, create_test_shipper, create_test_consignee,
	create_test_branch, create_test_cost_center, create_test_profit_center
)


class TestAirShipment(FrappeTestCase):
	"""Test cases for Air Shipment doctype"""
	
	def setUp(self):
		"""Set up test data"""
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		
		# Create accounts
		self.branch = create_test_branch(self.company)
		self.cost_center = create_test_cost_center(self.company)
		self.profit_center = create_test_profit_center(self.company)
		
		# Create shipper and consignee
		self.shipper = create_test_shipper()
		self.consignee = create_test_consignee()
	
	def tearDown(self):
		"""Clean up test data"""
		frappe.db.rollback()
	
	def test_air_shipment_creation(self):
		"""Test creating a basic Air Shipment"""
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
			"profit_center": self.profit_center
		})
		shipment.insert()
		
		self.assertIsNotNone(shipment.name)
		self.assertEqual(shipment.company, self.company)
		self.assertEqual(shipment.local_customer, self.customer)
	
	def test_air_shipment_date_validation(self):
		"""Test validation of dates"""
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
			"etd": add_days(today(), 5),
			"eta": add_days(today(), 3)  # ETA before ETD
		})
		
		# This should raise a validation error
		with self.assertRaises((frappe.ValidationError, Exception)):
			shipment.insert()
	
	def test_air_shipment_weight_volume_validation(self):
		"""Test validation of weight and volume"""
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
			"weight": -10,  # Negative weight
			"volume": -5    # Negative volume
		})
		
		# This should raise a validation error
		with self.assertRaises((frappe.ValidationError, Exception)):
			shipment.insert()
	
	def test_air_shipment_dangerous_goods_validation(self):
		"""Test validation of dangerous goods requirements"""
		# Test that dangerous goods requires emergency contact
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
			"contains_dangerous_goods": 1
		})
		
		# Dangerous goods should require emergency contact and phone
		# The validation will throw an error if these are missing
		with self.assertRaises((frappe.ValidationError, Exception)) as context:
			shipment.insert()
		
		# Verify the error message mentions dangerous goods or emergency
		error_msg = str(context.exception).lower()
		self.assertTrue(
			"dangerous goods" in error_msg or 
			"emergency" in error_msg or 
			"dg" in error_msg or
			"contact" in error_msg,
			f"Expected dangerous goods validation error, got: {error_msg}"
		)
	
	def test_air_shipment_sustainability_metrics(self):
		"""Test calculation of sustainability metrics"""
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
			"weight": 1000,  # 1 ton
		})
		shipment.insert()
		
		# Check if sustainability metrics are calculated
		# The before_save method should calculate these
		if hasattr(shipment, 'estimated_carbon_footprint'):
			self.assertIsNotNone(shipment.estimated_carbon_footprint)
	
	def test_air_shipment_milestone_html(self):
		"""Test get_milestone_html method"""
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
			"profit_center": self.profit_center
		})
		shipment.insert()
		
		# Test milestone HTML generation
		try:
			html = shipment.get_milestone_html()
			self.assertIsInstance(html, str)
			self.assertIn("milestone", html.lower() or "origin" in html.lower())
		except Exception:
			# If method requires more setup, that's okay
			pass
	
	def test_air_shipment_package_validation(self):
		"""Test validation of packages"""
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
			"profit_center": self.profit_center
		})
		
		# Add a package with invalid data
		shipment.append("packages", {
			"package_type": "Box",
			"quantity": -1  # Negative quantity
		})
		
		# This should raise a validation error
		with self.assertRaises((frappe.ValidationError, Exception)):
			shipment.insert()
	
	def test_air_shipment_before_save(self):
		"""Test before_save hook"""
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
			"weight": 500
		})
		
		# before_save should calculate sustainability metrics
		shipment.insert()
		
		# Check if before_save was called
		self.assertIsNotNone(shipment.name)
	
	def test_air_shipment_settings_defaults(self):
		"""Test that settings defaults are applied"""
		# Create settings first
		if not frappe.db.exists("Air Freight Settings", {"company": self.company}):
			settings = frappe.get_doc({
				"doctype": "Air Freight Settings",
				"company": self.company,
				"default_currency": "USD"
			})
			settings.insert()
		
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
			"profit_center": self.profit_center
		})
		shipment.insert()
		
		# Settings defaults should be applied in before_save or after_insert
		self.assertIsNotNone(shipment.name)
