# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from logistics.air_freight.tests.test_helpers import (
	create_test_branch,
	create_test_consignee,
	create_test_cost_center,
	create_test_profit_center,
	create_test_shipper,
	create_test_unloco,
	setup_basic_master_data,
)
from logistics.utils.house_document_defaults import (
	auto_populate_export_house_document_from_shipment_id,
)


class TestHouseDocumentDefaults(FrappeTestCase):
	def setUp(self):
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
			self.cost_center = frappe.db.get_value(
				"Cost Center", {"company": self.company, "is_group": 0}, "name"
			)
			self.profit_center = frappe.db.get_value("Profit Center", {"company": self.company}, "name")

	def tearDown(self):
		frappe.db.rollback()

	def test_export_air_shipment_auto_populates_house_awb_from_id(self):
		shipment = frappe.get_doc(
			{
				"doctype": "Air Shipment",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"direction": "Export",
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
			}
		)
		shipment.insert()

		self.assertEqual(shipment.house_awb, shipment.name)

	def test_import_air_shipment_does_not_auto_populate_house_awb(self):
		shipment = frappe.get_doc(
			{
				"doctype": "Air Shipment",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"direction": "Import",
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
			}
		)
		shipment.insert()

		self.assertFalse(shipment.house_awb)

	def test_existing_air_shipment_house_awb_is_not_overwritten(self):
		shipment = frappe.get_doc(
			{
				"doctype": "Air Shipment",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"direction": "Export",
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
				"house_awb": "CUSTOM-HAWB",
			}
		)
		shipment.insert()

		self.assertEqual(shipment.house_awb, "CUSTOM-HAWB")

	def test_export_sea_shipment_auto_populates_house_bl_from_id(self):
		shipment = frappe.get_doc(
			{
				"doctype": "Sea Shipment",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"direction": "Export",
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
			}
		)
		shipment.insert()

		self.assertEqual(shipment.house_bl, shipment.name)

	def test_export_sea_shipment_populates_when_direction_changes_on_save(self):
		shipment = frappe.get_doc(
			{
				"doctype": "Sea Shipment",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"direction": "Import",
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
			}
		)
		shipment.insert()
		self.assertFalse(shipment.house_bl)

		shipment.direction = "Export"
		shipment.save()

		self.assertEqual(shipment.house_bl, shipment.name)

	def test_auto_populate_helper_is_noop_without_name(self):
		shipment = frappe.get_doc(
			{
				"doctype": "Air Shipment",
				"direction": "Export",
			}
		)
		self.assertFalse(auto_populate_export_house_document_from_shipment_id(shipment))
		self.assertFalse(shipment.house_awb)
