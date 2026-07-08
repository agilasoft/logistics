# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for operational parents using Linked Service documents (no Internal Jobs grid)."""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.utils.internal_job_detail_copy import transfer_linked_services_to_parent
from logistics.utils.internal_job_persistence import (
	_linked_service_names_from_db,
	internal_job_detail_rows_for_parent,
	sync_internal_job_details_to_internal_jobs,
)
from logistics.utils.linked_service_compat import linked_service_doctype
from logistics.utils.virtual_internal_job_details import uses_virtual_internal_job_details


class TestOperationalLinkedServices(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("DocType", "Sea Booking"):
			self.skipTest("Sea Booking not installed")
		if not frappe.db.exists("DocType", linked_service_doctype()):
			self.skipTest("Linked Service not installed")
		self.assertTrue(uses_virtual_internal_job_details("Sea Booking"))

	def _minimal_sea_booking(self):
		doc = frappe.new_doc("Sea Booking")
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		return doc

	def _minimal_sea_shipment(self, booking_name: str | None = None):
		doc = frappe.new_doc("Sea Shipment")
		if booking_name:
			doc.sea_booking = booking_name
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		return doc

	def test_sync_creates_linked_service_from_staged_rows(self):
		booking = self._minimal_sea_booking()
		try:
			frappe.local._logistics_ij_client_rows = [frappe._dict(service_type="Sea")]
			sync_internal_job_details_to_internal_jobs(booking)
			names = _linked_service_names_from_db("Sea Booking", booking.name)
			self.assertEqual(len(names), 1)
			ls = frappe.get_doc(linked_service_doctype(), list(names)[0])
			self.assertEqual(ls.parent_booking_type, "Sea Booking")
			self.assertEqual(ls.parent_booking_name, booking.name)
			self.assertEqual(ls.service_type, "Sea")
		finally:
			if hasattr(frappe.local, "_logistics_ij_client_rows"):
				delattr(frappe.local, "_logistics_ij_client_rows")
			frappe.delete_doc("Sea Booking", booking.name, force=True, ignore_permissions=True)

	def test_rows_for_parent_reads_linked_services_from_db(self):
		booking = self._minimal_sea_booking()
		try:
			frappe.local._logistics_ij_client_rows = [frappe._dict(service_type="Transport")]
			sync_internal_job_details_to_internal_jobs(booking)
			rows = internal_job_detail_rows_for_parent(frappe.get_doc("Sea Booking", booking.name))
			self.assertEqual(len(rows), 1)
			self.assertEqual(rows[0].service_type, "Transport")
		finally:
			if hasattr(frappe.local, "_logistics_ij_client_rows"):
				delattr(frappe.local, "_logistics_ij_client_rows")
			frappe.delete_doc("Sea Booking", booking.name, force=True, ignore_permissions=True)

	def test_transfer_linked_services_reparents_to_shipment(self):
		booking = self._minimal_sea_booking()
		shipment = self._minimal_sea_shipment(booking.name)
		try:
			frappe.local._logistics_ij_client_rows = [frappe._dict(service_type="Sea")]
			sync_internal_job_details_to_internal_jobs(booking)
			ls_names = _linked_service_names_from_db("Sea Booking", booking.name)
			self.assertEqual(len(ls_names), 1)
			transfer_linked_services_to_parent(
				frappe.get_doc("Sea Booking", booking.name),
				frappe.get_doc("Sea Shipment", shipment.name),
			)
			self.assertEqual(_linked_service_names_from_db("Sea Booking", booking.name), set())
			shipment_ls = _linked_service_names_from_db("Sea Shipment", shipment.name)
			self.assertEqual(shipment_ls, ls_names)
		finally:
			if hasattr(frappe.local, "_logistics_ij_client_rows"):
				delattr(frappe.local, "_logistics_ij_client_rows")
			frappe.delete_doc("Sea Shipment", shipment.name, force=True, ignore_permissions=True)
			frappe.delete_doc("Sea Booking", booking.name, force=True, ignore_permissions=True)

	def test_meta_has_linked_services_field_on_sea_booking(self):
		meta = frappe.get_meta("Sea Booking")
		field = meta.get_field("linked_services")
		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Table")
		self.assertTrue(field.is_virtual)
		self.assertIsNone(meta.get_field("internal_job_details"))

	def test_meta_has_linked_services_field_on_sea_shipment(self):
		meta = frappe.get_meta("Sea Shipment")
		field = meta.get_field("linked_services")
		self.assertIsNotNone(field)
		self.assertEqual(field.fieldtype, "Table")
		self.assertTrue(field.is_virtual)
		self.assertIsNone(meta.get_field("internal_job_details"))
