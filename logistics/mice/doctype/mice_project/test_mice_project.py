# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from logistics.mice.doctype.mice_project.mice_project import (
	get_linkable_dockets_for_exhibit,
	get_sales_quote_defaults_from_exhibit,
	link_dockets_to_exhibit,
)
from logistics.mice.mice_project_lifecycle import LIFECYCLE_STAGES, get_standard_exhibit_activities


class TestShow(IntegrationTestCase):
	def _test_customer(self):
		return frappe.db.get_value("Customer", {}, "name")

	def _test_organizer(self, name_hint="Test Organizer"):
		"""Return (or create) a MICE Organizer linked to an arbitrary Customer."""
		customer = self._test_customer()
		if not customer:
			return None
		existing = frappe.db.get_value(
			"MICE Organizer", {"organizer_name": name_hint}, "name"
		)
		if existing:
			return existing
		doc = frappe.new_doc("MICE Organizer")
		doc.organizer_name = name_hint
		doc.organizer_type = "Company"
		doc.customer = customer
		doc.insert(ignore_permissions=True)
		return doc.name

	def _minimal_exhibit(self, project_name="Test Exhibit"):
		organizer = self._test_organizer()
		if not organizer:
			self.skipTest("No Customer in system (organizer needs a backing Customer)")
		doc = frappe.new_doc("MICE Project")
		doc.project_name = project_name
		doc.organizer = organizer
		doc.show_open_date = today()
		doc.show_close_date = add_days(today(), 3)
		doc.insert(ignore_permissions=True)
		return doc

	def _minimal_docket(self, exhibit, exhibitor=None):
		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket DocType not installed")
		exhibitor = exhibitor or self._test_customer()
		if not exhibitor:
			self.skipTest("No Customer in system")
		dk = frappe.new_doc("Docket")
		dk.exhibit = exhibit
		dk.exhibitor = exhibitor
		dk.flags.ignore_mandatory = True
		dk.insert(ignore_permissions=True)
		return dk
	def test_save_with_virtual_dockets_does_not_fail_version(self):
		"""Regression: virtual dockets grid must not break Version diff on save."""
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit DocType not installed")
		doc = self._minimal_exhibit("Test Virtual Dockets Save")
		try:
			doc = frappe.get_doc("MICE Project", doc.name)
			self.assertIsInstance(doc.get("dockets"), list)
			doc.description = (doc.description or "") + " updated"
			doc.save(ignore_permissions=True)
		finally:
			doc.delete(ignore_permissions=True)

	def test_standard_activities_loaded_on_insert(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit DocType not installed")
		organizer = self._test_organizer("Test Org Activities")
		if not organizer:
			self.skipTest("No Customer in system")
		doc = frappe.new_doc("MICE Project")
		doc.project_name = "Test Exhibit Details"
		doc.organizer = organizer
		doc.insert(ignore_permissions=True)
		lifecycle_jobs = [r for r in doc.lifecycle_jobs if r.activity_code]
		self.assertEqual(len(lifecycle_jobs), len(get_standard_exhibit_activities()))
		self.assertEqual(doc.lifecycle_stage, "Pre-Show")
		doc.delete(ignore_permissions=True)

	def test_phase_orders_created_on_approval(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit DocType not installed")
		frappe.db.set_single_value("MICE Settings", "auto_create_phase_orders", 1)
		organizer = self._test_organizer("Test Org Phase Orders")
		if not organizer:
			self.skipTest("No Customer in system")
		doc = frappe.new_doc("MICE Project")
		doc.project_name = "Test Phase Orders"
		doc.organizer = organizer
		doc.insert(ignore_permissions=True)
		doc.status = "Approved"
		doc.save(ignore_permissions=True)
		orders = frappe.get_all(
			"MICE Order",
			filters={"exhibit": doc.name},
			pluck="lifecycle_stage",
		)
		for stage in LIFECYCLE_STAGES[:-1]:
			self.assertIn(stage, orders)
		doc.delete(ignore_permissions=True)

	def test_get_sales_quote_defaults_from_exhibit(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit DocType not installed")
		organizer = self._test_organizer("Test Org SQ Defaults")
		if not organizer:
			self.skipTest("No Customer in system")
		doc = frappe.new_doc("MICE Project")
		doc.project_name = "Test SQ Defaults Exhibit"
		doc.organizer = organizer
		doc.show_open_date = today()
		doc.show_close_date = add_days(today(), 3)
		doc.priority = "High"
		doc.description = "Test exhibit description"
		doc.insert(ignore_permissions=True)
		try:
			defaults = get_sales_quote_defaults_from_exhibit(doc.name, None)
			self.assertEqual(defaults["exhibit"], doc.name)
			self.assertNotIn("customer", defaults)
			self.assertEqual(defaults["main_service"], "MICE")
			self.assertEqual(defaults["quotation_type"], "Project")
			self.assertEqual(defaults["naming_series"], "PQ.#####")
			self.assertEqual(defaults["exhibit_show_open_date"], str(doc.show_open_date))
			self.assertEqual(defaults["exhibit_show_close_date"], str(doc.show_close_date))
			self.assertEqual(defaults["priority"], "High")
			self.assertEqual(defaults["description"], doc.description)
		finally:
			doc.delete(ignore_permissions=True)

	def test_link_dockets_to_exhibit_sets_exhibit_field(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit DocType not installed")
		target = self._minimal_exhibit("Test Link Target")
		source_exhibit = self._minimal_exhibit("Test Link Source")
		# Resolve the target's billing Customer via the linked Organizer (MICE
		# Project no longer carries a customer link directly).
		target_customer = (
			frappe.db.get_value("MICE Organizer", target.organizer, "customer")
			if target.organizer
			else None
		)
		other_exhibitor = (
			frappe.db.get_value("Customer", {"name": ["!=", target_customer]}, "name")
			if target_customer
			else None
		) or target_customer or self._test_customer()
		dk = self._minimal_docket(source_exhibit.name, other_exhibitor)
		try:
			result = link_dockets_to_exhibit(target.name, [dk.name])
			self.assertEqual(len(result["linked"]), 1)
			self.assertEqual(frappe.db.get_value("Docket", dk.name, "exhibit"), target.name)
		finally:
			dk.delete(ignore_permissions=True)
			source_exhibit.delete(ignore_permissions=True)
			target.delete(ignore_permissions=True)

	def test_link_dockets_rejects_duplicate_exhibitor_on_exhibit(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit DocType not installed")
		target = self._minimal_exhibit("Test Dup Exhibitor Target")
		other_exhibit = self._minimal_exhibit("Test Dup Exhibitor Other")
		exhibitor = self._test_customer()
		first = self._minimal_docket(target.name, exhibitor)
		second = self._minimal_docket(other_exhibit.name, exhibitor)
		try:
			result = link_dockets_to_exhibit(target.name, [second.name])
			self.assertEqual(len(result["linked"]), 0)
			self.assertTrue(result["errors"])
		finally:
			second.delete(ignore_permissions=True)
			first.delete(ignore_permissions=True)
			other_exhibit.delete(ignore_permissions=True)
			target.delete(ignore_permissions=True)

	def test_get_linkable_dockets_includes_only_on_exhibit(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit DocType not installed")
		exhibit = self._minimal_exhibit("Test Linkable List")
		other_exhibit = self._minimal_exhibit("Test Linkable Other")
		exhibitor = self._test_customer()
		on_exhibit = self._minimal_docket(exhibit.name, exhibitor)
		other_exhibitor = frappe.db.get_value(
			"Customer", {"name": ["!=", exhibitor]}, "name"
		) or exhibitor
		on_other = self._minimal_docket(other_exhibit.name, other_exhibitor)
		unlinked = frappe.new_doc("Docket")
		unlinked.exhibitor = other_exhibitor
		unlinked.flags.ignore_mandatory = True
		unlinked.insert(ignore_permissions=True)
		try:
			rows = get_linkable_dockets_for_exhibit(exhibit.name)
			names = [r["name"] for r in rows]
			self.assertIn(on_exhibit.name, names)
			self.assertNotIn(on_other.name, names)
			self.assertNotIn(unlinked.name, names)
			for row in rows:
				self.assertEqual(row.get("row_type"), "eligible")
		finally:
			unlinked.delete(ignore_permissions=True)
			on_other.delete(ignore_permissions=True)
			on_exhibit.delete(ignore_permissions=True)
			other_exhibit.delete(ignore_permissions=True)
			exhibit.delete(ignore_permissions=True)

	def test_get_linkable_dockets_respects_exclude_list(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit DocType not installed")
		exhibit = self._minimal_exhibit("Test Linkable Exclude")
		exhibitor = self._test_customer()
		dk = self._minimal_docket(exhibit.name, exhibitor)
		try:
			rows = get_linkable_dockets_for_exhibit(
				exhibit.name, exclude_dockets=[dk.name]
			)
			names = [r["name"] for r in rows]
			self.assertNotIn(dk.name, names)
			rows_all = get_linkable_dockets_for_exhibit(exhibit.name)
			self.assertIn(dk.name, [r["name"] for r in rows_all])
		finally:
			dk.delete(ignore_permissions=True)
			exhibit.delete(ignore_permissions=True)
