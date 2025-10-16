# Copyright (c) 2025, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import flt


class TestWarehouseJob(FrappeTestCase):
	def test_post_standard_costs(self):
		"""Test the post_standard_costs functionality"""
		# This is a basic test to ensure the function exists and can be called
		# In a real test environment, you would create test data first
		
		# Test that the function exists and is callable
		from logistics.warehousing.doctype.warehouse_job.warehouse_job import post_standard_costs
		
		# Test with a non-existent warehouse job
		result = post_standard_costs("NON-EXISTENT-JOB")
		self.assertFalse(result["ok"])
		self.assertIn("No charges found", result["message"])
	
	def test_post_standard_costs_validation(self):
		"""Test validation logic for post_standard_costs"""
		# Test that the function handles missing warehouse job gracefully
		from logistics.warehousing.doctype.warehouse_job.warehouse_job import post_standard_costs
		
		# This should return an error for non-existent job
		result = post_standard_costs("INVALID-JOB-NAME")
		self.assertFalse(result["ok"])
		self.assertIsInstance(result["message"], str)
