# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
import unittest
from frappe.tests.utils import FrappeTestCase
from logistics.air_freight.tests.test_helpers import create_test_airline


class TestAirline(FrappeTestCase):
	"""Test cases for Airline doctype"""
	
	def setUp(self):
		"""Set up test data"""
		pass
	
	def tearDown(self):
		"""Clean up test data"""
		frappe.db.rollback()
	
	def test_airline_creation(self):
		"""Test creating an Airline"""
		airline = frappe.get_doc({
			"doctype": "Airline",
			"code": "TA",  # Required field
			"airline_name": "Test Airline",
			"iata_code": "TA",
			"icao_code": "TAL"
		})
		airline.insert()
		
		self.assertEqual(airline.airline_name, "Test Airline")
		self.assertEqual(airline.iata_code, "TA")
		self.assertEqual(airline.icao_code, "TAL")
	
	def test_airline_basic_fields(self):
		"""Test basic airline fields"""
		airline = frappe.get_doc({
			"doctype": "Airline",
			"code": "TA2",  # Required field
			"airline_name": "Test Airline 2"
		})
		airline.insert()
		
		self.assertIsNotNone(airline.name)
		self.assertEqual(airline.airline_name, "Test Airline 2")
	
	def test_airline_with_contact_info(self):
		"""Test creating airline with contact information"""
		airline = frappe.get_doc({
			"doctype": "Airline",
			"code": "TA3",  # Required field
			"airline_name": "Test Airline 3",
			"email": "test@airline.com",
			"phone": "+1-555-1234"
		})
		airline.insert()
		
		self.assertEqual(airline.email, "test@airline.com")
		self.assertEqual(airline.phone, "+1-555-1234")
	
	def test_airline_update(self):
		"""Test updating an airline"""
		airline = frappe.get_doc({
			"doctype": "Airline",
			"code": "TA4",  # Required field
			"airline_name": "Test Airline 4"
		})
		airline.insert()
		
		# Update airline
		airline.airline_name = "Updated Test Airline"
		airline.save()
		
		# Reload and verify
		airline.reload()
		self.assertEqual(airline.airline_name, "Updated Test Airline")
