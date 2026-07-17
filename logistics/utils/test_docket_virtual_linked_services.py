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
			ls = frappe.get_doc(linked_service_doctype(), next(iter(names)))
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
			# Virtual field: use property / helper, not Document.get (returns None).
			self.assertIsInstance(reloaded.linked_services, list)
			reloaded.description = (reloaded.description or "") + " updated"
			reloaded.flags.ignore_mandatory = True
			reloaded.save(ignore_permissions=True)
		finally:
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def test_persist_job_link_materializes_missing_linked_service_without_save_required(self):
		"""Desk form_rows without Docket-owned LS docs must not throw Save required.

		Simulates Create Booking/Order after a saved Docket whose Linked Services were never
		cloned from the quote: client rows are present, canonical LS docs are empty.
		"""
		from logistics.utils.internal_job_detail_copy import persist_internal_job_detail_job_link

		exhibit = self._minimal_exhibit("Docket Persist LS Materialize")
		dk = self._minimal_docket(exhibit.name)
		fake_job_no = f"SB-TEST-{frappe.generate_hash(length=8)}"
		try:
			self.assertEqual(_linked_service_names_from_db("Docket", dk.name), set())
			frappe.local._logistics_dk_ij_client_rows = [
				frappe._dict(
					{
						"service_type": "Sea",
						"job_type": "Sea Booking",
					}
				)
			]
			# Must not raise "Save required" — materializes a Linked Service then writes job_no.
			persist_internal_job_detail_job_link(
				"Docket",
				dk.name,
				"Sea Booking",
				fake_job_no,
				detail_idx=1,
			)
			names = _linked_service_names_from_db("Docket", dk.name)
			self.assertEqual(len(names), 1)
			ls = frappe.get_doc(linked_service_doctype(), list(names)[0])
			self.assertEqual(ls.parent_booking_type, "Docket")
			self.assertEqual(ls.parent_booking_name, dk.name)
			self.assertEqual((ls.job_type or "").strip(), "Sea Booking")
			self.assertEqual((ls.job_no or "").strip(), fake_job_no)
		finally:
			if hasattr(frappe.local, "_logistics_dk_ij_client_rows"):
				delattr(frappe.local, "_logistics_dk_ij_client_rows")
			for ls_name in _linked_service_names_from_db("Docket", dk.name):
				frappe.delete_doc(
					linked_service_doctype(), ls_name, force=True, ignore_permissions=True
				)
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def test_persist_job_link_empty_client_override_does_not_wipe_linked_services(self):
		"""Empty desk linked_services payload must not orphan-delete existing Docket LS docs.

		Create Booking/Order often sends ``[]`` for the virtual grid; persist must stamp
		``job_no`` without parent-save orphan sync wiping sibling Linked Services.
		"""
		from logistics.utils.internal_job_detail_copy import persist_internal_job_detail_job_link

		exhibit = self._minimal_exhibit("Docket Persist LS Wipe Guard")
		dk = self._minimal_docket(exhibit.name)
		fake_job_no = f"SB-TEST-{frappe.generate_hash(length=8)}"
		ls_names: list[str] = []
		try:
			for service_type, job_type in (("Sea", "Sea Booking"), ("Air", "Air Booking")):
				ls = frappe.new_doc(linked_service_doctype())
				ls.parent_booking_type = "Docket"
				ls.parent_booking_name = dk.name
				ls.service_type = service_type
				ls.job_type = job_type
				ls.flags.ignore_mandatory = True
				ls.insert(ignore_permissions=True)
				ls_names.append(ls.name)

			before = _linked_service_names_from_db("Docket", dk.name)
			self.assertEqual(before, set(ls_names))

			# Simulate Create Booking desk payload: empty virtual grid override.
			frappe.local._logistics_dk_ij_client_rows = []
			persist_internal_job_detail_job_link(
				"Docket",
				dk.name,
				"Sea Booking",
				fake_job_no,
				detail_idx=1,
			)

			after = _linked_service_names_from_db("Docket", dk.name)
			self.assertEqual(after, set(ls_names))
			sea = frappe.get_doc(linked_service_doctype(), ls_names[0])
			air = frappe.get_doc(linked_service_doctype(), ls_names[1])
			self.assertEqual((sea.job_type or "").strip(), "Sea Booking")
			self.assertEqual((sea.job_no or "").strip(), fake_job_no)
			self.assertEqual((air.job_type or "").strip(), "Air Booking")
			self.assertFalse((air.job_no or "").strip())
		finally:
			if hasattr(frappe.local, "_logistics_dk_ij_client_rows"):
				delattr(frappe.local, "_logistics_dk_ij_client_rows")
			for ls_name in _linked_service_names_from_db("Docket", dk.name):
				frappe.delete_doc(
					linked_service_doctype(), ls_name, force=True, ignore_permissions=True
				)
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def _minimal_sales_quote_with_linked_services(self, title: str):
		"""Sales Quote owning Sea + Transport Linked Services (for Docket heal tests)."""
		if not frappe.db.exists("DocType", "Sales Quote"):
			self.skipTest("Sales Quote not installed")
		sq = frappe.new_doc("Sales Quote")
		sq.quotation_type = "Regular"
		sq.main_service = "Sea"
		sq.naming_series = "SQU.#########"
		sq.customer = frappe.db.get_value("Customer", {}, "name")
		if not sq.customer:
			self.skipTest("No Customer in system")
		sq.shipper = frappe.db.get_value("Shipper", {}, "name")
		sq.consignee = frappe.db.get_value("Consignee", {}, "name")
		if not sq.shipper or not sq.consignee:
			self.skipTest("No Shipper/Consignee in system")
		sq.date = today()
		sq.valid_until = add_days(today(), 30)
		sq.flags.ignore_mandatory = True
		sq.flags.ignore_validate = True
		sq.insert(ignore_permissions=True)
		for service_type, job_type in (("Sea", "Sea Booking"), ("Transport", "Transport Order")):
			ls = frappe.new_doc(linked_service_doctype())
			ls.parent_booking_type = "Sales Quote"
			ls.parent_booking_name = sq.name
			ls.service_type = service_type
			ls.job_type = job_type
			ls.flags.ignore_mandatory = True
			ls.insert(ignore_permissions=True)
		return sq

	def test_get_docket_booking_choices_materializes_from_sales_quote(self):
		"""Empty Docket LS + quote-owned LS → choices materialize Docket clones."""
		from logistics.mice.doctype.docket.docket_booking_creation import (
			get_docket_booking_choices,
		)

		exhibit = self._minimal_exhibit("Docket Choices LS Heal")
		dk = self._minimal_docket(exhibit.name)
		sq = self._minimal_sales_quote_with_linked_services("Docket Choices LS Heal SQ")
		try:
			frappe.db.set_value("Docket", dk.name, "sales_quote", sq.name, update_modified=False)
			self.assertEqual(_linked_service_names_from_db("Docket", dk.name), set())
			self.assertEqual(len(_linked_service_names_from_db("Sales Quote", sq.name)), 2)

			msg = get_docket_booking_choices(dk.name, linked_services="[]")
			choices = msg.get("choices") or []
			self.assertGreaterEqual(len(choices), 2)
			dk_ls = _linked_service_names_from_db("Docket", dk.name)
			self.assertEqual(len(dk_ls), 2)
			# Quote originals remain; Docket clones are distinct.
			self.assertFalse(dk_ls & _linked_service_names_from_db("Sales Quote", sq.name))
			sea_choices = [c for c in choices if c.get("job_type") == "Sea Booking"]
			self.assertTrue(sea_choices)
		finally:
			for ls_name in _linked_service_names_from_db("Docket", dk.name):
				frappe.delete_doc(
					linked_service_doctype(), ls_name, force=True, ignore_permissions=True
				)
			for ls_name in _linked_service_names_from_db("Sales Quote", sq.name):
				frappe.delete_doc(
					linked_service_doctype(), ls_name, force=True, ignore_permissions=True
				)
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)

	def test_docket_onload_materializes_from_sales_quote(self):
		"""Opening a Docket with sales_quote but no LS clones from the quote."""
		exhibit = self._minimal_exhibit("Docket Onload LS Heal")
		dk = self._minimal_docket(exhibit.name)
		sq = self._minimal_sales_quote_with_linked_services("Docket Onload LS Heal SQ")
		try:
			frappe.db.set_value("Docket", dk.name, "sales_quote", sq.name, update_modified=False)
			self.assertEqual(_linked_service_names_from_db("Docket", dk.name), set())

			reloaded = frappe.get_doc("Docket", dk.name)
			reloaded.run_method("onload")
			dk_ls = _linked_service_names_from_db("Docket", dk.name)
			self.assertEqual(len(dk_ls), 2)
			self.assertEqual(len(reloaded.linked_services), 2)
		finally:
			for ls_name in _linked_service_names_from_db("Docket", dk.name):
				frappe.delete_doc(
					linked_service_doctype(), ls_name, force=True, ignore_permissions=True
				)
			for ls_name in _linked_service_names_from_db("Sales Quote", sq.name):
				frappe.delete_doc(
					linked_service_doctype(), ls_name, force=True, ignore_permissions=True
				)
			frappe.delete_doc("Docket", dk.name, force=True, ignore_permissions=True)
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)
			frappe.delete_doc("MICE Project", exhibit.name, force=True, ignore_permissions=True)
