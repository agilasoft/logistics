# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today
from logistics.air_freight.tests.test_helpers import (
	setup_basic_master_data,
	create_test_shipper,
	create_test_consignee,
	create_test_unloco,
	create_test_branch,
	create_test_cost_center,
	create_test_profit_center,
)


class TestSeaShipment(FrappeTestCase):
	"""Test cases for Sea Shipment doctype"""

	def setUp(self):
		"""Set up test data"""
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		self.shipper = create_test_shipper()
		self.consignee = create_test_consignee()
		create_test_unloco("USLAX", "Los Angeles", "LAX", "US", "Airport")
		create_test_unloco("USJFK", "New York JFK", "JFK", "US", "Airport")
		try:
			self.branch = create_test_branch(self.company)
			self.cost_center = create_test_cost_center(self.company)
			self.profit_center = create_test_profit_center(self.company)
		except Exception:
			self.branch = frappe.db.get_value("Branch", {"custom_company": self.company}, "name")
			self.cost_center = frappe.db.get_value("Cost Center", {"company": self.company, "is_group": 0}, "name")
			self.profit_center = frappe.db.get_value("Profit Center", {"company": self.company}, "name")

	def tearDown(self):
		frappe.db.rollback()

	def test_sea_shipment_creation(self):
		"""Test creating a basic Sea Shipment"""
		shipment = frappe.get_doc({
			"doctype": "Sea Shipment",
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
		})
		shipment.insert()

		self.assertIsNotNone(shipment.name)
		self.assertEqual(shipment.company, self.company)
		self.assertEqual(shipment.local_customer, self.customer)

	def test_sea_shipment_required_fields(self):
		"""Test that required fields are enforced"""
		shipment = frappe.get_doc({"doctype": "Sea Shipment", "booking_date": today()})
		with self.assertRaises((frappe.ValidationError, frappe.MandatoryError)):
			shipment.insert()

	def test_sea_shipment_with_packages(self):
		"""Test creating Sea Shipment with packages"""
		shipment = frappe.get_doc({
			"doctype": "Sea Shipment",
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
		})
		shipment.append("packages", {
			"package_type": "Box",
			"quantity": 10,
			"weight": 100,
			"volume": 0.5,
		})
		shipment.insert()

		self.assertEqual(len(shipment.packages), 1)
		self.assertEqual(shipment.packages[0].quantity, 10)

	def test_sea_booking_applies_sea_freight_settings_accounting_defaults(self):
		"""New Sea Booking should get branch, cost center, and profit center from Sea Freight Settings when blank."""
		branch = create_test_branch(self.company, "SF Settings Branch SBK")
		cost_center = create_test_cost_center(self.company, "SF Settings CC SBK")
		profit_center = create_test_profit_center(self.company, "SF Settings PC SBK", code="SF-SBK-PC")

		settings = frappe.get_doc("Sea Freight Settings")
		settings.default_branch = branch
		settings.default_cost_center = cost_center
		settings.default_profit_center = profit_center
		settings.default_company = self.company
		settings.save(ignore_permissions=True)

		booking = frappe.get_doc({
			"doctype": "Sea Booking",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"direction": "Export",
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "USLAX",
			"destination_port": "USJFK",
		})
		booking.insert()

		self.assertEqual(booking.branch, branch)
		self.assertEqual(booking.cost_center, cost_center)
		self.assertEqual(booking.profit_center, profit_center)

	def test_sea_booking_settings_defaults_do_not_override_existing_accounting(self):
		"""Sea Freight Settings should only fill empty accounting fields."""
		settings_branch = create_test_branch(self.company, "SF Branch A")
		settings_cc = create_test_cost_center(self.company, "SF CC A")
		settings_pc = create_test_profit_center(self.company, "SF PC A", code="SF-PC-A")
		manual_branch = create_test_branch(self.company, "SF Manual Branch")

		settings = frappe.get_doc("Sea Freight Settings")
		settings.default_branch = settings_branch
		settings.default_cost_center = settings_cc
		settings.default_profit_center = settings_pc
		settings.default_company = self.company
		settings.save(ignore_permissions=True)

		booking = frappe.get_doc({
			"doctype": "Sea Booking",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"direction": "Export",
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"branch": manual_branch,
		})
		booking.insert()

		self.assertEqual(booking.branch, manual_branch)
		self.assertEqual(booking.cost_center, settings_cc)
		self.assertEqual(booking.profit_center, settings_pc)

	def test_sea_freight_settings_skips_when_default_company_mismatch(self):
		"""When Default Company is set, defaults apply only if it matches the document company."""
		from unittest.mock import patch

		from logistics.sea_freight.sea_freight_settings_defaults import (
			apply_accounting_defaults_from_sea_freight_settings,
		)

		branch = create_test_branch(self.company, "SF Mismatch Branch")

		class _FakeSettings:
			default_company = "Nonexistent Company For Mismatch Test"
			default_branch = branch
			default_cost_center = None
			default_profit_center = None

		doc = frappe.get_doc({"doctype": "Sea Booking", "company": self.company})
		with patch(
			"logistics.sea_freight.sea_freight_settings_defaults.frappe.get_single",
			return_value=_FakeSettings(),
		):
			apply_accounting_defaults_from_sea_freight_settings(doc)

		self.assertFalse(doc.branch)

	def test_sea_shipment_applies_sea_freight_settings_accounting_defaults(self):
		"""New Sea Shipment must receive accounting defaults from Sea Freight Settings (required Account fields)."""
		branch = create_test_branch(self.company, "SF Shipment Branch")
		cc = create_test_cost_center(self.company, "SF Shipment CC")
		pc = create_test_profit_center(self.company, "SF Shipment PC", code="SF-SSP-PC")

		settings = frappe.get_doc("Sea Freight Settings")
		settings.default_branch = branch
		settings.default_cost_center = cc
		settings.default_profit_center = pc
		settings.default_company = self.company
		settings.save(ignore_permissions=True)

		booking = frappe.get_doc({
			"doctype": "Sea Booking",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"direction": "Export",
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"branch": branch,
			"cost_center": cc,
			"profit_center": pc,
		})
		booking.insert()

		shipment = frappe.get_doc({
			"doctype": "Sea Shipment",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"direction": "Export",
			"sea_booking": booking.name,
		})
		shipment.insert()

		self.assertEqual(shipment.branch, branch)
		self.assertEqual(shipment.cost_center, cc)
		self.assertEqual(shipment.profit_center, pc)
