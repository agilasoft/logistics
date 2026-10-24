# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_to_date, flt, getdate, now_datetime, today
from logistics.air_freight.tests.test_helpers import (
	create_test_branch,
	create_test_cost_center,
	create_test_profit_center,
	create_test_unloco,
	setup_basic_master_data,
)


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


class TestAssignMAWBFromStock(FrappeTestCase):
	"""Action → Assign MAWB from Stock links a Master Air Waybill issued from stock."""

	def setUp(self):
		data = setup_basic_master_data()
		self.company = data["company"]
		create_test_unloco("USLAX", "Los Angeles", "LAX", "US", "Airport")
		create_test_unloco("USJFK", "New York JFK", "JFK", "US", "Airport")
		self.airline = "Z" + frappe.generate_hash(length=4).upper()
		if not frappe.db.exists("Airline", self.airline):
			frappe.get_doc({
				"doctype": "Airline",
				"code": self.airline,
				"airline_name": "Assign MAWB Test {0}".format(self.airline),
				"iata_code": self.airline[:2],
				"is_active": 1,
			}).insert(ignore_permissions=True)
		self._cleanup = [("Airline", self.airline)]
		self.departure = now_datetime()
		self.arrival = add_to_date(self.departure, days=1)
		branches = frappe.get_all("Branch", pluck="name", limit=1)
		self.branch = branches[0] if branches else create_test_branch(self.company)
		self.cost_center = frappe.db.get_value(
			"Cost Center", {"company": self.company, "is_group": 0}, "name"
		)
		if not self.cost_center:
			self.cost_center = create_test_cost_center(self.company)
		self.profit_center = frappe.db.get_value("Profit Center", {"company": self.company}, "name")
		if not self.profit_center:
			self.profit_center = create_test_profit_center(self.company)

	def tearDown(self):
		# issue_mawb_from_stock commits. Delete dependents first, then commit.
		ranges = [name for doctype, name in self._cleanup if doctype == "MAWB Stock Range" and name]
		mawbs = [name for doctype, name in self._cleanup if doctype == "Master Air Waybill" and name]
		consols = [name for doctype, name in self._cleanup if doctype == "Air Consolidation" and name]
		airlines = [name for doctype, name in self._cleanup if doctype == "Airline" and name]
		if ranges:
			mawbs.extend(
				frappe.get_all(
					"Master Air Waybill",
					filters={"mawb_stock_range": ["in", ranges]},
					pluck="name",
				)
			)
		seen = set()
		for doctype, names in (
			("Air Consolidation", consols),
			("Master Air Waybill", mawbs),
			("MAWB Stock Range", ranges),
			("Airline", airlines),
		):
			for name in names:
				key = (doctype, name)
				if key in seen or not frappe.db.exists(doctype, name):
					continue
				seen.add(key)
				frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)
		frappe.db.commit()

	def _track(self, doctype, name):
		self._cleanup.append((doctype, name))
		return name

	def _stock_range(self, prefix, serial, company=None, is_default=0):
		doc = frappe.get_doc({
			"doctype": "MAWB Stock Range",
			"naming_series": "MAWB-STOCK-.####",
			"airline": self.airline,
			"prefix": prefix,
			"from_serial": serial,
			"to_serial": serial + 5,
			"next_serial": serial,
			"company": company,
			"is_default": is_default,
		})
		doc.insert(ignore_permissions=True)
		return self._track("MAWB Stock Range", doc.name)

	def _consolidation(self, status="Draft"):
		doc = frappe.get_doc({
			"doctype": "Air Consolidation",
			"naming_series": "AC-{MM}-{YYYY}-{####}",
			"consolidation_date": today(),
			"consolidation_type": "Direct Consolidation",
			"status": status,
			"company": self.company,
			"branch": self.branch,
			"cost_center": self.cost_center,
			"profit_center": self.profit_center,
			"airline": self.airline,
			"origin_airport": "USLAX",
			"destination_airport": "USJFK",
			"departure_date": self.departure,
			"arrival_date": self.arrival,
			"flight_number": "ZX100",
		})
		doc.insert(ignore_permissions=True)
		self._track("Air Consolidation", doc.name)
		return doc

	def test_assigns_mawb_from_company_stock_range(self):
		blank_company_range = self._stock_range("997", 100, company=None, is_default=1)
		company_range = self._stock_range("998", 200, company=self.company, is_default=0)
		consolidation = self._consolidation()

		result = consolidation.assign_mawb_from_stock()

		self.assertTrue(result["mawb_name"])
		self.assertEqual(result["master_awb_no"], "998-00000200")
		self.assertEqual(result["stock_range"], company_range)
		self._track("Master Air Waybill", result["mawb_name"])

		consolidation.reload()
		self.assertEqual(consolidation.master_awb, result["mawb_name"])
		self.assertEqual(consolidation.status, "Draft")

		mawb = frappe.get_doc("Master Air Waybill", result["mawb_name"])
		self.assertEqual(mawb.master_awb_no, "998-00000200")
		self.assertEqual(mawb.airline, self.airline)
		self.assertEqual(mawb.origin_airport, "USLAX")
		self.assertEqual(mawb.destination_airport, "USJFK")
		self.assertEqual(mawb.flight_no, "ZX100")
		self.assertEqual(getdate(mawb.flight_date), getdate(self.departure))
		self.assertEqual(mawb.issued_from_stock, 1)
		self.assertEqual(mawb.mawb_stock_range, company_range)
		self.assertEqual(
			frappe.db.get_value("MAWB Stock Range", company_range, "next_serial"),
			201,
		)
		self.assertEqual(
			frappe.db.get_value("MAWB Stock Range", blank_company_range, "next_serial"),
			100,
		)

		with self.assertRaises(ValidationError):
			consolidation.assign_mawb_from_stock()
		self.assertEqual(
			frappe.db.get_value("MAWB Stock Range", company_range, "next_serial"),
			201,
		)

	def test_planning_consolidation_becomes_ready_for_departure(self):
		stock_range = self._stock_range("996", 300, company=self.company, is_default=1)
		consolidation = self._consolidation(status="Planning")

		result = consolidation.assign_mawb_from_stock()
		self._track("Master Air Waybill", result["mawb_name"])

		consolidation.reload()
		self.assertEqual(consolidation.master_awb, result["mawb_name"])
		self.assertEqual(consolidation.status, "Ready for Departure")
		self.assertEqual(result["stock_range"], stock_range)

	def test_missing_stock_range_does_not_issue_a_mawb(self):
		consolidation = self._consolidation()
		before = frappe.db.count("Master Air Waybill")

		with self.assertRaises(ValidationError) as ctx:
			consolidation.assign_mawb_from_stock()

		self.assertIn(self.airline, str(ctx.exception))
		self.assertEqual(frappe.db.count("Master Air Waybill"), before)
		consolidation.reload()
		self.assertFalse(consolidation.master_awb)

	def test_exhausted_stock_is_rejected(self):
		stock_range = self._stock_range("995", 400, company=self.company)
		frappe.db.set_value("MAWB Stock Range", stock_range, "next_serial", 406)
		consolidation = self._consolidation()

		with self.assertRaises(ValidationError) as ctx:
			consolidation.assign_mawb_from_stock()

		self.assertIn("exhausted", str(ctx.exception).lower())
		consolidation.reload()
		self.assertFalse(consolidation.master_awb)
