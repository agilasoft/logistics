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
	USAGE_ROLE_SATELLITE_JOB,
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

	def _insert_execution(self, doctype: str, **fields):
		doc = frappe.new_doc(doctype)
		for key, value in fields.items():
			setattr(doc, key, value)
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		doc.flags.ignore_validate = True
		doc.insert(ignore_permissions=True)
		return doc

	def test_declaration_job_no_resolves_from_order_without_shipment_usage(self):
		"""Customs Job No is the Declaration even when only the Declaration Order was tagged."""
		ls = self._linked_service("Customs")
		air_shipment = f"ASP-TEST-{frappe.generate_hash(length=8)}"
		order_name = f"DCO-TEST-{frappe.generate_hash(length=8)}"
		declaration = None
		try:
			declaration = self._insert_execution(
				"Declaration",
				naming_series="CD.#########",
				declaration_order=order_name,
			)
			record_linked_service_usage(
				ls.name, "Air Shipment", air_shipment, usage_role=USAGE_ROLE_SHIPMENT
			)
			record_linked_service_usage(
				ls.name,
				"Declaration Order",
				order_name,
				usage_role=USAGE_ROLE_SATELLITE_JOB,
			)
			self.assertEqual(latest_shipment_from_usage(ls.name), ("", ""))
			view = build_linked_services_view_for_booking("Air Shipment", air_shipment)
			self.assertEqual(view[0].get("order_no"), order_name)
			self.assertEqual(view[0].get("job_no"), declaration.name)
		finally:
			if declaration and declaration.name:
				frappe.delete_doc("Declaration", declaration.name, force=True, ignore_permissions=True)
			frappe.delete_doc(
				linked_service_doctype(), ls.name, force=True, ignore_permissions=True
			)

	def test_cross_dock_warehouse_job_fills_job_no(self):
		"""Cross-Docking Job No is the Cross Dock Warehouse Job, not the order and not a storage job."""
		cross_ls = self._linked_service("Cross-Docking")
		wh_ls = self._linked_service("Warehousing")
		air_shipment = f"ASP-TEST-{frappe.generate_hash(length=8)}"
		order_name = f"WCD-TEST-{frappe.generate_hash(length=8)}"
		cross_job = None
		putaway_job = None
		try:
			cross_job = self._insert_execution(
				"Warehouse Job",
				naming_series="WJ-.##########",
				type="Cross Dock",
				reference_order_type="Cross-Docking Order",
				reference_order=order_name,
			)
			putaway_job = self._insert_execution(
				"Warehouse Job",
				naming_series="WJ-.##########",
				type="Putaway",
				reference_order_type="Cross-Docking Order",
				reference_order=order_name,
			)
			for ls in (cross_ls, wh_ls):
				record_linked_service_usage(
					ls.name, "Air Shipment", air_shipment, usage_role=USAGE_ROLE_SHIPMENT
				)
				record_linked_service_usage(
					ls.name,
					"Cross-Docking Order",
					order_name,
					usage_role=USAGE_ROLE_SATELLITE_JOB,
				)
			record_linked_service_usage(
				cross_ls.name,
				"Warehouse Job",
				cross_job.name,
				usage_role=USAGE_ROLE_SHIPMENT,
			)
			record_linked_service_usage(
				wh_ls.name,
				"Warehouse Job",
				putaway_job.name,
				usage_role=USAGE_ROLE_SHIPMENT,
			)
			self.assertEqual(
				latest_shipment_from_usage(cross_ls.name), ("Warehouse Job", cross_job.name)
			)
			self.assertEqual(
				latest_shipment_from_usage(wh_ls.name), ("Warehouse Job", putaway_job.name)
			)
			# Cross Dock usage on a Warehousing leg must not become that row's Job No.
			record_linked_service_usage(
				wh_ls.name,
				"Warehouse Job",
				cross_job.name,
				usage_role=USAGE_ROLE_SHIPMENT,
			)
			self.assertEqual(
				latest_shipment_from_usage(wh_ls.name), ("Warehouse Job", putaway_job.name)
			)
			view = build_linked_services_view_for_booking("Air Shipment", air_shipment)
			by_type = {(row.get("service_type") or ""): row for row in view}
			self.assertEqual(by_type["Cross-Docking"].get("order_no"), order_name)
			self.assertEqual(by_type["Cross-Docking"].get("job_no"), cross_job.name)
			self.assertEqual(by_type["Warehousing"].get("job_no"), putaway_job.name)
		finally:
			for job in (cross_job, putaway_job):
				if job and job.name:
					frappe.delete_doc(
						"Warehouse Job", job.name, force=True, ignore_permissions=True
					)
			for ls in (cross_ls, wh_ls):
				frappe.delete_doc(
					linked_service_doctype(), ls.name, force=True, ignore_permissions=True
				)

	def test_cross_dock_job_no_resolves_from_order_without_shipment_usage(self):
		ls = self._linked_service("Cross-Docking")
		air_shipment = f"ASP-TEST-{frappe.generate_hash(length=8)}"
		order_name = f"WCD-TEST-{frappe.generate_hash(length=8)}"
		cross_job = None
		try:
			cross_job = self._insert_execution(
				"Warehouse Job",
				naming_series="WJ-.##########",
				type="Cross Dock",
				reference_order_type="Cross-Docking Order",
				reference_order=order_name,
			)
			record_linked_service_usage(
				ls.name, "Air Shipment", air_shipment, usage_role=USAGE_ROLE_SHIPMENT
			)
			record_linked_service_usage(
				ls.name,
				"Cross-Docking Order",
				order_name,
				usage_role=USAGE_ROLE_SATELLITE_JOB,
			)
			self.assertEqual(latest_shipment_from_usage(ls.name), ("", ""))
			view = build_linked_services_view_for_booking("Air Shipment", air_shipment)
			self.assertEqual(view[0].get("job_no"), cross_job.name)
		finally:
			if cross_job and cross_job.name:
				frappe.delete_doc(
					"Warehouse Job", cross_job.name, force=True, ignore_permissions=True
				)
			frappe.delete_doc(
				linked_service_doctype(), ls.name, force=True, ignore_permissions=True
			)
