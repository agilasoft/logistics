# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for Sales Quote virtual ``linked_services`` grid backed by Linked Service docs."""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.utils.internal_job_persistence import (
	_linked_service_names_from_db,
	sync_internal_job_details_to_internal_jobs,
)
from logistics.utils.linked_service_compat import linked_service_doctype


class TestSalesQuoteVirtualLinkedServices(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("DocType", "Sales Quote"):
			self.skipTest("Sales Quote not installed")
		if not frappe.db.exists("DocType", linked_service_doctype()):
			self.skipTest("Linked Service not installed")

	def _minimal_sales_quote(self, title: str):
		doc = frappe.new_doc("Sales Quote")
		doc.quotation_type = "Project"
		doc.main_service = "Special Project"
		doc.naming_series = "PQ.#####"
		doc.project_name = title
		doc.customer = frappe.db.get_value("Customer", {}, "name")
		if not doc.customer:
			self.skipTest("No Customer in system")
		doc.date = frappe.utils.today()
		doc.valid_until = frappe.utils.add_days(frappe.utils.today(), 30)
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		return doc

	def test_save_creates_linked_service_document(self):
		sq = self._minimal_sales_quote("SQ Virtual LS Create")
		try:
			sq.append(
				"linked_services",
				{"service_type": "Sea", "load_type": None},
			)
			sq.flags._linked_services_from_form = True
			sync_internal_job_details_to_internal_jobs(sq)
			names = _linked_service_names_from_db("Sales Quote", sq.name)
			self.assertEqual(len(names), 1)
			ls = frappe.get_doc(linked_service_doctype(), list(names)[0])
			self.assertEqual(ls.parent_booking_type, "Sales Quote")
			self.assertEqual(ls.parent_booking_name, sq.name)
			self.assertEqual(ls.service_type, "Sea")
		finally:
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)

	def test_save_persists_linked_service_via_before_save_hook(self):
		"""Full save path: grid rows must sync in before_save before virtual rows are cleared."""
		sq = self._minimal_sales_quote("SQ Virtual LS Full Save")
		try:
			doc = frappe.get_doc("Sales Quote", sq.name)
			doc.append("linked_services", {"service_type": "Air"})
			doc.flags.ignore_mandatory = True
			doc.save(ignore_permissions=True)
			names = _linked_service_names_from_db("Sales Quote", sq.name)
			self.assertEqual(len(names), 1)
			ls = frappe.get_doc(linked_service_doctype(), list(names)[0])
			self.assertEqual(ls.parent_booking_type, "Sales Quote")
			self.assertEqual(ls.parent_booking_name, sq.name)
			self.assertEqual(ls.service_type, "Air")
			reloaded = frappe.get_doc("Sales Quote", sq.name)
			self.assertEqual(len(reloaded.linked_services), 1)
			self.assertEqual(reloaded.linked_services[0].get("service_type"), "Air")
		finally:
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)

	def test_virtual_grid_reloads_from_linked_service(self):
		sq = self._minimal_sales_quote("SQ Virtual LS Reload")
		try:
			sq.append(
				"linked_services",
				{"service_type": "Transport"},
			)
			sq.flags._linked_services_from_form = True
			sync_internal_job_details_to_internal_jobs(sq)
			reloaded = frappe.get_doc("Sales Quote", sq.name)
			rows = reloaded.linked_services
			self.assertEqual(len(rows), 1)
			self.assertEqual(rows[0].get("service_type"), "Transport")
			self.assertTrue(rows[0].get("linked_service"))
		finally:
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)

	def test_save_with_virtual_linked_services_does_not_fail_version(self):
		"""Regression: virtual Services grid must not break Version diff on save."""
		sq = self._minimal_sales_quote("SQ Virtual LS Version")
		try:
			sq.append("linked_services", {"service_type": "Customs"})
			sq.flags._linked_services_from_form = True
			sq.save(ignore_permissions=True)
			reloaded = frappe.get_doc("Sales Quote", sq.name)
			self.assertIsInstance(reloaded.linked_services, list)
			reloaded.description = (reloaded.description or "") + " updated"
			reloaded.flags.ignore_mandatory = True
			reloaded.save(ignore_permissions=True)
		finally:
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)

	def test_delete_last_linked_service_row_on_full_save(self):
		"""Deleting the only Services row and saving must remove the backing Linked Service."""
		sq = self._minimal_sales_quote("SQ Virtual LS Delete Last")
		try:
			doc = frappe.get_doc("Sales Quote", sq.name)
			doc.append("linked_services", {"service_type": "Sea"})
			doc.flags.ignore_mandatory = True
			doc.save(ignore_permissions=True)
			self.assertEqual(len(_linked_service_names_from_db("Sales Quote", sq.name)), 1)

			doc2 = frappe.get_doc("Sales Quote", sq.name)
			doc2.__dict__["linked_services"] = []
			doc2.flags.ignore_mandatory = True
			doc2.save(ignore_permissions=True)

			self.assertEqual(len(_linked_service_names_from_db("Sales Quote", sq.name)), 0)
			reloaded = frappe.get_doc("Sales Quote", sq.name)
			self.assertEqual(len(reloaded.linked_services), 0)
		finally:
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)

	def test_unrelated_save_keeps_linked_services(self):
		"""Saving another field must not drop Services loaded from Linked Service documents."""
		sq = self._minimal_sales_quote("SQ Virtual LS Unrelated Save")
		try:
			doc = frappe.get_doc("Sales Quote", sq.name)
			doc.append("linked_services", {"service_type": "Air"})
			doc.flags.ignore_mandatory = True
			doc.save(ignore_permissions=True)
			self.assertEqual(len(_linked_service_names_from_db("Sales Quote", sq.name)), 1)

			doc2 = frappe.get_doc("Sales Quote", sq.name)
			doc2.description = (doc2.description or "") + " updated"
			doc2.flags.ignore_mandatory = True
			doc2.save(ignore_permissions=True)

			self.assertEqual(len(_linked_service_names_from_db("Sales Quote", sq.name)), 1)
			reloaded = frappe.get_doc("Sales Quote", sq.name)
			self.assertEqual(len(reloaded.linked_services), 1)
		finally:
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)

	def test_clone_linked_service_to_booking(self):
		"""Quote conversion clones Linked Service records onto the booking; quote keeps originals."""
		from logistics.utils.sales_quote_one_off_internal_jobs import (
			propagate_one_off_internal_jobs_to_booking,
		)

		sq = self._minimal_sales_quote("SQ Clone LS To Booking")
		booking = None
		try:
			sq.append("linked_services", {"service_type": "Sea"})
			sq.flags._linked_services_from_form = True
			sync_internal_job_details_to_internal_jobs(sq)
			ls_names = _linked_service_names_from_db("Sales Quote", sq.name)
			self.assertEqual(len(ls_names), 1)
			ls_name = list(ls_names)[0]

			booking = frappe.new_doc("Sea Booking")
			booking.flags.ignore_mandatory = True
			booking.insert(ignore_permissions=True)
			mapping = propagate_one_off_internal_jobs_to_booking(sq, booking)
			self.assertNotEqual(mapping.get(ls_name), ls_name)

			ls = frappe.get_doc(linked_service_doctype(), ls_name)
			self.assertEqual(ls.parent_booking_type, "Sales Quote")
			self.assertEqual(ls.parent_booking_name, sq.name)
			self.assertEqual(len(_linked_service_names_from_db("Sales Quote", sq.name)), 1)

			reloaded_sq = frappe.get_doc("Sales Quote", sq.name)
			self.assertEqual(len(reloaded_sq.linked_services), 1)
		finally:
			if booking and frappe.db.exists("Sea Booking", booking.name):
				frappe.delete_doc("Sea Booking", booking.name, force=True, ignore_permissions=True)
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)
