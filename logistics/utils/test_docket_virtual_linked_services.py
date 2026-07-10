# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for Docket virtual read-only ``linked_services`` grid backed by Linked Service docs."""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from logistics.utils.internal_job_persistence import (
	_linked_service_names_from_db,
	sync_internal_job_details_to_internal_jobs,
)
from logistics.utils.linked_service_compat import linked_service_doctype


class TestDocketVirtualLinkedServices(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket not installed")
		if not frappe.db.exists("DocType", linked_service_doctype()):
			self.skipTest("Linked Service not installed")

	def _minimal_exhibit(self, project_name: str):
		customer = frappe.db.get_value("Customer", {}, "name")
		if not customer:
			self.skipTest("No Customer in system")
		organizer = frappe.db.get_value("MICE Organizer", {}, "name")
		if not organizer:
			org = frappe.new_doc("MICE Organizer")
			org.organizer_name = f"Test Org {project_name}"
			org.organizer_type = "Company"
			org.customer = customer
			org.insert(ignore_permissions=True)
			organizer = org.name
		doc = frappe.new_doc("MICE Project")
		doc.project_name = project_name
		doc.organizer = organizer
		doc.show_open_date = today()
		doc.show_close_date = add_days(today(), 3)
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		return doc

	def _minimal_docket(self, exhibit_name: str):
		customer = frappe.db.get_value("Customer", {}, "name")
		dk = frappe.new_doc("Docket")
		dk.exhibit = exhibit_name
		dk.exhibitor = customer
		dk.flags.ignore_mandatory = True
		dk.insert(ignore_permissions=True)
		return dk

	def test_linked_services_view_from_owned_documents(self):
		exhibit = self._minimal_exhibit("Docket Virtual LS View")
		dk = self._minimal_docket(exhibit.name)
		try:
			ls = frappe.new_doc(linked_service_doctype())
			ls.parent_booking_type = "Docket"
			ls.parent_booking_name = dk.name
			ls.service_type = "Air"
			ls.flags.ignore_mandatory = True
			ls.insert(ignore_permissions=True)
			reloaded = frappe.get_doc("Docket", dk.name)
			self.assertEqual(len(reloaded.linked_services), 1)
			self.assertEqual(reloaded.linked_services[0].get("service_type"), "Air")
		finally:
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def test_staged_sync_creates_linked_service_document(self):
		exhibit = self._minimal_exhibit("Docket Virtual LS Sync")
		dk = self._minimal_docket(exhibit.name)
		try:
			doc = frappe.get_doc("Docket", dk.name)
			frappe.local._logistics_dk_ij_client_rows = [
				frappe._dict({"service_type": "Sea", "job_type": "Sea Booking"})
			]
			sync_internal_job_details_to_internal_jobs(doc)
			names = _linked_service_names_from_db("Docket", dk.name)
			self.assertEqual(len(names), 1)
			ls = frappe.get_doc(linked_service_doctype(), names[0])
			self.assertEqual(ls.parent_booking_type, "Docket")
			self.assertEqual(ls.parent_booking_name, dk.name)
			self.assertEqual(ls.service_type, "Sea")
		finally:
			if hasattr(frappe.local, "_logistics_dk_ij_client_rows"):
				delattr(frappe.local, "_logistics_dk_ij_client_rows")
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def test_save_with_virtual_linked_services_does_not_fail_version(self):
		exhibit = self._minimal_exhibit("Docket Virtual LS Version")
		dk = self._minimal_docket(exhibit.name)
		try:
			doc = frappe.get_doc("Docket", dk.name)
			doc.flags.ignore_mandatory = True
			doc.save(ignore_permissions=True)
			reloaded = frappe.get_doc("Docket", dk.name)
			self.assertIsInstance(reloaded.get("linked_services"), list)
			reloaded.description = (reloaded.description or "") + " updated"
			reloaded.flags.ignore_mandatory = True
			reloaded.save(ignore_permissions=True)
		finally:
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)
