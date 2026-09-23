# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Job No on the Services grid must be the linked service's own execution job.

Creating a main Air Shipment tags every IJ-… with Shipment usage of that Air Shipment.
Sea / Customs / Transport rows must not show that parent shipment number as Job No.
"""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.utils.linked_service_compat import linked_service_doctype
from logistics.utils.linked_service_usage import (
	USAGE_ROLE_PARENT_BOOKING,
	USAGE_ROLE_SHIPMENT,
	latest_shipment_from_usage,
	record_linked_service_usage,
)
from logistics.utils.virtual_linked_services_view import build_linked_services_view_for_booking


class TestLinkedServiceJobNoFromUsage(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("DocType", linked_service_doctype()):
			self.skipTest("Linked Service not installed")
		if not frappe.db.exists("DocType", "Linked Service Usage"):
			self.skipTest("Linked Service Usage not installed")

	def _linked_service(self, service_type: str):
		ls = frappe.new_doc(linked_service_doctype())
		ls.service_type = service_type
		ls.flags.ignore_mandatory = True
		ls.insert(ignore_permissions=True)
		return ls

	def test_parent_air_shipment_does_not_fill_sea_job_no(self):
		"""ASP-000000393 / issue 1408: Sea Job No stays empty after main Air Shipment create."""
		ls = self._linked_service("Sea")
		air_shipment = f"ASP-TEST-{frappe.generate_hash(length=8)}"
		try:
			record_linked_service_usage(
				ls.name, "Air Booking", "ABK-TEST", usage_role=USAGE_ROLE_PARENT_BOOKING
			)
			record_linked_service_usage(
				ls.name, "Air Shipment", air_shipment, usage_role=USAGE_ROLE_SHIPMENT
			)
			self.assertEqual(latest_shipment_from_usage(ls.name), ("", ""))
			view = build_linked_services_view_for_booking("Air Shipment", air_shipment)
			self.assertEqual(len(view), 1)
			self.assertEqual(view[0].get("service_type"), "Sea")
			self.assertFalse(view[0].get("job_no"))
		finally:
			frappe.delete_doc(
				linked_service_doctype(), ls.name, force=True, ignore_permissions=True
			)

	def test_matching_sea_shipment_fills_job_no(self):
		ls = self._linked_service("Sea")
		air_shipment = f"ASP-TEST-{frappe.generate_hash(length=8)}"
		sea_shipment = f"SF-TEST-{frappe.generate_hash(length=8)}"
		try:
			record_linked_service_usage(
				ls.name, "Air Shipment", air_shipment, usage_role=USAGE_ROLE_SHIPMENT
			)
			record_linked_service_usage(
				ls.name, "Sea Shipment", sea_shipment, usage_role=USAGE_ROLE_SHIPMENT
			)
			self.assertEqual(latest_shipment_from_usage(ls.name), ("Sea Shipment", sea_shipment))
			view = build_linked_services_view_for_booking("Air Shipment", air_shipment)
			self.assertEqual(view[0].get("job_no"), sea_shipment)
		finally:
			frappe.delete_doc(
				linked_service_doctype(), ls.name, force=True, ignore_permissions=True
			)

	def test_transport_job_still_fills_job_no_when_parent_air_shipment_tagged(self):
		ls = self._linked_service("Transport")
		air_shipment = f"ASP-TEST-{frappe.generate_hash(length=8)}"
		transport_job = f"TRJ-TEST-{frappe.generate_hash(length=8)}"
		try:
			record_linked_service_usage(
				ls.name, "Air Shipment", air_shipment, usage_role=USAGE_ROLE_SHIPMENT
			)
			record_linked_service_usage(
				ls.name, "Transport Job", transport_job, usage_role=USAGE_ROLE_SHIPMENT
			)
			self.assertEqual(
				latest_shipment_from_usage(ls.name), ("Transport Job", transport_job)
			)
		finally:
			frappe.delete_doc(
				linked_service_doctype(), ls.name, force=True, ignore_permissions=True
			)
