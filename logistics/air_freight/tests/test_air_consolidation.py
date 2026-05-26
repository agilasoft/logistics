# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today, getdate, flt
from logistics.air_freight.tests.test_helpers import setup_basic_master_data, create_test_unloco


class TestAirConsolidation(FrappeTestCase):
	"""Test cases for Air Consolidation doctype"""

	def setUp(self):
		"""Set up test data"""
		data = setup_basic_master_data()
		self.company = data["company"]
		# Air Consolidation uses UNLOCO for origin_airport/destination_airport
		create_test_unloco("USLAX", "Los Angeles", "LAX", "US", "Airport")
		create_test_unloco("USJFK", "New York JFK", "JFK", "US", "Airport")
	
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
			"origin_airport": "USLAX",
			"destination_airport": "USJFK"
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
			"origin_airport": "USLAX",
			"destination_airport": "USJFK"
		})
		
		# Test that validation methods exist (routes/packages enforced in before_submit)
		self.assertTrue(hasattr(consolidation, 'validate'))
		self.assertTrue(hasattr(consolidation, 'validate_dates'))
		self.assertTrue(hasattr(consolidation, 'before_submit'))
	
	def test_air_consolidation_before_save(self):
		"""Test before_save hook"""
		consolidation = frappe.get_doc({
			"doctype": "Air Consolidation",
			"naming_series": "AC-{MM}-{YYYY}-{####}",
			"consolidation_date": today(),
			"consolidation_type": "Direct Consolidation",
			"status": "Draft",
			"company": self.company,
			"origin_airport": "USLAX",
			"destination_airport": "USJFK"
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
			"origin_airport": "USLAX",
			"destination_airport": "USJFK"
		})
		
		# Test that after_insert method exists
		self.assertTrue(hasattr(consolidation, 'after_insert'))


class TestAirConsolidationChargeQuantitySync(FrappeTestCase):
	"""calculate_total_charges quantity fill; in-memory only (no company master setup)."""

	def tearDown(self):
		frappe.db.rollback()

	def test_calculate_total_charges_fills_quantity_weight(self):
		doc = frappe.new_doc("Air Consolidation")
		doc.chargeable_weight = 607.5
		doc.total_weight = 500
		doc.total_volume = 1
		doc.total_packages = 4
		doc.append(
			"consolidation_charges",
			{
				"charge_type": "Revenue",
				"charge_category": "Transportation",
				"revenue_calculation_method": "Per Unit",
				"unit_type": "Weight",
				"rate": 60,
				"currency": "USD",
				"quantity": 0,
			},
		)
		doc.calculate_total_charges()
		ch = doc.consolidation_charges[0]
		self.assertEqual(flt(ch.quantity), 500)
		self.assertEqual(flt(ch.base_amount), 500 * 60)

	def test_calculate_total_charges_fills_quantity_chargeable_weight(self):
		doc = frappe.new_doc("Air Consolidation")
		doc.chargeable_weight = 607.5
		doc.total_weight = 500
		doc.append(
			"consolidation_charges",
			{
				"charge_type": "Revenue",
				"charge_category": "Transportation",
				"revenue_calculation_method": "Per Unit",
				"unit_type": "Chargeable Weight",
				"rate": 60,
				"currency": "USD",
				"quantity": 0,
			},
		)
		doc.calculate_total_charges()
		ch = doc.consolidation_charges[0]
		self.assertEqual(flt(ch.quantity), 607.5)
		self.assertEqual(flt(ch.base_amount), 607.5 * 60)

	def test_calculate_total_charges_realigns_stale_quantity_for_unit_type(self):
		"""Stale quantity from a prior unit_type is replaced on save (Volume → total_volume)."""
		doc = frappe.new_doc("Air Consolidation")
		doc.chargeable_weight = 133600
		doc.total_weight = 200
		doc.total_volume = 800
		doc.append(
			"consolidation_charges",
			{
				"charge_type": "Revenue",
				"charge_category": "Transportation",
				"revenue_calculation_method": "Per Unit",
				"unit_type": "Volume",
				"rate": 50,
				"currency": "USD",
				"quantity": 200,
			},
		)
		doc.calculate_total_charges()
		ch = doc.consolidation_charges[0]
		self.assertEqual(flt(ch.quantity), 800)
		self.assertEqual(flt(ch.base_amount), 800 * 50)

	def test_calculate_total_charges_fills_quantity_volume(self):
		doc = frappe.new_doc("Air Consolidation")
		doc.total_volume = 12.5
		doc.append(
			"consolidation_charges",
			{
				"charge_type": "Revenue",
				"charge_category": "Transportation",
				"revenue_calculation_method": "Per Unit",
				"unit_type": "Volume",
				"rate": 10,
				"currency": "USD",
				"quantity": 0,
			},
		)
		doc.calculate_total_charges()
		ch = doc.consolidation_charges[0]
		self.assertEqual(flt(ch.quantity), 12.5)
		self.assertEqual(flt(ch.base_amount), 125)

	def test_calculate_total_charges_fills_quantity_shipment_uom(self):
		doc = frappe.new_doc("Air Consolidation")
		doc.chargeable_weight = 100
		doc.total_weight = 100
		doc.append(
			"consolidation_packages",
			{
				"package_reference": "PKG-TQ-1",
				"air_freight_job": "SHIP-TQ-A",
				"package_count": 1,
				"package_weight": 10,
			},
		)
		doc.append("consolidation_planning_lines", {"air_shipment": "SHIP-TQ-B"})
		doc.append(
			"consolidation_charges",
			{
				"charge_type": "Revenue",
				"charge_category": "Transportation",
				"revenue_calculation_method": "Per Unit",
				"unit_type": "Weight",
				"unit_of_measure": "shipment",
				"rate": 100,
				"currency": "USD",
				"quantity": 0,
			},
		)
		doc.calculate_total_charges()
		ch = doc.consolidation_charges[0]
		self.assertEqual(flt(ch.quantity), 2)
		self.assertEqual(flt(ch.base_amount), 200)

	def test_calculate_total_charges_fills_quantity_chargeable_weight_fallback(self):
		doc = frappe.new_doc("Air Consolidation")
		doc.chargeable_weight = 0
		doc.total_weight = 400
		doc.append(
			"consolidation_charges",
			{
				"charge_type": "Revenue",
				"charge_category": "Transportation",
				"revenue_calculation_method": "Per Unit",
				"unit_type": "Chargeable Weight",
				"rate": 2,
				"currency": "USD",
				"quantity": 0,
			},
		)
		doc.calculate_total_charges()
		ch = doc.consolidation_charges[0]
		self.assertEqual(flt(ch.quantity), 400)
		self.assertEqual(flt(ch.base_amount), 800)
