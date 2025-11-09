# Copyright (c) 2025, logistics.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
import unittest
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today, flt, add_days
from logistics.pricing_center.doctype.sales_quote.sales_quote import (
	create_air_shipment_from_sales_quote,
	_populate_charges_from_sales_quote_air_freight
)


class TestAirFreightSalesQuotePricing(FrappeTestCase):
	"""Test cases for Air Freight pricing from Sales Quote"""
	
	def setUp(self):
		"""Set up test data"""
		# Create test company if not exists
		if not frappe.db.exists("Company", "Test Company"):
			company = frappe.get_doc({
				"doctype": "Company",
				"company_name": "Test Company",
				"abbr": "TC",
				"default_currency": "USD",
				"country": "United States"
			})
			company.insert()
		
		# Create test customer if not exists
		if not frappe.db.exists("Customer", "Test Customer"):
			customer = frappe.get_doc({
				"doctype": "Customer",
				"customer_name": "Test Customer",
				"customer_type": "Company"
			})
			customer.insert()
		
		# Create test items if not exists
		self.create_test_items()
		
		# Create test locations if not exists
		self.create_test_locations()
	
	def create_test_items(self):
		"""Create test items for charges"""
		items = [
			{"item_code": "TEST-AIR-FREIGHT", "item_name": "Test Air Freight Charge"},
			{"item_code": "TEST-FUEL-SURCHARGE", "item_name": "Test Fuel Surcharge"},
			{"item_code": "TEST-HANDLING", "item_name": "Test Handling Charge"}
		]
		
		for item_data in items:
			if not frappe.db.exists("Item", item_data["item_code"]):
				item = frappe.get_doc({
					"doctype": "Item",
					"item_code": item_data["item_code"],
					"item_name": item_data["item_name"],
					"item_group": "Services",
					"stock_uom": "Nos"
				})
				item.insert()
	
	def create_test_locations(self):
		"""Create test locations (airports)"""
		locations = [
			{"location_name": "Test Origin Airport", "location_type": "Airport"},
			{"location_name": "Test Destination Airport", "location_type": "Airport"}
		]
		
		for loc_data in locations:
			if not frappe.db.exists("Location", loc_data["location_name"]):
				location = frappe.get_doc({
					"doctype": "Location",
					"location_name": loc_data["location_name"],
					"location_type": loc_data["location_type"]
				})
				location.insert()
	
	def test_create_sales_quote_air_freight(self):
		"""Test creating Sales Quote with Air Freight lines"""
		# Create Sales Quote
		sales_quote = frappe.get_doc({
			"doctype": "Sales Quote",
			"customer": "Test Customer",
			"date": today(),
			"valid_until": add_days(today(), 30),
			"one_off": 1,
			"company": "Test Company",
			"weight": 100,
			"volume": 2.5,
			"chargeable": 100,
			"air_freight": [
				{
					"item_code": "TEST-AIR-FREIGHT",
					"calculation_method": "Per Unit",
					"unit_type": "Weight",
					"unit_rate": 10.0,
					"currency": "USD",
					"quantity": 100
				},
				{
					"item_code": "TEST-FUEL-SURCHARGE",
					"calculation_method": "Fixed Amount",
					"unit_rate": 50.0,
					"currency": "USD"
				}
			]
		})
		
		sales_quote.insert()
		
		# Verify Sales Quote was created
		self.assertIsNotNone(sales_quote.name)
		self.assertEqual(len(sales_quote.air_freight), 2)
		
		# Verify first Air Freight line
		first_line = sales_quote.air_freight[0]
		self.assertEqual(first_line.item_code, "TEST-AIR-FREIGHT")
		self.assertEqual(first_line.calculation_method, "Per Unit")
		self.assertEqual(first_line.unit_type, "Weight")
		self.assertEqual(flt(first_line.unit_rate), 10.0)
		
		# Verify estimated revenue calculation
		sales_quote.save()
		self.assertGreater(flt(first_line.estimated_revenue), 0)
		
		# Cleanup
		sales_quote.delete()
	
	def test_create_air_shipment_from_sales_quote(self):
		"""Test creating Air Shipment from Sales Quote"""
		# Create Sales Quote with Air Freight lines
		sales_quote = frappe.get_doc({
			"doctype": "Sales Quote",
			"customer": "Test Customer",
			"date": today(),
			"valid_until": add_days(today(), 30),
			"one_off": 1,
			"company": "Test Company",
			"weight": 100,
			"volume": 2.5,
			"chargeable": 100,
			"shipper": "Test Customer",
			"consignee": "Test Customer",
			"location_from": "Test Origin Airport",
			"location_to": "Test Destination Airport",
			"direction": "Export",
			"air_freight": [
				{
					"item_code": "TEST-AIR-FREIGHT",
					"calculation_method": "Per Unit",
					"unit_type": "Weight",
					"unit_rate": 10.0,
					"currency": "USD",
					"quantity": 100
				}
			]
		})
		sales_quote.insert()
		
		# Create Air Shipment from Sales Quote
		result = create_air_shipment_from_sales_quote(sales_quote.name)
		
		# Verify result
		self.assertTrue(result.get("success"))
		self.assertIsNotNone(result.get("air_shipment"))
		
		# Get created Air Shipment
		air_shipment = frappe.get_doc("Air Shipment", result["air_shipment"])
		
		# Verify Air Shipment fields
		self.assertEqual(air_shipment.sales_quote, sales_quote.name)
		self.assertEqual(air_shipment.local_customer, "Test Customer")
		self.assertEqual(flt(air_shipment.weight), 100)
		self.assertEqual(flt(air_shipment.volume), 2.5)
		self.assertEqual(flt(air_shipment.chargeable), 100)
		
		# Verify charges were populated
		self.assertGreater(len(air_shipment.charges), 0)
		
		# Cleanup
		air_shipment.delete()
		sales_quote.delete()
	
	def test_populate_charges_from_sales_quote(self):
		"""Test populating charges from Sales Quote"""
		# Create Sales Quote with Air Freight lines
		sales_quote = frappe.get_doc({
			"doctype": "Sales Quote",
			"customer": "Test Customer",
			"date": today(),
			"valid_until": add_days(today(), 30),
			"one_off": 1,
			"company": "Test Company",
			"weight": 100,
			"volume": 2.5,
			"chargeable": 100,
			"air_freight": [
				{
					"item_code": "TEST-AIR-FREIGHT",
					"calculation_method": "Per Unit",
					"unit_type": "Weight",
					"unit_rate": 10.0,
					"currency": "USD",
					"quantity": 100
				},
				{
					"item_code": "TEST-FUEL-SURCHARGE",
					"calculation_method": "Fixed Amount",
					"unit_rate": 50.0,
					"currency": "USD"
				}
			]
		})
		sales_quote.insert()
		
		# Create Air Shipment
		air_shipment = frappe.get_doc({
			"doctype": "Air Shipment",
			"local_customer": "Test Customer",
			"booking_date": today(),
			"sales_quote": sales_quote.name,
			"shipper": "Test Customer",
			"consignee": "Test Customer",
			"origin_port": "Test Origin Airport",
			"destination_port": "Test Destination Airport",
			"direction": "Export",
			"weight": 100,
			"volume": 2.5,
			"chargeable": 100,
			"company": "Test Company"
		})
		air_shipment.insert()
		
		# Populate charges from Sales Quote
		result = air_shipment.populate_charges_from_sales_quote()
		
		# Verify result
		self.assertTrue(result.get("success"))
		self.assertGreater(result.get("charges_added"), 0)
		
		# Reload Air Shipment
		air_shipment.reload()
		
		# Verify charges were populated
		self.assertEqual(len(air_shipment.charges), 2)
		
		# Verify first charge
		first_charge = air_shipment.charges[0]
		self.assertEqual(first_charge.item_code, "TEST-AIR-FREIGHT")
		self.assertEqual(first_charge.charge_basis, "Per kg")
		self.assertEqual(flt(first_charge.rate), 10.0)
		self.assertEqual(flt(first_charge.quantity), 100)
		
		# Cleanup
		air_shipment.delete()
		sales_quote.delete()
	
	def test_charge_calculation(self):
		"""Test charge calculation logic"""
		# Create Air Shipment
		air_shipment = frappe.get_doc({
			"doctype": "Air Shipment",
			"local_customer": "Test Customer",
			"booking_date": today(),
			"shipper": "Test Customer",
			"consignee": "Test Customer",
			"origin_port": "Test Origin Airport",
			"destination_port": "Test Destination Airport",
			"direction": "Export",
			"weight": 100,
			"volume": 2.5,
			"chargeable": 100,
			"company": "Test Company",
			"charges": [
				{
					"item_code": "TEST-AIR-FREIGHT",
					"charge_type": "Freight",
					"charge_category": "Transportation",
					"charge_basis": "Per kg",
					"rate": 10.0,
					"currency": "USD",
					"quantity": 100
				}
			]
		})
		air_shipment.insert()
		
		# Get charge
		charge = air_shipment.charges[0]
		
		# Calculate charge amount
		charge.calculate_charge_amount()
		
		# Verify calculation
		expected_base = 10.0 * 100  # rate * quantity
		self.assertEqual(flt(charge.base_amount), expected_base)
		self.assertEqual(flt(charge.total_amount), expected_base)
		
		# Test with discount
		charge.discount_percentage = 10
		charge.calculate_charge_amount()
		
		expected_discount = expected_base * 0.1
		expected_total = expected_base - expected_discount
		self.assertEqual(flt(charge.discount_amount), expected_discount)
		self.assertEqual(flt(charge.total_amount), expected_total)
		
		# Cleanup
		air_shipment.delete()
	
	def test_charge_calculation_fixed_amount(self):
		"""Test charge calculation for Fixed Amount basis"""
		# Create Air Shipment
		air_shipment = frappe.get_doc({
			"doctype": "Air Shipment",
			"local_customer": "Test Customer",
			"booking_date": today(),
			"shipper": "Test Customer",
			"consignee": "Test Customer",
			"origin_port": "Test Origin Airport",
			"destination_port": "Test Destination Airport",
			"direction": "Export",
			"weight": 100,
			"volume": 2.5,
			"chargeable": 100,
			"company": "Test Company",
			"charges": [
				{
					"item_code": "TEST-FUEL-SURCHARGE",
					"charge_type": "Fuel Surcharge",
					"charge_category": "Surcharges",
					"charge_basis": "Fixed amount",
					"rate": 50.0,
					"currency": "USD"
				}
			]
		})
		air_shipment.insert()
		
		# Get charge
		charge = air_shipment.charges[0]
		
		# Calculate charge amount
		charge.calculate_charge_amount()
		
		# Verify calculation (Fixed amount should equal rate)
		self.assertEqual(flt(charge.base_amount), 50.0)
		self.assertEqual(flt(charge.total_amount), 50.0)
		
		# Cleanup
		air_shipment.delete()
	
	def test_charge_calculation_percentage(self):
		"""Test charge calculation for Percentage basis"""
		# Create Air Shipment
		air_shipment = frappe.get_doc({
			"doctype": "Air Shipment",
			"local_customer": "Test Customer",
			"booking_date": today(),
			"shipper": "Test Customer",
			"consignee": "Test Customer",
			"origin_port": "Test Origin Airport",
			"destination_port": "Test Destination Airport",
			"direction": "Export",
			"weight": 100,
			"volume": 2.5,
			"chargeable": 100,
			"company": "Test Company",
			"charges": [
				{
					"item_code": "TEST-HANDLING",
					"charge_type": "Handling",
					"charge_category": "Handling",
					"charge_basis": "Percentage",
					"rate": 5.0,  # 5%
					"currency": "USD"
				}
			]
		})
		air_shipment.insert()
		
		# Get charge
		charge = air_shipment.charges[0]
		
		# Calculate charge amount
		charge.calculate_charge_amount()
		
		# Verify calculation (5% of 100 chargeable weight = 5)
		expected_base = 5.0 * (100 * 0.01)  # rate * (chargeable * 0.01)
		self.assertEqual(flt(charge.base_amount), expected_base)
		
		# Cleanup
		air_shipment.delete()
	
	def test_recalculate_all_charges(self):
		"""Test recalculating all charges"""
		# Create Air Shipment with charges
		air_shipment = frappe.get_doc({
			"doctype": "Air Shipment",
			"local_customer": "Test Customer",
			"booking_date": today(),
			"shipper": "Test Customer",
			"consignee": "Test Customer",
			"origin_port": "Test Origin Airport",
			"destination_port": "Test Destination Airport",
			"direction": "Export",
			"weight": 100,
			"volume": 2.5,
			"chargeable": 100,
			"company": "Test Company",
			"charges": [
				{
					"item_code": "TEST-AIR-FREIGHT",
					"charge_type": "Freight",
					"charge_category": "Transportation",
					"charge_basis": "Per kg",
					"rate": 10.0,
					"currency": "USD",
					"quantity": 100
				}
			]
		})
		air_shipment.insert()
		
		# Change weight
		air_shipment.weight = 150
		air_shipment.save()
		
		# Recalculate all charges
		result = air_shipment.recalculate_all_charges()
		
		# Verify result
		self.assertTrue(result.get("success"))
		
		# Reload Air Shipment
		air_shipment.reload()
		
		# Verify quantity was updated
		charge = air_shipment.charges[0]
		self.assertEqual(flt(charge.quantity), 150)
		
		# Cleanup
		air_shipment.delete()
	
	def test_validation_errors(self):
		"""Test validation errors"""
		# Test creating Air Shipment from non-One-Off Sales Quote
		sales_quote = frappe.get_doc({
			"doctype": "Sales Quote",
			"customer": "Test Customer",
			"date": today(),
			"valid_until": add_days(today(), 30),
			"one_off": 0,  # Not One-Off
			"company": "Test Company",
			"air_freight": [
				{
					"item_code": "TEST-AIR-FREIGHT",
					"calculation_method": "Per Unit",
					"unit_type": "Weight",
					"unit_rate": 10.0,
					"currency": "USD"
				}
			]
		})
		sales_quote.insert()
		
		# Try to create Air Shipment - should fail
		with self.assertRaises(frappe.ValidationError):
			create_air_shipment_from_sales_quote(sales_quote.name)
		
		# Cleanup
		sales_quote.delete()
		
		# Test creating Air Shipment from Sales Quote without Air Freight lines
		sales_quote2 = frappe.get_doc({
			"doctype": "Sales Quote",
			"customer": "Test Customer",
			"date": today(),
			"valid_until": add_days(today(), 30),
			"one_off": 1,
			"company": "Test Company"
			# No air_freight lines
		})
		sales_quote2.insert()
		
		# Try to create Air Shipment - should fail
		with self.assertRaises(frappe.ValidationError):
			create_air_shipment_from_sales_quote(sales_quote2.name)
		
		# Cleanup
		sales_quote2.delete()
	
	def tearDown(self):
		"""Clean up test data"""
		# Delete test documents
		frappe.db.rollback()


if __name__ == "__main__":
	unittest.main()

