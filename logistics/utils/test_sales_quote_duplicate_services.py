# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for Copy Quotation Services on Sales Quote duplicate."""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.pricing_center.doctype.sales_quote.sales_quote import (
	_clone_sales_quote_linked_services,
	_remap_sales_quote_charges_from_duplicate_source,
	copy_quotation_services_from_duplicate_source,
)
from logistics.utils.internal_job_persistence import (
	_linked_service_names_from_db,
	sync_internal_job_details_to_internal_jobs,
)
from logistics.utils.linked_service_compat import (
	CHARGE_SCOPE_LINKED,
	charge_row_linked_service_link,
	linked_service_doctype,
)


class TestSalesQuoteDuplicateServices(FrappeTestCase):
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

	def _add_linked_service(self, sq, service_type: str):
		sq.append("linked_services", {"service_type": service_type})
		sq.flags._linked_services_from_form = True
		sync_internal_job_details_to_internal_jobs(sq)
		names = _linked_service_names_from_db("Sales Quote", sq.name)
		self.assertTrue(names)
		return names[0]

	def test_clone_sales_quote_linked_services_creates_new_docs(self):
		source = self._minimal_sales_quote("SQ Dup Services Source")
		target = self._minimal_sales_quote("SQ Dup Services Target")
		try:
			ls1 = self._add_linked_service(source, "Sea")
			ls2 = self._add_linked_service(source, "Air")
			source_names = set(_linked_service_names_from_db("Sales Quote", source.name))

			mapping = _clone_sales_quote_linked_services(source.name, target.name)
			self.assertEqual(len(mapping), 2)
			self.assertIn(ls1, mapping)
			self.assertIn(ls2, mapping)

			target_names = set(_linked_service_names_from_db("Sales Quote", target.name))
			self.assertEqual(len(target_names), 2)
			self.assertTrue(target_names.isdisjoint(source_names))

			for ls_name in target_names:
				ls = frappe.get_doc(linked_service_doctype(), ls_name)
				self.assertEqual(ls.parent_booking_type, "Sales Quote")
				self.assertEqual(ls.parent_booking_name, target.name)

			self.assertEqual(
				set(_linked_service_names_from_db("Sales Quote", source.name)), source_names
			)
		finally:
			for name in (source.name, target.name):
				if frappe.db.exists("Sales Quote", name):
					frappe.delete_doc("Sales Quote", name, force=True, ignore_permissions=True)

	def test_remap_sales_quote_charges_from_duplicate_source(self):
		source = self._minimal_sales_quote("SQ Dup Charge Source")
		target = self._minimal_sales_quote("SQ Dup Charge Target")
		try:
			source_ls = self._add_linked_service(source, "Sea")
			mapping = _clone_sales_quote_linked_services(source.name, target.name)
			target_ls = mapping[source_ls]

			source.reload()
			source.append(
				"charges",
				{
					"service_type": "Sea",
					"charge_scope": CHARGE_SCOPE_LINKED,
					"linked_service": source_ls,
					"item_code": frappe.db.get_value("Item", {"is_stock_item": 0}, "name"),
				},
			)
			source.flags.ignore_mandatory = True
			source.save(ignore_permissions=True)

			target.reload()
			target.append(
				"charges",
				{
					"service_type": "Sea",
					"charge_scope": "Main",
					"item_code": source.charges[0].item_code,
				},
			)
			target.flags.ignore_mandatory = True
			target.save(ignore_permissions=True)

			_remap_sales_quote_charges_from_duplicate_source(target, source.name, mapping)
			target_row = target.charges[0]
			self.assertEqual(target_row.charge_scope, CHARGE_SCOPE_LINKED)
			self.assertEqual(charge_row_linked_service_link(target_row), target_ls)
		finally:
			for name in (source.name, target.name):
				if frappe.db.exists("Sales Quote", name):
					frappe.delete_doc("Sales Quote", name, force=True, ignore_permissions=True)

	def test_copy_quotation_services_from_duplicate_source(self):
		source = self._minimal_sales_quote("SQ Dup Copy Source")
		target = self._minimal_sales_quote("SQ Dup Copy Target")
		try:
			self._add_linked_service(source, "Sea")
			self._add_linked_service(source, "Transport")
			frappe.db.set_value(
				"Sales Quote",
				target.name,
				"logistics_duplicate_from",
				source.name,
				update_modified=False,
			)

			result = copy_quotation_services_from_duplicate_source(target.name)
			self.assertTrue(result["success"])
			self.assertEqual(result["copied_count"], 2)
			self.assertFalse(
				frappe.db.get_value("Sales Quote", target.name, "logistics_duplicate_from")
			)
			self.assertEqual(len(_linked_service_names_from_db("Sales Quote", target.name)), 2)
		finally:
			for name in (source.name, target.name):
				if frappe.db.exists("Sales Quote", name):
					frappe.delete_doc("Sales Quote", name, force=True, ignore_permissions=True)

	def test_copy_quotation_services_rejects_missing_duplicate_source(self):
		target = self._minimal_sales_quote("SQ Dup No Marker")
		try:
			with self.assertRaises(frappe.ValidationError):
				copy_quotation_services_from_duplicate_source(target.name)
		finally:
			frappe.delete_doc("Sales Quote", target.name, force=True, ignore_permissions=True)

	def test_copy_quotation_services_rejects_when_services_already_exist(self):
		source = self._minimal_sales_quote("SQ Dup Idem Source")
		target = self._minimal_sales_quote("SQ Dup Idem Target")
		try:
			self._add_linked_service(source, "Air")
			self._add_linked_service(target, "Sea")
			frappe.db.set_value(
				"Sales Quote",
				target.name,
				"logistics_duplicate_from",
				source.name,
				update_modified=False,
			)
			with self.assertRaises(frappe.ValidationError):
				copy_quotation_services_from_duplicate_source(target.name)
		finally:
			for name in (source.name, target.name):
				if frappe.db.exists("Sales Quote", name):
					frappe.delete_doc("Sales Quote", name, force=True, ignore_permissions=True)
