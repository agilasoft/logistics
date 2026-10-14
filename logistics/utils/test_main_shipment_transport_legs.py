# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Legs on a Transport Order created from an Air or Sea Shipment."""

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.utils.module_integration import _seed_transport_order_legs_from_main_shipment


class TestMainShipmentTransportLegs(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _ensure_load_type(self, name: str, **flags):
		if frappe.db.exists("Load Type", name):
			doc = frappe.get_doc("Load Type", name)
			for key, value in flags.items():
				doc.set(key, value)
			doc.save(ignore_permissions=True)
			return doc.name

		doc = frappe.new_doc("Load Type")
		doc.load_type_name = name
		doc.description = name
		doc.is_active = 1
		for key, value in flags.items():
			doc.set(key, value)
		doc.insert(ignore_permissions=True)
		return doc.name

	def _shipment(self):
		return frappe._dict(
			shipper="SHIP-DOOR",
			consignee="CON-DOOR",
			shipper_address="ADDR-PICK",
			consignee_address="ADDR-DROP",
			eta="2026-10-20",
		)

	def test_template_is_the_only_leg_source(self):
		ftl = self._ensure_load_type("FTL", transport=1, non_container=1)
		tpl = frappe.get_doc(
			{
				"doctype": "Transport Template",
				"code": "TO-SHIP-TPL-LEGS",
				"description": "Shipment create lane",
				"default_load_type": ftl,
				"legs": [
					{
						"facility_type_from": "Container Freight Station",
						"facility_type_to": "Storage Facility",
					},
					{
						"facility_type_from": "Storage Facility",
						"facility_type_to": "Consignee",
					},
				],
				"allowed_load_types": [{"load_type": ftl}],
			}
		)
		tpl.insert(ignore_permissions=True)

		order = frappe.new_doc("Transport Order")
		order.transport_template = tpl.name
		order.transport_job_type = "Non-Container"
		order.scheduled_date = "2026-10-20"
		order.append(
			"legs",
			{
				"facility_type_from": "Shipper",
				"facility_from": "SHIP-DOOR",
				"facility_type_to": "Consignee",
				"facility_to": "CON-DOOR",
			},
		)

		_seed_transport_order_legs_from_main_shipment(order, self._shipment())

		self.assertEqual(len(order.legs or []), 2)
		self.assertEqual(order.legs[0].facility_type_from, "Container Freight Station")
		self.assertEqual(order.legs[0].facility_type_to, "Storage Facility")
		self.assertEqual(order.legs[1].facility_type_from, "Storage Facility")
		self.assertEqual(order.legs[1].facility_type_to, "Consignee")
		self.assertFalse(any(getattr(leg, "facility_from", None) == "SHIP-DOOR" for leg in order.legs))
		self.assertEqual(order.legs[0].transport_job_type, "Non-Container")

	def test_door_leg_when_no_template(self):
		order = frappe.new_doc("Transport Order")
		order.transport_job_type = "Non-Container"

		_seed_transport_order_legs_from_main_shipment(order, self._shipment())

		self.assertEqual(len(order.legs or []), 1)
		leg = order.legs[0]
		self.assertEqual(leg.facility_type_from, "Shipper")
		self.assertEqual(leg.facility_from, "SHIP-DOOR")
		self.assertEqual(leg.facility_type_to, "Consignee")
		self.assertEqual(leg.facility_to, "CON-DOOR")
		self.assertEqual(leg.pick_address, "ADDR-PICK")
		self.assertEqual(leg.drop_address, "ADDR-DROP")
		self.assertEqual(str(leg.scheduled_date), "2026-10-20")
