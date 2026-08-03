# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Integration tests for Linked Service propagation (reuse + Usage tagging)."""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.utils.internal_job_persistence import (
	_linked_service_names_from_db,
	sync_internal_job_details_to_internal_jobs,
)
from logistics.utils.linked_service_compat import linked_service_doctype
from logistics.utils.linked_service_usage import get_linked_services_used_by, get_usages_for_linked_service
from logistics.utils.sales_quote_one_off_internal_jobs import (
	linked_service_names_from_quote_charges,
	propagate_linked_services_and_remap_charges,
	propagate_linked_services_from_sales_quote_to_booking,
)


class TestSalesQuoteLinkedServicePropagation(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("DocType", "Sales Quote"):
			self.skipTest("Sales Quote not installed")
		if not frappe.db.exists("DocType", linked_service_doctype()):
			self.skipTest("Linked Service not installed")
		if not frappe.db.exists("DocType", "Linked Service Usage"):
			self.skipTest("Linked Service Usage not installed")

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
		doc.shipper = frappe.db.get_value("Shipper", {}, "name")
		doc.consignee = frappe.db.get_value("Consignee", {}, "name")
		if not doc.shipper or not doc.consignee:
			self.skipTest("No Shipper/Consignee in system")
		doc.date = frappe.utils.today()
		doc.valid_until = frappe.utils.add_days(frappe.utils.today(), 30)
		# Required for Sea Regular/One-off validation on insert/save.
		# Export: origin must be in company country (PH); destination abroad.
		origin = (
			frappe.db.get_value("UNLOCO", {"is_active": 1, "name": ("like", "PH%")}, "name")
			or "PHMNL"
		)
		dest = (
			frappe.db.get_value(
				"UNLOCO", {"is_active": 1, "name": ("not like", "PH%")}, "name"
			)
			or "USLAX"
		)
		doc.origin_port = origin
		doc.destination_port = dest
		doc.direction = "Export"
		if hasattr(doc, "origin_port_sea"):
			doc.origin_port_sea = origin
		if hasattr(doc, "destination_port_sea"):
			doc.destination_port_sea = dest
		doc.flags.ignore_validate = True
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True)
		return doc

	def test_reuse_keeps_quote_owned_linked_service(self):
		sq = self._minimal_sales_quote("SQ Reuse LS", quotation_type="Regular")
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
				sq, booking, clone=False, ls_names=[ls_name]
			)
			self.assertEqual(mapping.get(ls_name), ls_name)
			self.assertEqual(len(_linked_service_names_from_db("Sales Quote", sq.name)), 1)
			self.assertEqual(
				frappe.db.get_value(linked_service_doctype(), ls_name, "parent_booking_name"),
				sq.name,
			)
			self.assertEqual(get_linked_services_used_by("Sea Booking", booking.name), [ls_name])
			usages = get_usages_for_linked_service(ls_name)
			self.assertEqual(len(usages), 1)
			self.assertEqual(usages[0]["used_on_doctype"], "Sea Booking")
			self.assertEqual(usages[0]["used_on_name"], booking.name)
		finally:
			if booking and frappe.db.exists("Sea Booking", booking.name):
				frappe.delete_doc("Sea Booking", booking.name, force=True, ignore_permissions=True)
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)

	def test_regular_full_conversion_reuses_linked_services(self):
		"""Regular quote → booking reuses quote-owned LS IDs and records Usage."""
		from logistics.pricing_center.doctype.sales_quote.sales_quote import (
			_propagate_linked_services_to_created_booking,
		)

		sq = self._minimal_sales_quote("SQ Regular Reuse", quotation_type="Regular")
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
			# Booking does not own a clone; Usage points at the quote IJ.
			self.assertEqual(len(_linked_service_names_from_db("Sea Booking", booking.name)), 0)
			self.assertEqual(get_linked_services_used_by("Sea Booking", booking.name), [ls_name])
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

	def test_regular_propagates_all_services_when_only_one_charge_tagged(self):
		"""All Services grid rows are tagged on the booking even if only one charge is Linked."""
		sq = self._minimal_sales_quote("SQ Regular All LS", quotation_type="Regular")
		booking = None
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
			# No save required — propagation reads quote-owned Linked Services directly.

			booking = frappe.new_doc("Sea Booking")
			booking.sales_quote = sq.name
			booking.flags.ignore_mandatory = True
			booking.insert(ignore_permissions=True)
			propagate_linked_services_from_sales_quote_to_booking(sq, booking)

			used = set(get_linked_services_used_by("Sea Booking", booking.name))
			self.assertEqual(used, set(ls_names))
			self.assertEqual(len(_linked_service_names_from_db("Sales Quote", sq.name)), 2)
			self.assertEqual(len(_linked_service_names_from_db("Sea Booking", booking.name)), 0)
		finally:
			if booking and frappe.db.exists("Sea Booking", booking.name):
				frappe.delete_doc("Sea Booking", booking.name, force=True, ignore_permissions=True)
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)

	def test_multi_transport_legs_all_tagged_on_booking(self):
		"""Multiple Transport Linked Services are all reused (no one-per-service-type skip)."""
		sq = self._minimal_sales_quote("SQ Multi Transport", quotation_type="Regular")
		booking = None
		try:
			for _ in range(3):
				sq.append("linked_services", {"service_type": "Transport"})
			sq.flags._linked_services_from_form = True
			sync_internal_job_details_to_internal_jobs(sq)
			ls_names = list(_linked_service_names_from_db("Sales Quote", sq.name))
			self.assertEqual(len(ls_names), 3)

			booking = frappe.new_doc("Sea Booking")
			booking.sales_quote = sq.name
			booking.flags.ignore_mandatory = True
			booking.insert(ignore_permissions=True)
			mapping = propagate_linked_services_from_sales_quote_to_booking(sq, booking)
			self.assertEqual(len(mapping), 3)
			for ls in ls_names:
				self.assertEqual(mapping.get(ls), ls)

			used = get_linked_services_used_by("Sea Booking", booking.name)
			self.assertEqual(sorted(used), sorted(ls_names))
		finally:
			if booking and frappe.db.exists("Sea Booking", booking.name):
				frappe.delete_doc("Sea Booking", booking.name, force=True, ignore_permissions=True)
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)

	def test_one_off_sea_booking_conversion_populates_linked_services(self):
		"""End-to-end: Create > Sea Booking reuses subsidiary services via Usage."""
		from logistics.pricing_center.doctype.sales_quote.sales_quote import (
			create_sea_booking_from_sales_quote,
		)
		from logistics.logistics.doctype.linked_service.linked_service import (
			get_linked_services_for_booking,
		)

		sq = self._minimal_sales_quote("SQ One-off Sea LS", quotation_type="One-off")
		sbk_name = None
		try:
			sq.direction = "Export"
			sq.append(
				"charges",
				{
					"service_type": "Sea",
					"origin_port": sq.origin_port,
					"destination_port": sq.destination_port,
					"direction": "Export",
				},
			)
			sq.append("linked_services", {"service_type": "Transport"})
			sq.append("linked_services", {"service_type": "Customs"})
			sq.flags._linked_services_from_form = True
			sq.flags.ignore_mandatory = True
			sq.save(ignore_permissions=True)
			quote_ls = list(_linked_service_names_from_db("Sales Quote", sq.name))
			self.assertEqual(len(quote_ls), 2)

			result = create_sea_booking_from_sales_quote(sq.name)
			self.assertTrue(result.get("success"))
			sbk_name = result.get("sea_booking")
			self.assertTrue(sbk_name)

			rows = get_linked_services_for_booking("Sea Booking", sbk_name)
			self.assertEqual(len(rows), 2)
			service_types = {getattr(r, "service_type", None) for r in rows}
			self.assertEqual(service_types, {"Transport", "Customs"})
			self.assertEqual(len(_linked_service_names_from_db("Sales Quote", sq.name)), 2)
			# Same IJ names reused on the booking.
			self.assertEqual(
				sorted(get_linked_services_used_by("Sea Booking", sbk_name)),
				sorted(quote_ls),
			)
		finally:
			if sbk_name and frappe.db.exists("Sea Booking", sbk_name):
				frappe.delete_doc("Sea Booking", sbk_name, force=True, ignore_permissions=True)
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)
