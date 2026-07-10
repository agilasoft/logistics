# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.utils.freight_agent_service import (
	resolve_service_type_label_for_freight_agent,
	validate_freight_agent_link,
	validate_freight_agent_links_on_doc,
)
from logistics.utils.service_mode_flags import validate_service_mode_link


class TestFreightAgentService(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _insert_agent(self, sfx: str, **flags):
		return (
			frappe.get_doc(
				{
					"doctype": "Freight Agent",
					"code": f"TST-FA-{sfx}",
					"freight_agent_name": f"Test Agent {sfx}",
					**flags,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def test_validate_service_mode_link_rejects_freight_agent_mismatch(self):
		sfx = frappe.generate_hash(length=6)
		agent = self._insert_agent(sfx, sea=1, air=0)
		with self.assertRaises(frappe.ValidationError):
			validate_service_mode_link(
				"Freight Agent",
				agent,
				"Air",
				context="test",
			)

	def test_validate_freight_agent_link_accepts_match(self):
		sfx = frappe.generate_hash(length=6)
		agent = self._insert_agent(sfx, air=1)
		validate_freight_agent_link(agent, "Air", context="test")

	def test_resolve_service_type_for_sea_booking_freight_agent(self):
		doc = frappe._dict({"doctype": "Sea Booking"})
		self.assertEqual(
			resolve_service_type_label_for_freight_agent(doc, "freight_agent"),
			"Sea",
		)

	def test_resolve_service_type_ignores_linked_main_service_job_id(self):
		doc = frappe._dict(
			{
				"doctype": "Sea Booking",
				"service_role": "Linked",
				"main_service_type": "Air Shipment",
				"main_service": "ASP-000000337",
			}
		)
		self.assertEqual(
			resolve_service_type_label_for_freight_agent(doc, "freight_agent"),
			"Sea",
		)

	def test_resolve_service_type_uses_sales_quote_main_service_select(self):
		doc = frappe._dict({"doctype": "Sales Quote", "main_service": "Air"})
		self.assertEqual(
			resolve_service_type_label_for_freight_agent(doc, "freight_agent"),
			"Air",
		)

	def test_resolve_service_type_for_shipper_air_default(self):
		doc = frappe._dict({"doctype": "Shipper"})
		self.assertEqual(
			resolve_service_type_label_for_freight_agent(doc, "air_default_sending_agent"),
			"Air",
		)

	def test_validate_freight_agent_links_on_air_booking(self):
		sfx = frappe.generate_hash(length=6)
		agent = self._insert_agent(sfx, sea=1, air=0)
		doc = frappe.get_doc(
			{
				"doctype": "Air Booking",
				"freight_agent": agent,
			}
		)
		with self.assertRaises(frappe.ValidationError):
			validate_freight_agent_links_on_doc(doc)

	def test_freight_agent_requires_applicable_service_type(self):
		sfx = frappe.generate_hash(length=6)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Freight Agent",
					"code": f"TST-FA-NOSVC-{sfx}",
					"freight_agent_name": f"No Service Agent {sfx}",
				}
			).insert(ignore_permissions=True)
