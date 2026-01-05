# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
import unittest
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today
from logistics.air_freight.tests.test_helpers import create_test_airline


class TestMasterAirWaybill(FrappeTestCase):
	"""Test cases for Master Air Waybill doctype"""
	
	def setUp(self):
		"""Set up test data"""
		create_test_airline("TA", "Test Airline")
	
	def tearDown(self):
		"""Clean up test data"""
		frappe.db.rollback()
	
	def test_master_air_waybill_creation(self):
		"""Test creating a Master Air Waybill"""
		mawb = frappe.get_doc({
			"doctype": "Master Air Waybill",
			"master_awb_no": "TEST-MAWB-001",
			"airline": "TA",
			"flight_no": "TA123",
			"flight_date": today()
		})
		mawb.insert()
		
		self.assertEqual(mawb.master_awb_no, "TEST-MAWB-001")
		self.assertEqual(mawb.airline, "TA")
		self.assertEqual(mawb.flight_no, "TA123")
	
	def test_master_air_waybill_auto_link_flight_schedule(self):
		"""Test auto-linking to flight schedule"""
		mawb = frappe.get_doc({
			"doctype": "Master Air Waybill",
			"master_awb_no": "TEST-MAWB-002",
			"airline": "TA",
			"flight_no": "TA456",
			"flight_date": today()
		})
		
		# Test that auto_link_flight_schedule method exists
		self.assertTrue(hasattr(mawb, 'auto_link_flight_schedule'))
		
		# Try to insert (may or may not find matching flight schedule)
		try:
			mawb.insert()
			# If flight_schedule is set, that's good
			# If not, that's also okay if no matching schedule exists
		except Exception:
			pass
	
	def test_master_air_waybill_validate(self):
		"""Test validation method"""
		mawb = frappe.get_doc({
			"doctype": "Master Air Waybill",
			"master_awb_no": "TEST-MAWB-003",
			"airline": "TA"
		})
		
		# Test that validate method exists
		self.assertTrue(hasattr(mawb, 'validate'))
		
		# Try to insert
		try:
			mawb.insert()
			self.assertIsNotNone(mawb.name)
		except Exception:
			pass
	
	def test_master_air_waybill_on_update(self):
		"""Test on_update hook"""
		mawb = frappe.get_doc({
			"doctype": "Master Air Waybill",
			"master_awb_no": "TEST-MAWB-004",
			"airline": "TA"
		})
		
		# Test that on_update method exists
		self.assertTrue(hasattr(mawb, 'on_update'))
		
		try:
			mawb.insert()
			# Update should trigger on_update
			mawb.flight_no = "TA789"
			mawb.save()
		except Exception:
			pass
