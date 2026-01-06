# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
import unittest
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today, getdate
from logistics.air_freight.tests.test_helpers import setup_basic_master_data, create_test_airport


class TestAirConsolidation(FrappeTestCase):
	"""Test cases for Air Consolidation doctype"""
	
	def setUp(self):
		"""Set up test data"""
		data = setup_basic_master_data()
		self.company = data["company"]
		create_test_airport("LAX")
		create_test_airport("JFK")
	
	def tearDown(self):
		"""Clean up test data"""
		frappe.db.rollback()
	
	def test_air_consolidation_creation(self):
		"""Test creating a basic Air Consolidation"""
		consolidation = frappe.get_doc({
			"doctype": "Air Consolidation",
			"naming_series": "AC-{MM}-{YYYY}-{####}",
			"consolidation_date": today(),
			"consolidation_type": "Direct Consolidation",
			"status": "Draft",
			"company": self.company,
			"origin_airport": "LAX",
			"destination_airport": "JFK"
		})
		
		consolidation.insert()
		self.assertIsNotNone(consolidation.name)
	
	def test_air_consolidation_validation(self):
		"""Test consolidation validation methods"""
		consolidation = frappe.get_doc({
			"doctype": "Air Consolidation",
			"naming_series": "AC-{MM}-{YYYY}-{####}",
			"consolidation_date": today(),
			"consolidation_type": "Direct Consolidation",
			"status": "Draft",
			"company": self.company,
			"origin_airport": "LAX",
			"destination_airport": "JFK"
		})
		
		# Test that validation methods exist
		self.assertTrue(hasattr(consolidation, 'validate'))
		self.assertTrue(hasattr(consolidation, 'validate_dates'))
		self.assertTrue(hasattr(consolidation, 'validate_consolidation_data'))
	
	def test_air_consolidation_before_save(self):
		"""Test before_save hook"""
		consolidation = frappe.get_doc({
			"doctype": "Air Consolidation",
			"naming_series": "AC-{MM}-{YYYY}-{####}",
			"consolidation_date": today(),
			"consolidation_type": "Direct Consolidation",
			"status": "Draft",
			"company": self.company,
			"origin_airport": "LAX",
			"destination_airport": "JFK"
		})
		
		# Test that before_save method exists
		self.assertTrue(hasattr(consolidation, 'before_save'))
	
	def test_air_consolidation_after_insert(self):
		"""Test after_insert hook"""
		consolidation = frappe.get_doc({
			"doctype": "Air Consolidation",
			"naming_series": "AC-{MM}-{YYYY}-{####}",
			"consolidation_date": today(),
			"consolidation_type": "Direct Consolidation",
			"status": "Draft",
			"company": self.company,
			"origin_airport": "LAX",
			"destination_airport": "JFK"
		})
		
		# Test that after_insert method exists
		self.assertTrue(hasattr(consolidation, 'after_insert'))
