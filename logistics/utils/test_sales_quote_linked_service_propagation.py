# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Integration tests for Linked Service propagation (clone + re-parent)."""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.utils.internal_job_persistence import (
	_linked_service_names_from_db,
	sync_internal_job_details_to_internal_jobs,
)
from logistics.utils.linked_service_compat import linked_service_doctype
from logistics.utils.sales_quote_one_off_internal_jobs import (
	linked_service_names_from_quote_charges,
	propagate_linked_services_and_remap_charges,
)


class TestSalesQuoteLinkedServicePropagation(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("DocType", "Sales Quote"):
			self.skipTest("Sales Quote not installed")
		if not frappe.db.exists("DocType", linked_service_doctype()):
			self.skipTest("Linked Service not installed")

	def _minimal_sales_quote(self, title: str, *, quotation_type="Regular"):
		doc = frappe.new_doc("Sales Quote")
		doc.quotation_type = quotation_type
		doc.main_service = "Sea"
		doc.naming_series = "SQU.#########" if quotation_type == "Regular" else "OOQ.#####"
		if quotation_type == "Project":
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

	def test_clone_keeps_quote_owned_linked_service(self):
		sq = self._minimal_sales_quote("SQ Clone LS", quotation_type="Regular")
		booking = None
		try:
			sq.append("linked_services", {"service_type": "Transport"})
			sq.flags._linked_services_from_form = True
			sync_internal_job_details_to_internal_jobs(sq)
			ls_name = list(_linked_service_names_from_db("Sales Quote", sq.name))[0]

			booking = frappe.new_doc("Sea Booking")
			booking.flags.ignore_mandatory = True
			booking.insert(ignore_permissions=True)
			mapping = propagate_linked_services_and_remap_charges(
				sq, booking, clone=True, ls_names=[ls_name]
			)
			self.assertNotEqual(mapping.get(ls_name), ls_name)
			self.assertEqual(len(_linked_service_names_from_db("Sales Quote", sq.name)), 1)
			self.assertEqual(
				frappe.db.get_value(linked_service_doctype(), ls_name, "parent_booking_name"),
				sq.name,
			)
			clone_name = mapping[ls_name]
			self.assertEqual(
				frappe.db.get_value(linked_service_doctype(), clone_name, "parent_booking_name"),
				booking.name,
			)
		finally:
			if booking and frappe.db.exists("Sea Booking", booking.name):
				frappe.delete_doc("Sea Booking", booking.name, force=True, ignore_permissions=True)
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)

	def test_regular_full_conversion_clones_linked_services(self):
		"""Regular quote → booking uses clone so quote-owned LS records stay on the quote."""
		from logistics.pricing_center.doctype.sales_quote.sales_quote import (
			_propagate_linked_services_to_created_booking,
		)

		sq = self._minimal_sales_quote("SQ Regular Clone", quotation_type="Regular")
		booking = None
		try:
			sq.append("linked_services", {"service_type": "Transport"})
			sq.flags._linked_services_from_form = True
			sync_internal_job_details_to_internal_jobs(sq)
			ls_name = list(_linked_service_names_from_db("Sales Quote", sq.name))[0]

			booking = frappe.new_doc("Sea Booking")
			booking.sales_quote = sq.name
			booking.flags.ignore_mandatory = True
			booking.insert(ignore_permissions=True)
			_propagate_linked_services_to_created_booking(sq, booking, blanket_call_off=False)
			self.assertEqual(len(_linked_service_names_from_db("Sales Quote", sq.name)), 1)
			self.assertEqual(
				frappe.db.get_value(linked_service_doctype(), ls_name, "parent_booking_name"),
				sq.name,
			)
		finally:
			if booking and frappe.db.exists("Sea Booking", booking.name):
				frappe.delete_doc("Sea Booking", booking.name, force=True, ignore_permissions=True)
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)

	def test_linked_service_names_from_quote_charges_filters_by_row_name(self):
		sq = self._minimal_sales_quote("SQ Charge LS Filter")
		try:
			sq.append("linked_services", {"service_type": "Transport"})
			sq.append("linked_services", {"service_type": "Customs"})
			sq.flags._linked_services_from_form = True
			sync_internal_job_details_to_internal_jobs(sq)
			ls_names = list(_linked_service_names_from_db("Sales Quote", sq.name))
			self.assertEqual(len(ls_names), 2)
			sq.append(
				"charges",
				{
					"service_type": "Sea",
					"charge_scope": "Linked",
					"linked_service": ls_names[0],
				},
			)
			ch_row = sq.charges[-1]
			found = linked_service_names_from_quote_charges(sq, [ch_row.name])
			self.assertEqual(found, [ls_names[0]])
		finally:
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)
