# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from logistics.exhibits.doctype.docket.docket import get_recommended_booth_numbers


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestDocket(IntegrationTestCase):
	"""
	Integration tests for Docket.
	Use this class for testing interactions between multiple components.
	"""

	def _test_customer(self):
		return frappe.db.get_value("Customer", {}, "name")

	def _minimal_exhibit(self, project_name="Test Exhibit"):
		customer = self._test_customer()
		if not customer:
			self.skipTest("No Customer in system")
		doc = frappe.new_doc("Exhibit")
		doc.project_name = project_name
		doc.customer = customer
		doc.show_open_date = today()
		doc.show_close_date = add_days(today(), 3)
		doc.insert(ignore_permissions=True)
		return doc

	def _minimal_docket(self, exhibit, exhibitor=None, booth_no=None, docstatus=0):
		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket DocType not installed")
		exhibitor = exhibitor or self._test_customer()
		if not exhibitor:
			self.skipTest("No Customer in system")
		dk = frappe.new_doc("Docket")
		dk.exhibit = exhibit
		dk.exhibitor = exhibitor
		if booth_no is not None:
			dk.booth_no = booth_no
		dk.flags.ignore_mandatory = True
		dk.insert(ignore_permissions=True)
		if docstatus == 2:
			dk.cancel()
		return dk

	def test_booth_no_unique_per_exhibit_including_cancelled(self):
		if not frappe.db.exists("DocType", "Exhibit"):
			self.skipTest("Exhibit DocType not installed")
		exhibit = self._minimal_exhibit("Test Booth Unique Exhibit")
		try:
			d1 = self._minimal_docket(exhibit.name, booth_no="HALL3-09")
			self.addCleanup(lambda: d1.delete(ignore_permissions=True))

			# Cancel the first docket; booth should still be blocked for reuse.
			d1.cancel()

			d2 = frappe.new_doc("Docket")
			d2.exhibit = exhibit.name
			d2.exhibitor = self._test_customer()
			d2.booth_no = "HALL3-09"
			d2.flags.ignore_mandatory = True
			with self.assertRaises(frappe.ValidationError):
				d2.insert(ignore_permissions=True)
		finally:
			exhibit.delete(ignore_permissions=True)

	def test_booking_creation_persists_job_no_on_internal_jobs_row(self):
		"""Create > Booking/Order must write job_no on the Internal Jobs child row and backing Internal Job."""
		if not frappe.db.exists("DocType", "Exhibit"):
			self.skipTest("Exhibit DocType not installed")
		exhibit = self._minimal_exhibit("Test Docket IJ Persist Exhibit")
		dk = None
		booking_name = None
		try:
			dk = self._minimal_docket(exhibit.name)
			dk.append("internal_jobs", {"service_type": "Air"})
			dk.save(ignore_permissions=True)

			from logistics.exhibits.doctype.docket.docket_booking_creation import (
				create_booking_or_order_from_docket,
			)

			result = create_booking_or_order_from_docket(
				docket=dk.name,
				job_type="Air Booking",
				internal_job_idx=1,
			)
			booking_name = result.get("air_booking")
			self.assertTrue(booking_name)

			row = frappe.db.get_value(
				"Internal Job Detail",
				{"parent": dk.name, "parenttype": "Docket", "parentfield": "internal_jobs"},
				["job_type", "job_no", "internal_job"],
				as_dict=True,
			)
			self.assertEqual(row.job_type, "Air Booking")
			self.assertEqual(row.job_no, booking_name)
			self.assertTrue(row.internal_job)
			ij_job_no = frappe.db.get_value("Internal Job", row.internal_job, "job_no")
			self.assertEqual(ij_job_no, booking_name)
		finally:
			if booking_name and frappe.db.exists("Air Booking", booking_name):
				frappe.delete_doc("Air Booking", booking_name, force=True, ignore_permissions=True)
			if dk and dk.name and frappe.db.exists("Docket", dk.name):
				dk.delete(ignore_permissions=True)
			exhibit.delete(ignore_permissions=True)

	def test_get_recommended_booth_numbers_increments_last_number_and_pages(self):
		if not frappe.db.exists("DocType", "Exhibit"):
			self.skipTest("Exhibit DocType not installed")
		exhibit = self._minimal_exhibit("Test Booth Suggest Exhibit")
		try:
			seed = self._minimal_docket(exhibit.name, booth_no="HALL3-09")
			self.addCleanup(lambda: seed.delete(ignore_permissions=True))

			# Mark a couple as used so recommender skips them.
			used1 = self._minimal_docket(exhibit.name, exhibitor=self._test_customer(), booth_no="HALL3-10")
			self.addCleanup(lambda: used1.delete(ignore_permissions=True))
			used2 = self._minimal_docket(exhibit.name, exhibitor=self._test_customer(), booth_no="HALL3-12")
			self.addCleanup(lambda: used2.delete(ignore_permissions=True))

			r1 = get_recommended_booth_numbers(exhibit.name, start=0, limit=10)
			s1 = r1.get("suggestions") or []
			self.assertTrue(s1)
			self.assertNotIn("HALL3-10", s1)
			self.assertNotIn("HALL3-12", s1)
			self.assertEqual(s1[0], "HALL3-11")  # 10 used; next is 11

			next_start = r1.get("next_start")
			r2 = get_recommended_booth_numbers(exhibit.name, start=next_start, limit=10)
			s2 = r2.get("suggestions") or []
			self.assertTrue(s2)
			# Ensure paging advances (no overlap at start of list)
			self.assertNotEqual(s1[0], s2[0])
		finally:
			exhibit.delete(ignore_permissions=True)
