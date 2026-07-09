# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for MICE Project virtual ``linked_services`` grid backed by Linked Service docs."""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from logistics.utils.internal_job_persistence import (
	_linked_service_names_from_db,
	sync_internal_job_details_to_internal_jobs,
)
from logistics.utils.linked_service_compat import linked_service_doctype


class TestMiceProjectVirtualLinkedServices(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("MICE Project not installed")
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

	def test_append_and_save_creates_linked_service(self):
		exhibit = self._minimal_exhibit("MICE Virtual LS Append")
		try:
			doc = frappe.get_doc("MICE Project", exhibit.name)
			doc.append("linked_services", {"service_type": "Air"})
			self.assertTrue(doc.flags.get("_linked_services_from_form"))
			self.assertEqual(len(doc.linked_services), 1)
			doc.flags.ignore_mandatory = True
			doc.save(ignore_permissions=True)
			names = _linked_service_names_from_db("MICE Project", exhibit.name)
			self.assertEqual(len(names), 1)
			reloaded = frappe.get_doc("MICE Project", exhibit.name)
			self.assertEqual(len(reloaded.linked_services), 1)
			self.assertEqual(reloaded.linked_services[0].get("service_type"), "Air")
		finally:
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def test_sync_creates_linked_service_document(self):
		exhibit = self._minimal_exhibit("MICE Virtual LS Sync")
		try:
			doc = frappe.get_doc("MICE Project", exhibit.name)
			doc.append("linked_services", {"service_type": "Sea"})
			doc.flags._linked_services_from_form = True
			sync_internal_job_details_to_internal_jobs(doc)
			names = _linked_service_names_from_db("MICE Project", exhibit.name)
			self.assertEqual(len(names), 1)
			ls = frappe.get_doc(linked_service_doctype(), names[0])
			self.assertEqual(ls.parent_booking_type, "MICE Project")
			self.assertEqual(ls.parent_booking_name, exhibit.name)
			self.assertEqual(ls.service_type, "Sea")
		finally:
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def test_save_with_virtual_linked_services_does_not_fail_version(self):
		"""Regression: virtual linked_services grid must not break Version diff on save."""
		exhibit = self._minimal_exhibit("MICE Virtual LS Version")
		try:
			doc = frappe.get_doc("MICE Project", exhibit.name)
			doc.append("linked_services", {"service_type": "Transport"})
			doc.flags.ignore_mandatory = True
			doc.save(ignore_permissions=True)
			doc.reload()
			doc.flags.ignore_mandatory = True
			doc.save(ignore_permissions=True)
		finally:
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)
